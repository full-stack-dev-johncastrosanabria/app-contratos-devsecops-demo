import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

import httpx2
from anthropic import AsyncAnthropic
from openai import AsyncAzureOpenAI

from assessment.analytics import build_powerbi_metrics, render_powerbi_csv
from assessment.ci import matches_expected
from assessment.demo_reset import execute_demo_reset, restore_latest_archive
from assessment.evidence import APP, CRITERION, PROJECT, collect, read_cobertura
from assessment.integrations import audit_repo_governance, parse_boards_criteria
from assessment.policy import evaluate, evaluate_criteria_matrix, source_tests
from assessment.remediation import (
    apply_local_remediation,
    close_github_remediation_prs,
    create_github_remediation_pr,
    generate_remediation,
    revert_local_remediation,
)
from assessment.workflow import (
    AZURE_KEYS,
    AnthropicClient,
    DecisionAlreadyResolved,
    OpenAIChatCompletionClient,
    Request,
    build_eight_stages,
    reopen_governance_decision,
    resolve_boards_closure,
    resolve_human_decision,
    run,
)

ROOT = Path(__file__).resolve().parents[2]


def copy_version(source: Path, root: Path) -> None:
    for path in (APP, PROJECT.parent):
        shutil.copytree(source / path, root / path, ignore=shutil.ignore_patterns("bin", "obj", "TestResults"))


class CollectionErrors(unittest.TestCase):
    def test_absent_or_invalid_trx_and_old_report(self):
        for report, diagnostic in [(None, "TRX_AUSENTE"), ("<rota", "TRX_INVALIDO"),
                                   ("<TestRun/>", "TRX_INVALIDO")]:
            with self.subTest(report=report), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp)
                (output / "resultados.trx").write_text("TRX de otra ejecución", encoding="utf-8")

                def fake_dotnet(cmd, **kwargs):
                    directory = Path(cmd[cmd.index("--results-directory") + 1])
                    self.assertIn("-p:ContinuousIntegrationBuild=false", cmd)
                    self.assertEqual(kwargs["env"].get("DOTNET_CLI_UI_LANGUAGE"), "en")
                    self.assertEqual(kwargs["env"].get("VSLANG"), "1033")
                    self.assertEqual(kwargs["env"].get("LC_MESSAGES"), "C")
                    self.assertNotIn("ANTHROPIC_API_KEY", kwargs["env"])
                    self.assertNotEqual(directory, output)
                    self.assertFalse((directory / "resultados.trx").exists())
                    if report:
                        (directory / "resultados.trx").write_text(report, encoding="utf-8")
                    else:
                        kwargs["stdout"].write(b"Program.cs(1,1): error CS1002: ; expected\n")
                    return subprocess.CompletedProcess(cmd, 1)

                real_run = subprocess.run
                with (patch.dict(os.environ, {"ANTHROPIC_API_KEY": "secret-should-not-leak"}),
                      patch("assessment.evidence.subprocess.run",
                            side_effect=lambda cmd, **kw: fake_dotnet(cmd, **kw) if cmd[0] == "dotnet" else real_run(cmd, **kw))):
                    evidence = collect(ROOT / "v1", output)
                codes = {item["codigo"] for item in evidence.diagnostics}
                self.assertIn(diagnostic, codes)
                if report is None:
                    self.assertIn("ERROR_COMPILACION_O_RESTAURACION", codes)
                self.assertEqual(evidence.results, [])
                self.assertEqual(evaluate(evidence, source_tests(evidence.sources))["veredicto"], "EVIDENCIA_INSUFICIENTE")


@unittest.skipUnless(shutil.which("dotnet"), "requiere dotnet")
class DotnetIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.directory = Path(tmp.name)
        cls.renamed = cls.directory / "carpeta-sin-numero"
        copy_version(ROOT / "v2", cls.renamed)
        cls.failed = collect(cls.renamed, cls.directory / "runs")

    def test_renamed_project_keeps_functional_failure(self):
        evidence = self.failed
        verdict = evaluate(evidence, source_tests(evidence.sources))
        self.assertEqual(evidence.identity["version"], "carpeta-sin-numero")
        self.assertEqual(evidence.identity["codigo_dotnet"], 1)
        self.assertTrue(evidence.identity["sha256_archivos"])
        self.assertEqual(verdict["veredicto"], "INCUMPLIDO")
        theories = [row for row in evidence.results if row.method.endswith(".ActivoGeneraUnSoloAviso")]
        self.assertEqual(len({row.execution_id for row in theories}), 3)
        self.assertEqual(len({row.name for row in theories}), 3)

    def test_unrelated_exception_and_ambiguous_or_skipped_result(self):
        target = next(row for row in self.failed.results if row.outcome == "Failed")
        for rows in ([replace(target, error="System.InvalidOperationException: otro problema")],
                     [replace(target, stack=target.stack.replace(":line 26", ":line 24"))],
                     [target, replace(target, execution_id="duplicado")],
                     [replace(target, outcome="NotExecuted")]):
            with self.subTest(rows=rows):
                evidence = replace(self.failed, results=rows, diagnostics=[])
                verdict = evaluate(evidence, source_tests(evidence.sources))
                self.assertEqual(verdict["veredicto"], "EVIDENCIA_INSUFICIENTE")
                if len(rows) == 1 and rows[0].outcome == "Failed":
                    self.assertEqual(evidence.diagnostics[0]["codigo"], "RESULTADO_DEL_CASO_NO_CONCLUYENTE")

    def test_explicit_link_alone_does_not_cover_cancellation(self):
        evidence = replace(self.failed, results=[replace(row, outcome="Passed") for row in self.failed.results])
        sources = {path: code.replace("Caso(true, 7)", "Caso(false, 7)") for path, code in evidence.sources.items()}
        verdict = evaluate(evidence, source_tests(sources))
        self.assertTrue(verdict["referencias"][0]["vinculada"])
        self.assertEqual(verdict["veredicto"], "EVIDENCIA_INSUFICIENTE")

    def test_ci_only_accepts_the_known_v2_failure(self):
        self.assertTrue(matches_expected(self.failed, "v2"))
        for rows in (
            [replace(row, error="Error ajeno a REN-001") for row in self.failed.results],
            [replace(row, outcome="Failed") for row in self.failed.results],
        ):
            with self.subTest(rows=rows):
                self.assertFalse(matches_expected(replace(self.failed, results=rows, diagnostics=[]), "v2"))

    def test_real_maf_tool_dispatch_with_stubbed_azure_http(self):
        evidence = self.failed
        test = next(test for test in source_tests(evidence.sources) if test.linked)
        result = next(row for row in evidence.results if row.method == test.method)
        pending = iter([
            ("buscar_pruebas_vinculadas", {}),
            ("inspeccionar_prueba", {"prueba": test.ref}),
            ("listar_resultados", {}),
        ])
        observed = []

        def reply(request):
            body = json.loads(request.content)
            observed.append(body)
            message = {"role": "assistant"}
            if tool := next(pending, None):
                name, args = tool
                message["tool_calls"] = [{"id": f"call_{len(observed)}", "type": "function",
                                          "function": {"name": name, "arguments": json.dumps(args)}}]
                reason = "tool_calls"
            else:
                message["content"] = json.dumps({
                    "explicacion": "Comparé la aserción con el fallo del TRX.",
                    "referencias": [{"prueba": test.ref, "ejecuciones": [result.execution_id]},
                                    {"prueba": "../otro.cs:1", "ejecuciones": [result.execution_id]}],
                })
                reason = "stop"
            return httpx2.Response(200, json={"id": "chatcmpl-local", "object": "chat.completion",
                                             "created": 0, "model": "stub",
                                             "choices": [{"index": 0, "message": message, "finish_reason": reason}]})

        async def execute():
            async with httpx2.AsyncClient(transport=httpx2.MockTransport(reply)) as http:
                async with AsyncAzureOpenAI(
                    azure_endpoint="https://mock.openai.azure.com", api_version="2024-10-21",
                    api_key="test", http_client=http,
                ) as azure:
                    with (patch.dict(os.environ, {"ASSESSMENT_PROVIDER": "azure", **dict(zip(AZURE_KEYS, ("https://mock.openai.azure.com", "stub", "test")))}),
                          patch("assessment.workflow.collect", return_value=evidence),
                          patch("assessment.workflow.OpenAIChatCompletionClient",
                                return_value=OpenAIChatCompletionClient(model="stub", async_client=azure))):
                        return await run(Request(evidence.root, evidence.directory.parent, True))

        report = asyncio.run(execute())
        qa = report["investigacion"]
        self.assertEqual(qa["estado"], "COMPLETADA", qa)
        self.assertEqual([call["herramienta"] for call in qa["llamadas"]],
                         ["buscar_pruebas_vinculadas", "inspeccionar_prueba", "listar_resultados"])
        self.assertEqual(len(observed), 4)
        self.assertTrue(qa["referencias"][0]["correlacion_valida"])
        self.assertTrue(qa["referencias"][0]["cubre_criterio"])
        self.assertFalse(qa["referencias"][1]["correlacion_valida"])
        self.assertEqual(report["veredicto"], "INCUMPLIDO")

    def test_anthropic_tool_dispatch_with_structured_output(self):
        evidence = self.failed
        model = "claude-sonnet-4-6"
        test = next(test for test in source_tests(evidence.sources) if test.linked)
        result = next(row for row in evidence.results if row.method == test.method)
        requests = []

        def reply(request):
            body = json.loads(request.content)
            requests.append(body)
            if len(requests) == 1:
                content = [{"type": "tool_use", "id": "toolu_fake", "name": "listar_resultados", "input": {}}]
                reason = "tool_use"
            else:
                content = [{"type": "text", "text": json.dumps({
                    "explicacion": "El TRX contiene el fallo de la prueba vinculada.",
                    "referencias": [{"prueba": test.ref, "ejecuciones": [result.execution_id]}],
                })}]
                reason = "end_turn"
            return httpx2.Response(200, json={"id": "msg_fake", "type": "message", "role": "assistant",
                                             "model": model, "content": content, "stop_reason": reason,
                                             "usage": {"input_tokens": 20, "output_tokens": 10}})

        async def execute():
            async with httpx2.AsyncClient(transport=httpx2.MockTransport(reply)) as http:
                async with AsyncAnthropic(api_key="test", http_client=http) as anthropic:
                    with (patch.dict(os.environ, {"ASSESSMENT_PROVIDER": "anthropic",
                                                  "ANTHROPIC_API_KEY": "test", "ANTHROPIC_CHAT_MODEL": model}),
                          patch("assessment.workflow.collect", return_value=evidence),
                          patch("assessment.workflow.AnthropicClient",
                                return_value=AnthropicClient(model=model, anthropic_client=anthropic))):
                        return await run(Request(evidence.root, evidence.directory.parent, True))

        report = asyncio.run(execute())
        qa = report["investigacion"]
        self.assertEqual(qa["estado"], "COMPLETADA", qa)
        self.assertEqual(qa["proveedor"], "anthropic")
        self.assertEqual([call["herramienta"] for call in qa["llamadas"]], ["listar_resultados"])
        self.assertEqual(len(requests), 2)
        output_format = requests[0]["output_config"]["format"]
        self.assertEqual(output_format["type"], "json_schema")
        prompt_text = json.dumps(requests[0]["messages"], ensure_ascii=False)
        self.assertNotIn(evidence.identity["id"], prompt_text)
        self.assertIn("listar_resultados", json.dumps(requests[0].get("system", ""), ensure_ascii=False))
        schema = output_format["schema"]
        self.assertIs(schema["additionalProperties"], False)
        self.assertIs(schema["$defs"]["Reference"]["additionalProperties"], False)
        self.assertEqual(requests[1]["messages"][-1]["content"][0]["type"], "tool_result")
        self.assertTrue(qa["referencias"][0]["correlacion_valida"])
        self.assertEqual(report["veredicto"], "INCUMPLIDO")

    def test_devsecops_parallel_branches_and_human_approval_checkpoint(self):
        fake_cloud = {
            "habilitado": True,
            "politica_version": "REN-001.v2",
            "boards": {"disponible": True, "id": 1, "referencia": "AB#1", "titulo": "Excluir cancelados", "url": "https://dev.azure.com/org/proj/_workitems/edit/1"},
            "github": {
                "disponible": True, "repositorio": "org/repo", "url_repositorio": "https://github.com/org/repo",
                "pull_request": {"numero": 1, "estado": "merged", "referencias_boards": ["AB#1"], "url": "https://github.com/org/repo/pull/1"},
                "pipeline_ci": {"run_id": 10, "url": "https://github.com/org/repo/actions/runs/10"},
                "seguridad_origen": {"dependabot_configurado": True, "code_scanning": {"estado": "activo", "alertas_abiertas": 0, "hallazgos": []}},
            },
            "azure": {
                "disponible": True,
                "despliegue": {"recurso": "ca-appcontratos", "estado": "Succeeded", "revision_activa": "ca--rev1", "version_app": "v2", "url": "https://ca.azurecontainerapps.io", "https_exclusivo": True, "identidad_administrada": "None"},
                "defender": {"https_exclusivo_verificado": True, "hallazgos": [{"codigo": "AZ-POSTURE-MI-001", "alcance": "recurso", "severidad": "Baja", "detalle": "Sin Managed Identity"}]},
                "telemetria": {"disponible": True, "total_solicitudes": 12, "fallos_5xx": 0, "tasa_error_pct": 0.0, "latencia_promedio_ms": 18.4},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            local_ev = replace(self.failed, directory=out_dir / "demo_run", identity={**self.failed.identity, "id": "demo_run"})
            local_ev.directory.mkdir(parents=True)
            with (patch("assessment.workflow.collect", return_value=local_ev),
                  patch("assessment.workflow.collect_devsecops_context", return_value=fake_cloud)):
                report = asyncio.run(run(Request(local_ev.root, out_dir, agent=False, devsecops=True)))
            (local_ev.directory / "informe.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

            self.assertEqual(len(report["etapas_devsecops"]), 8)
            self.assertIn("pregunta", report["etapas_devsecops"][0])
            self.assertIn("datos", report["etapas_devsecops"][0])
            self.assertEqual(report["etapas_devsecops"][0]["bloque"], "DevSec")
            self.assertEqual(report["etapas_devsecops"][4]["bloque"], "CloudOps")
            self.assertEqual(report["investigacion_secops"]["estado"], "SOLO_EVIDENCIA")
            self.assertEqual(report["investigacion_secops"]["hallazgos"][0]["alcance"], "recurso")
            self.assertEqual(report["accion_propuesta"]["estado"], "PENDIENTE_APROBACION")
            self.assertTrue((local_ev.directory / "checkpoint_aprobacion.json").is_file())

            with (patch("assessment.workflow.APPROVAL_LOCK", out_dir / "approvals.sqlite3"),
                  patch("assessment.workflow.upsert_boards_task", return_value={
                "operacion": "creada", "work_item_id": 7, "referencia": "AB#7",
                "fingerprint": report["accion_propuesta"]["fingerprint"], "url": "https://dev.azure.com/org/proj/_workitems/edit/7",
            }) as upsert):
                approved = resolve_human_decision(local_ev.directory, approve=True, note="Aprobado en comité")
                self.assertEqual(resolve_human_decision(local_ev.directory, approve=True), approved)
                with self.assertRaises(DecisionAlreadyResolved):
                    resolve_human_decision(local_ev.directory, approve=False)
                upsert.assert_called_once()
            self.assertEqual(approved["accion_propuesta"]["estado"], "APROBADA")
            self.assertEqual(approved["accion_propuesta"]["boards_resultado"]["referencia"], "AB#7")


class DevSecOpsRegression(unittest.TestCase):
    def test_deployment_requires_a_matching_revision(self):
        deployed = dict(recurso="ca-appcontratos", estado="Succeeded", revision_activa="ca--rev1",
                        version_app="v1", commit_desplegado="a" * 40)
        cloud = {"habilitado": True, "azure": {"despliegue": deployed}}
        execution = dict(version="v1", commit="a" * 40, cambios_locales=False)
        report = dict(criterio=CRITERION, veredicto="VERIFICADO", resultados_trx=[],
                      justificacion="", referencias=[], ejecucion=execution)
        self.assertEqual(build_eight_stages(report, cloud)[4]["estado"], "verificado")
        for changes in ({"version": "v2"}, {"commit": "b" * 40}, {"commit": None}, {"cambios_locales": True}):
            with self.subTest(changes=changes):
                report["ejecucion"] = {**execution, **changes}
                self.assertEqual(build_eight_stages(report, cloud)[4]["estado"], "pendiente")
        report["ejecucion"] = execution
        deployed["revision_activa"] = None
        self.assertEqual(build_eight_stages(report, cloud)[4]["estado"], "pendiente")

    def test_concurrent_approvals_create_one_boards_task(self):
        first_query = Event()
        release_query = Event()
        second_started = Event()
        second_query = Event()
        created = []

        def api(method, url, headers, body):
            if "/wiql?" in url:
                if not first_query.is_set():
                    first_query.set()
                    self.assertTrue(release_query.wait(5))
                else:
                    second_query.set()
                return {"workItems": [{"id": 7}] if created else []}
            if method == "POST":
                created.append(body)
            return {"id": 7}

        def approve_second(directory):
            second_started.set()
            return resolve_human_decision(directory, approve=True)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dirs = [root / "one" / "first", root / "two" / "second"]
            for directory in dirs:
                directory.mkdir(parents=True)
                (directory / "informe.json").write_text(json.dumps({
                    "ejecucion": {"id": directory.name, "version": "v2"},
                    "criterio": {"id": "REN-001"}, "veredicto": "INCUMPLIDO",
                    "accion_propuesta": {
                        "estado": "PENDIENTE_APROBACION", "fingerprint": "abc", "tag_idempotencia": "devsecops-fp-abc",
                        "titulo": "Corregir", "descripcion": "REN-001", "criterio_reevaluacion": "Reevaluar",
                    },
                }), encoding="utf-8")
            with (patch("assessment.workflow.APPROVAL_LOCK", root / "lock" / "approvals.sqlite3"),
                  patch("assessment.integrations.load_settings", return_value={
                      "AZURE_DEVOPS_ORG_URL": "https://dev.azure.com/org",
                      "AZURE_DEVOPS_PROJECT": "proj", "AZURE_DEVOPS_PAT": "test-token",
                  }),
                  patch("assessment.integrations._http_json", side_effect=api),
                  ThreadPoolExecutor(max_workers=2) as pool):
                first = pool.submit(resolve_human_decision, dirs[0], True)
                try:
                    self.assertTrue(first_query.wait(5))
                    second = pool.submit(approve_second, dirs[1])
                    self.assertTrue(second_started.wait(5))
                    self.assertFalse(second_query.wait(0.2))
                finally:
                    release_query.set()
                results = [job.result(5)["accion_propuesta"]["boards_resultado"] for job in (first, second)]
        self.assertEqual(len(created), 1)
        self.assertEqual([(r["operacion"], r["work_item_id"]) for r in results], [("creada", 7), ("actualizada", 7)])

    def test_multi_criteria_cobertura_remediation_and_reversible_demo_cycle(self):
        parsed_criteria = parse_boards_criteria(
            "• REN-001: Al evaluar renovaciones, un contrato cancelado no debe generar un aviso.\n"
            "• REN-002: Evaluaciones repetidas en activos generan un solo aviso.\n"
            "• REN-003: Contratos vencidos no generan aviso."
        )
        self.assertEqual([c["id"] for c in parsed_criteria], ["REN-001", "REN-002", "REN-003"])

        gov = audit_repo_governance(ROOT)
        self.assertTrue(gov["copilot"]["configurado"])
        self.assertTrue(gov["pipelines"]["azure_pipelines_definido"])
        self.assertTrue(gov["aks"]["endurecido"])
        self.assertEqual(gov["aks"]["controles_verificados"], 6)
        self.assertTrue(gov["security_copilot"]["disponible"])

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cov_xml = base / "coverage.cobertura.xml"
            cov_xml.write_text(
                '<coverage line-rate="0.925" branch-rate="0.85" lines-covered="37" lines-valid="40" '
                'branches-covered="17" branches-valid="20"></coverage>',
                encoding="utf-8",
            )
            cov = read_cobertura(base)
            self.assertIsNotNone(cov)
            self.assertEqual(cov["lineas_pct"], 92.5)

            runs_dir = base / "runs"
            run_id = "b" * 32
            run_dir = runs_dir / run_id
            run_dir.mkdir(parents=True)
            sample_report = {
                "politica_version": "REN-001.v2",
                "criterio": CRITERION,
                "veredicto": "INCUMPLIDO",
                "justificacion": "Falló Assert.Empty.",
                "siguiente_paso": "Corregir filtro.",
                "referencias": [{"id": "tests/RenovacionesTests.cs:20", "metodo": "RenovacionesTests.CanceladoNoGeneraAviso"}],
                "resultados_trx": [{"outcome": "Passed"}, {"outcome": "Failed"}],
                "criterios_evaluados": [
                    {"id": "REN-001", "rol": "primario", "veredicto": "INCUMPLIDO", "texto": CRITERION["texto"]},
                    {"id": "REN-002", "rol": "secundario", "veredicto": "VERIFICADO", "texto": "Activos sin duplicados"},
                ],
                "cobertura": {
                    "criterios_verificados": 1,
                    "criterios_totales": 2,
                    "criterios_pct": 50.0,
                    "escenarios_dominio_verificados": 3,
                    "escenarios_dominio_totales": 4,
                    "escenarios_dominio_pct": 75.0,
                },
                "ejecucion": {"id": run_id, "version": "v2", "commit": "1234567890abcdef", "cambios_locales": False},
                "accion_propuesta": {
                    "estado": "APROBADA",
                    "fingerprint": "demo123",
                    "tag_idempotencia": "devsecops-fp-demo123",
                    "titulo": "Corregir v2",
                    "descripcion": "Excluir cancelados",
                    "criterio_reevaluacion": "Reevaluar v2",
                    "boards_resultado": {"operacion": "creada", "work_item_id": 12, "referencia": "AB#12", "url": "https://dev.azure.com/demo/12"},
                },
                "etapas_devsecops": [{"numero": 8, "estado": "verificado", "resumen": "Aprobada", "datos": {"Estado gobernanza": "APROBADA"}}],
            }
            (run_dir / "informe.json").write_text(json.dumps(sample_report, ensure_ascii=False), encoding="utf-8")

            # Draft remediation (0 tokens deterministic)
            draft = asyncio.run(generate_remediation(run_dir, use_ai=False))
            self.assertTrue(draft["disponible"])
            self.assertEqual(draft["origen"], "plantilla_determinista")
            self.assertIn("contrato.Cancelado", draft["codigo_sugerido"])

            # Reopen approved decision for next demo
            with (patch("assessment.workflow.APPROVAL_LOCK", base / "approvals.sqlite3"),
                  patch("assessment.demo_reset.revert_single_boards_task", return_value={"sincronizado": True}) as rev_task):
                reopened = reopen_governance_decision(run_dir, sync_boards=True)
                self.assertEqual(reopened["accion_propuesta"]["estado"], "PENDIENTE_APROBACION")
                self.assertNotIn("boards_resultado", reopened["accion_propuesta"])
                self.assertEqual(reopened["etapas_devsecops"][0]["estado"], "atencion")
                rev_task.assert_called_once_with(12, target_state="Removed")

            # Closed-loop resolution when VERIFICADO + reopen closure
            close_id = "c" * 32
            close_dir = runs_dir / close_id
            close_dir.mkdir(parents=True)
            (close_dir / "informe.json").write_text(json.dumps({
                "politica_version": "REN-001.v2",
                "criterio": CRITERION,
                "veredicto": "VERIFICADO",
                "resultados_trx": [{"outcome": "Passed"}],
                "referencias": [{"id": "t.cs:1"}],
                "ejecucion": {"id": close_id, "version": "v1", "commit": "abcdef123456"},
                "cierre_ciclo_boards": {
                    "estado": "LISTA_PARA_CERRAR",
                    "work_item_id": 15,
                    "referencia": "AB#15",
                    "fingerprint": "fp15",
                    "tag_idempotencia": "devsecops-fp-fp15",
                    "url": "https://dev.azure.com/demo/15",
                    "titulo": "Cerrar AB#15",
                },
                "etapas_devsecops": [{"numero": 8, "estado": "atencion", "resumen": "Pendiente cierre", "datos": {}}],
            }), encoding="utf-8")
            with (patch("assessment.workflow.APPROVAL_LOCK", base / "approvals.sqlite3"),
                  patch("assessment.workflow.close_boards_task", return_value={
                      "operacion": "cerrada", "work_item_id": 15, "referencia": "AB#15",
                      "fingerprint": "fp15", "url": "https://dev.azure.com/demo/15",
                  })):
                closed = resolve_boards_closure(close_dir, note="Certificado")
                self.assertEqual(closed["cierre_ciclo_boards"]["estado"], "CERRADA_VERIFICADA")

            # Power BI metrics before reset
            metrics = build_powerbi_metrics(runs_dir)
            self.assertEqual(metrics["kpis"]["corridas_totales"], 2)
            csv_text = render_powerbi_csv(runs_dir)
            self.assertIn("ejecucion_id,fecha_utc,version", csv_text)
            self.assertIn(run_id, csv_text)

            # Reversible multi-demo reset & restore
            fake_repo = base / "repo"
            (fake_repo / "v1" / "src" / "Contratos").mkdir(parents=True)
            (fake_repo / "v1" / "src" / "Contratos" / "datos.json").write_text("{}", encoding="utf-8")
            reset_res = execute_demo_reset(fake_repo, runs_dir, reset_runs=True, reset_sandbox=True, reset_boards=False)
            self.assertEqual(reset_res["corridas"]["archivadas"], 2)
            self.assertIn("v1/src/Contratos/datos.json", reset_res["sandbox_archivos_limpiados"])
            self.assertEqual(build_powerbi_metrics(runs_dir)["kpis"]["corridas_totales"], 0)

            restored_res = restore_latest_archive(runs_dir)
            self.assertEqual(restored_res["corridas_restauradas"], 2)
            self.assertEqual(build_powerbi_metrics(runs_dir)["kpis"]["corridas_totales"], 2)

            # Live local C# apply + real dotnet test verification + byte-exact revert on v2 & v3
            sandbox_repo = base / "live_repo"
            for ver, initial_verdict in (("v2", "INCUMPLIDO"), ("v3", "EVIDENCIA_INSUFICIENTE")):
                copy_version(ROOT / ver, sandbox_repo / ver)
                rel_cs = "src/Contratos/Renovaciones.cs" if ver == "v2" else "tests/Contratos.Tests/RenovacionesTests.cs"
                orig_bytes = (sandbox_repo / ver / rel_cs).read_bytes()
                rid = (ver * 16)[:32]
                rdir = runs_dir / rid
                rdir.mkdir(parents=True, exist_ok=True)
                (rdir / "informe.json").write_text(json.dumps({
                    "criterio": CRITERION,
                    "veredicto": initial_verdict,
                    "justificacion": "Brecha detectada",
                    "ejecucion": {"id": rid, "version": ver},
                }), encoding="utf-8")

                applied = asyncio.run(apply_local_remediation(sandbox_repo, runs_dir, rid, use_ai=False))
                self.assertTrue(applied["aplicado"])
                ev_after = collect(sandbox_repo / ver, base / f"after_{ver}")
                tests_after = source_tests(ev_after.sources)
                verd_after = evaluate(ev_after, tests_after)
                self.assertEqual(verd_after["veredicto"], "VERIFICADO", f"{ver} no pasó tras remediación")
                mat_after = evaluate_criteria_matrix(ev_after, tests_after, verd_after)
                self.assertEqual(mat_after["cobertura"]["criterios_verificados"], 2)

                # Ephemeral GitOps PR create & reversible close
                gh_calls = []

                def fake_gh_json(method, url, headers, body=None, timeout=15):
                    gh_calls.append((method, url))
                    if url.endswith("/git/ref/heads/main"):
                        return {"object": {"sha": "1" * 40}}
                    if "/git/commits/" in url:
                        return {"tree": {"sha": "2" * 40}}
                    if url.endswith("/git/trees"):
                        return {"sha": "3" * 40}
                    if url.endswith("/git/commits"):
                        return {"sha": "4" * 40}
                    if url.endswith("/git/refs"):
                        return {"ref": body["ref"]}
                    if url.endswith("/pulls"):
                        return {"number": 42, "html_url": "https://github.com/org/repo/pull/42"}
                    return {"state": "closed"}

                with (patch("assessment.remediation._gh_token", return_value="gho_fake"),
                      patch("assessment.remediation._http_json", side_effect=fake_gh_json),
                      patch("assessment.remediation._http_no_body", return_value=204)):
                    pr_created = asyncio.run(
                        create_github_remediation_pr(
                            sandbox_repo, runs_dir, rid, settings={"GITHUB_REPO": "org/repo"}
                        )
                    )
                    self.assertEqual(pr_created["operacion"], "creado")
                    self.assertEqual(pr_created["pr"]["numero"], 42)
                    closed_prs = close_github_remediation_prs(
                        runs_dir, version=ver, settings={"GITHUB_REPO": "org/repo"}
                    )
                    self.assertEqual(len(closed_prs), 1)

                reverted_list = revert_local_remediation(sandbox_repo, runs_dir, version=ver)
                self.assertEqual(len(reverted_list), 1)
                self.assertEqual((sandbox_repo / ver / rel_cs).read_bytes(), orig_bytes)


if __name__ == "__main__":
    unittest.main()
