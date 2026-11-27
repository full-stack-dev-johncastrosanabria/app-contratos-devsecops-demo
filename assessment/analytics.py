"""Analítica longitudinal e integración tabular para Power BI y Microsoft Fabric."""
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path


CSV_COLUMNS = (
    "ejecucion_id",
    "fecha_utc",
    "version",
    "modo",
    "politica_version",
    "veredicto_ren001",
    "criterios_verificados",
    "criterios_totales",
    "cobertura_criterios_pct",
    "escenarios_dominio_pct",
    "casos_trx_totales",
    "casos_trx_aprobados",
    "casos_trx_fallidos",
    "pruebas_vinculadas_ren001",
    "archivos_firmados_sha256",
    "commit_sha",
    "cambios_locales",
    "alertas_sast_abiertas",
    "dependabot_prs_abiertos",
    "paquetes_sbom",
    "defender_puntaje_pct",
    "defender_hallazgos",
    "telemetria_solicitudes_24h",
    "telemetria_tasa_5xx_pct",
    "estado_accion_boards",
    "referencia_boards",
)


def _extract_row(report_file: Path) -> tuple[float, dict] | None:
    try:
        mtime = report_file.stat().st_mtime
        data = json.loads(report_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    ejecucion = data.get("ejecucion") or {}
    version = ejecucion.get("version")
    if not version or "veredicto" not in data:
        return None

    trx = data.get("resultados_trx") or []
    passed = sum(1 for r in trx if r.get("outcome") == "Passed")
    failed = sum(1 for r in trx if r.get("outcome") == "Failed")

    cobertura = data.get("cobertura") or {}
    criterios = data.get("criterios_evaluados") or []
    if cobertura:
        crit_ok = int(cobertura.get("criterios_verificados", 0))
        crit_total = int(cobertura.get("criterios_totales", len(criterios) or 1))
        crit_pct = float(cobertura.get("criterios_pct", 0.0))
        dom_pct = float(cobertura.get("escenarios_dominio_pct", 0.0))
    else:
        crit_ok = 1 if data["veredicto"] == "VERIFICADO" else 0
        crit_total = 1
        crit_pct = 100.0 if crit_ok else 0.0
        dom_pct = round((passed / max(len(trx), 1)) * 100.0, 1) if trx else 0.0

    devsecops = data.get("devsecops") or {}
    gh_sec = (devsecops.get("github") or {}).get("seguridad_origen") or {}
    sast_open = int(((gh_sec.get("code_scanning") or {}).get("alertas_abiertas")) or 0)
    dep_prs = int(((gh_sec.get("dependabot") or {}).get("prs_abiertos")) or 0)
    sbom_pkgs = int(((gh_sec.get("sbom") or {}).get("paquetes")) or 0)

    azure = devsecops.get("azure") or {}
    dfd = azure.get("defender") or {}
    dfd_score = dfd.get("puntaje_seguro_pct")
    dfd_findings = len(dfd.get("hallazgos") or [])
    tel = azure.get("telemetria") or {}

    action = data.get("accion_propuesta") or {}
    close_info = data.get("cierre_ciclo_boards") or {}
    boards_ref = (
        (action.get("boards_resultado") or {}).get("referencia")
        or (close_info.get("boards_resultado") or {}).get("referencia")
        or ""
    )
    action_state = action.get("estado") or (close_info.get("estado") if close_info else "CUMPLIDO")

    hashes = ejecucion.get("sha256_archivos") or {}
    row = {
        "ejecucion_id": ejecucion.get("id") or report_file.parent.name,
        "fecha_utc": datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": version,
        "modo": data.get("modo", "solo evidencia"),
        "politica_version": data.get("politica_version", "REN-001.v2"),
        "veredicto_ren001": data["veredicto"],
        "criterios_verificados": crit_ok,
        "criterios_totales": crit_total,
        "cobertura_criterios_pct": crit_pct,
        "escenarios_dominio_pct": dom_pct,
        "casos_trx_totales": len(trx),
        "casos_trx_aprobados": passed,
        "casos_trx_fallidos": failed,
        "pruebas_vinculadas_ren001": len(data.get("referencias") or []),
        "archivos_firmados_sha256": len(hashes) if isinstance(hashes, dict) else int(ejecucion.get("archivos_firmados") or 0),
        "commit_sha": (ejecucion.get("commit") or "")[:12],
        "cambios_locales": bool(ejecucion.get("cambios_locales")),
        "alertas_sast_abiertas": sast_open,
        "dependabot_prs_abiertos": dep_prs,
        "paquetes_sbom": sbom_pkgs,
        "defender_puntaje_pct": dfd_score if dfd_score is not None else "",
        "defender_hallazgos": dfd_findings,
        "telemetria_solicitudes_24h": int(tel.get("total_solicitudes") or 0),
        "telemetria_tasa_5xx_pct": float(tel.get("tasa_error_pct") or 0.0),
        "estado_accion_boards": action_state,
        "referencia_boards": boards_ref,
    }
    return mtime, row


def build_powerbi_metrics(runs_dir: Path) -> dict:
    extracted: list[tuple[float, dict]] = []
    if runs_dir.is_dir():
        for report_file in runs_dir.glob("*/informe.json"):
            if report_file.parent.name.startswith("_"):
                continue
            item = _extract_row(report_file)
            if item is not None:
                extracted.append(item)

    extracted.sort(key=lambda pair: pair[0], reverse=True)
    rows = [item[1] for item in extracted]

    latest_by_version: dict[str, dict] = {}
    for row in rows:
        ver = row["version"]
        if ver in ("v1", "v2", "v3") and ver not in latest_by_version:
            latest_by_version[ver] = row

    total_runs = len(rows)
    verified_runs = sum(1 for r in rows if r["veredicto_ren001"] == "VERIFICADO")
    failed_runs = sum(1 for r in rows if r["veredicto_ren001"] == "INCUMPLIDO")
    insufficient_runs = sum(1 for r in rows if r["veredicto_ren001"] == "EVIDENCIA_INSUFICIENTE")

    # Controles con evidencia determinista verificable (VERIFICADO o INCUMPLIDO probado por TRX + fuente).
    backed_by_evidence = sum(1 for r in rows if r["pruebas_vinculadas_ren001"] > 0 and r["casos_trx_totales"] > 0)
    evidence_rate_pct = round((backed_by_evidence / total_runs) * 100.0, 1) if total_runs else 0.0

    latest_vals = list(latest_by_version.values())
    latest_crit_ok = sum(r["criterios_verificados"] for r in latest_vals)
    latest_crit_total = sum(r["criterios_totales"] for r in latest_vals)
    latest_crit_pct = round((latest_crit_ok / latest_crit_total) * 100.0, 1) if latest_crit_total else 0.0

    actions_approved = sum(1 for r in rows if r["estado_accion_boards"] == "APROBADA")
    actions_closed = sum(1 for r in rows if r["estado_accion_boards"] == "CERRADA_VERIFICADA")
    actions_pending = sum(1 for r in latest_vals if r["estado_accion_boards"] == "PENDIENTE_APROBACION")

    return {
        "generado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "esquema": "NextGenDevSecOps.PowerBI.v1",
        "compatible_con": ["Power BI Desktop (Web.Contents)", "Microsoft Fabric OneLake / Dataflow Gen2"],
        "kpis": {
            "corridas_totales": total_runs,
            "entregas_monitoreadas": len(latest_by_version),
            "corridas_verificadas": verified_runs,
            "corridas_incumplidas": failed_runs,
            "corridas_evidencia_insuficiente": insufficient_runs,
            "controles_con_evidencia_pct": evidence_rate_pct,
            "criterios_vigentes_verificados": latest_crit_ok,
            "criterios_vigentes_totales": latest_crit_total,
            "criterios_vigentes_pct": latest_crit_pct,
            "acciones_boards_aprobadas": actions_approved,
            "acciones_boards_cerradas": actions_closed,
            "acciones_boards_pendientes": actions_pending,
        },
        "ultimas_por_entrega": latest_by_version,
        "columnas": list(CSV_COLUMNS),
        "corridas": rows,
    }


def render_powerbi_csv(runs_dir: Path) -> str:
    payload = build_powerbi_metrics(runs_dir)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(CSV_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for row in payload["corridas"]:
        writer.writerow(row)
    return buf.getvalue()
