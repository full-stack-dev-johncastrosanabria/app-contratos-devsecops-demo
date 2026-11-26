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

from .__main__ import ROOT, apply_decision, assess_project
from .integrations import load_settings
from .workflow import DecisionAlreadyResolved

STATIC = Path(__file__).with_name("static")
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
    for optional_key in ("politica_version", "investigacion_secops", "etapas_devsecops", "accion_propuesta"):
        if optional_key in report:
            summary[optional_key] = report[optional_key]
    summary["resultados_trx"] = [{"outcome": row["outcome"], "name": row.get("name")} for row in report["resultados_trx"]]
    summary["ejecucion"] = {
        key: report["ejecucion"].get(key)
        for key in ("id", "version", "trx", "log", "commit")
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
    return {
        "boards_url": f"{org}/{proj}/_workitems/edit/{wi}" if org and proj else None,
        "boards_project_url": f"{org}/{proj}/_workitems" if org and proj else None,
        "github_url": f"https://github.com/{gh_repo}" if gh_repo else None,
        "github_pr_url": f"https://github.com/{gh_repo}/pull/1" if gh_repo else None,
        "github_actions_url": f"https://github.com/{gh_repo}/actions" if gh_repo else None,
        "github_security_url": f"https://github.com/{gh_repo}/security" if gh_repo else None,
        "sandbox": _probe_local_sandbox(),
    }


class DemoHandler(BaseHTTPRequestHandler):
    @property
    def host(self) -> str:
        return f"127.0.0.1:{self.server.server_port}"

    def send_content(self, status: int, content: bytes, mime: str) -> None:
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
        if clean_path == "/api/ecosistema":
            self.send_json(200, {"ecosistema": ecosystem_links(), "ultimos": latest_reports(OUTPUT)})
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
            if not re.fullmatch(r"[0-9a-f]{32}", str(run_id)) or decision not in ("aprobar", "descartar"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Solicitud de aprobación inválida."})
            return
        try:
            with EVAL_LOCK:
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
            "etapas_devsecops": updated.get("etapas_devsecops", []),
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
