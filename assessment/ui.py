"""Interfaz HTTP local e interoperable de NextGen DevSecOps Assessment (REN-001)."""
import argparse
import asyncio
import atexit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import signal
import subprocess
from threading import Lock
import time
import urllib.request

from .__main__ import ROOT, apply_closure, apply_decision, apply_reopen, assess_project
from .analytics import build_powerbi_metrics, render_powerbi_csv
from .demo_reset import execute_demo_reset, list_archived_sessions, restore_latest_archive
from .integrations import fetch_sonarqube_context, load_settings
from .powerbi_cloud import get_powerbi_state, sync_powerbi_cloud
from .remediation import (
    apply_local_remediation,
    close_github_remediation_prs,
    create_github_remediation_pr,
    generate_remediation,
    public_remediation_state,
    revert_local_remediation,
)
from .vulnerabilities import (
    apply_vuln_remediation,
    close_vuln_github_prs,
    create_vuln_github_pr,
    generate_vuln_remediation,
    public_vuln_state,
    revert_vuln_remediation,
    scan_vulnerabilities,
)
from .workflow import DecisionAlreadyResolved

STATIC = Path(__file__).with_name("static")
COPILOT_DIR = ROOT / "copilot"
OUTPUT = ROOT / "assessment/runs"
EVAL_LOCK = Lock()
SANDBOX_LOCK = Lock()
SANDBOX_PORT = 5080
_SANDBOX_PROC: subprocess.Popen | None = None
_SANDBOX_VERSION: str | None = None

ASSETS = {
    "/": ("index.html", "text/html"),
    "/app.js": ("app.js", "text/javascript"),
    "/style.css": ("style.css", "text/css"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/brand-mark.png": ("brand-mark.png", "image/png"),
}
COPILOT_FILES = {
    "/copilot/openapi.yaml": "openapi.yaml",
    "/copilot/security-copilot-skill.yaml": "security-copilot-skill.yaml",
}
REPORTS = {
    "informe.md": "text/plain",
    "informe.json": "application/json",
    "resultados.trx": "application/xml",
    "dotnet-test.log": "text/plain",
    "checkpoint_aprobacion.json": "application/json",
}


def stop_sandbox() -> None:
    global _SANDBOX_PROC, _SANDBOX_VERSION
    with SANDBOX_LOCK:
        if _SANDBOX_PROC and _SANDBOX_PROC.poll() is None:
            try:
                os.killpg(_SANDBOX_PROC.pid, signal.SIGTERM)
                _SANDBOX_PROC.wait(timeout=4)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(_SANDBOX_PROC.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        _SANDBOX_PROC = None
        _SANDBOX_VERSION = None


atexit.register(stop_sandbox)


def _probe_local_sandbox() -> dict:
    url = f"http://127.0.0.1:{SANDBOX_PORT}"
    try:
        with urllib.request.urlopen(f"{url}/api/salud", timeout=1.2) as resp:
            if resp.status == 200:
                info = json.loads(resp.read())
                return {
                    "activo": True,
                    "version": info.get("version") or _SANDBOX_VERSION or "local",
                    "commit": info.get("commit"),
                    "url": url,
                }
    except Exception:
        pass
    return {"activo": False, "version": None, "url": url}


def start_sandbox(version: str) -> dict:
    global _SANDBOX_PROC, _SANDBOX_VERSION
    current = _probe_local_sandbox()
    if current["activo"] and current["version"] == version:
        return current
    stop_sandbox()
    with SANDBOX_LOCK:
        project_dir = ROOT / version / "src" / "Contratos"
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("AZURE_OPENAI_", "ANTHROPIC_", "AZURE_DEVOPS_PAT"))
        }
        env["APP_VERSION"] = version
        _SANDBOX_PROC = subprocess.Popen(
            ["dotnet", "run", "--project", str(project_dir), "--urls", f"http://127.0.0.1:{SANDBOX_PORT}"],
            cwd=str(ROOT / version),
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _SANDBOX_VERSION = version
    for _ in range(25):
        state = _probe_local_sandbox()
        if state["activo"]:
            return state
        if _SANDBOX_PROC and _SANDBOX_PROC.poll() is not None:
            break
        time.sleep(0.4)
    raise RuntimeError(f"No se pudo iniciar la instancia local de {version} en el puerto {SANDBOX_PORT}.")


def _format_summary(report: dict) -> dict:
    summary = {key: report[key] for key in (
        "veredicto", "justificacion", "siguiente_paso", "referencias",
        "investigacion", "diagnosticos",
    )}
    for optional_key in (
        "politica_version",
        "criterios_evaluados",
        "cobertura",
        "reporte_vulnerabilidades",
        "investigacion_secops",
        "etapas_devsecops",
        "accion_propuesta",
        "cierre_ciclo_boards",
    ):
        if optional_key in report:
            summary[optional_key] = report[optional_key]
    sonar_ctx = (report.get("devsecops") or {}).get("sonarqube")
    if sonar_ctx:
        summary["sonarqube"] = sonar_ctx
    summary["resultados_trx"] = [{"outcome": row["outcome"], "name": row.get("name")} for row in report["resultados_trx"]]
    summary["ejecucion"] = {
        key: report["ejecucion"].get(key)
        for key in ("id", "version", "trx", "log", "commit", "cobertura_xml")
    }
    if "sha256_archivos" in report["ejecucion"]:
        summary["ejecucion"]["archivos_firmados"] = len(report["ejecucion"]["sha256_archivos"] or {})
    if "cambios_locales" in report["ejecucion"]:
        summary["ejecucion"]["cambios_locales"] = report["ejecucion"]["cambios_locales"]
    return summary


def latest_reports(output_dir: Path) -> dict[str, dict]:
    if not output_dir.is_dir():
        return {}
    latest_by_version: dict[str, tuple[float, dict]] = {}
    for report_file in output_dir.glob("*/informe.json"):
        if report_file.parent.name.startswith("_"):
            continue
        try:
            mtime = report_file.stat().st_mtime
            data = json.loads(report_file.read_text(encoding="utf-8"))
            ver = (data.get("ejecucion") or {}).get("version")
            if ver in ("v1", "v2", "v3"):
                prev = latest_by_version.get(ver)
                if prev is None or mtime > prev[0]:
                    formatted = _format_summary(data)
                    formatted["registrado_ms"] = int(mtime * 1000)
                    latest_by_version[ver] = (mtime, formatted)
        except Exception:
            continue
    return {ver: item[1] for ver, item in latest_by_version.items()}


def ecosystem_links() -> dict:
    s = load_settings()
    org = s.get("AZURE_DEVOPS_ORG_URL", "").rstrip("/")
    proj = s.get("AZURE_DEVOPS_PROJECT", "")
    wi = s.get("AZURE_DEVOPS_WORK_ITEM_ID") or "1"
    gh_repo = s.get("GITHUB_REPO", "")
    sonar_key = s.get("SONAR_PROJECT_KEY") or (
        "full-stack-dev-johncastrosanabria_app-contratos-devsecops-demo"
        if "nextgen-devsecops-assessment" in gh_repo else ""
    )
    return {
        "boards_url": f"{org}/{proj}/_workitems/edit/{wi}" if org and proj else None,
        "boards_project_url": f"{org}/{proj}/_workitems" if org and proj else None,
        "github_url": f"https://github.com/{gh_repo}" if gh_repo else None,
        "github_pr_url": f"https://github.com/{gh_repo}/pull/1" if gh_repo else None,
        "github_actions_url": f"https://github.com/{gh_repo}/actions" if gh_repo else None,
        "github_security_url": f"https://github.com/{gh_repo}/security" if gh_repo else None,
        "sonarqube_url": f"https://sonarcloud.io/project/overview?id={sonar_key}" if sonar_key else None,
        "powerbi_csv_url": "/api/metricas-powerbi.csv",
        "powerbi_json_url": "/api/metricas-powerbi.json",
        "powerbi_web_url": get_powerbi_state(OUTPUT).get("report_url"),
        "security_copilot_url": "/copilot/security-copilot-skill.yaml",
        "openapi_url": "/copilot/openapi.yaml",
        "sandbox": _probe_local_sandbox(),
    }


class DemoHandler(BaseHTTPRequestHandler):
    @property
    def host(self) -> str:
        return f"127.0.0.1:{self.server.server_port}"

    def send_content(self, status: int, content: bytes, mime: str, extra_headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
        )
        for header_name, header_val in (extra_headers or {}).items():
            self.send_header(header_name, header_val)
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status: int, value: dict) -> None:
        self.send_content(status, json.dumps(value, ensure_ascii=False).encode(), "application/json")

    def _read_json_body(self, max_bytes: int = 1024) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= max_bytes or self.headers.get_content_type() != "application/json":
            raise ValueError
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError
        return data

    def do_GET(self) -> None:
        if self.headers.get("Host") != self.host:
            self.send_json(403, {"error": "Abrí la dirección local que imprime el servidor."})
            return
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        clean_path = self.path.split("?", 1)[0]
        if clean_path in ASSETS:
            name, mime = ASSETS[clean_path]
            self.send_content(200, (STATIC / name).read_bytes(), mime)
            return
        if clean_path in COPILOT_FILES:
            target = COPILOT_DIR / COPILOT_FILES[clean_path]
            if target.is_file():
                self.send_content(200, target.read_bytes(), "text/yaml")
                return
        if clean_path == "/api/ecosistema":
            self.send_json(200, {
                "ecosistema": ecosystem_links(),
                "ultimos": latest_reports(OUTPUT),
                "analitica": build_powerbi_metrics(OUTPUT)["kpis"],
                "archivos_demo": list_archived_sessions(OUTPUT),
                "remediacion_activa": public_remediation_state(OUTPUT),
                "vulnerabilidades": {
                    ver: scan_vulnerabilities(ROOT, version=ver, runs_dir=OUTPUT)
                    for ver in ("v1", "v2", "v3")
                },
                "estado_vulnerabilidades": public_vuln_state(OUTPUT),
                "powerbi": get_powerbi_state(OUTPUT),
            })
            return
        if clean_path == "/api/vulnerabilidades":
            self.send_json(200, {
                "vulnerabilidades": {
                    ver: scan_vulnerabilities(ROOT, version=ver, runs_dir=OUTPUT)
                    for ver in ("v1", "v2", "v3")
                },
                "sonarqube": fetch_sonarqube_context(load_settings()),
                "estado_vulnerabilidades": public_vuln_state(OUTPUT),
            })
            return
        if clean_path == "/api/metricas-powerbi.json":
            self.send_json(200, build_powerbi_metrics(OUTPUT))
            return
        if clean_path == "/api/metricas-powerbi.csv":
            csv_bytes = render_powerbi_csv(OUTPUT).encode("utf-8")
            headers = {"Content-Disposition": 'attachment; filename="nextgen-devsecops-powerbi.csv"'}
            self.send_content(200, csv_bytes, "text/csv", extra_headers=headers)
            return
        match = re.fullmatch(r"/informes/([0-9a-f]{32})/([a-z0-9_.-]+)", clean_path)
        if match and match[2] in REPORTS:
            path = OUTPUT / match[1] / match[2]
            if path.is_file():
                self.send_content(200, path.read_bytes(), REPORTS[match[2]])
                return
        self.send_json(404, {"error": "Recurso no encontrado."})

    def do_POST(self) -> None:
        if self.headers.get("Host") != self.host or self.headers.get("Origin") != f"http://{self.host}":
            self.send_json(403, {"error": "La evaluación debe iniciarse desde la demo local."})
            return
        if self.path == "/api/evaluar":
            self._handle_evaluate()
            return
        if self.path == "/api/acciones":
            self._handle_action()
            return
        if self.path == "/api/remediacion":
            self._handle_remediation()
            return
        if self.path == "/api/remediacion/aplicar":
            self._handle_remediation_apply()
            return
        if self.path == "/api/remediacion/revertir":
            self._handle_remediation_revert()
            return
        if self.path == "/api/remediacion/pr":
            self._handle_remediation_pr()
            return
        if self.path == "/api/remediacion/pr/cerrar":
            self._handle_remediation_pr_close()
            return
        if self.path == "/api/powerbi/publicar":
            self._handle_powerbi_publish()
            return
        if self.path == "/api/vulnerabilidades/remediar":
            self._handle_vuln_draft()
            return
        if self.path == "/api/vulnerabilidades/aplicar":
            self._handle_vuln_apply()
            return
        if self.path == "/api/vulnerabilidades/revertir":
            self._handle_vuln_revert()
            return
        if self.path == "/api/vulnerabilidades/pr":
            self._handle_vuln_pr()
            return
        if self.path == "/api/vulnerabilidades/pr/cerrar":
            self._handle_vuln_pr_close()
            return
        if self.path == "/api/demo/reiniciar":
            self._handle_demo_reset()
            return
        if self.path == "/api/demo/restaurar":
            self._handle_demo_restore()
            return
        if self.path == "/api/sandbox":
            self._handle_sandbox()
            return
        self.send_json(404, {"error": "Recurso no encontrado."})

    def _handle_evaluate(self) -> None:
        try:
            payload = self._read_json_body(512)
            version, mode = payload["version"], payload["modo"]
            devsecops = payload.get("devsecops")
            if version not in ("v1", "v2", "v3") or mode not in ("solo-evidencia", "agente"):
                raise ValueError
            if devsecops is not None and not isinstance(devsecops, bool):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Elegí una versión y un modo válidos."})
            return
        try:
            with EVAL_LOCK:
                coro = (assess_project(ROOT / version, OUTPUT, mode == "agente")
                        if devsecops is None
                        else assess_project(ROOT / version, OUTPUT, mode == "agente", devsecops=devsecops))
                report = asyncio.run(coro)
        except Exception:
            self.send_json(500, {"error": "Ocurrió un error al ejecutar la evaluación o guardar el informe."})
            return
        self.send_json(200, _format_summary(report))

    def _handle_action(self) -> None:
        try:
            payload = self._read_json_body(1024)
            run_id = payload["ejecucion"]
            decision = payload["decision"]
            note = str(payload.get("nota") or "")[:300]
            sync_boards = bool(payload.get("sincronizar_boards", True))
            if not re.fullmatch(r"[0-9a-f]{32}", str(run_id)) or decision not in ("aprobar", "descartar", "cerrar", "reabrir"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Solicitud de aprobación inválida."})
            return
        try:
            with EVAL_LOCK:
                if decision == "reabrir":
                    updated = apply_reopen(OUTPUT / run_id, sync_boards=sync_boards)
                elif decision == "cerrar":
                    updated = apply_closure(OUTPUT / run_id, note)
                else:
                    updated = apply_decision(OUTPUT / run_id, decision == "aprobar", note)
        except DecisionAlreadyResolved as exc:
            self.send_json(409, {"error": str(exc)})
            return
        except FileNotFoundError:
            self.send_json(404, {"error": "No se encontró la ejecución indicada."})
            return
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo procesar la acción: {exc}"})
            return
        self.send_json(200, {
            "accion_propuesta": updated.get("accion_propuesta"),
            "cierre_ciclo_boards": updated.get("cierre_ciclo_boards"),
            "etapas_devsecops": updated.get("etapas_devsecops", []),
        })

    def _handle_remediation(self) -> None:
        try:
            payload = self._read_json_body(512)
            run_id = payload["ejecucion"]
            use_ai = bool(payload.get("usar_ia", False))
            if not re.fullmatch(r"[0-9a-f]{32}", str(run_id)):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Indicá un ID de ejecución válido para generar remediación."})
            return
        try:
            draft = asyncio.run(generate_remediation(OUTPUT / run_id, use_ai=use_ai))
        except FileNotFoundError:
            self.send_json(404, {"error": "No se encontró la ejecución indicada."})
            return
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo generar el borrador de remediación: {exc}"})
            return
        self.send_json(200, draft)

    def _handle_remediation_apply(self) -> None:
        try:
            payload = self._read_json_body(16384)
            run_id = payload["ejecucion"]
            mode = payload.get("modo", "solo-evidencia")
            use_ai = bool(payload.get("usar_ia", False))
            custom_code = payload.get("codigo")
            if not re.fullmatch(r"[0-9a-f]{32}", str(run_id)) or mode not in ("solo-evidencia", "agente"):
                raise ValueError
            if custom_code is not None and not isinstance(custom_code, str):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Parámetros inválidos para aplicar la remediación local."})
            return
        try:
            with EVAL_LOCK:
                applied = asyncio.run(
                    apply_local_remediation(ROOT, OUTPUT, run_id, use_ai=use_ai, custom_code=custom_code)
                )
                version = applied["version"]
                current_sb = _probe_local_sandbox()
                if current_sb.get("activo") and current_sb.get("version") == version:
                    start_sandbox(version)
                report = asyncio.run(assess_project(ROOT / version, OUTPUT, mode == "agente"))
        except FileNotFoundError:
            self.send_json(404, {"error": "No se encontró la ejecución indicada."})
            return
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo aplicar la remediación ni reevaluar: {exc}"})
            return
        self.send_json(200, {
            "aplicacion": applied,
            "informe": _format_summary(report),
            "analitica": build_powerbi_metrics(OUTPUT)["kpis"],
            "remediacion_activa": public_remediation_state(OUTPUT),
        })

    def _handle_remediation_revert(self) -> None:
        try:
            payload = self._read_json_body(512)
            version = payload["version"]
            mode = payload.get("modo", "solo-evidencia")
            reevaluate = bool(payload.get("reevaluar", True))
            if version not in ("v2", "v3") or mode not in ("solo-evidencia", "agente"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Indicá una versión válida (v2 o v3) para revertir su código."})
            return
        try:
            with EVAL_LOCK:
                reverted = revert_local_remediation(ROOT, OUTPUT, version=version)
                current_sb = _probe_local_sandbox()
                if current_sb.get("activo") and current_sb.get("version") == version:
                    start_sandbox(version)
                report = asyncio.run(assess_project(ROOT / version, OUTPUT, mode == "agente")) if reevaluate else None
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo revertir el código original: {exc}"})
            return
        self.send_json(200, {
            "archivos_revertidos": reverted,
            "informe": _format_summary(report) if report else None,
            "analitica": build_powerbi_metrics(OUTPUT)["kpis"],
            "remediacion_activa": public_remediation_state(OUTPUT),
        })

    def _handle_remediation_pr(self) -> None:
        try:
            payload = self._read_json_body(16384)
            run_id = payload["ejecucion"]
            use_ai = bool(payload.get("usar_ia", False))
            custom_code = payload.get("codigo")
            if not re.fullmatch(r"[0-9a-f]{32}", str(run_id)):
                raise ValueError
            if custom_code is not None and not isinstance(custom_code, str):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Solicitud inválida para crear Pull Request de remediación."})
            return
        try:
            with EVAL_LOCK:
                res = asyncio.run(
                    create_github_remediation_pr(ROOT, OUTPUT, run_id, use_ai=use_ai, custom_code=custom_code)
                )
        except FileNotFoundError:
            self.send_json(404, {"error": "No se encontró la ejecución indicada."})
            return
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo crear el Pull Request en GitHub: {exc}"})
            return
        self.send_json(200, res)

    def _handle_remediation_pr_close(self) -> None:
        try:
            payload = self._read_json_body(512)
            version = payload.get("version")
            if version is not None and version not in ("v2", "v3"):
                raise ValueError
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Parámetros inválidos para cerrar el PR de demostración."})
            return
        try:
            with EVAL_LOCK:
                closed = close_github_remediation_prs(OUTPUT, version=version)
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo cerrar el PR efímero: {exc}"})
            return
        self.send_json(200, {
            "prs_cerrados": closed,
            "remediacion_activa": public_remediation_state(OUTPUT),
        })

    def _refresh_cached_stage3(self) -> dict[str, dict]:
        vulns_by_ver = {
            ver: scan_vulnerabilities(ROOT, version=ver, runs_dir=OUTPUT)
            for ver in ("v1", "v2", "v3")
        }
        if OUTPUT.is_dir():
            for report_file in OUTPUT.glob("*/informe.json"):
                if report_file.parent.name.startswith("_"):
                    continue
                try:
                    data = json.loads(report_file.read_text(encoding="utf-8"))
                    ver = (data.get("ejecucion") or {}).get("version")
                    if ver not in vulns_by_ver:
                        continue
                    vscan = vulns_by_ver[ver]
                    data["reporte_vulnerabilidades"] = vscan
                    for st in data.get("etapas_devsecops") or []:
                        if st.get("numero") == 3:
                            v_open = vscan["abiertas"]
                            v_mit = vscan["mitigadas"]
                            v_tot = vscan["total"]
                            st["estado"] = (
                                "verificado" if v_open == 0 and v_mit == v_tot
                                else "atencion" if vscan.get("altas_abiertas", 0) > 0
                                else "informativo"
                            )
                            st["resumen"] = f"Reporte SecOps: {v_open} abiertas · {v_mit}/{v_tot} mitigadas"
                            if isinstance(st.get("datos"), dict):
                                st["datos"]["Vulnerabilidades auditadas"] = f"{v_open} abiertas · {v_mit} mitigadas (de {v_tot})"
                    tmp = report_file.with_suffix(".json.tmp")
                    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    tmp.replace(report_file)
                except Exception:
                    continue
        return vulns_by_ver

    def _handle_vuln_draft(self) -> None:
        try:
            payload = self._read_json_body(512)
            vuln_id = str(payload["id"])
            version = payload.get("version", "v1")
            use_ai = bool(payload.get("usar_ia", False))
            if vuln_id not in ("SEC-CI-001", "SEC-DOCKER-001", "SEC-K8S-001", "SEC-WEB-001") or version not in ("v1", "v2", "v3"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Parámetros inválidos para investigar la vulnerabilidad."})
            return
        try:
            draft = asyncio.run(generate_vuln_remediation(ROOT, OUTPUT, vuln_id, version=version, use_ai=use_ai))
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo generar la remediación SecOps: {exc}"})
            return
        self.send_json(200, draft)

    def _handle_vuln_apply(self) -> None:
        try:
            payload = self._read_json_body(512)
            vuln_id = str(payload["id"])
            version = payload.get("version", "v1")
            origen = str(payload.get("origen") or "agente_secops")[:40]
            if vuln_id not in ("SEC-CI-001", "SEC-DOCKER-001", "SEC-K8S-001", "SEC-WEB-001", "TODAS") or version not in ("v1", "v2", "v3"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Solicitud inválida para mitigar vulnerabilidad."})
            return
        try:
            with EVAL_LOCK:
                res = apply_vuln_remediation(ROOT, OUTPUT, vuln_id, version=version, origen=origen)
                vulns_by_ver = self._refresh_cached_stage3()
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo aplicar la mitigación SecOps: {exc}"})
            return
        self.send_json(200, {
            **res,
            "vulnerabilidades": vulns_by_ver,
            "ultimos": latest_reports(OUTPUT),
        })

    def _handle_vuln_revert(self) -> None:
        try:
            payload = self._read_json_body(512)
            vuln_id = payload.get("id")
            version = payload.get("version", "v1")
            if vuln_id is not None and vuln_id not in ("SEC-CI-001", "SEC-DOCKER-001", "SEC-K8S-001", "SEC-WEB-001", "TODAS"):
                raise ValueError
            if version not in ("v1", "v2", "v3"):
                raise ValueError
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Parámetros inválidos para revertir mitigación SecOps."})
            return
        try:
            with EVAL_LOCK:
                res = revert_vuln_remediation(ROOT, OUTPUT, vuln_id=vuln_id, version=version)
                vulns_by_ver = self._refresh_cached_stage3()
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo revertir la mitigación SecOps: {exc}"})
            return
        self.send_json(200, {
            **res,
            "vulnerabilidades": vulns_by_ver,
            "ultimos": latest_reports(OUTPUT),
        })

    def _handle_vuln_pr(self) -> None:
        try:
            payload = self._read_json_body(512)
            vuln_id = str(payload["id"])
            version = payload.get("version", "v1")
            if vuln_id not in ("SEC-CI-001", "SEC-DOCKER-001", "SEC-K8S-001", "SEC-WEB-001") or version not in ("v1", "v2", "v3"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Solicitud inválida para abrir PR SecOps."})
            return
        try:
            with EVAL_LOCK:
                res = asyncio.run(create_vuln_github_pr(ROOT, OUTPUT, vuln_id, version=version))
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo abrir el PR SecOps en GitHub: {exc}"})
            return
        self.send_json(200, {
            **res,
            "vulnerabilidades": {
                ver: scan_vulnerabilities(ROOT, version=ver, runs_dir=OUTPUT)
                for ver in ("v1", "v2", "v3")
            },
        })

    def _handle_vuln_pr_close(self) -> None:
        try:
            payload = self._read_json_body(512)
            vuln_id = payload.get("id")
            version = payload.get("version", "v1")
            if version not in ("v1", "v2", "v3"):
                raise ValueError
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Parámetros inválidos para cerrar PR SecOps."})
            return
        try:
            with EVAL_LOCK:
                closed = close_vuln_github_prs(OUTPUT, vuln_id=vuln_id, version=version)
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo cerrar el PR SecOps: {exc}"})
            return
        self.send_json(200, {
            "prs_cerrados": closed,
            "estado_vulnerabilidades": public_vuln_state(OUTPUT),
            "vulnerabilidades": {
                ver: scan_vulnerabilities(ROOT, version=ver, runs_dir=OUTPUT)
                for ver in ("v1", "v2", "v3")
            },
        })

    def _handle_powerbi_publish(self) -> None:
        try:
            payload = self._read_json_body(512)
            recreate = bool(payload.get("regenerar", False))
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Parámetros inválidos para publicar en Power BI."})
            return
        try:
            with EVAL_LOCK:
                state = sync_powerbi_cloud(OUTPUT, ensure_report=True, recreate_report=recreate)
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo sincronizar con Power BI Service: {exc}"})
            return
        self.send_json(200, {
            "powerbi": state,
            "analitica": build_powerbi_metrics(OUTPUT)["kpis"],
        })

    def _handle_demo_reset(self) -> None:
        try:
            payload = self._read_json_body(512)
            reset_runs = bool(payload.get("corridas", True))
            reset_sandbox = bool(payload.get("sandbox", True))
            reset_boards = bool(payload.get("boards", False))
            reset_code = bool(payload.get("codigo", True))
            reset_prs = bool(payload.get("prs", True))
            sync_pbi = bool(payload.get("powerbi", False))
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Parámetros de reinicio de demostración inválidos."})
            return
        try:
            with EVAL_LOCK:
                if reset_sandbox or reset_code:
                    stop_sandbox()
                res = execute_demo_reset(
                    ROOT,
                    OUTPUT,
                    reset_runs=reset_runs,
                    reset_sandbox=reset_sandbox,
                    reset_boards=reset_boards,
                    reset_code=reset_code,
                    reset_github_prs=reset_prs,
                    sync_powerbi=sync_pbi,
                )
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo reiniciar el estado de demostración: {exc}"})
            return
        self.send_json(200, {
            "reinicio": res,
            "ultimos": latest_reports(OUTPUT),
            "analitica": build_powerbi_metrics(OUTPUT)["kpis"],
            "sandbox": _probe_local_sandbox(),
            "remediacion_activa": public_remediation_state(OUTPUT),
            "vulnerabilidades": {
                ver: scan_vulnerabilities(ROOT, version=ver, runs_dir=OUTPUT)
                for ver in ("v1", "v2", "v3")
            },
            "estado_vulnerabilidades": public_vuln_state(OUTPUT),
        })

    def _handle_demo_restore(self) -> None:
        try:
            payload = self._read_json_body(512)
            sesion = payload.get("sesion")
            if sesion is not None and not isinstance(sesion, str):
                raise ValueError
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Solicitud de restauración inválida."})
            return
        try:
            with EVAL_LOCK:
                res = restore_latest_archive(OUTPUT, session_name=sesion)
        except FileNotFoundError as exc:
            self.send_json(404, {"error": str(exc)})
            return
        except Exception as exc:
            self.send_json(500, {"error": f"No se pudo restaurar la sesión archivada: {exc}"})
            return
        self.send_json(200, {
            "restauracion": res,
            "ultimos": latest_reports(OUTPUT),
            "analitica": build_powerbi_metrics(OUTPUT)["kpis"],
        })

    def _handle_sandbox(self) -> None:
        try:
            payload = self._read_json_body(256)
            action = payload.get("accion", "iniciar")
            version = payload.get("version", "v1")
            if action not in ("iniciar", "detener") or (action == "iniciar" and version not in ("v1", "v2", "v3")):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Parámetros de instancia local inválidos."})
            return
        try:
            if action == "detener":
                stop_sandbox()
                self.send_json(200, {"sandbox": _probe_local_sandbox()})
            else:
                state = start_sandbox(version)
                state["url_interoperable"] = f"{state['url']}/?evaluador=http://{self.host}&version={version}"
                self.send_json(200, {"sandbox": state})
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Abre la consola NextGen DevSecOps Assessment (REN-001)")
    parser.add_argument("--puerto", type=int, default=8050)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.puerto), DemoHandler) as server:
        print(f"Demo REN-001 · http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        finally:
            stop_sandbox()


if __name__ == "__main__":
    main()
