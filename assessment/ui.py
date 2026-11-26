"""Interfaz HTTP local de la demo NextGen DevSecOps Assessment (REN-001)."""
import argparse
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from threading import Lock

from .__main__ import ROOT, apply_decision, assess_project

STATIC = Path(__file__).with_name("static")
OUTPUT = ROOT / "assessment/runs"
EVAL_LOCK = Lock()
ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/style.css": ("style.css", "text/css")}
REPORTS = {
    "informe.md": "text/plain",
    "informe.json": "application/json",
    "resultados.trx": "application/xml",
    "dotnet-test.log": "text/plain",
    "checkpoint_aprobacion.json": "application/json",
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
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'")
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
        if self.path in ASSETS:
            name, mime = ASSETS[self.path]
            self.send_content(200, (STATIC / name).read_bytes(), mime)
            return
        match = re.fullmatch(r"/informes/([0-9a-f]{32})/([a-z0-9_.-]+)", self.path)
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

        summary = {key: report[key] for key in (
            "veredicto", "justificacion", "siguiente_paso", "referencias",
            "investigacion", "diagnosticos",
        )}
        for optional_key in ("politica_version", "investigacion_secops", "etapas_devsecops", "accion_propuesta"):
            if optional_key in report:
                summary[optional_key] = report[optional_key]
        summary["resultados_trx"] = [{"outcome": row["outcome"]} for row in report["resultados_trx"]]
        summary["ejecucion"] = {key: report["ejecucion"].get(key) for key in ("id", "trx", "log", "commit")}
        self.send_json(200, summary)

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Abre la demo local NextGen DevSecOps Assessment (REN-001)")
    parser.add_argument("--puerto", type=int, default=8050)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.puerto), DemoHandler) as server:
        print(f"Demo REN-001 · http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
