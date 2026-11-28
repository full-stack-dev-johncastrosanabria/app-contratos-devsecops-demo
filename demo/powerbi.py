"""Power BI en la demo: perfil de Chrome con sesión, reporte insertado y respaldo del dataset.

El botón de la consola sincroniza el dataset borrando y volviendo a cargar todas sus filas. La demo
guarda antes las que había y las repone al restaurar, así Power BI queda como lo encontró.
"""
import base64
import html
import json
import re
from pathlib import Path
from urllib.parse import urlencode

from assessment.integrations import _az_token
from assessment.powerbi_cloud import DATASET_NAME, PBI_BASE, PBI_RESOURCE, _pbi_json

DEMO = Path(__file__).resolve().parent
PERFIL = DEMO / ".perfil"  # perfil de Chrome de la demo: conserva la sesión de Power BI (fuera de git)
RESPALDO = DEMO / ".registro" / "powerbi-previo.json"
ESTADO = DEMO.parent / "assessment/runs/_estado_powerbi.json"
TABLA = "Corridas"
LOTE = 5000  # la Push API acepta hasta 10.000 filas por POST
# Página local donde se inserta el reporte, en el sitio de la consola: la sesión del iframe se guarda
# particionada por ese sitio, así que solo vale la que se inicia ahí (no la del reporte suelto).
PRUEBA = "/__demo/prueba-powerbi"
VISUAL = "visual-container, .visual-container"  # un visual ya dibujado dentro del reporte


def abrir_perfil(pw, argumentos: list[str], headless: bool = False):
    # bypass_csp: el director se inyecta en la consola y su CSP (default-src 'self') bloquearía el iframe del reporte.
    return pw.chromium.launch_persistent_context(
        PERFIL, channel="chrome", headless=headless, args=argumentos,
        ignore_default_args=["--enable-automation"], no_viewport=True, bypass_csp=True)


def _insertado(url: str) -> str:
    return f'<!doctype html><iframe src="{html.escape(url)}" style="width:1280px;height:720px;border:0"></iframe>'


def iniciar_sesion(consola: str) -> str | None:
    """Abre el reporte insertado como en la demo para que la persona inicie sesión una vez (con MFA).
    Al cerrar la ventana lo comprueba como la revisión previa: None si ya se dibuja; si no, qué falló."""
    from playwright.sync_api import Error as ErrorPlaywright, sync_playwright
    url = url_embebida(json.loads(ESTADO.read_text(encoding="utf-8"))["report_id"], inquilino(token()))
    with sync_playwright() as pw:
        contexto = abrir_perfil(pw, ["--window-size=1320,860"])
        try:
            pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
            pagina.route(consola + PRUEBA, lambda r: r.fulfill(content_type="text/html; charset=utf-8", body=_insertado(url)))
            pagina.goto(consola + PRUEBA)
            print("Pulsa «Iniciar sesión» dentro del reporte y completa el acceso; si te lo ofrece, mantén la sesión\n"
                  "iniciada. Cuando veas el reporte, cierra la ventana.", flush=True)
            pagina.wait_for_event("close", timeout=0)
        except ErrorPlaywright:
            pass  # cerró Chrome entero en vez de la ventana
        finally:
            try:
                contexto.close()
            except ErrorPlaywright:
                pass
    return problema_sesion(url, consola)


def problema_sesion(url: str, consola: str, espera_ms: int = 45_000) -> str | None:
    """Inserta el reporte en una página local sin ventana, con el perfil de la demo: igual que en la demo
    (iframe de terceros sobre la consola). None si se dibuja; si no, qué falló."""
    from playwright.sync_api import Error as ErrorPlaywright, TimeoutError as TiempoAgotado, sync_playwright
    prueba = consola + PRUEBA
    with sync_playwright() as pw:
        try:
            contexto = abrir_perfil(pw, [], headless=True)
        except ErrorPlaywright as exc:
            return f"no se pudo abrir el perfil de la demo (¿sigue abierta la ventana de inicio de sesión?): {str(exc).splitlines()[0]}"
        try:
            pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
            pagina.route(prueba, lambda r: r.fulfill(content_type="text/html; charset=utf-8", body=_insertado(url)))
            pagina.goto(prueba)
            pagina.frame_locator("iframe").locator(VISUAL).first.wait_for(timeout=espera_ms)
            return None
        except TiempoAgotado:
            return "el reporte insertado no se dibujó: el perfil de la demo no tiene sesión en el iframe de Power BI"
        finally:
            contexto.close()


def inquilino(token: str) -> str:
    carga = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(carga + "=" * (-len(carga) % 4)))["tid"]


def url_embebida(report_id: str, tenant: str) -> str:
    """Inserción segura: el iframe usa la sesión del navegador (autoAuth); la página no recibe tokens."""
    return "https://app.powerbi.com/reportEmbed?" + urlencode({
        "reportId": report_id, "autoAuth": "true", "ctid": tenant,
        "navContentPaneEnabled": "false", "filterPaneEnabled": "false"})


def token() -> str:
    valor = _az_token(PBI_RESOURCE)
    if not valor:
        raise RuntimeError("no hay sesión de Azure CLI con acceso a Power BI (az login)")
    return valor


def _dataset(token: str) -> str:
    datasets = _pbi_json("GET", f"{PBI_BASE}/datasets", token).get("value") or []
    ds = next((d for d in datasets if d.get("name") == DATASET_NAME), None)
    if not ds:
        raise RuntimeError(f"no existe el dataset «{DATASET_NAME}» en Power BI")
    return ds["id"]


def respaldar(ruta: Path = RESPALDO) -> int:
    """Guarda las filas actuales del dataset. Un respaldo que quedó sin reponer (la corrida anterior
    murió después de sincronizar) vale más que el dataset, que ya trae filas de la demo: se conserva."""
    if ruta.is_file():
        return len(json.loads(ruta.read_text(encoding="utf-8"))["filas"])
    tk = token()
    dataset = _dataset(tk)
    r = _pbi_json("POST", f"{PBI_BASE}/datasets/{dataset}/executeQueries", tk,
                  {"queries": [{"query": f"EVALUATE {TABLA}"}], "serializerSettings": {"includeNulls": True}})
    filas = [{clave.split("[", 1)[1].rstrip("]"): valor for clave, valor in fila.items()}
             for fila in r["results"][0]["tables"][0].get("rows") or []]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"dataset_id": dataset, "filas": filas}, ensure_ascii=False), encoding="utf-8")
    return len(filas)


def _utc(valor):
    # DAX devuelve las fechas sin zona; la consola las carga en UTC con «Z».
    return valor + "Z" if isinstance(valor, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?", valor) else valor


def reponer(ruta: Path = RESPALDO) -> int | None:
    """Deja el dataset con las filas del respaldo y borra el respaldo. None si no había."""
    if not ruta.is_file():
        return None
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    filas = [{**f, "fecha_utc": _utc(f["fecha_utc"])} if "fecha_utc" in f else f for f in datos["filas"]]
    tk = token()
    url = f"{PBI_BASE}/datasets/{datos['dataset_id']}/tables/{TABLA}/rows"
    _pbi_json("DELETE", url, tk)
    for i in range(0, len(filas), LOTE):
        _pbi_json("POST", url, tk, {"rows": filas[i:i + LOTE]})
    ruta.unlink()
    return len(filas)
