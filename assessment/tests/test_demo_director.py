"""Pruebas del director de la demo en un Chrome headless real (sin servidor de la consola)."""
import html
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import urllib.parse

DEMO = Path(__file__).resolve().parents[2] / "demo"
PAGINA = "<!doctype html><html lang='es'><body style='margin:0'><input id='campo'><div id='objetivo' style='width:240px;height:80px;margin:300px'>objetivo</div></body></html>"
ESCENAS = "[{id:'a', titulo:'Escena A'}, {id:'b', titulo:'Escena B'}]"
# Captura simulada de 1600×1000, como las de GitHub Actions (tamaño natural conocido).
CAPTURA = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='1000'>"
           "<rect width='1600' height='1000' fill='%23dde6f3'/></svg>")
CAJAS_JS = """() => {
    const raiz = document.querySelector('#demo-director').shadowRoot;
    const caja = (el) => { const b = el.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; };
    return {img: caja(raiz.querySelector('.s-captura img')), b: caja(raiz.querySelector('.caja[data-caja="b"]')),
            n: raiz.querySelectorAll('.s-captura .caja[data-caja]').length};
}"""
MEDIR_JS = """() => {
    const raiz = document.querySelector('#demo-director').shadowRoot;
    const caja = (el) => { const b = el.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; };
    return {hueco: caja(raiz.querySelector('.foco')),
            cajas: Object.fromEntries([...raiz.querySelectorAll('.s-captura .caja')].map((el) => [el.dataset.caja, caja(el)]))};
}"""

# Portal del sandbox simulado: el botón escribe el resultado en #estado un momento después.
PORTAL_FALSO = ("<!doctype html><body style='margin:0;font:16px system-ui'>"
                "<button id='btn-simular' style='margin:40px'>Ejecutar simulación REN-001 →</button>"
                "<p id='estado' role='status' style='margin:40px;width:420px;height:40px'></p>"
                "<script>document.querySelector('#btn-simular').addEventListener('click', () => setTimeout(() => {"
                " document.querySelector('#estado').textContent = '✕ INCUMPLIMIENTO REN-001 OBSERVADO'; }, 300));</script></body>")


def pagina_actions(jobs, banner=False) -> str:
    """Corrida falsa con la lista lateral de la real (nav «Workflow run», un enlace por job) como data: URL."""
    enlaces = "".join(
        f'<a href="/o/r/actions/runs/7/job/{i}" style="position:absolute;left:32px;top:{370 + 32 * i}px;display:block;'
        f'width:272px;height:32px;overflow:hidden;white-space:nowrap">{html.escape(job)}</a>'
        for i, job in enumerate(jobs))
    tapa = '<div style="position:fixed;left:0;top:300px;width:400px;height:500px;background:#fff"></div>' if banner else ""
    return "data:text/html;charset=utf-8," + urllib.parse.quote(
        f'<!doctype html><body style="margin:0"><nav aria-label="Workflow run">{enlaces}</nav>{tapa}</body>')


try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - el venv de la demo la instala
    sync_playwright = None


def script_director() -> str:
    css = (DEMO / "director.css").read_text(encoding="utf-8")
    return f"window.__DIRECTOR_CSS = {json.dumps(css)};\n" + (DEMO / "director.js").read_text(encoding="utf-8")


@unittest.skipIf(sync_playwright is None, "Playwright no está instalado")
class DirectorEnPagina(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch(channel="chrome", headless=True)
        except Exception as exc:  # pragma: no cover - sin Google Chrome instalado
            cls.pw.stop()
            raise unittest.SkipTest(f"Chrome no disponible: {exc}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def abrir(self, ancho=1440, alto=900, velocidad=1):
        page = self.browser.new_page(viewport={"width": ancho, "height": alto})
        self.addCleanup(page.close)
        page.set_content(PAGINA)
        page.add_script_tag(content=script_director())
        page.evaluate(f"() => __director.iniciar({{escenas: {ESCENAS}, velocidad: {velocidad}, pasoAPaso: false, total_s: 60}})")
        return page

    def test_pausa_descuenta(self):
        page = self.abrir()
        page.evaluate("() => { window.__t0 = performance.now(); window.__fin = null; __director.decir('x', null, 1.0).then(() => { window.__fin = performance.now() - window.__t0; }); }")
        page.wait_for_timeout(300)
        page.evaluate("() => __director.pausar()")
        self.assertTrue(page.evaluate("() => __director.estado().pausado"))
        page.wait_for_timeout(1000)
        page.keyboard.press("Space")
        page.wait_for_function("() => window.__fin !== null", timeout=5000)
        self.assertTrue(1900 <= page.evaluate("() => window.__fin") <= 2300)

    def test_velocidad_escala(self):
        page = self.abrir(velocidad=1.25)
        ms = page.evaluate("async () => { const t = performance.now(); await __director.esperar(1000); return performance.now() - t; }")
        self.assertAlmostEqual(ms, 800, delta=150)

    def test_siguiente_corta(self):
        page = self.abrir()
        page.evaluate("() => { window.__t0 = performance.now(); window.__fin = null; __director.decir('línea', null, 5).then(() => { window.__fin = performance.now() - window.__t0; }); }")
        page.wait_for_timeout(100)
        page.keyboard.press("n")
        page.wait_for_function("() => window.__fin !== null", timeout=3000)
        self.assertLess(page.evaluate("() => window.__fin"), 500)

    def test_teclas_en_input_no_controlan(self):
        page = self.abrir()
        page.focus("#campo")
        page.keyboard.type("a b")
        self.assertFalse(page.evaluate("() => __director.estado().pausado"))
        self.assertEqual(page.input_value("#campo"), "a b")

    def test_terminar_en_pausa_libera_turno(self):
        page = self.abrir()
        page.evaluate("() => { window.__eventos = []; window.__demoEvento = (e) => { window.__eventos.push(e.tipo); }; }")
        page.evaluate("() => { __director.pausar(); window.__libre = false; __director.turno().then(() => { window.__libre = true; }); }")
        page.wait_for_timeout(150)
        self.assertFalse(page.evaluate("() => window.__libre"))
        page.keyboard.press("q")
        page.keyboard.press("q")
        page.wait_for_function("() => window.__libre", timeout=2000)
        self.assertIn("terminar", page.evaluate("() => window.__eventos"))

    def test_tras_terminar_no_hay_mas_lineas(self):
        page = self.abrir()
        page.keyboard.press("q")
        page.keyboard.press("q")
        ms = page.evaluate("async () => { const t = performance.now(); await __director.decir('x', null, 5); await __director.esperar(5000); return performance.now() - t; }")
        self.assertLess(ms, 300)
        self.assertTrue(page.evaluate("() => __director.estado().terminado"))

    def subtitulo_visible(self, page) -> bool:
        return page.evaluate("() => document.querySelector('#demo-director').shadowRoot"
                             ".querySelector('.subtitulos').hasAttribute('data-visible')")

    def test_con_voz_no_hay_subtitulo(self):
        page = self.abrir()
        # En la misma tarea JS: antes de que el clip pueda fallar y degradar a subtítulo.
        self.assertFalse(page.evaluate(
            "() => { __director.decir('Con voz.', 'data:audio/mpeg;base64,AAAA', 5);"
            " return document.querySelector('#demo-director').shadowRoot.querySelector('.subtitulos').hasAttribute('data-visible'); }"))

    def test_si_el_clip_falla_vuelve_el_subtitulo(self):
        page = self.abrir()
        page.evaluate("() => { __director.decir('Sin audio.', 'data:audio/mpeg;base64,AAAA', 5); }")
        page.wait_for_function("() => document.querySelector('#demo-director').shadowRoot"
                               ".querySelector('.subtitulos').hasAttribute('data-visible')", timeout=3000)
        self.assertTrue(self.subtitulo_visible(page))

    def test_foco_espera_al_elemento_que_aparece_tarde(self):
        # La consola dibuja algunas piezas tras una llamada al servidor (p. ej. la plantilla de remediación).
        from demo.__main__ import Corrida
        page = self.abrir()
        page.evaluate("() => setTimeout(() => { const d = document.createElement('div'); d.id = 'tarde';"
                      " d.style.cssText = 'width:120px;height:40px'; document.body.append(d); }, 400)")
        corrida = Corrida({"escenas": []}, {"Mira esto.": {"archivo": None, "duracion": 0.2}}, sin_voz=True, ensayo=True)
        corrida.page = page
        corrida._narrar({"tipo": "narrar", "voz": "Mira esto.", "foco": "#tarde"}, {"narracion_s": 0.0})
        self.assertEqual(corrida.fallos, [])

    def test_reporte_ocupa_la_pantalla_sin_tapar_la_barra(self):
        for ancho, alto in ((1440, 900), (1920, 1080)):
            with self.subTest(viewport=f"{ancho}x{alto}"):
                page = self.abrir(ancho, alto)
                page.evaluate("() => __director.slide('reporte', {url: 'about:blank', titulo: 'Reporte ejecutivo de Power BI'})")
                d = page.evaluate("""() => {
                    const raiz = document.querySelector('#demo-director').shadowRoot;
                    const marco = raiz.querySelector('.slide iframe');
                    const caja = (el) => { const b = el.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
                    return {src: marco.getAttribute('src'), tab: marco.tabIndex, punteros: getComputedStyle(marco).pointerEvents,
                            titulo: marco.title, marco: caja(marco), barra: caja(raiz.querySelector('.barra')),
                            membrete: caja(raiz.querySelector('.membrete'))};
                }""")
                # El iframe nunca toma el foco: Espacio, flechas y Q siguen llegando al director.
                self.assertEqual((d["src"], d["tab"], d["punteros"], d["titulo"]),
                                 ("about:blank", -1, "none", "Reporte ejecutivo de Power BI"))
                izq, arriba, der, abajo = d["marco"]
                self.assertLessEqual(abajo, d["barra"][1], f"la barra tapa el reporte: {d}")
                self.assertLessEqual(d["membrete"][3], arriba, f"el membrete pisa el reporte: {d}")
                self.assertGreater(der - izq, 0.9 * ancho)
                self.assertGreater(abajo - arriba, 0.75 * alto)

    def test_reporte_inserta_power_bi_espera_que_dibuje_y_narra(self):
        from demo import powerbi
        from demo.__main__ import Corrida
        page = self.abrir()
        pedidas = []

        def power_bi_falso(route):
            pedidas.append(route.request.url)
            route.fulfill(content_type="text/html", body=(
                "<!doctype html><body><script>setTimeout(() => { const v = document.createElement('visual-container');"
                " v.style.cssText = 'display:block;width:200px;height:80px'; document.body.append(v); }, 300)</script></body>"))
        page.route("https://app.powerbi.com/**", power_bi_falso)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(powerbi, "ESTADO", Path(tmp) / "estado.json"):
            powerbi.ESTADO.write_text(json.dumps({"report_id": "rep-1"}), encoding="utf-8")
            corrida = Corrida({"escenas": []}, {"Este es el reporte.": {"archivo": None, "duracion": 0.2}}, sin_voz=True, ensayo=True)
            corrida.page, corrida.inquilino = page, "t-1"
            corrida._reporte({"tipo": "reporte", "voz": "Este es el reporte.", "max_s": 10, "espera_s": [1, 3]},
                             {"narracion_s": 0.0, "espera_s": 0.0})
        self.assertEqual(corrida.fallos, [])
        self.assertTrue(pedidas and "reportId=rep-1" in pedidas[0] and "ctid=t-1" in pedidas[0], pedidas)
        self.assertTrue(page.evaluate("() => document.querySelector('#demo-director').shadowRoot.querySelector('.slide').hidden"))

    def test_layout_sin_solapes(self):
        for ancho, alto in ((1440, 900), (1920, 1080)):
            with self.subTest(viewport=f"{ancho}x{alto}"):
                page = self.abrir(ancho, alto)
                page.evaluate("() => { __director.decir('Esta es una línea de narración larga, de las que ocupan dos renglones en pantalla para comprobar que los subtítulos nunca tapan la barra de control.', null, 30); }")
                page.wait_for_timeout(400)
                cajas = page.evaluate("""() => {
                    const raiz = document.querySelector('#demo-director').shadowRoot;
                    const r = (sel) => { const b = raiz.querySelector(sel).getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
                    return {sub: r('.subtitulos'), barra: r('.barra')};
                }""")
                sub, barra = cajas["sub"], cajas["barra"]
                self.assertTrue(sub[3] <= barra[1] or barra[3] <= sub[1], f"se solapan: {cajas}")
                for caja in (sub, barra):
                    self.assertTrue(caja[0] >= 0 and caja[1] >= 0 and caja[2] <= ancho and caja[3] <= alto, f"fuera del viewport: {caja}")


    def test_app_ocupa_la_pantalla_sin_tapar_la_barra(self):
        for ancho, alto in ((1440, 900), (1920, 1080)):
            with self.subTest(viewport=f"{ancho}x{alto}"):
                page = self.abrir(ancho, alto)
                page.evaluate("() => __director.slide('app', {url: 'about:blank', titulo: 'Portal de Contratos · v2'})")
                d = page.evaluate("""() => {
                    const raiz = document.querySelector('#demo-director').shadowRoot;
                    const marco = raiz.querySelector('.slide iframe.marco-app');
                    const url = raiz.querySelector('.s-app .url');
                    const caja = (el) => { const b = el.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
                    return {src: marco.getAttribute('src'), tab: marco.tabIndex, punteros: getComputedStyle(marco).pointerEvents,
                            titulo: marco.title, marco: caja(marco), ventana: caja(raiz.querySelector('.s-app .navegador')),
                            url: url.textContent, urlCaja: caja(url),
                            barra: caja(raiz.querySelector('.barra')), membrete: caja(raiz.querySelector('.membrete'))};
                }""")
                # El portal nunca toma el foco ni los punteros: el teclado sigue siendo del director.
                self.assertEqual((d["src"], d["tab"], d["punteros"], d["titulo"]),
                                 ("about:blank", -1, "none", "Portal de Contratos · v2"))
                self.assertEqual(d["url"], "about:blank")
                izq, arriba, der, abajo = d["ventana"]
                self.assertLessEqual(abajo, d["barra"][1], f"la barra tapa el portal: {d}")
                self.assertLessEqual(d["membrete"][3], arriba, f"el membrete pisa el portal: {d}")
                self.assertGreater(der - izq, 0.9 * ancho)
                self.assertGreater(d["marco"][3] - d["marco"][1], 0.65 * alto)
                self.assertTrue(arriba <= d["urlCaja"][1] and d["urlCaja"][3] <= d["marco"][1], f"la URL no se ve sobre el portal: {d}")

    def test_captura_marca_cada_job(self):
        for ancho, alto in ((1440, 900), (1920, 1080)):
            with self.subTest(viewport=f"{ancho}x{alto}"):
                page = self.abrir(ancho, alto)
                page.evaluate("""(src) => __director.slide('captura', {src, titulo: 'Corrida verde en main', ancho: 1600, alto: 1000,
                                  cajas: {a: [100, 100, 400, 80], b: [800, 500, 600, 120]}})""", CAPTURA)
                d = page.evaluate(CAJAS_JS)
                self.assertEqual(d["n"], 2)
                ix, iy, iw, ih = d["img"]
                bx, by, bw, bh = d["b"]
                k = iw / 1600
                self.assertAlmostEqual(ih, 1000 * k, delta=2)
                for real, esperado in ((bx, ix + 800 * k), (by, iy + 500 * k), (bw, 600 * k), (bh, 120 * k)):
                    self.assertAlmostEqual(real, esperado, delta=2)
                self.assertTrue(ix <= bx and bx + bw <= ix + iw and iy <= by and by + bh <= iy + ih)

    def test_documento_muestra_el_html_con_formato(self):
        html = ("<h1>Informe de v2</h1><h2>Matriz de criterios evaluados</h2>"
                "<table><thead><tr><th>Criterio</th><th>Estado</th></tr></thead>"
                "<tbody><tr><td>REN-001</td><td><strong>Incumplido</strong></td></tr></tbody></table>")
        for ancho, alto in ((1440, 900), (1920, 1080)):
            with self.subTest(viewport=f"{ancho}x{alto}"):
                page = self.abrir(ancho, alto)
                page.evaluate("(html) => __director.slide('documento', {titulo: 'informe.md · v2', html})", html)
                d = page.evaluate("""() => {
                    const raiz = document.querySelector('#demo-director').shadowRoot;
                    const caja = (el) => { const b = el.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
                    const doc = raiz.querySelector('article.s-documento');
                    return {tabla: caja(doc.querySelector('table')), negrita: !!doc.querySelector('td strong'),
                            h1: getComputedStyle(doc.querySelector('h1')).fontSize, barra: caja(raiz.querySelector('.barra'))};
                }""")
                self.assertTrue(d["negrita"])
                izq, arriba, der, abajo = d["tabla"]
                self.assertTrue(izq >= 0 and arriba >= 0 and der <= ancho, f"la tabla se sale: {d}")
                self.assertLessEqual(abajo, d["barra"][1], f"la barra tapa la tabla: {d}")
                self.assertLess(float(d["h1"].rstrip("px")), 48, "el h1 del informe no debe heredar el titular de slide")

    def test_foco_por_caja_sobre_una_slide(self):
        page = self.abrir()
        page.evaluate("(src) => __director.slide('captura', {src, titulo: 'x', ancho: 1600, alto: 1000, cajas: {b: [800, 500, 600, 120]}})", CAPTURA)
        ix, iy, iw, ih = page.evaluate(CAJAS_JS)["img"]
        bx, by, bw, bh = page.evaluate(CAJAS_JS)["b"]
        self.assertTrue(page.evaluate("(c) => __director.foco(c)", {"x": bx, "y": by, "width": bw, "height": bh}))
        page.wait_for_timeout(400)
        d = page.evaluate("""() => {
            const raiz = document.querySelector('#demo-director').shadowRoot;
            const velo = raiz.querySelector('.velo-foco'), hueco = raiz.querySelector('.foco').getBoundingClientRect();
            return {visible: velo.hasAttribute('data-visible') && !velo.hidden, opacidad: +getComputedStyle(velo).opacity,
                    zVelo: +getComputedStyle(velo).zIndex, zSlide: +getComputedStyle(raiz.querySelector('.slide')).zIndex,
                    hueco: [hueco.left, hueco.top, hueco.width, hueco.height]};
        }""")
        self.assertTrue(d["visible"] and d["opacidad"] > 0.9, d)
        self.assertGreater(d["zVelo"], d["zSlide"], "el velo debe quedar sobre la slide")
        for real, esperado in zip(d["hueco"], (bx, by, bw, bh)):
            self.assertAlmostEqual(real, esperado, delta=2)


    def test_captura_de_actions_devuelve_una_caja_por_job(self):
        from demo import actions
        with tempfile.TemporaryDirectory() as tmp:
            captura = actions.capturar({"id": 7, "url": pagina_actions(actions.JOBS)}, Path(tmp), self.pw)
            png = captura["imagen"].read_bytes()
        self.assertEqual(list(captura["cajas"]), list(actions.JOBS))
        self.assertEqual(captura["cajas"]["Evidencia xUnit (v2)"], [32, 402, 272, 32])
        self.assertEqual(captura["imagen"].name, "actions-7.png")
        # 1280×800: en la slide de 1440×900 el texto de GitHub queda en ~12 px en vez de ~9,5 px.
        self.assertEqual((captura["ancho"], captura["alto"]), (1280, 800))
        self.assertEqual(struct.unpack(">II", png[16:24]), (2560, 1600), "device scale 2")

    def test_captura_de_actions_aborta_si_falta_o_se_tapa_un_job(self):
        from demo import actions
        sin_trivy = [j for j in actions.JOBS if "Trivy" not in j]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, r"Escaneo IaC, contenedor y SCA \(Trivy\)"):
                actions.capturar({"id": 7, "url": pagina_actions(sin_trivy)}, Path(tmp), self.pw)
            with self.assertRaisesRegex(RuntimeError, r"Evidencia xUnit \(v1\)"):
                actions.capturar({"id": 7, "url": pagina_actions(actions.JOBS, banner=True)}, Path(tmp), self.pw)
            self.assertEqual(list(Path(tmp).iterdir()), [], "sin todos los jobs no se guarda la captura")

    def test_slide_de_captura_recorre_los_jobs_con_el_foco(self):
        from demo.__main__ import Corrida
        page = self.abrir()
        textos = ["Primero las pruebas.", "Luego la imagen.", "Uno más."]
        corrida = Corrida({"escenas": []}, {t: {"archivo": None, "duracion": 0.2} for t in textos}, sin_voz=True, ensayo=True)
        corrida.page, corrida.k, corrida.planos = page, 0, [{}, {}]  # no es la última slide: al terminar se oculta
        corrida.actions = {"src": CAPTURA, "ancho": 1600, "alto": 1000, "titulo": "Corrida verde en main",
                           "cajas": {"v1": [32, 370, 272, 32], "v2": [32, 402, 272, 32], "oci": [32, 562, 272, 32]}}
        vistos, decir = [], corrida.decir

        def decir_y_medir(texto, fila):  # el hueco del velo y las cajas mientras suena cada frase
            page.wait_for_timeout(700)
            vistos.append(page.evaluate(MEDIR_JS))
            decir(texto, fila)
        corrida.decir = decir_y_medir
        corrida._slide({"tipo": "slide", "plantilla": "captura", "voz": textos[:2], "focos": [["v1", "v2"], "oci"]},
                       {"narracion_s": 0.0})
        self.assertEqual(corrida.fallos, [])
        (h1, c1), (h2, c2) = [(v["hueco"], v["cajas"]) for v in vistos]
        union = [c1["v1"][0], c1["v1"][1], c1["v1"][2], c1["v2"][1] + c1["v2"][3] - c1["v1"][1]]
        for real, esperado in [*zip(h1, union), *zip(h2, c2["oci"])]:
            self.assertAlmostEqual(real, esperado, delta=2)
        self.assertTrue(page.evaluate("""() => { const r = document.querySelector('#demo-director').shadowRoot;
            return r.querySelector('.slide').hidden && !r.querySelector('.velo-foco').hasAttribute('data-visible'); }"""))
        corrida.decir = decir
        corrida._slide({"tipo": "slide", "plantilla": "captura", "voz": textos[2:], "focos": ["no-existe"]}, {"narracion_s": 0.0})
        self.assertEqual(len(corrida.fallos), 1)
        self.assertIn("no-existe", corrida.fallos[0])


    def test_app_actua_dentro_del_portal_sin_robar_el_teclado(self):
        from demo.__main__ import Corrida
        page = self.abrir()
        page.route("http://127.0.0.1:5080/**", lambda r: r.fulfill(content_type="text/html", body=PORTAL_FALSO))
        corrida = Corrida({"escenas": []}, {"Miren el estado.": {"archivo": None, "duracion": 0.2}}, sin_voz=True, ensayo=True)
        corrida.page = page
        fila = {"narracion_s": 0.0, "espera_s": 0.0}
        corrida._app({"tipo": "app", "titulo": "Portal de Contratos · v2"}, fila)
        self.assertTrue(corrida.marco.url.startswith("http://127.0.0.1:5080"), corrida.marco.url)
        corrida._clic({"tipo": "clic", "selector": "#btn-simular"}, fila)
        corrida._esperar({"tipo": "esperar", "condicion": "document.querySelector('#estado').textContent.includes('OBSERVADO')",
                          "max_s": 5, "espera_s": [0, 2]}, fila)
        corrida._narrar({"tipo": "narrar", "voz": "Miren el estado.", "foco": "#estado"}, fila)
        self.assertEqual(corrida.fallos, [])
        page.wait_for_timeout(700)
        caja = corrida.marco.locator("#estado").bounding_box()
        hueco = page.evaluate("""() => { const b = document.querySelector('#demo-director').shadowRoot.querySelector('.foco').getBoundingClientRect();
                                 return [b.left, b.top, b.width, b.height]; }""")
        for real, esperado in zip(hueco, (caja["x"], caja["y"], caja["width"], caja["height"])):
            self.assertAlmostEqual(real, esperado, delta=2)
        page.keyboard.press("Space")  # el iframe nunca tomó el foco: el teclado sigue siendo del director
        self.assertTrue(page.evaluate("() => __director.estado().pausado"))
        page.keyboard.press("Space")
        corrida._app({"tipo": "app", "cerrar": True}, fila)
        self.assertIsNone(corrida.marco)
        self.assertTrue(page.evaluate("() => document.querySelector('#demo-director').shadowRoot.querySelector('.slide').hidden"))
        self.assertEqual(corrida.fallos, [])


    def test_documento_muestra_el_informe_mas_reciente_de_la_version(self):
        import os
        from demo import __main__ as runner
        page = self.abrir()
        corrida = runner.Corrida({"escenas": []}, {"El informe.": {"archivo": None, "duracion": 0.2}}, sin_voz=True, ensayo=True)
        corrida.page = page
        paso = {"tipo": "slide", "plantilla": "documento", "informe": "v2", "titulo": "informe.md · v2",
                "secciones": ["Matriz de criterios evaluados"], "voz": "El informe."}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner, "RUNS", Path(tmp)):
            for nombre, version, marca, cuando in (("a", "v2", "vieja", 1000), ("b", "v2", "nueva", 2000),
                                                   ("c", "v1", "otra-version", 3000), ("_archivo", "v2", "archivada", 4000)):
                carpeta = Path(tmp) / nombre
                carpeta.mkdir()
                (carpeta / "informe.json").write_text(json.dumps({"ejecucion": {"version": version}}), encoding="utf-8")
                (carpeta / "informe.md").write_text(
                    f"# REN-001 · {version}\n\n**{marca}-dictamen**\n\n## Matriz de criterios evaluados\n\n"
                    f"| Criterio | Veredicto |\n| --- | --- |\n| `REN-001` | `{marca}` |\n\n## Siguiente paso\n\nOtra cosa.\n",
                    encoding="utf-8")
                os.utime(carpeta / "informe.json", (cuando, cuando))
            corrida._slide(paso, {"narracion_s": 0.0})
            self.assertEqual(corrida.fallos, [])
            texto = page.evaluate("() => document.querySelector('#demo-director').shadowRoot.querySelector('.s-documento').innerText")
            self.assertIn("nueva", texto)
            for fuera in ("vieja", "otra-version", "archivada", "Siguiente paso", "nueva-dictamen"):
                self.assertNotIn(fuera, texto)
            corrida._slide({**paso, "informe": "v3"}, {"narracion_s": 0.0})
        self.assertEqual(len(corrida.fallos), 1)
        self.assertIn("v3", corrida.fallos[0])

    def test_la_consola_no_abre_pestanas_durante_la_demo(self):
        # La consola abre una pestaña al lanzar el sandbox y otra para Power BI: le quitarían la pantalla a la demo.
        from demo.__main__ import SIN_VENTANAS
        page = self.abrir()
        page.add_script_tag(content=SIN_VENTANAS)
        self.assertEqual(page.evaluate("() => ['nextgen_powerbi_web', 'nextgen_sandbox_5080'].map((n) => window.open('about:blank', n))"),
                         [None, None])


if __name__ == "__main__":
    unittest.main()
