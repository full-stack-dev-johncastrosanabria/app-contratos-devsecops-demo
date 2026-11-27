from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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
        ]
        self.assertEqual(len(guion.validar(malo)), 3)

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

    @unittest.skipUnless(sys.platform == "darwin", "afinfo y say solo existen en macOS")
    def test_duracion_mp3(self):
        from demo import voz
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "x.aiff"
            subprocess.run(["say", "-o", str(clip), "hola"], check=True)
            self.assertTrue(0 < voz.duracion_mp3(clip) < 3)


if __name__ == "__main__":
    unittest.main()
