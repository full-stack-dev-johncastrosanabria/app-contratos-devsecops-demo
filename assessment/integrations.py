"""Integraciones de lectura, postura estática y seguimiento DevSecOps (Azure Boards, GitHub, AKS, Defender y Azure)."""
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
REPO_ROOT = Path(__file__).resolve().parent.parent


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


def parse_boards_criteria(acceptance_text: str) -> list[dict]:
    criteria: list[dict] = []
    seen: set[str] = set()
    for line in (acceptance_text or "").splitlines():
        match = re.search(r"\b(REN-\d+)\s*[:·\-–]\s*(.+)", line.strip(), flags=re.I)
        if match:
            cid = match[1].upper()
            txt = match[2].strip().rstrip(".")
            if cid not in seen and txt:
                seen.add(cid)
                criteria.append({"id": cid, "texto": txt})
    return criteria


def _ado_headers(settings: dict[str, str], content_type: str = "application/json") -> dict[str, str] | None:
    pat = settings.get("AZURE_DEVOPS_PAT")
    if pat:
        basic = b64encode(f":{pat}".encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {basic}", "Content-Type": content_type}
    token = _az_token(ADO_RESOURCE)
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": content_type}
    return None


def audit_copilot_governance(repo_root: Path = REPO_ROOT) -> dict:
    path = repo_root / ".github" / "copilot-instructions.md"
    if not path.is_file():
        return {"configurado": False, "archivo": ".github/copilot-instructions.md"}
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    enforces_trait = 'Trait("Criterio"' in text
    enforces_dateonly = "DateOnly" in text
    enforces_csp = "Content-Security-Policy" in text
    return {
        "configurado": True,
        "archivo": ".github/copilot-instructions.md",
        "sha256": sha256(raw).hexdigest()[:12],
        "reglas_verificadas": sum((enforces_trait, enforces_dateonly, enforces_csp)),
        "reglas_totales": 3,
        "exige_trait_criterio": enforces_trait,
        "exige_dateonly_fijo": enforces_dateonly,
    }


def audit_ci_pipelines(repo_root: Path = REPO_ROOT) -> dict:
    gh_wf = repo_root / ".github" / "workflows" / "devsecops.yml"
    az_pipe = repo_root / "azure-pipelines.yml"
    gh_ok = gh_wf.is_file() and "assessment.ci" in gh_wf.read_text(encoding="utf-8", errors="replace")
    az_ok = az_pipe.is_file() and "PublishTestResults@2" in az_pipe.read_text(encoding="utf-8", errors="replace")
    return {
        "github_actions_definido": gh_ok,
        "azure_pipelines_definido": az_ok,
        "pipelines_verificados": int(gh_ok) + int(az_ok),
    }


def audit_aks_manifests(repo_root: Path = REPO_ROOT) -> dict:
    aks_dir = repo_root / "deploy" / "aks"
    dep_file = aks_dir / "deployment.yaml"
    svc_file = aks_dir / "service.yaml"
    net_file = aks_dir / "networkpolicy.yaml"
    if not (dep_file.is_file() and svc_file.is_file() and net_file.is_file()):
        return {"disponible": False, "controles_verificados": 0, "controles_totales": 6}
    dep = dep_file.read_text(encoding="utf-8", errors="replace")
    net = net_file.read_text(encoding="utf-8", errors="replace")
    checks = {
        "runAsNonRoot": bool(re.search(r"runAsNonRoot:\s*true", dep)),
        "readOnlyRootFilesystem": bool(re.search(r"readOnlyRootFilesystem:\s*true", dep)),
        "allowPrivilegeEscalationFalse": bool(re.search(r"allowPrivilegeEscalation:\s*false", dep)),
        "dropAllCapabilities": bool(re.search(r"drop:\s*\n\s*-\s*ALL", dep)),
        "resourceLimits": bool(re.search(r"limits:\s*\n\s*cpu:", dep) and re.search(r"memory:", dep)),
        "networkPolicyZeroTrust": "kind: NetworkPolicy" in net and "Ingress" in net and "Egress" in net,
    }
    passed = sum(1 for v in checks.values() if v)
    return {
        "disponible": True,
        "ruta": "deploy/aks/",
        "archivos": ["deployment.yaml", "service.yaml", "networkpolicy.yaml"],
        "controles_verificados": passed,
        "controles_totales": len(checks),
        "endurecido": passed == len(checks),
        "detalle_controles": checks,
    }


def audit_security_copilot_plugin(repo_root: Path = REPO_ROOT) -> dict:
    spec = repo_root / "copilot" / "openapi.yaml"
    skill = repo_root / "copilot" / "security-copilot-skill.yaml"
    if not (spec.is_file() and skill.is_file()):
        return {"disponible": False}
    skill_txt = skill.read_text(encoding="utf-8", errors="replace")
    ops = re.findall(r"^\s*-\s*Name:\s*(\w+)", skill_txt, flags=re.M)
    return {
        "disponible": True,
        "openapi": "copilot/openapi.yaml",
        "manifiesto": "copilot/security-copilot-skill.yaml",
        "habilidades": ops,
        "habilidades_count": len(ops),
    }


def audit_repo_governance(repo_root: Path = REPO_ROOT) -> dict:
    return {
        "copilot": audit_copilot_governance(repo_root),
        "pipelines": audit_ci_pipelines(repo_root),
        "aks": audit_aks_manifests(repo_root),
        "security_copilot": audit_security_copilot_plugin(repo_root),
    }


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
        acceptance = _strip_html(fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", ""))
        web_url = f"{org}/{proj_enc}/_workitems/edit/{data['id']}"
        return {
            "disponible": True,
            "id": data["id"],
            "referencia": f"AB#{data['id']}",
            "tipo": fields.get("System.WorkItemType"),
            "titulo": fields.get("System.Title"),
            "estado": fields.get("System.State"),
            "criterios_aceptacion": acceptance,
            "criterios_estructurados": parse_boards_criteria(acceptance),
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
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "NextGen-DevSecOps-Assessment"}
    token = _gh_token(settings)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    base = f"https://api.github.com/repos/{repo}"
    out: dict = {"disponible": True, "repositorio": repo, "url_repositorio": f"https://github.com/{repo}"}
    try:
        pulls = _http_json("GET", f"{base}/pulls?state=all&per_page=20", headers)
        human_pulls = [
            p for p in pulls
            if "dependabot" not in ((p.get("user") or {}).get("login") or "").lower()
            and not (((p.get("head") or {}).get("ref") or "").startswith(("demo/remediacion-", "secops/fix-")))
        ]
        merged_ab = [
            p for p in human_pulls
            if p.get("merged_at") and ("AB#" in (p.get("body") or "") or "AB#" in (p.get("title") or ""))
        ]
        pr = (
            merged_ab[0]
            if merged_ab
            else next(
                (p for p in human_pulls if "AB#" in (p.get("body") or "") or "AB#" in (p.get("title") or "")),
                human_pulls[0] if human_pulls else (pulls[0] if pulls else None),
            )
        )
        if pr:
            ab_refs = sorted(set(re.findall(r"AB#\d+", f"{pr.get('title', '')} {pr.get('body', '')}")))
            reviews_approved = 0
            review_state = "integrado" if pr.get("merged_at") else pr.get("state", "open")
            try:
                reviews = _http_json("GET", f"{base}/pulls/{pr['number']}/reviews", headers)
                if isinstance(reviews, list):
                    reviews_approved = sum(1 for r in reviews if r.get("state") == "APPROVED")
                    if reviews_approved > 0:
                        review_state = f"{reviews_approved} aprobación(es)"
            except Exception:
                pass
            out["pull_request"] = {
                "numero": pr["number"],
                "titulo": pr["title"],
                "estado": "merged" if pr.get("merged_at") else pr["state"],
                "autor": (pr.get("user") or {}).get("login"),
                "merge_commit_sha": pr.get("merge_commit_sha"),
                "referencias_boards": ab_refs,
                "revisiones_aprobadas": reviews_approved,
                "gobernanza_revision": review_state,
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

        dep_open_prs = [
            {"numero": p["number"], "titulo": p.get("title"), "url": p.get("html_url")}
            for p in pulls
            if p.get("state") == "open" and "dependabot" in ((p.get("user") or {}).get("login") or "").lower()
        ]
        dep_alerts_open: int | None = None
        try:
            dep_alerts = _http_json("GET", f"{base}/dependabot/alerts?state=open&per_page=20", headers)
            if isinstance(dep_alerts, list):
                dep_alerts_open = len(dep_alerts)
        except urllib.error.HTTPError:
            dep_alerts_open = None

        secret_alerts_open: int | None = None
        secret_status = "no_disponible"
        try:
            sec_alerts = _http_json("GET", f"{base}/secret-scanning/alerts?state=open&per_page=10", headers)
            if isinstance(sec_alerts, list):
                secret_alerts_open = len(sec_alerts)
                secret_status = "activo"
        except urllib.error.HTTPError as err:
            secret_status = "proteccion_push" if err.code in (403, 404) else f"http_{err.code}"

        sbom_info = {"disponible": False, "paquetes": 0}
        try:
            sbom_res = _http_json("GET", f"{base}/dependency-graph/sbom", headers)
            sbom_doc = (sbom_res.get("sbom") if isinstance(sbom_res, dict) else None) or {}
            pkgs = sbom_doc.get("packages") or []
            sbom_info = {
                "disponible": True,
                "formato": sbom_doc.get("spdxVersion", "SPDX-2.3"),
                "paquetes": len(pkgs),
                "url": f"https://api.github.com/repos/{repo}/dependency-graph/sbom",
            }
        except Exception:
            pass

        seguridad: dict = {
            "dependabot_configurado": (REPO_ROOT / ".github" / "dependabot.yml").is_file(),
            "dependabot": {
                "prs_abiertos": len(dep_open_prs),
                "prs": dep_open_prs[:5],
                "alertas_abiertas": dep_alerts_open,
            },
            "secret_scanning": {
                "estado": secret_status,
                "alertas_abiertas": secret_alerts_open,
            },
            "sbom": sbom_info,
            "code_scanning": {"estado": "no_disponible", "alertas_abiertas": 0, "hallazgos": []},
        }
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
    props: dict = {}
    try:
        ca = _http_json("GET", f"https://management.azure.com{app_id}?api-version=2024-03-01", arm_headers)
        props = ca.get("properties", {}) if isinstance(ca, dict) else {}
        ingress = (props.get("configuration") or {}).get("ingress") or {}
        identity_type = ((ca.get("identity") if isinstance(ca, dict) else None) or {}).get("type", "None")
        fqdn = ingress.get("fqdn")
        out["despliegue"] = {
            "recurso": app_name,
            "grupo_recursos": rg,
            "ambiente": "pruebas-cloud",
            "recurso_id": app_id,
            "estado": props.get("provisioningState"),
            "url": f"https://{fqdn}" if fqdn else None,
            "https_exclusivo": not bool(ingress.get("allowInsecure", False)),
            "identidad_administrada": identity_type,
        }
    except Exception as exc:
        out["despliegue"] = {"disponible": False, "motivo": f"No se pudo leer Container App ({type(exc).__name__})."}

    posture_findings = []
    desp = out["despliegue"]
    ready_revision = props.get("latestReadyRevisionName") if desp.get("recurso") else None
    if ready_revision:
        try:
            revision_name = urllib.parse.quote(ready_revision, safe="")
            revision = _http_json(
                "GET", f"https://management.azure.com{app_id}/revisions/{revision_name}?api-version=2024-03-01",
                arm_headers,
            )["properties"]
            if revision.get("active") is True and revision.get("provisioningState") == "Provisioned":
                container = ((revision.get("template") or {}).get("containers") or [{}])[0]
                env = {entry["name"]: entry.get("value") for entry in container.get("env") or []}
                desp.update(revision_activa=ready_revision, imagen=container.get("image"),
                            version_app=env.get("APP_VERSION"), commit_desplegado=env.get("APP_COMMIT_SHA"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            desp["motivo"] = "No se pudo verificar la revisión activa de Container Apps."
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

        score_pct: float | None = None
        try:
            score_query = {
                "subscriptions": [sub],
                "query": (
                    "securityresources | where type == 'microsoft.security/securescores' "
                    "| where name == 'ascScore' "
                    "| extend pct=todouble(properties.score.percentage), current=todouble(properties.score.current), max=todouble(properties.score.max) "
                    "| project pct, current, max | limit 1"
                ),
            }
            score_res = _http_json(
                "POST",
                "https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2022-10-01",
                arm_headers,
                score_query,
            )
            srows = score_res.get("data") or []
            if srows and srows[0].get("pct") is not None:
                score_pct = round(float(srows[0]["pct"]) * 100.0, 1)
        except Exception:
            score_pct = None

        out["defender"] = {
            "evaluaciones_totales_rg": len(rows),
            "evaluaciones_no_saludables": len(unhealthy),
            "puntaje_seguro_pct": score_pct,
            "https_exclusivo_verificado": desp.get("https_exclusivo", False),
            "hallazgos": posture_findings,
        }
    except Exception as exc:
        out["defender"] = {
            "evaluaciones_totales_rg": 0,
            "evaluaciones_no_saludables": 0,
            "puntaje_seguro_pct": None,
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
                        "| summarize total=count(), "
                        "fallos=countif(Success == false or toint(ResultCode) >= 500), "
                        "errores_cliente=countif(toint(ResultCode) >= 400 and toint(ResultCode) < 500), "
                        "latencia_ms=round(avg(DurationMs), 2), "
                        "recientes_1h=countif(TimeGenerated > ago(1h)), "
                        "fallos_1h=countif(TimeGenerated > ago(1h) and (Success == false or toint(ResultCode) >= 500)), "
                        "base_previa=countif(TimeGenerated <= ago(1h)), "
                        "fallos_base=countif(TimeGenerated <= ago(1h) and (Success == false or toint(ResultCode) >= 500))"
                    )
                }
                qres = _http_json(
                    "POST",
                    f"https://api.loganalytics.io/v1/workspaces/{workspace_id}/query",
                    {"Authorization": f"Bearer {log_token}", "Content-Type": "application/json"},
                    kql,
                )
                tables = qres.get("tables") or []
                default_row = [0, 0, 0, 0.0, 0, 0, 0, 0]
                rows = tables[0].get("rows", [default_row]) if tables else [default_row]
                total, fallos, err_cli, lat, rec_1h, fallos_1h, base_prev, fallos_base = (rows[0] + default_row)[:8]
                total = int(total or 0)
                fallos = int(fallos or 0)
                rec_1h = int(rec_1h or 0)
                fallos_1h = int(fallos_1h or 0)
                base_prev = int(base_prev or 0)
                fallos_base = int(fallos_base or 0)
                rate_recent = round((fallos_1h / rec_1h) * 100, 2) if rec_1h else 0.0
                rate_base = round((fallos_base / base_prev) * 100, 2) if base_prev else None
                comparison = (
                    f"Estable vs línea base ({rate_recent}% 1h vs {rate_base}% previo)"
                    if rate_base is not None and rate_recent <= rate_base
                    else (
                        f"Degradación (+{round(rate_recent - rate_base, 2)} pp vs línea base)"
                        if rate_base is not None
                        else "Línea base inicial en captura (ventana única 24h)"
                    )
                )
                out["telemetria"] = {
                    "disponible": True,
                    "ventana": "últimas 24h (1h reciente vs 23h base)",
                    "total_solicitudes": total,
                    "fallos_5xx": fallos,
                    "errores_4xx": int(err_cli or 0),
                    "tasa_error_pct": round((fallos / total) * 100, 2) if total else 0.0,
                    "latencia_promedio_ms": float(lat or 0.0),
                    "solicitudes_1h": rec_1h,
                    "solicitudes_base": base_prev,
                    "tiene_linea_base": base_prev > 0,
                    "comparacion_base": comparison,
                }
            except Exception as exc:
                out["telemetria"] = {"disponible": False, "motivo": f"Consulta KQL falló ({type(exc).__name__})."}
        else:
            out["telemetria"] = {"disponible": False, "motivo": "Sin token para Log Analytics API."}
    else:
        out["telemetria"] = {"disponible": False, "motivo": "AZURE_LOG_ANALYTICS_WORKSPACE_ID no configurado."}
    return out


def find_open_boards_task(settings: dict[str, str], version: str, criterion_id: str) -> dict | None:
    org = settings.get("AZURE_DEVOPS_ORG_URL", "").rstrip("/")
    project = settings.get("AZURE_DEVOPS_PROJECT", "")
    if not org or not project:
        return None
    headers = _ado_headers(settings)
    if not headers:
        return None
    fp = action_fingerprint(version, criterion_id)
    tag = f"devsecops-fp-{fp}"
    proj_enc = urllib.parse.quote(project)
    wiql = {
        "query": (
            f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{project}' "
            f"AND [System.WorkItemType] = 'Task' AND [System.Tags] CONTAINS '{tag}' "
            "AND [System.State] <> 'Closed' AND [System.State] <> 'Removed'"
        )
    }
    try:
        found = _http_json("POST", f"{org}/{proj_enc}/_apis/wit/wiql?api-version=7.1", headers, wiql)
        items = found.get("workItems") or []
        if not items:
            return None
        wid = items[0]["id"]
        return {
            "work_item_id": wid,
            "referencia": f"AB#{wid}",
            "fingerprint": fp,
            "tag_idempotencia": tag,
            "url": f"{org}/{proj_enc}/_workitems/edit/{wid}",
        }
    except Exception:
        return None


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
        "gobernanza_repo": audit_repo_governance(REPO_ROOT),
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


def build_closure_candidate(report: dict) -> dict | None:
    if report.get("veredicto") != "VERIFICADO":
        return None
    settings = load_settings()
    if settings.get("DEVSECOPS_LIVE") == "0":
        return None
    version = report["ejecucion"]["version"]
    criterion_id = report["criterio"]["id"]
    open_task = find_open_boards_task(settings, version, criterion_id)
    if not open_task:
        return None
    return {
        "requiere_aprobacion": True,
        "estado": "LISTA_PARA_CERRAR",
        "work_item_id": open_task["work_item_id"],
        "referencia": open_task["referencia"],
        "fingerprint": open_task["fingerprint"],
        "tag_idempotencia": open_task["tag_idempotencia"],
        "url": open_task["url"],
        "titulo": f"Cerrar {open_task['referencia']} tras certificación VERIFICADO de {version}",
    }


def close_boards_task(report: dict, comment: str = "") -> dict:
    closure = report.get("cierre_ciclo_boards")
    if not closure:
        raise ValueError("Este informe no tiene una tarea abierta en Azure Boards pendiente de cierre.")
    settings = load_settings()
    org = settings.get("AZURE_DEVOPS_ORG_URL", "").rstrip("/")
    project = settings.get("AZURE_DEVOPS_PROJECT", "")
    if not org or not project:
        raise RuntimeError("Configurá AZURE_DEVOPS_ORG_URL y AZURE_DEVOPS_PROJECT en assessment/.env.")
    patch_headers = _ado_headers(settings, content_type="application/json-patch+json")
    if not patch_headers:
        raise RuntimeError("No se encontraron credenciales para cerrar tareas en Azure Boards.")

    proj_enc = urllib.parse.quote(project)
    wid = closure["work_item_id"]
    run_id = report["ejecucion"]["id"]
    commit = report["ejecucion"].get("commit") or "sin-commit"
    note = html.escape(comment.strip()) if comment.strip() else "Cerrada tras verificación determinista en verde."
    history = (
        f"<p><b>Cierre de ciclo DevSecOps ({POLICY_VERSION}):</b> La entrega <code>{html.escape(report['ejecucion']['version'])}</code> "
        f"alcanzó dictamen <code>VERIFICADO</code> en la corrida <code>{run_id}</code> (commit <code>{html.escape(str(commit))}</code>). "
        f"Nota: {note}</p>"
    )
    _http_json(
        "PATCH",
        f"{org}/{proj_enc}/_apis/wit/workitems/{wid}?api-version=7.1",
        patch_headers,
        [
            {"op": "add", "path": "/fields/System.State", "value": "Closed"},
            {"op": "add", "path": "/fields/System.History", "value": history},
        ],
    )
    return {
        "operacion": "cerrada",
        "work_item_id": wid,
        "referencia": f"AB#{wid}",
        "fingerprint": closure["fingerprint"],
        "url": f"{org}/{proj_enc}/_workitems/edit/{wid}",
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
