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

    def abrir(self, ancho=1440, alto=900, velocidad=1, gsap=False, movimiento=None):
        page = self.browser.new_page(viewport={"width": ancho, "height": alto}, reduced_motion=movimiento)
        self.addCleanup(page.close)
        page.set_content(PAGINA)
        if gsap:  # el mismo GSAP que inyecta el runner; sin él, el director no anima y nada más cambia
            from demo.__main__ import GSAP
            page.add_script_tag(content=GSAP)
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

    def test_respiro_en_segundos_reales_y_siguiente_lo_corta(self):
        page = self.abrir(velocidad=1.25)
        # A 1,25× el respiro tras la línea no se acelera: 2 s reales, no 1,6.
        ms = page.evaluate("async () => { const t = performance.now(); await __director.decir('línea', null, 0, 2); return performance.now() - t; }")
        self.assertAlmostEqual(ms, 2000, delta=150)
        for duracion in (0, 5):  # «Siguiente» corta el respiro, y si corta la línea tampoco deja respiro
            page.evaluate(f"() => {{ window.__t0 = performance.now(); window.__fin = null; __director.decir('línea', null, {duracion}, 5).then(() => {{ window.__fin = performance.now() - window.__t0; }}); }}")
            page.wait_for_timeout(100)
            page.keyboard.press("n")
            page.wait_for_function("() => window.__fin !== null", timeout=3000)
            self.assertLess(page.evaluate("() => window.__fin"), 500, duracion)

    def test_pregunta_pone_el_logo_de_cada_fuente(self):
        page = self.abrir()
        page.evaluate("() => __director.slide('pregunta', {pregunta: '¿?', remate: 'r', fuentes: [{nombre: 'GitHub', logo: '/logos/github.svg'}, 'Sin logo']})")
        islas = page.evaluate("""() => [...document.querySelector('#demo-director').shadowRoot.querySelectorAll('.islas li')].map((li) => {
            const img = li.querySelector('img');
            return {texto: li.textContent.trim(), logo: img ? img.getAttribute('src') : null, alt: img ? img.getAttribute('alt') : null,
                    nodo: Boolean(li.querySelector('.nodo'))};
        })""")
        self.assertEqual(islas, [{"texto": "GitHub", "logo": "/logos/github.svg", "alt": "", "nodo": False},
                                 {"texto": "Sin logo", "logo": None, "alt": None, "nodo": True}])

    def test_cierre_pone_un_icono_propio_por_tesis(self):
        page = self.abrir()
        page.evaluate("() => __director.slide('cierre', {tesis: [{texto: 'a', icono: 'investigar'}, {texto: 'b', icono: 'evidencia'}, {texto: 'c', icono: 'humano'}, 'd']})")
        tesis = page.evaluate("""() => [...document.querySelector('#demo-director').shadowRoot.querySelectorAll('.tesis li')].map((li) => {
            const svg = li.querySelector('svg.ico');
            return {texto: li.querySelector('p').textContent, forma: svg ? svg.innerHTML : '', nodo: Boolean(li.querySelector('.nodo'))};
        })""")
        self.assertEqual([t["texto"] for t in tesis], ["a", "b", "c", "d"])
        self.assertTrue(all(t["forma"] and not t["nodo"] for t in tesis[:3]), tesis)
        self.assertEqual(len({t["forma"] for t in tesis[:3]}), 3)  # un dibujo distinto por idea
        self.assertEqual((tesis[3]["forma"], tesis[3]["nodo"]), ("", True))  # sin icono, el nodo de siempre

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
            # Como el Power BI real: <visual-container> queda inline y sin caja; lo que se ve es su <visual-modern>.
            route.fulfill(content_type="text/html", body=(
                "<!doctype html><body><script>setTimeout(() => { document.body.innerHTML = '<visual-container>"
                "<div class=\"visual\" style=\"position:absolute;left:0;top:0;width:200px;height:80px\">"
                "<visual-modern style=\"display:block;width:200px;height:80px\"></visual-modern></div></visual-container>'; }, 300)"
                "</script></body>"))
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

    # ---------- Animaciones (GSAP) ----------

    def test_gsap_sigue_la_velocidad_y_la_pausa(self):
        page = self.abrir(velocidad=0.75, gsap=True)
        reloj = "() => [gsap.globalTimeline.timeScale(), gsap.globalTimeline.paused()]"
        self.assertEqual(page.evaluate(reloj), [0.75, False])
        page.keyboard.press(">")
        page.evaluate("() => __director.pausar()")
        self.assertEqual(page.evaluate(reloj), [1, True])
        page.keyboard.press("Space")
        self.assertEqual(page.evaluate(reloj), [1, False])
        # Otra corrida en la misma página parte sin pausa y a su propia velocidad.
        page.evaluate("() => __director.pausar()")
        page.evaluate(f"() => __director.iniciar({{escenas: {ESCENAS}, velocidad: 1.25, pasoAPaso: false, total_s: 60}})")
        self.assertEqual(page.evaluate(reloj), [1.25, False])

    def test_maf_los_tres_agentes_trabajan_a_la_vez_y_la_pausa_los_congela(self):
        page = self.abrir(gsap=True)
        page.evaluate("() => __director.slide('maf', {})")
        raiz = "document.querySelector('#demo-director').shadowRoot"
        paquetes = f"() => [...{raiz}.querySelectorAll('.grafo .paquete')].map((p) => getComputedStyle(p).transform + ' ' + getComputedStyle(p).opacity)"
        self.assertEqual(len(page.evaluate(paquetes)), 4)  # uno por rama y uno hacia la aprobación humana
        # Las tres ramas corren en paralelo: hay un momento en que los tres agentes trabajan juntos.
        page.wait_for_function(f"() => [...{raiz}.querySelectorAll('.agentes .trabajo')].filter((t) => +getComputedStyle(t).opacity > 0.5).length === 3",
                               timeout=8000)
        page.wait_for_function(f"() => [...{raiz}.querySelectorAll('.grafo .paquete')].some((p) => +getComputedStyle(p).opacity > 0.5)",
                               timeout=8000)
        antes = page.evaluate(paquetes)
        page.wait_for_timeout(150)
        self.assertNotEqual(page.evaluate(paquetes), antes)
        page.evaluate("() => __director.pausar()")
        congelado = page.evaluate(paquetes)
        page.wait_for_timeout(400)
        self.assertEqual(page.evaluate(paquetes), congelado)

    def test_slide_animada_no_retrasa_el_guion(self):
        # Las animaciones son decorativas: slide() resuelve a los 0,6 s de contenido, como sin GSAP.
        page = self.abrir(velocidad=1.25, gsap=True)
        ms = page.evaluate("async () => { const t = performance.now(); await __director.slide('maf', {}); return performance.now() - t; }")
        self.assertAlmostEqual(ms, 600 / 1.25, delta=150)

    def test_cambiar_o_retirar_la_slide_detiene_sus_animaciones(self):
        page = self.abrir(gsap=True)
        vivas = "() => gsap.globalTimeline.getChildren(true, true, true).length"
        page.evaluate("() => __director.slide('maf', {})")
        self.assertGreater(page.evaluate(vivas), 0)
        page.evaluate("() => __director.slide('portada', {titulo: 'T', subtitulo: 'S'})")
        self.assertEqual(page.evaluate(vivas), 0)
        page.evaluate("() => __director.slide('gobernanza', {pasos: ['a', {texto: 'b', destacar: true}, 'c']})")
        self.assertGreater(page.evaluate(vivas), 0)
        page.evaluate("() => __director.ocultarSlide()")
        self.assertEqual(page.evaluate(vivas), 0)

    def test_movimiento_reducido_no_anima_las_slides(self):
        page = self.abrir(gsap=True, movimiento="reduce")
        for plantilla, datos in (("maf", {}), ("gobernanza", {"pasos": ["a", {"texto": "b", "destacar": True}]}),
                                 ("pregunta", {"pregunta": "¿?", "fuentes": ["A", "B"], "remate": "r"}),
                                 ("cierre", {"tesis": [{"texto": "t", "icono": "humano"}]})):
            page.evaluate("([p, d]) => __director.slide(p, d)", [plantilla, datos])
            self.assertEqual(page.evaluate("() => gsap.globalTimeline.getChildren(true, true, true).length"), 0, plantilla)

    def test_pregunta_y_cierre_terminan_de_dibujarse(self):
        page = self.abrir(velocidad=1.25, gsap=True)
        raiz = "document.querySelector('#demo-director').shadowRoot"
        page.evaluate("() => __director.slide('pregunta', {pregunta: '¿?', fuentes: ['A', 'B', 'C'], remate: 'r'})")
        islas = f"[...{raiz}.querySelectorAll('.islas li')]"
        self.assertGreater(page.evaluate(f"() => gsap.getTweensOf({islas}).length"), 0)
        page.wait_for_function(f"() => gsap.getTweensOf({islas}).length === 0", timeout=5000)
        self.assertEqual(page.evaluate(f"() => {islas}.map((li) => getComputedStyle(li).getPropertyValue('--trazo').trim())"), ["1", "1", "1"])
        page.evaluate("() => __director.slide('cierre', {tesis: [{texto: 'a', icono: 'investigar'}, {texto: 'b', icono: 'humano'}]})")
        trazos = f"[...{raiz}.querySelectorAll('.tesis .insignia .ico > *')]"
        self.assertGreater(page.evaluate(f"() => gsap.getTweensOf({trazos}).length"), 0)
        page.wait_for_function(f"() => gsap.getTweensOf({trazos}).length === 0", timeout=5000)
        self.assertTrue(page.evaluate(f"() => {trazos}.every((t) => parseFloat(getComputedStyle(t).strokeDashoffset) === 0)"))

    def test_en_vivo_de_los_agentes_muestra_tres_trabajando(self):
        page = self.abrir()
        ver = ("() => { const e = document.querySelector('#demo-director').shadowRoot.querySelector('.envivo');"
               " return {agentes: [...e.querySelectorAll('.agente')].filter((a) => a.checkVisibility()).length,"
               " punto: e.querySelector('.punto').checkVisibility()}; }")
        page.evaluate("() => __director.enVivo('los agentes evalúan las tres entregas', {agentes: true})")
        self.assertEqual(page.evaluate(ver), {"agentes": 3, "punto": False})
        page.evaluate("() => __director.enVivo('la consola trabaja')")
        self.assertEqual(page.evaluate(ver), {"agentes": 0, "punto": True})

    def test_gsap_solo_en_el_marco_principal(self):
        # add_init_script corre en cada marco: el reporte de Power BI y el portal no necesitan GSAP.
        from demo.__main__ import GSAP
        page = self.browser.new_page()
        self.addCleanup(page.close)
        page.set_content("<iframe srcdoc='<p>marco</p>'></iframe>")
        page.add_script_tag(content=GSAP)
        marco = page.frames[1]
        marco.add_script_tag(content=GSAP)
        self.assertEqual([page.evaluate("() => typeof window.gsap"), marco.evaluate("() => typeof window.gsap")],
                         ["object", "undefined"])


if __name__ == "__main__":
    unittest.main()
