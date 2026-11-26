from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from assessment.ui import DemoHandler


class DemoHTTP(unittest.TestCase):
    def test_local_web_contract(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler) as server, TemporaryDirectory() as temp:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(thread.join)

            def request(method, path, payload=None, origin=None):
                connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                headers = {"Origin": origin, "Content-Type": "application/json"} if origin else {}
                try:
                    connection.request(method, path, payload, headers)
                    response = connection.getresponse()
                    return response.status, response.read()
                finally:
                    connection.close()

            root = Path(temp)
            run_id = "a" * 32
            directory = root / run_id
            directory.mkdir()
            (directory / "informe.json").write_text('{"veredicto":"INCUMPLIDO"}', encoding="utf-8")
            (directory / "dotnet-test.log").write_text("Ejecución de dotnet test\n", encoding="utf-8")
            report = {
                "veredicto": "INCUMPLIDO", "justificacion": "Se generó un aviso.",
                "siguiente_paso": None, "referencias": [], "resultados_trx": [{"outcome": "Failed"}],
                "investigacion": {"estado": "SOLO_EVIDENCIA"}, "diagnosticos": [],
                "ejecucion": {"id": run_id, "trx": "resultados.trx", "log": "dotnet-test.log"},
            }
            origin = f"http://127.0.0.1:{server.server_port}"
            try:
                with (patch("assessment.ui.OUTPUT", root),
                      patch("assessment.ui.assess_project", return_value=report) as assess):
                    self.assertIn(b'Evaluador de renovaciones', request("GET", "/")[1])
                    self.assertEqual(request("POST", "/api/evaluar", "{}")[0], 403)
                    self.assertEqual(request("POST", "/api/evaluar", '{"version":"../v2","modo":"agente"}', origin)[0], 400)
                    status, body = request("POST", "/api/evaluar", '{"version":"v2","modo":"solo-evidencia"}', origin)
                    self.assertEqual(status, 200)
                    parsed = json.loads(body)
                    self.assertEqual(parsed["veredicto"], "INCUMPLIDO")
                    self.assertEqual(parsed["ejecucion"]["log"], "dotnet-test.log")
                    self.assertEqual(request("GET", f"/informes/{run_id}/informe.json")[0], 200)
                    self.assertEqual(request("GET", f"/informes/{run_id}/dotnet-test.log")[0], 200)
                    self.assertEqual(request("GET", "/.env")[0], 404)
                    assess.assert_awaited_once()
                with (patch("assessment.ui.OUTPUT", root),
                      patch("assessment.ui.assess_project", side_effect=ValueError("fallo inesperado"))):
                    self.assertEqual(request("POST", "/api/evaluar", '{"version":"v1","modo":"solo-evidencia"}', origin)[0], 500)
            finally:
                server.shutdown()
