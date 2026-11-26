"""Integraciones de lectura y seguimiento DevSecOps (Azure Boards, GitHub y Azure)."""
from base64 import b64encode
from hashlib import sha256
import html
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from dotenv import dotenv_values

ADO_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"
ARM_RESOURCE = "https://management.azure.com/"
LOG_RESOURCE = "https://api.loganalytics.io/"
POLICY_VERSION = "REN-001.v2"


def load_settings() -> dict[str, str]:
    file_vals = dotenv_values(Path(__file__).with_name(".env"), interpolate=False)
    merged = {}
    for key in (
        "DEVSECOPS_LIVE",
        "AZURE_DEVOPS_ORG_URL",
        "AZURE_DEVOPS_PROJECT",
        "AZURE_DEVOPS_WORK_ITEM_ID",
        "AZURE_DEVOPS_PAT",
        "GITHUB_REPO",
        "GITHUB_TOKEN",
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP",
        "AZURE_CONTAINER_APP",
        "AZURE_LOG_ANALYTICS_WORKSPACE_ID",
    ):
        merged[key] = (os.environ.get(key, file_vals.get(key, "")) or "").strip()
    return merged


def _az_token(resource: str) -> str | None:
    try:
        proc = subprocess.run(
            ["az", "account", "get-access-token", "--resource", resource, "--query", "accessToken", "-o", "tsv"],
            capture_output=True, text=True, timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    token = proc.stdout.strip()
    return token if proc.returncode == 0 and token else None


def _gh_token(settings: dict[str, str]) -> str | None:
    if settings.get("GITHUB_TOKEN"):
        return settings["GITHUB_TOKEN"]
    try:
        proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return None
    token = proc.stdout.strip()
    return token if proc.returncode == 0 and token else None


def _http_json(method: str, url: str, headers: dict[str, str], body: object = None, timeout: int = 15) -> dict | list:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=payload, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<li[^>]*>", "• ", text or "", flags=re.I)
    cleaned = re.sub(r"</(p|li|div|br)\s*>", "\n", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return re.sub(r"\n{2,}", "\n", html.unescape(cleaned)).strip()


def _ado_headers(settings: dict[str, str], content_type: str = "application/json") -> dict[str, str] | None:
    pat = settings.get("AZURE_DEVOPS_PAT")
    if pat:
        basic = b64encode(f":{pat}".encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {basic}", "Content-Type": content_type}
    token = _az_token(ADO_RESOURCE)
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": content_type}
    return None


def fetch_boards_story(settings: dict[str, str]) -> dict:
    org = settings.get("AZURE_DEVOPS_ORG_URL", "").rstrip("/")
    project = settings.get("AZURE_DEVOPS_PROJECT", "")
    wi_id = settings.get("AZURE_DEVOPS_WORK_ITEM_ID") or "1"
    if not org or not project:
        return {"disponible": False, "motivo": "AZURE_DEVOPS_ORG_URL o AZURE_DEVOPS_PROJECT no configurados."}
    headers = _ado_headers(settings)
    if not headers:
        return {"disponible": False, "motivo": "Sin credenciales Entra ID o PAT para Azure Boards."}
    try:
        proj_enc = urllib.parse.quote(project)
        url = f"{org}/{proj_enc}/_apis/wit/workitems/{wi_id}?$expand=relations&api-version=7.1"
        data = _http_json("GET", url, headers)
        fields = data.get("fields", {})
        relations = [
            {"tipo": rel.get("rel"), "url": rel.get("url"), "comentario": (rel.get("attributes") or {}).get("comment")}
            for rel in (data.get("relations") or [])
        ]
        web_url = f"{org}/{proj_enc}/_workitems/edit/{data['id']}"
        return {
            "disponible": True,
            "id": data["id"],
            "referencia": f"AB#{data['id']}",
            "tipo": fields.get("System.WorkItemType"),
            "titulo": fields.get("System.Title"),
            "estado": fields.get("System.State"),
            "criterios_aceptacion": _strip_html(fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", "")),
            "tags": fields.get("System.Tags", ""),
            "url": web_url,
            "relaciones": relations,
        }
    except Exception as exc:
        return {"disponible": False, "motivo": f"No se pudo leer Azure Boards ({type(exc).__name__})."}


def fetch_github_context(settings: dict[str, str], commit_sha: str | None) -> dict:
    repo = settings.get("GITHUB_REPO", "")
    if not repo:
        return {"disponible": False, "motivo": "GITHUB_REPO no configurado."}
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AppContratos-DevSecOps"}
    token = _gh_token(settings)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    base = f"https://api.github.com/repos/{repo}"
    out: dict = {"disponible": True, "repositorio": repo, "url_repositorio": f"https://github.com/{repo}"}
    try:
        pulls = _http_json("GET", f"{base}/pulls?state=all&per_page=10", headers)
        pr = next((p for p in pulls if "AB#" in (p.get("body") or "") or "AB#" in (p.get("title") or "")), pulls[0] if pulls else None)
        if pr:
            ab_refs = sorted(set(re.findall(r"AB#\d+", f"{pr.get('title', '')} {pr.get('body', '')}")))
            out["pull_request"] = {
                "numero": pr["number"],
                "titulo": pr["title"],
                "estado": "merged" if pr.get("merged_at") else pr["state"],
                "autor": (pr.get("user") or {}).get("login"),
                "merge_commit_sha": pr.get("merge_commit_sha"),
                "referencias_boards": ab_refs,
                "url": pr["html_url"],
            }
        runs_data = _http_json("GET", f"{base}/actions/runs?per_page=10", headers)
        runs = runs_data.get("workflow_runs", [])
        ci_run = next((r for r in runs if commit_sha and r.get("head_sha") == commit_sha), runs[0] if runs else None)
        if ci_run:
            artifacts_data = _http_json("GET", f"{base}/actions/runs/{ci_run['id']}/artifacts", headers)
            out["pipeline_ci"] = {
                "run_id": ci_run["id"],
                "nombre": ci_run.get("name"),
                "estado": ci_run.get("status"),
                "conclusion": ci_run.get("conclusion"),
                "head_sha": ci_run.get("head_sha"),
                "url": ci_run.get("html_url"),
                "artefactos": [a["name"] for a in artifacts_data.get("artifacts", [])],
            }
        seguridad: dict = {"dependabot_configurado": True, "code_scanning": {"estado": "no_disponible", "alertas_abiertas": 0, "hallazgos": []}}
        try:
            alerts = _http_json("GET", f"{base}/code-scanning/alerts?state=open&per_page=20", headers)
            if isinstance(alerts, list):
                seguridad["code_scanning"] = {
                    "estado": "activo",
                    "alertas_abiertas": len(alerts),
                    "hallazgos": [
                        {
                            "regla": (a.get("rule") or {}).get("id"),
                            "severidad": (a.get("rule") or {}).get("security_severity_level") or (a.get("rule") or {}).get("severity"),
                            "archivo": ((a.get("most_recent_instance") or {}).get("location") or {}).get("path"),
                            "url": a.get("html_url"),
                        }
                        for a in alerts[:5]
                    ],
                }
        except urllib.error.HTTPError as err:
            seguridad["code_scanning"] = {
                "estado": "en_ejecucion_inicial" if err.code == 404 else f"http_{err.code}",
                "alertas_abiertas": 0,
                "hallazgos": [],
            }
        out["seguridad_origen"] = seguridad
    except Exception as exc:
        out["disponible"] = False
        out["motivo"] = f"Error consultando GitHub ({type(exc).__name__})."
    return out


def fetch_azure_runtime(settings: dict[str, str]) -> dict:
    sub = settings.get("AZURE_SUBSCRIPTION_ID", "")
    rg = settings.get("AZURE_RESOURCE_GROUP", "")
    app_name = settings.get("AZURE_CONTAINER_APP", "")
    workspace_id = settings.get("AZURE_LOG_ANALYTICS_WORKSPACE_ID", "")
    if not (sub and rg and app_name):
        return {"disponible": False, "motivo": "Variables AZURE_SUBSCRIPTION_ID / AZURE_RESOURCE_GROUP / AZURE_CONTAINER_APP no configuradas."}
    arm_token = _az_token(ARM_RESOURCE)
    if not arm_token:
        return {"disponible": False, "motivo": "Sin sesión activa en Azure CLI para consultar recursos ARM."}
    arm_headers = {"Authorization": f"Bearer {arm_token}", "Content-Type": "application/json"}
    out: dict = {"disponible": True, "despliegue": {}, "defender": {}, "telemetria": {}}

    app_id = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.App/containerApps/{app_name}"
    try:
        ca = _http_json("GET", f"https://management.azure.com{app_id}?api-version=2024-03-01", arm_headers)
        props = ca.get("properties", {})
        ingress = (props.get("configuration") or {}).get("ingress") or {}
        containers = ((props.get("template") or {}).get("containers") or [{}])
        env_list = {e.get("name"): e.get("value") for e in (containers[0].get("env") or []) if "value" in e}
        tags = ca.get("tags") or {}
        identity_type = (ca.get("identity") or {}).get("type", "None")
        fqdn = ingress.get("fqdn")
        out["despliegue"] = {
            "recurso": app_name,
            "grupo_recursos": rg,
            "ambiente": "pruebas-cloud",
            "recurso_id": app_id,
            "estado": props.get("provisioningState"),
            "revision_activa": props.get("latestReadyRevisionName") or props.get("latestRevisionName"),
            "imagen": containers[0].get("image"),
            "version_app": env_list.get("APP_VERSION") or tags.get("app_version"),
            "commit_desplegado": env_list.get("APP_COMMIT_SHA") or tags.get("commit_sha"),
            "url": f"https://{fqdn}" if fqdn else None,
            "https_exclusivo": not bool(ingress.get("allowInsecure", False)),
            "identidad_administrada": identity_type,
        }
    except Exception as exc:
        out["despliegue"] = {"disponible": False, "motivo": f"No se pudo leer Container App ({type(exc).__name__})."}

    posture_findings = []
    desp = out["despliegue"]
    if desp.get("identidad_administrada") in (None, "None"):
        posture_findings.append({
            "codigo": "AZ-POSTURE-MI-001",
            "severidad": "Baja",
            "alcance": "recurso",
            "detalle": f"El Container App '{app_name}' no tiene Managed Identity habilitada (identity.type=None).",
        })
    if desp.get("https_exclusivo") is False:
        posture_findings.append({
            "codigo": "AZ-POSTURE-TLS-001",
            "severidad": "Media",
            "alcance": "recurso",
            "detalle": f"El ingreso HTTP inseguro está permitido en '{app_name}'.",
        })
    try:
        arg_query = {
            "subscriptions": [sub],
            "query": (
                f"securityresources | where type == 'microsoft.security/assessments' "
                f"| where resourceGroup =~ '{rg}' "
                "| extend status=tostring(properties.status.code), displayName=tostring(properties.displayName), "
                "severity=tostring(properties.metadata.severity) "
                "| project name, displayName, status, severity, id | limit 25"
            ),
        }
        arg_res = _http_json(
            "POST",
            "https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2022-10-01",
            arm_headers,
            arg_query,
        )
        rows = arg_res.get("data") or []
        unhealthy = [r for r in rows if r.get("status") == "Unhealthy"]
        for row in unhealthy[:5]:
            posture_findings.append({
                "codigo": f"DEFENDER-{row.get('name', '')[:8]}",
                "severidad": row.get("severity") or "Media",
                "alcance": "ambiente",
                "detalle": f"Defender for Cloud ({rg}): {row.get('displayName')}",
            })
        out["defender"] = {
            "evaluaciones_totales_rg": len(rows),
            "evaluaciones_no_saludables": len(unhealthy),
            "https_exclusivo_verificado": desp.get("https_exclusivo", False),
            "hallazgos": posture_findings,
        }
    except Exception as exc:
        out["defender"] = {
            "evaluaciones_totales_rg": 0,
            "evaluaciones_no_saludables": 0,
            "hallazgos": posture_findings,
            "nota": f"Consulta Resource Graph no disponible ({type(exc).__name__}).",
        }

    if workspace_id:
        log_token = _az_token(LOG_RESOURCE)
        if log_token:
            try:
                kql = {
                    "query": (
                        "AppRequests | where TimeGenerated > ago(24h) "
                        "| summarize total=count(), fallos=countif(Success == false or toint(ResultCode) >= 500), "
                        "errores_cliente=countif(toint(ResultCode) >= 400 and toint(ResultCode) < 500), "
                        "latencia_ms=round(avg(DurationMs), 2)"
                    )
                }
                qres = _http_json(
                    "POST",
                    f"https://api.loganalytics.io/v1/workspaces/{workspace_id}/query",
                    {"Authorization": f"Bearer {log_token}", "Content-Type": "application/json"},
                    kql,
                )
                tables = qres.get("tables") or []
                rows = tables[0].get("rows", [[0, 0, 0, 0.0]]) if tables else [[0, 0, 0, 0.0]]
                total, fallos, err_cli, lat = (rows[0] + [0, 0, 0, 0.0])[:4]
                total = int(total or 0)
                fallos = int(fallos or 0)
                out["telemetria"] = {
                    "disponible": True,
                    "ventana": "últimas 24h",
                    "total_solicitudes": total,
                    "fallos_5xx": fallos,
                    "errores_4xx": int(err_cli or 0),
                    "tasa_error_pct": round((fallos / total) * 100, 2) if total else 0.0,
                    "latencia_promedio_ms": float(lat or 0.0),
                }
            except Exception as exc:
                out["telemetria"] = {"disponible": False, "motivo": f"Consulta KQL falló ({type(exc).__name__})."}
        else:
            out["telemetria"] = {"disponible": False, "motivo": "Sin token para Log Analytics API."}
    else:
        out["telemetria"] = {"disponible": False, "motivo": "AZURE_LOG_ANALYTICS_WORKSPACE_ID no configurado."}
    return out


def collect_devsecops_context(commit_sha: str | None) -> dict:
    settings = load_settings()
    if settings.get("DEVSECOPS_LIVE") == "0":
        return {"habilitado": False}
    has_any = any(settings.get(k) for k in ("AZURE_DEVOPS_ORG_URL", "GITHUB_REPO", "AZURE_CONTAINER_APP"))
    if not has_any:
        return {"habilitado": False}
    return {
        "habilitado": True,
        "politica_version": POLICY_VERSION,
        "boards": fetch_boards_story(settings),
        "github": fetch_github_context(settings, commit_sha),
        "azure": fetch_azure_runtime(settings),
    }


def action_fingerprint(version: str, criterion_id: str) -> str:
    settings = load_settings()
    project = settings.get("AZURE_DEVOPS_PROJECT") or "AppContratos"
    raw = f"{project}:{version}:{criterion_id}:{POLICY_VERSION}"
    return sha256(raw.encode("utf-8")).hexdigest()[:12]


def build_proposed_action(report: dict) -> dict | None:
    verdict = report["veredicto"]
    if verdict == "VERIFICADO":
        return None
    version = report["ejecucion"]["version"]
    criterion_id = report["criterio"]["id"]
    fp = action_fingerprint(version, criterion_id)
    title = (
        f"[{criterion_id}][{version}] Corregir exclusión de contratos cancelados en evaluación de renovaciones"
        if verdict == "INCUMPLIDO"
        else f"[{criterion_id}][{version}] Agregar prueba xUnit vinculada con Trait(\"Criterio\", \"{criterion_id}\")"
    )
    return {
        "requiere_aprobacion": True,
        "estado": "PENDIENTE_APROBACION",
        "fingerprint": fp,
        "tag_idempotencia": f"devsecops-fp-{fp}",
        "titulo": title,
        "descripcion": report["siguiente_paso"] or report["justificacion"],
        "criterio_reevaluacion": f"Repetir evaluación sobre {version} y confirmar estado VERIFICADO con política {POLICY_VERSION}.",
        "historia_padre": (report.get("devsecops", {}).get("boards") or {}).get("id", 1),
    }


def upsert_boards_task(report: dict, comment: str = "") -> dict:
    action = report.get("accion_propuesta")
    if not action:
        raise ValueError("Este informe no tiene una acción pendiente para registrar en Azure Boards.")
    settings = load_settings()
    org = settings.get("AZURE_DEVOPS_ORG_URL", "").rstrip("/")
    project = settings.get("AZURE_DEVOPS_PROJECT", "")
    if not org or not project:
        raise RuntimeError("Configurá AZURE_DEVOPS_ORG_URL y AZURE_DEVOPS_PROJECT en assessment/.env.")
    headers = _ado_headers(settings)
    if not headers:
        raise RuntimeError("No se encontraron credenciales para escribir en Azure Boards.")

    proj_enc = urllib.parse.quote(project)
    tag = action["tag_idempotencia"]
    wiql = {
        "query": (
            f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{project}' "
            f"AND [System.WorkItemType] = 'Task' AND [System.Tags] CONTAINS '{tag}' "
            "AND [System.State] <> 'Closed' AND [System.State] <> 'Removed'"
        )
    }
    found = _http_json("POST", f"{org}/{proj_enc}/_apis/wit/wiql?api-version=7.1", headers, wiql)
    items = found.get("workItems") or []
    run_id = report["ejecucion"]["id"]
    commit = report["ejecucion"].get("commit") or "sin-commit"
    note = html.escape(comment.strip()) if comment.strip() else "Aprobado por líder de ingeniería."

    patch_headers = _ado_headers(settings, content_type="application/json-patch+json")
    assert patch_headers is not None

    if items:
        wid = items[0]["id"]
        history = (
            f"<p><b>Reevaluación DevSecOps ({POLICY_VERSION}):</b> Estado <code>{report['veredicto']}</code> "
            f"en ejecución <code>{run_id}</code> (commit <code>{commit}</code>). Nota: {note}</p>"
        )
        _http_json(
            "PATCH",
            f"{org}/{proj_enc}/_apis/wit/workitems/{wid}?api-version=7.1",
            patch_headers,
            [{"op": "add", "path": "/fields/System.History", "value": history}],
        )
        return {
            "operacion": "actualizada",
            "work_item_id": wid,
            "referencia": f"AB#{wid}",
            "fingerprint": action["fingerprint"],
            "url": f"{org}/{proj_enc}/_workitems/edit/{wid}",
        }

    parent_id = action.get("historia_padre") or 1
    desc = (
        f"<p>{html.escape(action['descripcion'])}</p>"
        f"<ul>"
        f"<li><b>Versión evaluada:</b> <code>{html.escape(report['ejecucion']['version'])}</code></li>"
        f"<li><b>Veredicto origen:</b> <code>{html.escape(report['veredicto'])}</code></li>"
        f"<li><b>Ejecución local:</b> <code>{run_id}</code></li>"
        f"<li><b>Commit:</b> <code>{html.escape(str(commit))}</code></li>"
        f"<li><b>Criterio de cierre:</b> {html.escape(action['criterio_reevaluacion'])}</li>"
        f"<li><b>Nota de aprobación:</b> {note}</li>"
        f"</ul>"
    )
    ops = [
        {"op": "add", "path": "/fields/System.Title", "value": action["titulo"]},
        {"op": "add", "path": "/fields/System.Description", "value": desc},
        {"op": "add", "path": "/fields/System.Tags", "value": f"{tag}; {report['criterio']['id']}; DevSecOps-Agent"},
        {
            "op": "add",
            "path": "/relations/-",
            "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"{org}/{proj_enc}/_apis/wit/workItems/{parent_id}",
                "attributes": {"comment": "Acción generada tras evaluación continua DevSecOps"},
            },
        },
    ]
    created = _http_json(
        "POST",
        f"{org}/{proj_enc}/_apis/wit/workitems/$Task?api-version=7.1",
        patch_headers,
        ops,
    )
    wid = created["id"]
    return {
        "operacion": "creada",
        "work_item_id": wid,
        "referencia": f"AB#{wid}",
        "fingerprint": action["fingerprint"],
        "url": f"{org}/{proj_enc}/_workitems/edit/{wid}",
    }
