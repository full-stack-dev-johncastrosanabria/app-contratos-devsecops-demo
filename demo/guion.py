"""Esquema del guion de la demo y modelo de tiempo (narración que escala con la velocidad, esperas reales que no)."""
from pathlib import Path

import yaml

TIPOS: dict[str, tuple[str, ...]] = {
    "slide": ("plantilla", "voz"),
    "narrar": ("voz",),
    "clic": ("selector",),
    "elegir": ("selector", "valor"),
    "escribir": ("selector", "texto"),
    "esperar": ("condicion", "max_s", "espera_s"),
    "reporte": ("voz", "max_s", "espera_s"),  # Power BI insertado: espera a que se dibuje y narra encima
}
MOTORES = ("agente", "solo-evidencia")
VENTANA_S = (480, 720)
LIMITE_S = 690
CARACTERES_POR_S = 17  # ritmo medido de Dalia a 1×
OVERHEAD = {"slide": 1.5, "narrar": 0.6, "clic": 1.2, "elegir": 1.0, "escribir": 0.0, "esperar": 0.0, "reporte": 1.0}
TECLEO_S = 0.06
ESPERAS = ("esperar", "reporte")  # pasos con una espera real que «voz_mientras» puede cubrir


def cargar(ruta: Path) -> dict:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def validar(guion: dict) -> list[str]:
    errores: list[str] = []
    if not isinstance(guion, dict) or not guion.get("voz"):
        errores.append("El guion necesita «voz» (nombre de la voz neural).")
    escenas = (guion or {}).get("escenas") or []
    if not escenas:
        errores.append("El guion necesita al menos una escena.")
    for e_idx, escena in enumerate(escenas, 1):
        nombre = escena.get("id") or f"escena {e_idx}"
        if not escena.get("id") or not escena.get("titulo"):
            errores.append(f"{nombre}: falta «id» o «titulo».")
        for p_idx, paso in enumerate(escena.get("pasos") or [], 1):
            donde = f"{nombre} · paso {p_idx}"
            tipo = paso.get("tipo")
            if tipo not in TIPOS:
                errores.append(f"{donde}: tipo desconocido «{tipo}».")
                continue
            for campo in TIPOS[tipo]:
                if paso.get(campo) in (None, "", []):
                    errores.append(f"{donde}: «{tipo}» necesita «{campo}».")
            if paso.get("motor") not in (None, *MOTORES):
                errores.append(f"{donde}: «motor» debe ser agente o solo-evidencia.")
            if paso.get("opcional") and tipo != "narrar":
                errores.append(f"{donde}: «opcional» solo vale en «narrar».")
            espera = paso.get("espera_s")
            if tipo in ESPERAS and espera and not (isinstance(espera, list) and len(espera) == 2 and espera[0] <= espera[1]):
                errores.append(f"{donde}: «espera_s» debe ser [min, max].")
    return errores


def filtrar(guion: dict, motor: str) -> dict:
    """El guion sin los pasos marcados para el otro motor; no modifica el original."""
    return {**guion, "escenas": [
        {**escena, "pasos": [p for p in escena.get("pasos") or [] if p.get("motor") in (None, motor)]}
        for escena in guion.get("escenas") or []
    ]}


def lista(valor) -> list[str]:
    if not valor:
        return []
    return [valor] if isinstance(valor, str) else list(valor)


def voces(paso: dict) -> list[str]:
    return lista(paso.get("voz")) + lista(paso.get("voz_mientras")) + lista(paso.get("relleno"))


def lineas(guion: dict) -> list[str]:
    vistas: dict[str, None] = {}
    for escena in guion.get("escenas") or []:
        for paso in escena.get("pasos") or []:
            for texto in voces(paso):
                vistas.setdefault(texto, None)
    return list(vistas)


def duracion_estimada(texto: str) -> float:
    return len(texto) / CARACTERES_POR_S


def proyectar(pasos: list[dict], duraciones: dict[str, float], velocidad: float,
              esperas: str = "nominal", opcionales: bool = True) -> float:
    total = 0.0
    for paso in pasos:
        tipo = paso["tipo"]
        if paso.get("opcional") and not opcionales:
            continue
        if tipo in ESPERAS:
            minimo, maximo = paso["espera_s"]
            espera = {"min": minimo, "max": maximo}.get(esperas, (minimo + maximo) / 2)
            cubierta = sum(duraciones[t] for t in lista(paso.get("voz_mientras")))
            total += max(espera, cubierta / velocidad)
            if tipo == "esperar":
                continue
        narracion = sum(duraciones[t] for t in lista(paso.get("voz")))
        accion = OVERHEAD[tipo] + (TECLEO_S * len(paso.get("texto", "")) if tipo == "escribir" else 0.0)
        total += (narracion + accion) / velocidad
    return total


def sonar_opcional(transcurrido_s: float, restante_s: float, linea_s: float, limite_s: float = LIMITE_S) -> bool:
    return transcurrido_s + restante_s + linea_s <= limite_s
