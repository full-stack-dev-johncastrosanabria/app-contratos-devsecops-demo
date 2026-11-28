"""Pruebas del director de la demo en un Chrome headless real (sin servidor de la consola)."""
import json
from pathlib import Path
import unittest

DEMO = Path(__file__).resolve().parents[2] / "demo"
PAGINA = "<!doctype html><html lang='es'><body style='margin:0'><input id='campo'><div id='objetivo' style='width:240px;height:80px;margin:300px'>objetivo</div></body></html>"
ESCENAS = "[{id:'a', titulo:'Escena A'}, {id:'b', titulo:'Escena B'}]"

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


if __name__ == "__main__":
    unittest.main()
