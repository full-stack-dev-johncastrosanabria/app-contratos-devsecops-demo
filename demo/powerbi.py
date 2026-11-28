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
PRUEBA = "/__demo/prueba-powerbi"  # página local donde se inserta el reporte, sobre el sitio de la consola como en la demo
# Un visual ya dibujado: <visual-container> queda inline y sin caja (Playwright nunca lo ve visible); su <visual-modern> sí.
VISUAL = "visual-modern"


def abrir_perfil(pw, argumentos: list[str], headless: bool = False):
    # bypass_csp: el director se inyecta en la consola y su CSP (default-src 'self') bloquearía el iframe del reporte.
    return pw.chromium.launch_persistent_context(
        PERFIL, channel="chrome", headless=headless, args=argumentos,
        ignore_default_args=["--enable-automation"], no_viewport=True, bypass_csp=True)


def _insertado(url: str) -> str:
    return f'<!doctype html><iframe src="{html.escape(url)}" style="width:1280px;height:720px;border:0"></iframe>'


def entrar(pagina, url: str, espera_ms: int = 45_000) -> bool:
    """Abre el reporte como página en esta pestaña: Power BI entra con la cookie de Entra del perfil, sin clics.
    La inserción segura guarda esa sesión por pestaña, así que el iframe solo la usa si va en la misma."""
    # shortcut: el iframe comparte el almacenamiento de la pestaña porque Playwright lanza Chrome sin
    # ThirdPartyStoragePartitioning; si eso cambia, el iframe pedirá iniciar sesión y la revisión previa lo detecta.
    from playwright.sync_api import TimeoutError as TiempoAgotado
    pagina.goto(url)
    try:
        pagina.locator(VISUAL).first.wait_for(timeout=espera_ms)
        return True
    except TiempoAgotado:
        return False


def iniciar_sesion(consola: str) -> str | None:
    """Abre el reporte como página en el perfil de la demo para que la persona inicie sesión una vez (con MFA).
    Al cerrar la ventana lo comprueba como la revisión previa: None si ya se dibuja; si no, qué falló."""
    from playwright.sync_api import Error as ErrorPlaywright, sync_playwright
    url = url_embebida(json.loads(ESTADO.read_text(encoding="utf-8"))["report_id"], inquilino(token()))
    with sync_playwright() as pw:
        contexto = abrir_perfil(pw, ["--window-size=1320,860"])
        try:
            pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
            pagina.goto(url)
            print("Si Power BI te lo pide, inicia sesión y elige mantener la sesión iniciada.\n"
                  "Cuando veas el reporte, cierra la ventana.", flush=True)
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
    """Como la demo, sin ventana y en una sola pestaña: abre el reporte como página y luego lo inserta sobre
    la consola. None si se dibuja; si no, qué falló."""
    from playwright.sync_api import Error as ErrorPlaywright, TimeoutError as TiempoAgotado, sync_playwright
    prueba = consola + PRUEBA
    with sync_playwright() as pw:
        try:
            contexto = abrir_perfil(pw, [], headless=True)
        except ErrorPlaywright as exc:
            return f"no se pudo abrir el perfil de la demo (¿sigue abierta la ventana de inicio de sesión?): {str(exc).splitlines()[0]}"
        try:
            pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
            if not entrar(pagina, url, espera_ms):
                return "Power BI no abrió el reporte con la sesión del perfil de la demo"
            pagina.route(prueba, lambda r: r.fulfill(content_type="text/html; charset=utf-8", body=_insertado(url)))
            pagina.goto(prueba)
            pagina.frame_locator("iframe").locator(VISUAL).first.wait_for(timeout=espera_ms)
            return None
        except TiempoAgotado:
            return "el reporte se abre como página, pero no se dibuja insertado sobre la consola"
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
