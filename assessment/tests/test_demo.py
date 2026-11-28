from copy import deepcopy
import json
from pathlib import Path
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
            {"tipo": "narrar", "voz": "x" * 34},
            {"tipo": "esperar", "condicion": "true", "max_s": 30, "espera_s": [10, 20], "voz_mientras": ["y" * 17]},
            {"tipo": "narrar", "voz": "z" * 17, "opcional": True},
        ]
        d = {t: guion.duracion_estimada(t) for p in pasos for t in guion.voces(p)}
        o = guion.OVERHEAD["narrar"]
        self.assertAlmostEqual(guion.proyectar(pasos, d, 1, "min", False), 2 + o + 10)
        self.assertAlmostEqual(
            guion.proyectar(pasos, d, 0.5, "max", True),
            (2 + o) / 0.5 + max(20, 1 / 0.5) + (1 + o) / 0.5,
        )

    def test_reporte_espera_que_se_dibuje_y_luego_narra(self):
        reporte = {"tipo": "reporte", "voz": "x" * 17, "voz_mientras": ["y" * 34], "max_s": 60, "espera_s": [10, 20]}
        g = deepcopy(MINIMO)
        g["escenas"][0]["pasos"] = [reporte, {"tipo": "reporte", "voz": "z", "espera_s": [9, 3]}]
        self.assertEqual(guion.validar(g), ["a · paso 2: «reporte» necesita «max_s».", "a · paso 2: «espera_s» debe ser [min, max]."])
        d = {t: guion.duracion_estimada(t) for t in guion.voces(reporte)}
        o = guion.OVERHEAD["reporte"]
        self.assertAlmostEqual(guion.proyectar([reporte], d, 1, "min"), 10 + 1 + o)
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
IDS_ESCENAS = ["portada", "pregunta", "consola", "caso", "ejecutar", "mientras-corre", "dictamen",
               "momento-v3", "etapas", "seguridad", "gobernanza", "remediacion", "valor", "cierre"]


class GuionReal(unittest.TestCase):
    def setUp(self):
        self.g = guion.cargar(GUION_REAL)

    def test_guion_real_valido(self):
        self.assertEqual(guion.validar(self.g), [])
        self.assertEqual([e["id"] for e in self.g["escenas"]], IDS_ESCENAS)

    def test_guion_real_ventana(self):
        g = guion.filtrar(self.g, "agente")
        pasos = [p for e in g["escenas"] for p in e["pasos"]]
        d = {t: guion.duracion_estimada(t) for t in guion.lineas(g)}
        self.assertGreaterEqual(guion.proyectar(pasos, d, 1.25, "min", True), 480)
        self.assertLessEqual(guion.proyectar(pasos, d, 0.75, "max", False), 720)


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


if __name__ == "__main__":
    unittest.main()
