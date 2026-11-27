from copy import deepcopy
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


if __name__ == "__main__":
    unittest.main()
