"""Analítica longitudinal, agente SRE/BI e integración tabular para Power BI y Microsoft Fabric."""
import asyncio
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path

from agent_framework import tool
from pydantic import BaseModel, ConfigDict


class ObservabilityBriefing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titular_ejecutivo: str
    diagnostico_sre: str
    hallazgos_tendencia: list[str]
    recomendacion_comite: str


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


async def analyze_observability_agent(runs_dir: Path, *, use_ai: bool = True) -> dict:
    from .integrations import fetch_azure_runtime, load_settings
    from .powerbi_cloud import get_powerbi_state
    from .workflow import _build_model_client, _resolve_provider_config

    metrics = build_powerbi_metrics(runs_dir)
    kpis = metrics["kpis"]
    pbi_state = get_powerbi_state(runs_dir)
    az_runtime = await asyncio.to_thread(fetch_azure_runtime, load_settings())
    tel = (az_runtime.get("telemetria") if isinstance(az_runtime, dict) else None) or {"disponible": False}

    fallback = {
        "disponible": True,
        "origen": "reglas_deterministas",
        "proveedor": None,
        "traza_herramientas": [],
        "titular_ejecutivo": (
            f"{kpis['corridas_totales']} corridas auditadas · {kpis['controles_con_evidencia_pct']}% con evidencia trazable"
        ),
        "diagnostico_sre": (
            f"Telemetría KQL en 24h: {tel.get('total_solicitudes', 0)} solicitudes, "
            f"{tel.get('fallos_5xx', 0)} errores 5xx ({tel.get('tasa_error_pct', 0.0)}%) y "
            f"latencia media de {tel.get('latencia_promedio_ms', 0.0)} ms."
        ),
        "hallazgos_tendencia": [
            f"Criterios vigentes certificados: {kpis['criterios_vigentes_verificados']}/{kpis['criterios_vigentes_totales']} ({kpis['criterios_vigentes_pct']}%).",
            f"Entregas bloqueadas por regresión funcional: {kpis['corridas_incumplidas']}; brechas silenciosas detectadas: {kpis['corridas_evidencia_insuficiente']}.",
        ],
        "recomendacion_comite": "Sincronizar dataset en Power BI Web antes del comité de release y exigir cierre de brechas en v2/v3.",
    }
    if not use_ai:
        return fallback

    provider, config, err = _resolve_provider_config()
    if err or not provider:
        fallback["nota_ia"] = err or "Proveedor IA no configurado; síntesis determinista activa."
        return fallback

    tool_trace: list[str] = []

    @tool
    def consultar_telemetria_kql_azure() -> dict:
        """Consulta solicitudes HTTP, tasa de error 5xx, latencia y comparación contra línea base en Application Insights."""
        tool_trace.append("consultar_telemetria_kql_azure")
        return tel

    @tool
    def consultar_historial_kpis_powerbi() -> dict:
        """Consulta KPIs longitudinales de corridas, criterios certificados, regresiones y brechas silenciosas."""
        tool_trace.append("consultar_historial_kpis_powerbi")
        return {"kpis": kpis, "ultimas_por_entrega": metrics.get("ultimas_por_entrega", {})}

    @tool
    def consultar_estado_dataset_powerbi_web() -> dict:
        """Consulta el estado de sincronización del dataset Push y reporte visual en app.powerbi.com."""
        tool_trace.append("consultar_estado_dataset_powerbi_web")
        return pbi_state

    try:
        async with asyncio.timeout(55):
            model_client = _build_model_client(provider, config)
            async with model_client as client:
                agent = client.as_agent(
                    name="Agente Analista SRE y Power BI (Etapa 7)",
                    instructions=(
                        "Sos el Agente Analista de Observabilidad SRE e Inteligencia Ejecutiva (Etapa 7). "
                        "Invocá primero consultar_telemetria_kql_azure, consultar_historial_kpis_powerbi y "
                        "consultar_estado_dataset_powerbi_web sin emitir texto previo. "
                        "Redactá en español ejecutivo el diagnóstico de estabilidad en producción, las tendencias de calidad "
                        "entre v1/v2/v3 y la recomendación concreta para el comité de release."
                    ),
                    tools=[
                        consultar_telemetria_kql_azure,
                        consultar_historial_kpis_powerbi,
                        consultar_estado_dataset_powerbi_web,
                    ],
                )
                resp = await agent.run(
                    "Analizá la telemetría KQL en vivo y los KPIs longitudinales de Power BI de esta sesión.",
                    options={"response_format": ObservabilityBriefing},
                )
                structured = resp.value
                if not isinstance(structured, ObservabilityBriefing):
                    raise ValueError("Respuesta estructurada SRE/BI ausente")
                dumped = structured.model_dump()
                return {
                    "disponible": True,
                    "origen": "agente_sre_bi_ia",
                    "proveedor": provider,
                    "traza_herramientas": tool_trace,
                    **dumped,
                }
    except Exception as exc:
        fallback["nota_ia"] = f"Se usó síntesis determinista tras error del modelo ({type(exc).__name__})."
        return fallback
