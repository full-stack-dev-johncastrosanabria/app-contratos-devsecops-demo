"""CLI local para la demo REN-001."""
import argparse
import asyncio
import json
from pathlib import Path

from .workflow import Request, run

ROOT = Path(__file__).resolve().parent.parent


def markdown(report: dict) -> str:
    criterion, identity, qa = (report[key] for key in ("criterio", "ejecucion", "investigacion"))
    dirty = {None: "sin información Git", True: "con cambios locales", False: "sin cambios locales"}[
        identity["cambios_locales"]]
    lines = [
        f"# {criterion['id']} · {identity['version']}", "",
        criterion["texto"] + ".", "",
        f"**{report['veredicto']}**", "", report["justificacion"], "",
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
    if report["siguiente_paso"]:
        lines += ["", "## Siguiente paso", "", report["siguiente_paso"]]
    return "\n".join(lines) + "\n"


async def assess_project(root: Path, output: Path, agent: bool) -> dict:
    report = await run(Request(root, output, agent))
    directory = output / report["ejecucion"]["id"]
    (directory / "informe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "informe.md").write_text(markdown(report), encoding="utf-8")
    return report


async def assess(roots: list[Path], output: Path, agent: bool) -> int:
    error = False
    for root in roots:
        report = await assess_project(root, output, agent)
        directory = output / report["ejecucion"]["id"]
        qa = report["investigacion"]
        print(f"{root.name} · {report['modo']} · {report['veredicto']} · {directory / 'informe.md'}")
        if qa.get("detalle"):
            print(f"  {qa['detalle']}")
        for call in qa["llamadas"]:
            print(f"  QA → {call['herramienta']}")
        error |= bool(report["diagnosticos"]) or qa["estado"] not in {"SOLO_EVIDENCIA", "COMPLETADA"}
    return 2 if error else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa la evidencia xUnit del criterio REN-001")
    parser.add_argument("proyecto", help="v1, v2, v3, una carpeta de proyecto o 'todas'")
    parser.add_argument("--modo", choices=("solo-evidencia", "agente"), default="solo-evidencia")
    parser.add_argument("--salida", type=Path, default=ROOT / "assessment/runs")
    args = parser.parse_args()
    versions = ("v1", "v2", "v3")
    if args.proyecto == "todas":
        roots = [ROOT / version for version in versions]
    else:
        roots = [ROOT / args.proyecto if args.proyecto in versions else Path(args.proyecto).resolve()]
    return asyncio.run(assess(roots, args.salida.resolve(), args.modo == "agente"))


if __name__ == "__main__":
    raise SystemExit(main())
