from copy import deepcopy
import json
import os
import shutil
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

from demo import documento, guion, powerbi

MINIMO = {
    "voz": "es-MX-DaliaMultilingualNeural",
    "escenas": [{"id": "a", "titulo": "A", "pasos": [{"tipo": "narrar", "voz": "Hola."}]}],
}


class GuionModelo(unittest.TestCase):
    def test_validar_detecta_errores(self):
        self.assertEqual(guion.validar(MINIMO), [])
        malo = deepcopy(MINIMO)
        malo["escenas"][0]["pasos"] += [
            {"tipo": "bailar"},
            {"tipo": "elegir", "selector": "#x"},
            {"tipo": "clic", "selector": "#y", "opcional": True},
            {"tipo": "narrar", "voz": "x", "motor": "gpt"},
        ]
        self.assertEqual(len(guion.validar(malo)), 4)

    def test_proyectar_modelo(self):
        pasos = [
            {"tipo": "narrar", "voz": "x" * 32},
            {"tipo": "esperar", "condicion": "true", "max_s": 30, "espera_s": [10, 20], "voz_mientras": ["y" * 16]},
            {"tipo": "narrar", "voz": "z" * 16, "opcional": True},
        ]
        d = {t: guion.duracion_estimada(t) for p in pasos for t in guion.voces(p)}
        o = guion.OVERHEAD["narrar"]
        self.assertAlmostEqual(guion.proyectar(pasos, d, 1, "min", False), 2 + o + 0.3 + 10)
        self.assertAlmostEqual(
            guion.proyectar(pasos, d, 0.5, "max", True),
            (2 + o) / 0.5 + max(20, 1 / 0.5) + (1 + o) / 0.5,
        )

    def test_proyectar_suma_el_respiro_segun_velocidad(self):
        # El respiro tras cada línea es tiempo real: no se divide por la velocidad. A 0,75× y en el ensayo (6×) no hay.
        pasos = [{"tipo": "narrar", "voz": ["x" * 16, "y" * 16]}]
        d = {t: guion.duracion_estimada(t) for t in guion.voces(pasos[0])}
        o = guion.OVERHEAD["narrar"]
        self.assertAlmostEqual(guion.proyectar(pasos, d, 1.25), (2 + o) / 1.25 + 2 * 0.6)
        self.assertAlmostEqual(guion.proyectar(pasos, d, 1), 2 + o + 2 * 0.3)
        self.assertAlmostEqual(guion.proyectar(pasos, d, 0.75), (2 + o) / 0.75)
        self.assertAlmostEqual(guion.proyectar(pasos, d, 6), (2 + o) / 6)

    def test_reporte_espera_que_se_dibuje_y_luego_narra(self):
        reporte = {"tipo": "reporte", "voz": "x" * 16, "voz_mientras": ["y" * 32], "max_s": 60, "espera_s": [10, 20]}
        g = deepcopy(MINIMO)
        g["escenas"][0]["pasos"] = [reporte, {"tipo": "reporte", "voz": "z", "espera_s": [9, 3]}]
        self.assertEqual(guion.validar(g), ["a · paso 2: «reporte» necesita «max_s».", "a · paso 2: «espera_s» debe ser [min, max]."])
        d = {t: guion.duracion_estimada(t) for t in guion.voces(reporte)}
        o = guion.OVERHEAD["reporte"]
        self.assertAlmostEqual(guion.proyectar([reporte], d, 1, "min"), 10 + 1 + o + 0.3)
        self.assertAlmostEqual(guion.proyectar([reporte], d, 0.05, "max"), 2 / 0.05 + (1 + o) / 0.05)

    def test_filtrar_motor(self):
        g = deepcopy(MINIMO)
        g["escenas"][0]["pasos"] = [
            {"tipo": "narrar", "voz": "común"},
            {"tipo": "narrar", "voz": "con agentes", "motor": "agente"},
            {"tipo": "narrar", "voz": "sin IA", "motor": "solo-evidencia"},
        ]
        voces = lambda motor: [p["voz"] for p in guion.filtrar(g, motor)["escenas"][0]["pasos"]]
        self.assertEqual(voces("agente"), ["común", "con agentes"])
        self.assertEqual(voces("solo-evidencia"), ["común", "sin IA"])
        self.assertEqual(len(g["escenas"][0]["pasos"]), 3)

    def test_sonar_opcional(self):
        self.assertIs(guion.sonar_opcional(600, 80, 9), True)
        self.assertIs(guion.sonar_opcional(600, 85, 9), False)


class VozCache(unittest.TestCase):
    def test_clave_clip_estable(self):
        from demo import voz
        self.assertEqual(voz.clave_clip(voz.VOZ, "Hola."), voz.clave_clip(voz.VOZ, "Hola."))
        self.assertNotEqual(voz.clave_clip(voz.VOZ, "Hola."), voz.clave_clip(voz.VOZ, "Hola!"))

    def test_ssml_escapa(self):
        from demo import voz
        doc = voz.ssml("A & B <x>", voz.VOZ)
        self.assertIn("A &amp; B &lt;x&gt;", doc)
        self.assertIn('xml:lang="es-MX"', doc)

    def test_preparar_sin_clave(self):
        from demo import voz
        with tempfile.TemporaryDirectory() as tmp:
            res = voz.preparar(["hola mundo"], voz.VOZ, Path(tmp), None)
        self.assertEqual(res, {"hola mundo": {"archivo": None, "duracion": guion.duracion_estimada("hola mundo")}})

    def test_preparar_sin_clave_usa_clip_en_cache(self):
        from demo import voz
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            archivo = cache / f"{voz.clave_clip(voz.VOZ, 'en caché')}.mp3"
            archivo.write_bytes(b"ID3")
            with mock.patch.object(voz, "duracion_mp3", return_value=4.2):
                res = voz.preparar(["en caché", "nueva"], voz.VOZ, cache, None)
        self.assertEqual(res["en caché"], {"archivo": archivo, "duracion": 4.2})
        self.assertEqual(res["nueva"], {"archivo": None, "duracion": guion.duracion_estimada("nueva")})

    def test_eleven_peticion(self):
        from demo import voz
        pedidos = []

        class Respuesta:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b"ID3audio"

        def urlopen(pedido, timeout):
            pedidos.append(pedido)
            return Respuesta()

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(voz.urllib.request, "urlopen", urlopen), \
                mock.patch.object(voz, "duracion_mp3", return_value=1.5):
            res = voz.preparar(["Hola, equipo."], "elevenlabs:abc123", Path(tmp), "clave-de-prueba")
            self.assertEqual(res["Hola, equipo."]["archivo"].read_bytes(), b"ID3audio")
        self.assertEqual(res["Hola, equipo."]["duracion"], 1.5)
        pedido = pedidos[0]
        self.assertEqual(pedido.full_url, "https://api.elevenlabs.io/v1/text-to-speech/abc123?output_format=mp3_44100_128")
        self.assertEqual(pedido.get_header("Xi-api-key"), "clave-de-prueba")
        self.assertEqual(json.loads(pedido.data), {"text": "Hola, equipo.", "model_id": "eleven_multilingual_v2"})

    def test_eleven_error_no_filtra_la_clave(self):
        from demo import voz

        def urlopen(pedido, timeout):
            raise urllib.error.HTTPError(pedido.full_url, 401, "Unauthorized", {}, None)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(voz.urllib.request, "urlopen", urlopen), \
                self.assertRaises(RuntimeError) as error:
            voz.preparar(["Hola."], "elevenlabs:abc123", Path(tmp), "clave-de-prueba")
        self.assertIn("ElevenLabs respondió HTTP 401", str(error.exception))
        self.assertNotIn("clave-de-prueba", str(error.exception))

    @unittest.skipUnless(sys.platform == "darwin", "afinfo y say solo existen en macOS")
    def test_duracion_mp3(self):
        from demo import voz
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "x.aiff"
            subprocess.run(["say", "-o", str(clip), "hola"], check=True)
            self.assertTrue(0 < voz.duracion_mp3(clip) < 3)


class PowerBIDemo(unittest.TestCase):
    """Respaldo del dataset alrededor de la demo y URL del reporte insertado (sin red)."""

    def api(self, filas_dax):
        self.llamadas = []

        def responder(metodo, url, token, cuerpo=None, timeout=20):
            self.llamadas.append((metodo, url, cuerpo))
            if url.endswith("/datasets"):
                return {"value": [{"id": "ds-1", "name": powerbi.DATASET_NAME}]}
            if url.endswith("/executeQueries"):
                return {"results": [{"tables": [{"rows": filas_dax}]}]}
            return {}
        return responder

    def test_respaldo_y_reposicion_ida_y_vuelta(self):
        dax = [{"Corridas[version]": "v1", "Corridas[fecha_utc]": "2026-11-26T15:27:39", "Corridas[modo]": None}]
        with (tempfile.TemporaryDirectory() as tmp, mock.patch("demo.powerbi._az_token", return_value="tok"),
              mock.patch("demo.powerbi._pbi_json", side_effect=self.api(dax))):
            ruta = Path(tmp) / "previo.json"
            self.assertEqual(powerbi.respaldar(ruta), 1)
            self.llamadas.clear()
            self.assertEqual(powerbi.reponer(ruta), 1)
            self.assertFalse(ruta.exists())
        self.assertEqual([m for m, u, _ in self.llamadas if u.endswith("/datasets/ds-1/tables/Corridas/rows")], ["DELETE", "POST"])
        post = next(c for m, u, c in self.llamadas if m == "POST" and u.endswith("/rows"))
        self.assertEqual(post, {"rows": [{"version": "v1", "fecha_utc": "2026-11-26T15:27:39Z", "modo": None}]})

    def test_respaldo_pendiente_no_se_pisa(self):
        # Si la corrida anterior murió tras sincronizar, el dataset tiene filas de demo: vale el respaldo viejo.
        with (tempfile.TemporaryDirectory() as tmp, mock.patch("demo.powerbi._az_token", return_value="tok"),
              mock.patch("demo.powerbi._pbi_json") as api):
            ruta = Path(tmp) / "previo.json"
            ruta.write_text(json.dumps({"dataset_id": "ds-1", "filas": [{"version": "v1"}, {"version": "v2"}]}))
            self.assertEqual(powerbi.respaldar(ruta), 2)
            self.assertIsNone(powerbi.reponer(Path(tmp) / "no-existe.json"))
        api.assert_not_called()

    def test_revision_previa_abre_el_reporte_en_la_pestana_antes_del_iframe(self):
        # La inserción segura guarda la sesión por pestaña («sign in whenever you open a new browser window or tab»):
        # abierto antes como página, el reporte entra con la cookie de Entra del perfil y el iframe de esa pestaña la usa.
        visitas = []
        pagina = mock.MagicMock()
        pagina.goto.side_effect = visitas.append
        url = powerbi.url_embebida("rep-1", "t-123")
        with (mock.patch.object(powerbi, "abrir_perfil", return_value=mock.MagicMock(pages=[pagina])),
              mock.patch("playwright.sync_api.sync_playwright")):
            self.assertIsNone(powerbi.problema_sesion(url, "http://127.0.0.1:8050"))
        self.assertEqual(visitas, [url, "http://127.0.0.1:8050" + powerbi.PRUEBA])

    def test_iniciar_sesion_abre_el_reporte_como_pagina_y_lo_comprueba(self):
        # Entra guarda la sesión persistente al iniciarla en una página, no dentro del iframe. Al cerrar la
        # ventana se comprueba como en la revisión previa.
        visitas = []
        pagina = mock.MagicMock()
        pagina.goto.side_effect = visitas.append
        insertada = powerbi.url_embebida("rep-1", "t-123")
        with (tempfile.TemporaryDirectory() as tmp,
              mock.patch.object(powerbi, "ESTADO", Path(tmp) / "estado.json"),
              mock.patch.object(powerbi, "abrir_perfil", return_value=mock.MagicMock(pages=[pagina])),
              mock.patch.object(powerbi, "token", return_value="tok"),
              mock.patch.object(powerbi, "inquilino", return_value="t-123"),
              mock.patch.object(powerbi, "problema_sesion", return_value="sigue sin dibujarse") as comprobar,
              mock.patch("playwright.sync_api.sync_playwright"), mock.patch("builtins.print")):
            powerbi.ESTADO.write_text(json.dumps({"report_id": "rep-1"}), encoding="utf-8")
            problema = powerbi.iniciar_sesion("http://127.0.0.1:8050")
        self.assertEqual(visitas, [insertada])
        comprobar.assert_called_once_with(insertada, "http://127.0.0.1:8050")
        self.assertEqual(problema, "sigue sin dibujarse")

    def test_url_del_reporte_insertado(self):
        import base64
        from urllib.parse import parse_qs, urlparse
        carga = base64.urlsafe_b64encode(json.dumps({"tid": "t-123"}).encode()).decode().rstrip("=")
        self.assertEqual(powerbi.inquilino(f"cabecera.{carga}.firma"), "t-123")
        url = powerbi.url_embebida("rep-1", "t-123")
        self.assertTrue(url.startswith("https://app.powerbi.com/reportEmbed?"))
        q = parse_qs(urlparse(url).query)
        self.assertEqual((q["reportId"], q["autoAuth"], q["ctid"]), (["rep-1"], ["true"], ["t-123"]))


GUION_REAL = Path(__file__).resolve().parents[2] / "demo/guion.yaml"
IDS_ESCENAS = ["portada", "pregunta", "caso", "ejecutar", "mientras-corre", "dictamen",
               "momento-v3", "seguridad", "gobernanza", "remediacion", "valor", "cierre"]


class GuionReal(unittest.TestCase):
    def setUp(self):
        self.g = guion.cargar(GUION_REAL)

    def test_guion_real_valido(self):
        self.assertEqual(guion.validar(self.g), [])
        self.assertEqual([e["id"] for e in self.g["escenas"]], IDS_ESCENAS)

    def test_detener_el_sandbox_confirma(self):
        # «Detener :5080» se arma en la primera pulsación: sin confirmar, v2 seguía activa y Remediación no podía relanzarla.
        clics = [p for e in self.g["escenas"] for p in e["pasos"] if p["tipo"] == "clic" and p["selector"] == "#stop-sandbox"]
        self.assertTrue(clics)
        self.assertTrue(all(p.get("confirmar") for p in clics), clics)

    def test_guion_real_logos_e_iconos(self):
        slides = {p["plantilla"]: p for e in self.g["escenas"] for p in e["pasos"] if p["tipo"] == "slide"}
        logos = Path(__file__).resolve().parents[1] / "static" / "logos"
        fuentes = slides["pregunta"]["fuentes"]
        self.assertEqual([f["nombre"] for f in fuentes], ["Azure Boards", "GitHub", "Pipelines", "Azure Monitor"])
        for f in fuentes:  # la consola sirve /logos/<nombre>.svg desde assessment/static/logos
            self.assertRegex(f["logo"], r"^/logos/[a-z0-9-]+\.svg$")
            self.assertTrue((logos / f["logo"].removeprefix("/logos/")).is_file(), f["logo"])
        self.assertEqual([t["icono"] for t in slides["cierre"]["tesis"]], ["investigar", "evidencia", "humano"])

    def test_guion_real_ventana(self):
        g = guion.filtrar(self.g, "agente")
        pasos = [p for e in g["escenas"] for p in e["pasos"]]
        d = {t: guion.duracion_estimada(t) for t in guion.lineas(g)}
        self.assertGreaterEqual(guion.proyectar(pasos, d, 1.25, "min", True), 480)
        self.assertLessEqual(guion.proyectar(pasos, d, 0.75, "max", False), 720)

    def test_guion_real_caracteres(self):
        # Quedan 13.548 caracteres en ElevenLabs: el guion completo (ambos motores) no pasa de 11.500.
        self.assertLessEqual(sum(len(t) for t in guion.lineas(self.g)), 11_500)


class RunnerPrevio(unittest.TestCase):
    def test_rutas_sucias(self):
        from demo.__main__ import rutas_sucias
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
            git("init", "-q")
            (repo / "Dockerfile").write_text("FROM x\n")
            (repo / "README.md").write_text("hola\n")
            git("add", ".")
            git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
            self.assertEqual(rutas_sucias(repo), [])
            (repo / "Dockerfile").write_text("FROM y\n")
            (repo / "README.md").write_text("cambio fuera de las rutas de la demo\n")
            self.assertEqual(rutas_sucias(repo), [" M Dockerfile"])

    def test_trivy_vigente(self):
        from datetime import datetime, timezone
        import json
        from demo.__main__ import trivy_vigente
        ahora = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            meta = Path(tmp) / "metadata.json"
            self.assertFalse(trivy_vigente(meta, ahora))
            meta.write_text(json.dumps({"NextUpdate": "2026-11-28T13:04:37.454241698Z"}))
            self.assertTrue(trivy_vigente(meta, ahora))
            meta.write_text(json.dumps({"NextUpdate": "2026-11-26T13:04:37.454241698Z"}))
            self.assertFalse(trivy_vigente(meta, ahora))


class _Screencapture:
    """screencapture -v medido en macOS 27.3: con -V (tope de tiempo), SIGINT la mata sin guardar; sin -V, SIGINT cierra el .mov."""

    def __init__(self, args, **_):
        self.args, self.returncode = args, None

    def poll(self):
        return self.returncode

    def send_signal(self, _senal):
        if any(a.startswith("-V") for a in self.args):
            self.returncode = -2
        else:
            Path(self.args[-1]).write_bytes(b"moov")
            self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


class Respiro(unittest.TestCase):
    def test_cada_linea_pide_el_respiro_que_proyecta_el_guion(self):
        # La página elige el respiro por la velocidad en curso: el mismo que suma proyectar().
        from demo import __main__ as runner
        corrida = runner.Corrida({"escenas": []}, {"hola": {"archivo": None, "duracion": 1.0}}, sin_voz=True, ensayo=False)
        llamadas = []
        corrida.js = lambda codigo, arg=None, en=None: llamadas.append(arg) or 0.0
        corrida.decir("hola", {"narracion_s": 0.0})
        self.assertEqual(llamadas[0][3], {str(v): s for v, s in guion.RESPIRO_S.items()})
        self.assertEqual(llamadas[0][3], {"0.75": 0.0, "1": 0.3, "1.25": 0.6})

    def test_la_espera_de_los_agentes_los_muestra_en_vivo(self):
        from demo import __main__ as runner
        corrida = runner.Corrida({"escenas": []}, {}, sin_voz=True, ensayo=False)
        llamadas = []
        corrida.js = lambda codigo, arg=None, en=None: llamadas.append((codigo, arg)) or {"transcurrido_s": 0.0}
        for agentes in (True, False):
            llamadas.clear()
            corrida._esperar({"en_vivo": "x", "agentes": agentes, "max_s": 5}, {"espera_s": 0.0}, listo=lambda: True)
            en_vivo = [arg for codigo, arg in llamadas if "enVivo(t, o)" in codigo]
            self.assertEqual(en_vivo, [["x", {"agentes": agentes}]])

    def test_guion_real_solo_la_espera_con_agentes_los_muestra(self):
        g = guion.cargar(Path(__file__).resolve().parents[2] / "demo" / "guion.yaml")
        esperas = [p for e in g["escenas"] for p in e["pasos"] if p["tipo"] == "esperar" and p.get("agentes")]
        self.assertEqual([p.get("motor") for p in esperas], ["agente"])


class PdfDelRecorrido(unittest.TestCase):
    """Fuera de las clases con navegador: Playwright síncrono no se anida y armar_pdf abre el suyo."""

    @unittest.skipIf(shutil.which("google-chrome") is None and not Path("/Applications/Google Chrome.app").exists(), "sin Chrome")
    def test_pdf_del_recorrido_una_pagina_por_captura(self):
        import re
        from demo import __main__ as runner
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            (carpeta / "001.png").write_bytes(png_liso())
            (carpeta / "002.png").write_bytes(png_liso(20, 12))  # la ventana cambió de tamaño a mitad de la corrida
            (carpeta / "capturas.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in [
                {"archivo": "001.png", "donde": "portada · paso 1", "texto": "Hola <b>ustedes</b>", "error": False, "t": 1.0},
                {"archivo": "002.png", "donde": "caso · paso 3", "texto": "no apareció «#x»", "error": True, "t": 42.5},
            ]), encoding="utf-8")
            ruta = runner.armar_pdf(Path(os.path.relpath(carpeta)))  # como en GUION_DEMO.md: ruta relativa al repo
            pdf = ruta.read_bytes()
            self.assertTrue(pdf.startswith(b"%PDF"))
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b(?!s)", pdf)), 2)
            pagina = (carpeta / "recorrido.html").read_text(encoding="utf-8")
            self.assertIn("Hola &lt;b&gt;ustedes&lt;/b&gt;", pagina)
            # Cada captura dice a qué tamaño se tomó: así se ve si el recorrido corrió más bajo que la presentación.
            self.assertIn("16×10", pagina)
            self.assertIn("20×12", pagina)


def png_liso(ancho=16, alto=10) -> bytes:
    """PNG azul marino mínimo, para probar el PDF sin tomar capturas."""
    import zlib
    trozo = lambda tipo, datos: struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))
    filas = (b"\x00" + b"\x08\x1c\x3a" * ancho) * alto
    return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
            + trozo(b"IDAT", zlib.compress(filas)) + trozo(b"IEND", b""))


class Grabacion(unittest.TestCase):
    def test_detener_la_grabacion_guarda_el_mov(self):
        from demo import __main__ as runner
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner.subprocess, "Popen", _Screencapture), \
                mock.patch.object(runner.time, "sleep"):
            destino = Path(tmp) / "demo.mov"
            runner.detener_grabacion(runner.grabar(destino))
            self.assertTrue(destino.is_file())

    def test_avisa_si_screencapture_no_guardo_la_grabacion(self):
        from demo import __main__ as runner
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner, "_aviso") as aviso:
            runner.detener_grabacion(_Screencapture(["screencapture", "-v", "-V60", str(Path(tmp) / "demo.mov")]))
        aviso.assert_called_once()
        self.assertIn("grabación", aviso.call_args.args[0])

    def test_la_restauracion_no_la_corta_otra_senal(self):
        # Ya restaurando, un segundo Ctrl+C, un kill o cerrar la terminal no la dejan a medias (28 nov: un SIGTERM
        # cortó la reposición de Power BI).
        import signal
        from demo.__main__ import atrapar_cortes, proteger_restauracion
        previos = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
        self.addCleanup(lambda: [signal.signal(s, h) for s, h in previos.items()])
        atrapar_cortes()
        proteger_restauracion()
        self.assertEqual({signal.getsignal(s) for s in previos}, {signal.SIG_IGN})

    def test_cerrar_la_terminal_corta_como_ctrl_c(self):
        import signal
        from demo.__main__ import atrapar_cortes
        previos = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGHUP)}
        self.addCleanup(lambda: [signal.signal(s, h) for s, h in previos.items()])
        atrapar_cortes()
        for corte in (signal.SIGTERM, signal.SIGHUP):  # se llama al manejador: un SIGHUP real mataría la suite si faltara
            with self.subTest(corte=corte.name), self.assertRaises(KeyboardInterrupt):
                signal.getsignal(corte)(corte, None)


class DocumentoMarkdown(unittest.TestCase):
    def test_tabla_markdown_a_html(self):
        self.assertEqual(
            documento.a_html("| a | b |\n|---|---|\n| 1 | **2** |"),
            "<table><thead><tr><th>a</th><th>b</th></tr></thead><tbody><tr><td>1</td><td><strong>2</strong></td></tr></tbody></table>")

    def test_escapa_html(self):
        html = documento.a_html("<script>x</script>")
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_secciones_elegidas(self):
        informe = ("# REN-001 · v2\n\n**INCUMPLIDO**\n\n"
                   "## Matriz de criterios evaluados\n\n| Criterio | Veredicto |\n| --- | --- |\n| `REN-001` | `INCUMPLIDO` |\n\n"
                   "## Diagnóstico\n\n- Aserción en línea 26\n\n"
                   "## Siguiente paso\n\nCorregir la exclusión de cancelados.\n")
        html = documento.a_html(informe, secciones=["Matriz de criterios evaluados"])
        self.assertTrue(html.startswith("<h1>REN-001 · v2</h1>"), html)
        self.assertIn("<h2>Matriz de criterios evaluados</h2>", html)
        self.assertIn("<td><code>REN-001</code></td>", html)
        for fuera in ("INCUMPLIDO</strong>", "Diagnóstico", "Siguiente paso"):
            self.assertNotIn(fuera, html)

    def test_enlaces_y_listas_anidadas_sin_markdown_crudo(self):
        html = documento.a_html("- Archivos en [informe.json](informe.json) · 6\n  - TRX `Cancelado` · `Failed`\n- Fin")
        self.assertEqual(html, '<ul><li>Archivos en <span class="enlace">informe.json</span> · 6'
                               "<ul><li>TRX <code>Cancelado</code> · <code>Failed</code></li></ul></li><li>Fin</li></ul>")



class ActionsPrevio(unittest.TestCase):
    def test_corrida_verde_elige_la_de_main(self):
        from demo import actions
        pedidas = []

        def github(metodo, url, cabeceras, cuerpo=None, timeout=15):
            pedidas.append((metodo, url))
            return {"workflow_runs": [{"id": 7, "html_url": "https://github.com/o/r/actions/runs/7",
                                       "head_sha": "a" * 40, "updated_at": "2026-11-27T17:53:45Z"}]}
        with mock.patch.object(actions, "load_settings", return_value={}), \
                mock.patch.object(actions, "_gh_token", return_value=None), mock.patch.object(actions, "_http_json", github):
            corrida = actions.corrida_verde("o/r")
        self.assertEqual(corrida, {"id": 7, "url": "https://github.com/o/r/actions/runs/7", "sha": "a" * 40,
                                   "fecha": "2026-11-27T17:53:45Z"})
        self.assertEqual(pedidas, [("GET", "https://api.github.com/repos/o/r/actions/workflows/devsecops.yml/runs"
                                           "?branch=main&status=success&per_page=1")])
        with mock.patch.object(actions, "load_settings", return_value={}), \
                mock.patch.object(actions, "_gh_token", return_value=None), \
                mock.patch.object(actions, "_http_json", return_value={"workflow_runs": []}), \
                self.assertRaisesRegex(RuntimeError, "verde"):
            actions.corrida_verde("o/r")

    def test_repo_origen_acepta_https_y_ssh(self):
        from demo import actions
        remoto = lambda url: mock.patch.object(actions.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=url))
        for url in ("https://github.com/o/r.git\n", "git@github.com:o/r.git\n", "https://github.com/o/r\n"):
            with remoto(url):
                self.assertEqual(actions.repo_origen(), "o/r")
        with remoto("https://dev.azure.com/o/p/_git/r\n"), self.assertRaises(RuntimeError):
            actions.repo_origen()

    def test_revision_previa_detecta_puerto_5080_ocupado(self):
        import socket
        from demo import __main__ as runner
        with socket.socket() as escucha:
            escucha.bind(("127.0.0.1", 0))
            escucha.listen()
            puerto = escucha.getsockname()[1]
            self.assertFalse(runner.puerto_libre(puerto))
        self.assertTrue(runner.puerto_libre(puerto))
        with mock.patch.object(runner, "rutas_sucias", return_value=[]), mock.patch.object(runner, "_ok"), \
                mock.patch.object(runner, "puerto_libre", return_value=False) as libre, \
                self.assertRaisesRegex(runner.Abortar, ":5080"):
            runner.revision_previa("solo-evidencia")
        libre.assert_called_once_with(5080)

    def test_focos_van_en_la_captura_con_una_entrada_por_frase(self):
        def errores(paso):
            g = deepcopy(MINIMO)
            g["escenas"][0]["pasos"] = [paso]
            return guion.validar(g)
        captura = {"tipo": "slide", "plantilla": "captura", "voz": ["Uno.", "Dos."]}
        self.assertEqual(errores({**captura, "focos": [["v1", "v2"], None]}), [])
        mal = ["a · paso 1: «focos» va en la slide «captura», con una entrada por frase de «voz»."]
        self.assertEqual(errores({**captura, "focos": ["v1"]}), mal)
        self.assertEqual(errores({"tipo": "narrar", "voz": "Hola.", "focos": ["v1"]}), mal)



class PasoApp(unittest.TestCase):
    ABRIR, CERRAR = {"tipo": "app", "titulo": "Portal de Contratos · v1"}, {"tipo": "app", "cerrar": True}

    def errores(self, pasos):
        g = deepcopy(MINIMO)
        g["escenas"][0]["pasos"] = pasos
        return guion.validar(g)

    def test_app_sin_cerrar_es_error(self):
        dentro = [{"tipo": "clic", "selector": "#btn-simular"},
                  {"tipo": "esperar", "condicion": "true", "max_s": 5, "espera_s": [0, 1]},
                  {"tipo": "narrar", "voz": "Hola.", "foco": "#estado"}]
        self.assertEqual(self.errores([self.ABRIR, *dentro, self.CERRAR]), [])
        self.assertEqual(self.errores([self.ABRIR, *dentro]), ["a: «app» sin cerrar."])
        self.assertEqual(self.errores([self.CERRAR]), ["a · paso 1: «app» cierra sin haberse abierto."])
        self.assertEqual(self.errores([{"tipo": "app"}, self.CERRAR]), ["a · paso 1: «app» necesita «titulo»."])
        self.assertEqual(guion.proyectar([self.ABRIR, self.CERRAR], {}, 1.0), 3.0)  # 1,5 s de acción cada uno

    def test_dentro_de_app_solo_clic_narrar_esperar(self):
        pasos = [self.ABRIR, {"tipo": "slide", "plantilla": "portada", "voz": "Hola."},
                 {"tipo": "app", "titulo": "Portal de Contratos · v2"}, self.CERRAR]
        self.assertEqual(self.errores(pasos), ["a · paso 2: dentro de «app» solo van clic, narrar y esperar.",
                                               "a · paso 3: dentro de «app» solo van clic, narrar y esperar."])

    def test_limpiar_detiene_el_sandbox_y_borra_sus_datos(self):
        from demo import __main__ as runner
        orden = []
        with mock.patch.object(runner, "_consola", side_effect=lambda *a, **k: orden.append(("consola", *a)) or {}), \
                mock.patch("assessment.demo_reset.clean_sandbox_data", side_effect=lambda repo: orden.append(("datos", repo)) or []), \
                mock.patch.object(runner, "reiniciar_por_http", side_effect=lambda: orden.append(("reinicio",)) or {}), \
                mock.patch.object(runner, "resumen_reinicio", return_value="ok"), \
                mock.patch.object(runner.powerbi, "reponer", return_value=None), \
                mock.patch.object(runner, "rutas_sucias", return_value=[]), \
                mock.patch.object(runner, "puerto_libre", return_value=True), \
                mock.patch.object(runner, "_ok"), mock.patch("builtins.print"):
            runner.limpiar(None, True)
        self.assertEqual(orden, [("consola", "POST", "/api/sandbox", {"accion": "detener"}), ("datos", runner.REPO), ("reinicio",)])


if __name__ == "__main__":
    unittest.main()
