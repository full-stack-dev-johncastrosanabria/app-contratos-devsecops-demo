"""CLI local y DevSecOps para la demo REN-001."""
import argparse
import asyncio
import json
from pathlib import Path

from .demo_reset import execute_demo_reset, restore_latest_archive
from .integrations import load_settings
from .workflow import (
    DecisionAlreadyResolved,
    Request,
    reopen_governance_decision,
    resolve_boards_closure,
    resolve_human_decision,
    run,
)

ROOT = Path(__file__).resolve().parent.parent


def markdown(report: dict) -> str:
    criterion, identity, qa = (report[key] for key in ("criterio", "ejecucion", "investigacion"))
    dirty = {None: "sin información Git", True: "con cambios locales", False: "sin cambios locales"}[
        identity["cambios_locales"]]
    lines = [
        f"# {criterion['id']} · {identity['version']}", "",
        criterion["texto"] + ".", "",
        f"**{report['veredicto']}**", "", report["justificacion"], "",
        f"- Política `{report.get('politica_version', 'REN-001.v1')}`",
        f"- Modo `{report['modo']}`",
        f"- Ejecución `{identity['id']}`",
        f"- Proyecto `{identity['proyecto']}`",
        f"- Commit `{identity['commit'] or 'no disponible'}`, {dirty}",
        f"- Archivos con SHA-256 en [informe.json](informe.json) · {len(identity.get('sha256_archivos', {}))}",
        f"- Código de salida de dotnet test · {identity['codigo_dotnet']}", "",
    ]
    for key in ("trx", "log"):
        if identity[key]:
            lines.append(f"- [{identity[key]}]({identity[key]})")
    if identity["trx_id"]:
        lines.append(f"- ID de TestRun `{identity['trx_id']}`")
    results = {row["execution_id"]: row for row in report["resultados_trx"]}
    for ref in report["referencias"]:
        lines.append(f"- Fuente `{ref['id']}` · `{ref['metodo']}`")
        if ref["linea_asercion"]:
            lines.append(f"  - Aserción en línea {ref['linea_asercion']}")
        for result_id in ref["resultados"]:
            row = results[result_id]
            lines.append(f"  - TRX `{row['name']}` · `{row['outcome']}` · `{result_id}`")
    if not report["referencias"]:
        lines.extend(f"- TRX `{row['name']}` · `{row['outcome']}` · `{row['execution_id']}`"
                     for row in results.values())
        lines.extend(f"- Fuente inspeccionada `{path}`" for path in
                     sorted({ref["archivo"] for ref in report["pruebas_fuente"]}))

    criteria_list = report.get("criterios_evaluados") or []
    if criteria_list:
        lines += ["", "## Matriz de criterios evaluados", "", "| Criterio | Rol | Veredicto | Evidencia |", "| --- | --- | --- | --- |"]
        for c in criteria_list:
            lines.append(f"| `{c['id']}` | {c.get('rol', 'primario')} | `{c['veredicto']}` | {c.get('resumen', '')} |")

    stages = report.get("etapas_devsecops") or []
    if stages:
        lines += ["", "## Recorrido DevSecOps (8 Etapas)", "", "| Etapa | Fuente | Estado | Evidencia |", "| --- | --- | --- | --- |"]
        for s in stages:
            ev = f"[{s['resumen']}]({s['url']})" if s.get("url") else s["resumen"]
            lines.append(f"| {s['numero']}. {s['etapa']} | {s['herramienta']} | `{s['estado']}` | {ev} |")

    if report["diagnosticos"]:
        lines += ["", "## Diagnóstico", ""]
        lines.extend(f"- `{d['codigo']}` · {d['detalle']}" for d in report["diagnosticos"])
    if report["modo"] == "agente":
        lines += ["", "## Investigación de QA", "", f"Estado `{qa['estado']}`.", ""]
        lines.extend(qa[key] for key in ("detalle", "explicacion") if key in qa)
        for ref in qa["referencias"]:
            status = "válida" if ref["correlacion_valida"] else "sin correlación confirmada"
            lines.append(f"- Referencia `{ref['prueba']}` · {status} · {', '.join(ref['ejecuciones'])}")
        lines.extend(f"- `{call['herramienta']}`" for call in qa["llamadas"])

    secops = report.get("investigacion_secops") or {}
    if secops.get("estado") not in (None, "NO_SOLICITADA"):
        lines += ["", "## Seguridad y Operación", "", f"Estado `{secops['estado']}`.", ""]
        for key in ("detalle", "resumen"):
            if secops.get(key):
                lines.append(secops[key])
        for item in secops.get("hallazgos") or []:
            lines.append(f"- **[{item['alcance']} · {item['severidad']}]** {item['titulo']}: {item['evidencia']}")
        lines.extend(f"- `{call['herramienta']}`" for call in secops.get("llamadas") or [])

    action = report.get("accion_propuesta")
    if action:
        lines += ["", "## Acción de Gobernanza (Azure Boards)", ""]
        lines.append(f"- Estado: `{action['estado']}` · Clave `{action['tag_idempotencia']}`")
        lines.append(f"- Propuesta: **{action['titulo']}**")
        if action.get("boards_resultado"):
            br = action["boards_resultado"]
            lines.append(f"- Work Item ({br['operacion']}): [{br['referencia']}]({br['url']})")
        elif action.get("nota_humana"):
            lines.append(f"- Nota: {action['nota_humana']}")

    closure = report.get("cierre_ciclo_boards")
    if closure:
        lines += ["", "## Cierre de Ciclo (Azure Boards)", ""]
        lines.append(f"- Estado: `{closure['estado']}` · Tarea [{closure['referencia']}]({closure['url']})")

    if report["siguiente_paso"]:
        lines += ["", "## Siguiente paso", "", report["siguiente_paso"]]
    return "\n".join(lines) + "\n"


def _devsecops_configured() -> bool:
    s = load_settings()
    if s.get("DEVSECOPS_LIVE") == "0":
        return False
    return any(s.get(k) for k in ("AZURE_DEVOPS_ORG_URL", "GITHUB_REPO", "AZURE_CONTAINER_APP"))


async def assess_project(root: Path, output: Path, agent: bool, devsecops: bool | None = None) -> dict:
    use_devsecops = _devsecops_configured() if devsecops is None else devsecops
    report = await run(Request(root, output, agent, devsecops=use_devsecops))
    directory = output / report["ejecucion"]["id"]
    (directory / "informe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "informe.md").write_text(markdown(report), encoding="utf-8")
    return report


def apply_decision(run_directory: Path, approve: bool, note: str = "") -> dict:
    report = resolve_human_decision(run_directory, approve=approve, note=note)
    (run_directory / "informe.md").write_text(markdown(report), encoding="utf-8")
    return report


def apply_closure(run_directory: Path, note: str = "") -> dict:
    report = resolve_boards_closure(run_directory, note=note)
    (run_directory / "informe.md").write_text(markdown(report), encoding="utf-8")
    return report


def apply_reopen(run_directory: Path, sync_boards: bool = True) -> dict:
    report = reopen_governance_decision(run_directory, sync_boards=sync_boards)
    (run_directory / "informe.md").write_text(markdown(report), encoding="utf-8")
    return report


async def assess(roots: list[Path], output: Path, agent: bool, devsecops: bool | None = None) -> int:
    error = False
    for root in roots:
        report = await assess_project(root, output, agent, devsecops=devsecops)
        directory = output / report["ejecucion"]["id"]
        qa = report["investigacion"]
        secops = report.get("investigacion_secops") or {}
        print(f"{root.name} · {report['modo']} · {report['veredicto']} · {directory / 'informe.md'}")
        if qa.get("detalle"):
            print(f"  {qa['detalle']}")
        for call in qa["llamadas"]:
            print(f"  QA → {call['herramienta']}")
        for call in secops.get("llamadas") or []:
            print(f"  SecOps → {call['herramienta']}")
        if report.get("accion_propuesta"):
            act = report["accion_propuesta"]
            print(f"  Acción ({act['estado']}) → {act['tag_idempotencia']}")
        error |= bool(report["diagnosticos"]) or qa["estado"] not in {"SOLO_EVIDENCIA", "COMPLETADA"}
    return 2 if error else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa el ciclo DevSecOps y evidencia xUnit del criterio REN-001")
    parser.add_argument(
        "proyecto",
        help="v1, v2, v3, carpeta, 'todas', 'aprobar'/'descartar'/'cerrar'/'reabrir' o 'reiniciar-demo'/'restaurar-demo'",
    )
    parser.add_argument("--modo", choices=("solo-evidencia", "agente"), default="solo-evidencia")
    parser.add_argument("--salida", type=Path, default=ROOT / "assessment/runs")
    parser.add_argument("--ejecucion", help="ID de ejecución para aprobar, descartar, cerrar o reabrir su acción")
    parser.add_argument("--motivo", default="", help="Nota o motivo de aprobación/descarte/cierre")
    parser.add_argument("--sin-nube", action="store_true", help="Omitir consultas o reinicio en vivo en Boards, GitHub y Azure")
    parser.add_argument("--con-boards", action="store_true", help="En reiniciar-demo, retirar tareas devsecops-fp-* y restaurar AB#1")
    args = parser.parse_args()

    if args.proyecto == "reiniciar-demo":
        res = execute_demo_reset(
            ROOT,
            args.salida.resolve(),
            reset_runs=True,
            reset_sandbox=True,
            reset_boards=bool(args.con_boards and not args.sin_nube),
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if args.proyecto == "restaurar-demo":
        res = restore_latest_archive(args.salida.resolve())
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if args.proyecto in ("aprobar", "descartar", "cerrar", "reabrir"):
        if not args.ejecucion:
            parser.error("Indicá --ejecucion <id> para gestionar una acción en Azure Boards.")
        try:
            if args.proyecto == "reabrir":
                updated = apply_reopen(args.salida.resolve() / args.ejecucion, sync_boards=not args.sin_nube)
                state = (updated.get("accion_propuesta") or updated.get("cierre_ciclo_boards") or {}).get("estado", "REABIERTA")
                print(f"{args.ejecucion} · {state}")
                return 0
            if args.proyecto == "cerrar":
                updated = apply_closure(args.salida.resolve() / args.ejecucion, args.motivo)
                cl = updated["cierre_ciclo_boards"]
                res = cl.get("boards_resultado") or {}
                print(f"{args.ejecucion} · {cl['estado']} · {res.get('referencia', cl['referencia'])} {res.get('url', '')}".strip())
                return 0
            updated = apply_decision(args.salida.resolve() / args.ejecucion, args.proyecto == "aprobar", args.motivo)
        except DecisionAlreadyResolved as exc:
            parser.error(str(exc))
        act = updated["accion_propuesta"]
        res = act.get("boards_resultado") or {}
        print(f"{args.ejecucion} · {act['estado']} · {res.get('referencia', act['tag_idempotencia'])} {res.get('url', '')}".strip())
        return 0

    versions = ("v1", "v2", "v3")
    if args.proyecto == "todas":
        roots = [ROOT / version for version in versions]
    else:
        roots = [ROOT / args.proyecto if args.proyecto in versions else Path(args.proyecto).resolve()]
    devsecops = False if args.sin_nube else None
    return asyncio.run(assess(roots, args.salida.resolve(), args.modo == "agente", devsecops=devsecops))


if __name__ == "__main__":
    raise SystemExit(main())
