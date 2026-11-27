"""Narración con voz neural de Azure Speech o con una voz propia de ElevenLabs, cacheada en disco por línea:
solo se regenera lo que cambia."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

from .guion import duracion_estimada

VOZ = "es-MX-DaliaMultilingualNeural"
FORMATO = "audio-48khz-96kbitrate-mono-mp3"
ENDPOINT = "https://westus3.tts.speech.microsoft.com/cognitiveservices/v1"
ELEVEN = "elevenlabs:"  # prefijo de una voz de ElevenLabs: «elevenlabs:<voice_id>»
ENDPOINT_ELEVEN = "https://api.elevenlabs.io/v1/text-to-speech/{}?output_format=mp3_44100_128"
MODELO_ELEVEN = "eleven_multilingual_v2"


def clave_clip(voz: str, texto: str) -> str:
    return hashlib.sha1(f"{voz}|{texto}".encode("utf-8")).hexdigest()


def ssml(texto: str, voz: str) -> str:
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{voz[:5]}">'
        f'<voice name="{escape(voz)}">{escape(texto)}</voice></speak>'
    )


def duracion_mp3(ruta: Path) -> float:
    salida = subprocess.run(["afinfo", str(ruta)], capture_output=True, text=True, check=True).stdout
    encontrada = re.search(r"estimated duration: ([\d.]+)", salida)
    if not encontrada:
        raise RuntimeError(f"No se pudo leer la duración de {Path(ruta).name}.")
    return float(encontrada.group(1))


def _sintetizar(texto: str, voz: str, destino: Path, clave: str) -> None:
    if voz.startswith(ELEVEN):
        servicio = "ElevenLabs"
        pedido = urllib.request.Request(
            ENDPOINT_ELEVEN.format(urllib.parse.quote(voz.removeprefix(ELEVEN), safe="")),
            data=json.dumps({"text": texto, "model_id": MODELO_ELEVEN}).encode("utf-8"),
            method="POST",
            headers={"xi-api-key": clave, "Content-Type": "application/json", "Accept": "audio/mpeg", "User-Agent": "demo-tts"},
        )
    else:
        servicio = "Azure Speech"
        pedido = urllib.request.Request(
            ENDPOINT,
            data=ssml(texto, voz).encode("utf-8"),
            method="POST",
            headers={
                "Ocp-Apim-Subscription-Key": clave,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": FORMATO,
                "User-Agent": "demo-tts",
            },
        )
    try:
        with urllib.request.urlopen(pedido, timeout=60) as respuesta:
            audio = respuesta.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{servicio} respondió HTTP {exc.code} al sintetizar «{texto[:48]}…».") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Sin conexión con {servicio} ({exc.reason}).") from None
    temporal = destino.with_suffix(".tmp")
    temporal.write_bytes(audio)
    temporal.replace(destino)  # un corte a medias nunca deja un clip truncado en la caché


def preparar(lineas: list[str], voz: str, cache: Path, clave: str | None) -> dict[str, dict]:
    """Un clip por línea. Sin clave no sintetiza: usa el clip si ya está en caché o la duración estimada."""
    clips: dict[str, dict] = {}
    for texto in lineas:
        archivo = cache / f"{clave_clip(voz, texto)}.mp3"
        if not archivo.is_file():
            if clave is None:
                clips[texto] = {"archivo": None, "duracion": duracion_estimada(texto)}
                continue
            cache.mkdir(parents=True, exist_ok=True)
            _sintetizar(texto, voz, archivo, clave)
        clips[texto] = {"archivo": archivo, "duracion": duracion_mp3(archivo)}
    return clips
