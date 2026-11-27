"""Publicación en tiempo real y generación automática de reporte ejecutivo en Power BI Service (app.powerbi.com)."""
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from .analytics import build_powerbi_metrics
from .integrations import _az_token

PBI_RESOURCE = "https://analysis.windows.net/powerbi/api"
PBI_BASE = "https://api.powerbi.com/v1.0/myorg"
DATASET_NAME = "NextGen DevSecOps Assessment"
REPORT_NAME = "NextGen DevSecOps Executive Report"


def _pbi_state_path(runs_dir: Path) -> Path:
    return runs_dir / "_estado_powerbi.json"


def get_powerbi_state(runs_dir: Path) -> dict:
    path = _pbi_state_path(runs_dir)
    if not path.is_file():
        return {"sincronizado": False}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"sincronizado": False}


def _save_powerbi_state(runs_dir: Path, data: dict) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = _pbi_state_path(runs_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _pbi_headers(token: str, content_type: str = "application/json") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": content_type}


def _pbi_json(method: str, url: str, token: str, body: object = None, timeout: int = 20) -> dict:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=payload, method=method, headers=_pbi_headers(token))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def _dataset_schema() -> dict:
    return {
        "name": DATASET_NAME,
        "defaultMode": "Push",
        "tables": [
            {
                "name": "Corridas",
                "columns": [
                    {"name": "ejecucion_id", "dataType": "String"},
                    {"name": "fecha_utc", "dataType": "DateTime"},
                    {"name": "version", "dataType": "String"},
                    {"name": "modo", "dataType": "String"},
                    {"name": "politica_version", "dataType": "String"},
                    {"name": "veredicto_ren001", "dataType": "String"},
                    {"name": "criterios_verificados", "dataType": "Int64"},
                    {"name": "criterios_totales", "dataType": "Int64"},
                    {"name": "cobertura_criterios_pct", "dataType": "Double"},
                    {"name": "escenarios_dominio_pct", "dataType": "Double"},
                    {"name": "casos_trx_totales", "dataType": "Int64"},
                    {"name": "casos_trx_aprobados", "dataType": "Int64"},
                    {"name": "casos_trx_fallidos", "dataType": "Int64"},
                    {"name": "pruebas_vinculadas_ren001", "dataType": "Int64"},
                    {"name": "archivos_firmados_sha256", "dataType": "Int64"},
                    {"name": "commit_sha", "dataType": "String"},
                    {"name": "cambios_locales", "dataType": "Boolean"},
                    {"name": "alertas_sast_abiertas", "dataType": "Int64"},
                    {"name": "dependabot_prs_abiertos", "dataType": "Int64"},
                    {"name": "paquetes_sbom", "dataType": "Int64"},
                    {"name": "defender_hallazgos", "dataType": "Int64"},
                    {"name": "telemetria_solicitudes_24h", "dataType": "Int64"},
                    {"name": "telemetria_tasa_5xx_pct", "dataType": "Double"},
                    {"name": "estado_accion_boards", "dataType": "String"},
                    {"name": "referencia_boards", "dataType": "String"},
                    {"name": "es_ultima_por_entrega", "dataType": "Boolean"},
                ],
                "measures": [
                    {"name": "Total Corridas", "expression": "COUNTROWS('Corridas')"},
                    {
                        "name": "Corridas Verificadas",
                        "expression": "CALCULATE(COUNTROWS('Corridas'), 'Corridas'[veredicto_ren001] = \"VERIFICADO\")",
                    },
                    {
                        "name": "Corridas Con Brecha",
                        "expression": "CALCULATE(COUNTROWS('Corridas'), 'Corridas'[veredicto_ren001] <> \"VERIFICADO\")",
                    },
                    {
                        "name": "Tasa Cumplimiento %",
                        "expression": "DIVIDE([Corridas Verificadas], [Total Corridas], 0) * 100",
                        "formatString": "0.0",
                    },
                    {
                        "name": "Controles con Evidencia %",
                        "expression": "DIVIDE(CALCULATE(COUNTROWS('Corridas'), 'Corridas'[pruebas_vinculadas_ren001] > 0), [Total Corridas], 0) * 100",
                        "formatString": "0.0",
                    },
                ],
            }
        ],
    }


def _visual_card(idx: int, x: int, y: int, w: int, h: int, measure_name: str, title_text: str) -> dict:
    ref = f"Corridas.{measure_name}"
    vc_config = {
        "name": f"card_{idx}",
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": idx * 100, "width": w, "height": h, "tabOrder": idx * 100}}],
        "singleVisual": {
            "visualType": "card",
            "projections": {"Values": [{"queryRef": ref}]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": "Corridas", "Type": 0}],
                "Select": [
                    {
                        "Measure": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": measure_name},
                        "Name": ref,
                        "NativeReferenceName": title_text,
                    }
                ],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return {
        "x": x,
        "y": y,
        "z": idx * 100,
        "width": w,
        "height": h,
        "config": json.dumps(vc_config),
        "filters": "[]",
    }


def _build_executive_pbix(dataset_id: str) -> bytes:
    cards = [
        _visual_card(1, 24, 18, 290, 128, "Total Corridas", "Corridas Auditadas"),
        _visual_card(2, 330, 18, 290, 128, "Tasa Cumplimiento %", "Cumplimiento REN-001 (%)"),
        _visual_card(3, 636, 18, 290, 128, "Controles con Evidencia %", "Evidencia Determinista (%)"),
        _visual_card(4, 942, 18, 314, 128, "Corridas Verificadas", "Corridas Verificadas"),
    ]

    col_chart_cfg = {
        "name": "chart_entregas_veredicto",
        "layouts": [{"id": 0, "position": {"x": 24, "y": 162, "z": 500, "width": 600, "height": 260, "tabOrder": 500}}],
        "singleVisual": {
            "visualType": "clusteredColumnChart",
            "projections": {
                "Category": [{"queryRef": "Corridas.version", "active": True}],
                "Series": [{"queryRef": "Corridas.veredicto_ren001"}],
                "Y": [{"queryRef": "Corridas.Total Corridas"}],
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": "Corridas", "Type": 0}],
                "Select": [
                    {
                        "Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "version"},
                        "Name": "Corridas.version",
                        "NativeReferenceName": "Entrega",
                    },
                    {
                        "Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "veredicto_ren001"},
                        "Name": "Corridas.veredicto_ren001",
                        "NativeReferenceName": "Dictamen REN-001",
                    },
                    {
                        "Measure": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "Total Corridas"},
                        "Name": "Corridas.Total Corridas",
                        "NativeReferenceName": "Corridas",
                    },
                ],
            },
            "drillFilterOtherVisuals": True,
        },
    }

    donut_cfg = {
        "name": "donut_dictamenes",
        "layouts": [{"id": 0, "position": {"x": 640, "y": 162, "z": 600, "width": 616, "height": 260, "tabOrder": 600}}],
        "singleVisual": {
            "visualType": "donutChart",
            "projections": {
                "Category": [{"queryRef": "Corridas.veredicto_ren001", "active": True}],
                "Y": [{"queryRef": "Corridas.Total Corridas"}],
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": "Corridas", "Type": 0}],
                "Select": [
                    {
                        "Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "veredicto_ren001"},
                        "Name": "Corridas.veredicto_ren001",
                        "NativeReferenceName": "Dictamen",
                    },
                    {
                        "Measure": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "Total Corridas"},
                        "Name": "Corridas.Total Corridas",
                        "NativeReferenceName": "Corridas",
                    },
                ],
            },
            "drillFilterOtherVisuals": True,
        },
    }

    table_cols = [
        ("fecha_utc", "Fecha UTC"),
        ("version", "Entrega"),
        ("veredicto_ren001", "Dictamen REN-001"),
        ("cobertura_criterios_pct", "Criterios %"),
        ("escenarios_dominio_pct", "Escenarios %"),
        ("casos_trx_aprobados", "TRX OK"),
        ("casos_trx_fallidos", "TRX Fallos"),
        ("dependabot_prs_abiertos", "Dependabot PRs"),
        ("estado_accion_boards", "Gobernanza Boards"),
        ("referencia_boards", "Work Item"),
        ("commit_sha", "Commit"),
    ]
    table_cfg = {
        "name": "tabla_historial",
        "layouts": [{"id": 0, "position": {"x": 24, "y": 436, "z": 700, "width": 1232, "height": 264, "tabOrder": 700}}],
        "singleVisual": {
            "visualType": "tableEx",
            "projections": {"Values": [{"queryRef": f"Corridas.{col}"} for col, _ in table_cols]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": "Corridas", "Type": 0}],
                "Select": [
                    {
                        "Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": col},
                        "Name": f"Corridas.{col}",
                        "NativeReferenceName": label,
                    }
                    for col, label in table_cols
                ],
                "OrderBy": [
                    {
                        "Direction": 2,
                        "Expression": {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "fecha_utc"}},
                    }
                ],
            },
            "drillFilterOtherVisuals": True,
        },
    }

    visual_containers = [
        *cards,
        {"x": 24, "y": 162, "z": 500, "width": 600, "height": 260, "config": json.dumps(col_chart_cfg), "filters": "[]"},
        {"x": 640, "y": 162, "z": 600, "width": 616, "height": 260, "config": json.dumps(donut_cfg), "filters": "[]"},
        {"x": 24, "y": 436, "z": 700, "width": 1232, "height": 264, "config": json.dumps(table_cfg), "filters": "[]"},
    ]

    layout = {
        "id": 0,
        "resourcePackages": [],
        "sections": [
            {
                "id": 0,
                "name": "ReportSectionDevSecOps",
                "displayName": "NextGen DevSecOps · Valor Continuo",
                "filters": "[]",
                "ordinal": 0,
                "visualContainers": visual_containers,
                "config": "{}",
                "displayOption": 1,
                "width": 1280,
                "height": 720,
            }
        ],
        "config": json.dumps({
            "version": "5.43",
            "themeCollection": {"baseTheme": {"name": "CY23SU04", "version": "5.45", "type": 2}},
            "activeSectionIndex": 0,
        }),
        "layoutOptimization": 0,
    }

    content_types = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="" />'
        '<Default Extension="json" ContentType="" />'
        '<Override PartName="/Version" ContentType="" />'
        '<Override PartName="/Report/Layout" ContentType="" />'
        '<Override PartName="/Settings" ContentType="" />'
        '<Override PartName="/Metadata" ContentType="" />'
        '<Override PartName="/Connections" ContentType="" />'
        "</Types>"
    )
    connections = {
        "Version": 2,
        "Connections": [
            {
                "Name": "EntityDataSource",
                "ConnectionString": (
                    f"Data Source=pbiazure://api.powerbi.com;"
                    f"Initial Catalog=sobe_wowvirtualserver-{dataset_id};Cube=Model"
                ),
                "ConnectionType": "pbiServiceLive",
                "PbiServiceModelId": 0,
                "PbiModelVirtualServerName": "sobe_wowvirtualserver",
                "PbiModelDatabaseName": dataset_id,
            }
        ],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        zf.writestr("Version", "1.28".encode("utf-16-le"))
        zf.writestr("Connections", json.dumps(connections).encode("utf-8"))
        zf.writestr("Report/Layout", json.dumps(layout).encode("utf-16-le"))
        zf.writestr("Settings", json.dumps({"Version": 3, "ReportSettings": {}}).encode("utf-16-le"))
        zf.writestr(
            "Metadata",
            json.dumps({"Version": 5, "AutoCreatedRelationships": [], "CreatedFrom": "Cloud", "CreatedFromRelease": "2024.05"}).encode("utf-16-le"),
        )
    return buf.getvalue()


def _upload_executive_pbix(token: str, dataset_id: str) -> dict:
    pbix_bytes = _build_executive_pbix(dataset_id)
    boundary = "----NextGenDevSecOpsPBIXBoundary9012"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{REPORT_NAME}.pbix"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + pbix_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    display_enc = urllib.parse.quote(f"{REPORT_NAME}.pbix")
    url = f"{PBI_BASE}/imports?datasetDisplayName={display_enc}&nameConflict=CreateOrOverwrite"
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        imp = json.loads(resp.read())

    imp_id = imp["id"]
    for _ in range(15):
        st = _pbi_json("GET", f"{PBI_BASE}/imports/{imp_id}", token)
        state = st.get("importState")
        if state == "Succeeded":
            reports = st.get("reports") or []
            if reports:
                return reports[0]
            break
        if state == "Failed":
            raise RuntimeError("Power BI rechazó la importación del layout del reporte.")
        time.sleep(0.7)
    raise RuntimeError("Tiempo agotado esperando publicación del reporte en Power BI Service.")


def sync_powerbi_cloud(
    runs_dir: Path,
    *,
    ensure_report: bool = True,
    recreate_report: bool = False,
) -> dict:
    token = _az_token(PBI_RESOURCE)
    if not token:
        raise RuntimeError(
            "No hay sesión Entra ID activa con acceso a Power BI Service (ejecutá 'az login')."
        )

    datasets = (_pbi_json("GET", f"{PBI_BASE}/datasets", token).get("value")) or []
    ds = next((d for d in datasets if d.get("name") == DATASET_NAME), None)
    if not ds:
        created = _pbi_json("POST", f"{PBI_BASE}/datasets?defaultRetentionPolicy=None", token, _dataset_schema())
        ds = _pbi_json("GET", f"{PBI_BASE}/datasets/{created['id']}", token)
    else:
        ds = _pbi_json("GET", f"{PBI_BASE}/datasets/{ds['id']}", token)

    dataset_id = ds["id"]
    dataset_url = ds.get("webUrl") or f"https://app.powerbi.com/groups/me/datasets/{dataset_id}"

    # Preparar y reemplazar filas en tiempo real
    metrics = build_powerbi_metrics(runs_dir)
    latest_ids = {r["ejecucion_id"] for r in metrics["ultimas_por_entrega"].values()}
    rows = []
    for r in metrics["corridas"]:
        clean_row = {k: v for k, v in r.items() if k != "defender_puntaje_pct"}
        clean_row["es_ultima_por_entrega"] = r["ejecucion_id"] in latest_ids
        rows.append(clean_row)

    _pbi_json("DELETE", f"{PBI_BASE}/datasets/{dataset_id}/tables/Corridas/rows", token)
    if rows:
        # Power BI Push API permite hasta 10,000 filas por POST
        for offset in range(0, len(rows), 5000):
            _pbi_json(
                "POST",
                f"{PBI_BASE}/datasets/{dataset_id}/tables/Corridas/rows",
                token,
                {"rows": rows[offset:offset + 5000]},
            )

    reports = (_pbi_json("GET", f"{PBI_BASE}/reports", token).get("value")) or []
    report = next(
        (rep for rep in reports if rep.get("name") == REPORT_NAME and rep.get("datasetId") == dataset_id),
        None,
    )
    if ensure_report and (report is None or recreate_report):
        report = _upload_executive_pbix(token, dataset_id)

    report_url = (report or {}).get("webUrl") or dataset_url
    state = {
        "sincronizado": True,
        "dataset_id": dataset_id,
        "dataset_url": dataset_url,
        "report_id": (report or {}).get("id"),
        "report_url": report_url,
        "filas_sincronizadas": len(rows),
        "actualizado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _save_powerbi_state(runs_dir, state)
    return state
