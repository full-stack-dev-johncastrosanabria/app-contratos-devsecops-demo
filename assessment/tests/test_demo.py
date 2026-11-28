from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

from demo import guion

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


if __name__ == "__main__":
    unittest.main()
