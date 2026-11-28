from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from assessment.ui import DemoHandler

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - el venv de la demo la instala
    sync_playwright = None


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
            (directory / "checkpoint_aprobacion.json").write_text('{"ejecucion_id":"' + run_id + '"}', encoding="utf-8")
            report = {
                "veredicto": "INCUMPLIDO", "justificacion": "Se generó un aviso.",
                "siguiente_paso": "Corregir filtro.", "referencias": [], "resultados_trx": [{"outcome": "Failed"}],
                "investigacion": {"estado": "SOLO_EVIDENCIA"}, "diagnosticos": [],
                "ejecucion": {"id": run_id, "trx": "resultados.trx", "log": "dotnet-test.log"},
                "accion_propuesta": {"estado": "PENDIENTE_APROBACION", "tag_idempotencia": "devsecops-fp-demo"},
            }
            origin = f"http://127.0.0.1:{server.server_port}"
            try:
                with (patch("assessment.ui.OUTPUT", root),
                      patch("assessment.ui.assess_project", return_value=report) as assess):
                    self.assertIn(b'Evaluador de entregas', request("GET", "/")[1])
                    self.assertEqual(request("POST", "/api/evaluar", "{}")[0], 403)
                    self.assertEqual(request("POST", "/api/evaluar", '{"version":"../v2","modo":"agente"}', origin)[0], 400)
                    status, body = request("POST", "/api/evaluar", '{"version":"v2","modo":"solo-evidencia"}', origin)
                    self.assertEqual(status, 200)
                    parsed = json.loads(body)
                    self.assertEqual(parsed["veredicto"], "INCUMPLIDO")
                    self.assertEqual(parsed["ejecucion"]["log"], "dotnet-test.log")
                    self.assertEqual(request("GET", f"/informes/{run_id}/informe.json")[0], 200)
                    self.assertEqual(request("GET", f"/informes/{run_id}/dotnet-test.log")[0], 200)
                    self.assertEqual(request("GET", f"/informes/{run_id}/checkpoint_aprobacion.json")[0], 200)
                    self.assertEqual(request("GET", "/api/ecosistema")[0], 200)
                    self.assertEqual(request("GET", "/api/metricas-powerbi.json")[0], 200)
                    st_csv, csv_body = request("GET", "/api/metricas-powerbi.csv")
                    self.assertEqual(st_csv, 200)
                    self.assertIn(b"ejecucion_id", csv_body)
                    self.assertEqual(request("GET", "/copilot/openapi.yaml")[0], 200)
                    self.assertEqual(request("GET", "/copilot/security-copilot-skill.yaml")[0], 200)
                    st_rem, rem_body = request("POST", "/api/remediacion", json.dumps({"ejecucion": run_id, "usar_ia": False}), origin)
                    self.assertEqual(st_rem, 200)
                    self.assertTrue(json.loads(rem_body)["disponible"])
                    self.assertEqual(request("GET", "/.env")[0], 404)
                    assess.assert_awaited_once()

                    with (patch("assessment.ui.apply_local_remediation", return_value={"aplicado": True, "version": "v2", "archivo": "v2/src/Contratos/Renovaciones.cs"}),
                          patch("assessment.ui.revert_local_remediation", return_value=["v2/src/Contratos/Renovaciones.cs"]),
                          patch("assessment.ui.create_github_remediation_pr", return_value={"operacion": "creado", "pr": {"numero": 15, "url": "https://github.com/demo/pull/15"}, "estado_remediacion": {"parches_locales": {}, "prs_efimeros": {}}}),
                          patch("assessment.ui.close_github_remediation_prs", return_value=[{"version": "v2", "numero": 15}]),
                          patch("assessment.ui.sync_powerbi_cloud", return_value={"sincronizado": True, "report_url": "https://app.powerbi.com/groups/me/reports/demo", "filas_sincronizadas": 1})):
                        self.assertEqual(request("POST", "/api/remediacion/aplicar", json.dumps({"ejecucion": run_id, "modo": "solo-evidencia"}), origin)[0], 200)
                        self.assertEqual(request("POST", "/api/remediacion/revertir", '{"version":"v2","modo":"solo-evidencia"}', origin)[0], 200)
                        self.assertEqual(request("POST", "/api/remediacion/pr", json.dumps({"ejecucion": run_id}), origin)[0], 200)
                        self.assertEqual(request("POST", "/api/remediacion/pr/cerrar", '{"version":"v2"}', origin)[0], 200)
                        st_pbi, body_pbi = request("POST", "/api/powerbi/publicar", "{}", origin)
                        self.assertEqual(st_pbi, 200)
                        self.assertIn("app.powerbi.com", json.loads(body_pbi)["powerbi"]["report_url"])

                    with (patch("assessment.ui.fetch_sonarqube_context", return_value={"disponible": True, "quality_gate": "FALLIDO", "vulnerabilidades": 10}),
                          patch("assessment.ui.triage_vulnerabilities", return_value={"disponible": True, "origen": "agente_triaje_secops_ia", "orden_prioridad": ["SEC-CI-001"]}),
                          patch("assessment.ui.analyze_observability_agent", return_value={"disponible": True, "origen": "agente_sre_bi_ia", "titular_ejecutivo": "OK"}),
                          patch("assessment.ui.generate_vuln_remediation", return_value={"disponible": True, "id": "SEC-DOCKER-001", "codigo_sugerido": "USER $APP_UID"}),
                          patch("assessment.ui.apply_vuln_remediation", return_value={"aplicados": ["Dockerfile"], "reporte_vulnerabilidades": {"abiertas": 3, "mitigadas": 1, "total": 4}}),
                          patch("assessment.ui.revert_vuln_remediation", return_value={"archivos_revertidos": ["Dockerfile"], "reporte_vulnerabilidades": {"abiertas": 4, "mitigadas": 0, "total": 4}})):
                        st_vuln, body_vuln = request("GET", "/api/vulnerabilidades")
                        self.assertEqual(st_vuln, 200)
                        self.assertEqual(json.loads(body_vuln)["sonarqube"]["quality_gate"], "FALLIDO")
                        self.assertEqual(request("POST", "/api/vulnerabilidades/triaje", '{"version":"v1","usar_ia":true}', origin)[0], 200)
                        self.assertEqual(request("POST", "/api/observabilidad/analizar", '{"usar_ia":true}', origin)[0], 200)
                        self.assertEqual(request("POST", "/api/vulnerabilidades/remediar", '{"id":"SEC-DOCKER-001","version":"v1"}', origin)[0], 200)
                        self.assertEqual(request("POST", "/api/vulnerabilidades/aplicar", '{"id":"SEC-DOCKER-001","version":"v1"}', origin)[0], 200)
                        self.assertEqual(request("POST", "/api/vulnerabilidades/revertir", '{"id":"SEC-DOCKER-001","version":"v1"}', origin)[0], 200)
                    self.assertEqual(assess.await_count, 3)

                    # Reversible demo reset & restore over HTTP
                    st_rst, rst_body = request("POST", "/api/demo/reiniciar", '{"corridas":true,"sandbox":false,"boards":false,"codigo":false,"prs":false}', origin)
                    self.assertEqual(st_rst, 200)
                    self.assertEqual(json.loads(rst_body)["reinicio"]["corridas"]["archivadas"], 1)
                    st_undo, undo_body = request("POST", "/api/demo/restaurar", "{}", origin)
                    self.assertEqual(st_undo, 200)
                    self.assertEqual(json.loads(undo_body)["restauracion"]["corridas_restauradas"], 1)

                with patch("assessment.ui.start_sandbox", return_value={"activo": True, "version": "v2", "url": "http://127.0.0.1:5080"}):
                    self.assertEqual(request("POST", "/api/sandbox", '{"accion":"iniciar","version":"v9"}', origin)[0], 400)
                    st_sb, body_sb = request("POST", "/api/sandbox", '{"accion":"iniciar","version":"v2"}', origin)
                    self.assertEqual(st_sb, 200)
                    self.assertIn("evaluador=", json.loads(body_sb)["sandbox"]["url_interoperable"])

                with (patch("assessment.ui.OUTPUT", root),
                      patch("assessment.ui.apply_decision", return_value={
                          "accion_propuesta": {
                              "estado": "APROBADA",
                              "boards_resultado": {"operacion": "creada", "referencia": "AB#9", "url": "https://dev.azure.com/demo"},
                          },
                          "etapas_devsecops": [{"numero": 8, "estado": "verificado"}],
                      }) as decide):
                    self.assertEqual(request("POST", "/api/acciones", "{}")[0], 403)
                    self.assertEqual(request("POST", "/api/acciones", '{"ejecucion":"invalido","decision":"aprobar"}', origin)[0], 400)
                    st, resp = request("POST", "/api/acciones", json.dumps({"ejecucion": run_id, "decision": "aprobar", "nota": "OK"}), origin)
                    self.assertEqual(st, 200)
                    self.assertEqual(json.loads(resp)["accion_propuesta"]["boards_resultado"]["referencia"], "AB#9")
                    decide.assert_called_once()

                with (patch("assessment.ui.OUTPUT", root),
                      patch("assessment.ui.assess_project", side_effect=ValueError("fallo inesperado"))):
                    self.assertEqual(request("POST", "/api/evaluar", '{"version":"v1","modo":"solo-evidencia"}', origin)[0], 500)
            finally:
                server.shutdown()


class Logos(unittest.TestCase):
    def test_sirve_los_logos_y_nada_mas(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler) as server:
            Thread(target=server.serve_forever, daemon=True).start()
            try:
                def pedir(ruta):
                    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
                    conn.request("GET", ruta)
                    resp = conn.getresponse()
                    cuerpo = resp.read()
                    conn.close()
                    return resp.status, resp.getheader("Content-Type"), cuerpo

                estado, tipo, cuerpo = pedir("/logos/github.svg")
                self.assertEqual((estado, tipo.split(";")[0]), (200, "image/svg+xml"))
                self.assertIn(b"<svg", cuerpo)
                for ruta in ("/logos/no-existe.svg", "/logos/GitHub.svg", "/logos/../app.js", "/logos/..%2Fapp.js",
                             "/logos/github.svg.bak", "/logos/", "/logos/CREDITOS.md"):
                    self.assertEqual(pedir(ruta)[0], 404, ruta)
            finally:
                server.shutdown()


@unittest.skipIf(sync_playwright is None, "Playwright no está instalado")
class ConsolaEnNavegador(unittest.TestCase):
    def test_cada_herramienta_de_la_etapa_lleva_su_logo(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler) as server:
            Thread(target=server.serve_forever, daemon=True).start()
            try:
                with sync_playwright() as pw:
                    try:
                        browser = pw.chromium.launch(channel="chrome", headless=True)
                    except Exception as exc:  # pragma: no cover - sin Google Chrome instalado
                        self.skipTest(f"Chrome no disponible: {exc}")
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    page.route("**/api/**", lambda r: r.fulfill(status=200, content_type="application/json", body="{}"))
                    page.goto(f"http://127.0.0.1:{server.server_port}/")
                    page.wait_for_function("() => document.querySelectorAll('.stage-tool').length === 9"
                                           " && [...document.querySelectorAll('.stage-tool img')].every((i) => i.complete)")
                    filas = page.evaluate("""() => [...document.querySelectorAll('.stage-tool')].map((s) => {
                        const imgs = [...s.querySelectorAll('img')];
                        return {texto: s.textContent, logos: imgs.map((i) => i.getAttribute('src')), abbr: Boolean(s.querySelector('abbr')),
                                cargados: imgs.every((i) => i.naturalWidth > 0), decorativos: imgs.every((i) => i.alt === '')};
                    })""")
                    browser.close()
            finally:
                server.shutdown()
        self.assertEqual(filas[1]["texto"], "GitHub + VS Code + Copilot")  # el nombre sigue siendo texto
        self.assertEqual(filas[1]["logos"], ["/logos/github.svg", "/logos/vscode.svg", "/logos/copilot.svg"])
        self.assertEqual(filas[2]["logos"], ["/logos/sonarqube.svg", "/logos/trivy.svg", "/logos/codeql.svg", "/logos/dependabot.svg"])
        self.assertEqual(filas[7]["logos"], ["/logos/ai-foundry.svg"])  # Fabric y Security Copilot no tienen logo oficial
        self.assertEqual(filas[8]["logos"], ["/logos/azure-devops.svg"])  # la fila «Decisión humana» también es Boards
        self.assertEqual(sum(len(f["logos"]) for f in filas), 19)
        self.assertTrue(filas[4]["abbr"])  # «AKS» conserva su glosario
        self.assertTrue(all(f["cargados"] and f["decorativos"] for f in filas), filas)

    """La consola servida de verdad en Chrome headless; las /api/ se simulan para no tocar integraciones reales."""

    def test_una_linea_larga_de_codigo_no_ensancha_la_consola(self):
        # Una línea de C# más ancha que la columna se desplaza dentro de su bloque: si ensancha la página,
        # la consola entera se corre a la izquierda (la demo lo mostró al enfocar la remediación).
        linea = "var aviso = new Aviso(contrato.Id, contrato.Correo, contrato.Renovacion, dias, contrato.Cliente.Nombre, contrato.Cliente.Segmento);"
        with ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler) as server:
            Thread(target=server.serve_forever, daemon=True).start()
            try:
                with sync_playwright() as pw:
                    try:
                        browser = pw.chromium.launch(channel="chrome", headless=True)
                    except Exception as exc:  # pragma: no cover - sin Google Chrome instalado
                        self.skipTest(f"Chrome no disponible: {exc}")
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    page.route("**/api/**", lambda r: r.fulfill(status=200, content_type="application/json", body="{}"))
                    page.goto(f"http://127.0.0.1:{server.server_port}/")
                    medir = """(linea) => {
                        const card = document.querySelector('article.card');
                        for (let el = card; el; el = el.parentElement) el.hidden = false;
                        const rem = card.querySelector('.remediation');
                        rem.innerHTML = '<div class="rem-panel"><div class="rem-output"><div class="copyable">'
                          + '<span class="copy"><button class="copy-button" type="button">Copiar C#</button></span>'
                          + '<pre class="rem-pre" tabindex="0"><code></code></pre></div><p class="rem-disclaimer">nota</p></div></div>';
                        rem.querySelector('code').textContent = linea;
                        const caja = (el) => { const b = el.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.right)]; };
                        const medida = () => ({pagina: document.documentElement.scrollWidth, vista: innerWidth,
                            pre: caja(rem.querySelector('.rem-pre')), card: caja(card), boton: caja(rem.querySelector('.copy-button')),
                            bloque: caja(rem.querySelector('.copyable'))});
                        const conPuntero = medida();
                        rem.querySelector('.copyable').style.display = 'flex';  // la variante sin hover (pantallas táctiles)
                        return {conPuntero, tactil: medida()};
                    }"""
                    d = page.evaluate(medir, linea)
                    browser.close()
            finally:
                server.shutdown()
        for variante, m in d.items():
            self.assertGreater(m["pre"][1] - m["pre"][0], 0, f"{variante}: el bloque no se dibujó: {m}")
            self.assertLessEqual(m["pagina"], m["vista"], f"{variante}: la línea ensancha la página: {m}")
            self.assertLessEqual(m["pre"][1], m["card"][1], f"{variante}: el bloque se sale del expediente: {m}")
            self.assertLessEqual(m["boton"][1], m["bloque"][1], f"{variante}: el botón Copiar queda fuera: {m}")

    def test_consola_elige_el_caso(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler) as server:
            Thread(target=server.serve_forever, daemon=True).start()
            try:
                with sync_playwright() as pw:
                    try:
                        browser = pw.chromium.launch(channel="chrome", headless=True)
                    except Exception as exc:  # pragma: no cover - sin Google Chrome instalado
                        self.skipTest(f"Chrome no disponible: {exc}")
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    page.route("**/api/**", lambda r: r.fulfill(status=200, content_type="application/json", body="{}"))
                    page.goto(f"http://127.0.0.1:{server.server_port}/")
                    titulo = page.inner_text("h1#title")
                    self.assertIn("Evaluador de entregas", page.title())
                    self.assertEqual(titulo, "Evaluador de entregas")
                    self.assertNotIn("renovaciones", page.title() + titulo)
                    boton = page.locator("#case-btn")
                    self.assertIn("Portal de Contratos · REN-001", boton.inner_text())
                    boton.click()
                    self.assertEqual(boton.get_attribute("aria-expanded"), "true")
                    opciones = page.locator("#case-list [role=option]")
                    self.assertEqual(opciones.count(), 1)
                    opciones.first.click()
                    self.assertEqual(boton.get_attribute("aria-expanded"), "false")
                    self.assertIn("Un contrato cancelado nunca debe recibir un aviso de renovación.", page.inner_text(".deck-rule"))
                    boton.click()
                    page.keyboard.press("Escape")
                    self.assertEqual(boton.get_attribute("aria-expanded"), "false")
                    self.assertEqual(page.evaluate("document.activeElement.id"), "case-btn")
                    browser.close()
            finally:
                server.shutdown()
