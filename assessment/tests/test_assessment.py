import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import httpx2
from anthropic import AsyncAnthropic
from openai import AsyncAzureOpenAI

from assessment.evidence import APP, PROJECT, collect
from assessment.policy import evaluate, source_tests
from assessment.workflow import (
    AZURE_KEYS,
    AnthropicClient,
    OpenAIChatCompletionClient,
    Request,
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
            self.assertEqual(report["investigacion_secops"]["estado"], "SOLO_EVIDENCIA")
            self.assertEqual(report["investigacion_secops"]["hallazgos"][0]["alcance"], "recurso")
            self.assertEqual(report["accion_propuesta"]["estado"], "PENDIENTE_APROBACION")
            self.assertTrue((local_ev.directory / "checkpoint_aprobacion.json").is_file())

            with patch("assessment.workflow.upsert_boards_task", return_value={
                "operacion": "creada", "work_item_id": 7, "referencia": "AB#7",
                "fingerprint": report["accion_propuesta"]["fingerprint"], "url": "https://dev.azure.com/org/proj/_workitems/edit/7",
            }):
                approved = resolve_human_decision(local_ev.directory, approve=True, note="Aprobado en comité")
            self.assertEqual(approved["accion_propuesta"]["estado"], "APROBADA")
            self.assertEqual(approved["accion_propuesta"]["boards_resultado"]["referencia"], "AB#7")


if __name__ == "__main__":
    unittest.main()
