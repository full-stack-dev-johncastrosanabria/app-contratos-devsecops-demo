"""La corrida verde más reciente del pipeline en main, capturada de su página pública en GitHub Actions.

github.com no se deja insertar en un iframe (X-Frame-Options: deny), así que la demo muestra una
captura tomada en la revisión previa, con la caja de cada job para recorrerlos con el foco.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess

from playwright.sync_api import Error as ErrorPlaywright

from assessment.integrations import _gh_token, _http_json, load_settings

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = "devsecops.yml"
# Nombres exactos de la lista lateral de la corrida; CodeQL es una matriz de dos jobs.
JOBS = (
    "Evidencia xUnit (v1)",
    "Evidencia xUnit (v2)",
    "Evidencia xUnit (v3)",
    "Seguridad en origen (CodeQL) (csharp, autobuild)",
    "Seguridad en origen (CodeQL) (python, none)",
    "Escaneo IaC, contenedor y SCA (Trivy)",
    "Construir imagen OCI (GHCR)",
)
ANCHO, ALTO = 1600, 1000
LISTA_JOBS = 'nav[aria-label="Workflow run"] a[href*="/job/"]'
# Caja de cada job que se ve entero y sin nada encima (un banner que lo tape cuenta como que falta).
CAJAS_JS = """(selector) => {
    const cajas = {};
    for (const a of document.querySelectorAll(selector)) {
        const r = a.getBoundingClientRect();
        if (!r.width || !r.height || r.right > innerWidth || r.bottom > innerHeight) continue;
        const encima = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        if (encima && a.contains(encima)) cajas[a.innerText.split(/\\s+/).join(' ').trim()] = [r.left, r.top, r.width, r.height].map(Math.round);
    }
    return cajas;
}"""


def repo_origen() -> str:
    url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    hallado = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/\s]+/[^/\s]+?)(?:\.git)?/?", url)
    if not hallado:
        raise RuntimeError("el remoto origin no es un repositorio de GitHub")
    return hallado.group(1)


def corrida_verde(repo: str) -> dict:
    cabeceras = {"Accept": "application/vnd.github+json", "User-Agent": "NextGen-DevSecOps-Assessment"}
    token = _gh_token(load_settings())  # con token el límite de la API sube de 60 a 5000 por hora
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/runs?branch=main&status=success&per_page=1"
    corridas = _http_json("GET", url, cabeceras).get("workflow_runs") or []
    if not corridas:
        raise RuntimeError(f"no hay ninguna corrida verde de {WORKFLOW} en main")
    c = corridas[0]
    return {"id": c["id"], "url": c["html_url"], "sha": c["head_sha"], "fecha": c["updated_at"]}


def capturar(corrida: dict, destino: Path, pw) -> dict:
    navegador = pw.chromium.launch(channel="chrome", headless=True)
    try:
        pagina = navegador.new_page(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=2)
        pagina.goto(corrida["url"], wait_until="load", timeout=60_000)
        try:  # la lista lateral se dibuja después de la carga
            pagina.locator(LISTA_JOBS).first.wait_for(timeout=30_000)
        except ErrorPlaywright:
            raise RuntimeError("la página de la corrida no muestra la lista de jobs") from None
        cajas = pagina.evaluate(CAJAS_JS, LISTA_JOBS)
        faltan = [job for job in JOBS if job not in cajas]
        if faltan:
            raise RuntimeError("la página de la corrida no deja ver " + ", ".join(f"«{job}»" for job in faltan))
        destino.mkdir(parents=True, exist_ok=True)
        imagen = destino / f"actions-{int(corrida['id'])}.png"
        pagina.screenshot(path=str(imagen))
    finally:
        navegador.close()
    return {"imagen": imagen, "ancho": ANCHO, "alto": ALTO, "cajas": {job: cajas[job] for job in JOBS}}
