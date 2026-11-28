"""Demo narrada de la consola REN-001 en Chrome a pantalla completa: python -m demo [opciones].

Reinicia el entorno, hace la revisión previa, abre Chrome con el director inyectado, recorre el guion
(grabando pantalla y audio en ~/Movies) y, al salir por cualquier vía, deja el entorno listo para repetir."""
import argparse
import base64
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from dotenv import dotenv_values
from playwright.sync_api import Error as ErrorPlaywright, TimeoutError as TiempoAgotado, sync_playwright

from . import actions, documento, guion, powerbi, voz

DEMO = Path(__file__).resolve().parent
REPO = DEMO.parent
RUNS = REPO / "assessment/runs"  # = assessment.ui.OUTPUT; importar ui tarda 5 s
CONSOLA = "http://127.0.0.1:8050"
PUERTO_SANDBOX = 5080  # = assessment.ui.SANDBOX_PORT
PORTAL = f"http://127.0.0.1:{PUERTO_SANDBOX}"
CABECERAS = {"Host": "127.0.0.1:8050", "Origin": CONSOLA, "Content-Type": "application/json"}
REINICIO_COMPLETO = {"corridas": True, "sandbox": True, "boards": True, "codigo": True, "prs": True}
RUTAS_DEMO = ("v1", "v2", "v3", "Dockerfile", "deploy", ".github")
TRIVY_META = Path.home() / "Library/Caches/trivy/db/metadata.json"
CACHE_VOZ = DEMO / ".voz"
REGISTROS = DEMO / ".registro"
GRABACIONES = Path.home() / "Movies"
ATAJOS_APAGADOS = 'try { localStorage.setItem("nextgen.atajos", "off"); } catch (e) {}'
# La demo enseña el reporte y el portal en sus propias slides: las pestañas que abre la consola le quitarían la pantalla.
SIN_VENTANAS = ('(() => { const abrir = window.open, propias = ["nextgen_powerbi_web", "nextgen_sandbox_5080"];'
                ' window.open = function (url, nombre, ...resto) {'
                ' return propias.includes(nombre) ? null : abrir.call(window, url, nombre, ...resto); }; })();')
OCULTAR_DIRECTOR = "#demo-director{visibility:hidden!important}"
VELOCIDAD_ENSAYO = 6  # fuera del menú: la primera tecla de velocidad vuelve a 0,75/1/1,25
ESPERA_ELEMENTO_MS = 10_000
MAX_REINTENTOS = 3
TOPE_GRABACION_S = 2700  # si el runner muere sin detenerla, screencapture para sola a los 45 min


class Abortar(Exception):
    """Falló un chequeo bloqueante de la revisión previa."""


class Terminar(Exception):
    """El presentador pulsó Terminar (Q dos veces)."""


def _ok(texto: str) -> None:
    print(f"  ✓ {texto}", flush=True)


def _aviso(texto: str) -> None:
    print(f"  ! {texto}", flush=True)


def _ajuste(clave: str) -> str:
    return (os.environ.get(clave) or dotenv_values(REPO / "assessment/.env", interpolate=False).get(clave) or "").strip()


def rutas_sucias(repo: Path) -> list[str]:
    salida = subprocess.run(["git", "status", "--porcelain", "--", *RUTAS_DEMO], cwd=repo,
                            capture_output=True, text=True, check=True).stdout
    return [linea for linea in salida.splitlines() if linea.strip()]


def trivy_vigente(metadata: Path, ahora: datetime) -> bool:
    try:
        return datetime.fromisoformat(json.loads(metadata.read_text(encoding="utf-8"))["NextUpdate"]) > ahora
    except (OSError, ValueError, KeyError, TypeError):
        return False


# ---------- Consola (:8050) ----------

def _consola(metodo: str, ruta: str, cuerpo: dict | None = None, timeout: float = 15) -> dict:
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    pedido = urllib.request.Request(CONSOLA + ruta, data=datos, method=metodo, headers=CABECERAS if datos else {})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as respuesta:
            return json.loads(respuesta.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            detalle = json.loads(exc.read()).get("error")
        except (ValueError, AttributeError):
            detalle = None
        raise RuntimeError(detalle or f"HTTP {exc.code}") from None


def _responde(url: str, timeout: float = 3) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except OSError:
        return False


def informe_reciente(version: str) -> str | None:
    """informe.md de la evaluación más reciente de la versión; como la consola, salta las carpetas «_» (archivo)."""
    hallados = []
    for informe in RUNS.glob("*/informe.json"):
        md = informe.parent / "informe.md"
        if informe.parent.name.startswith("_") or not md.is_file():
            continue
        try:
            if (json.loads(informe.read_text(encoding="utf-8")).get("ejecucion") or {}).get("version") == version:
                hallados.append((informe.stat().st_mtime, md))
        except (OSError, ValueError):
            continue
    return max(hallados)[1].read_text(encoding="utf-8") if hallados else None


def puerto_libre(puerto: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", puerto)) != 0


def asegurar_consola() -> subprocess.Popen | None:
    """None si la consola ya respondía; si no, la lanza y devuelve su proceso (la demo la detiene al salir)."""
    if _responde(CONSOLA + "/"):
        return None
    REGISTROS.mkdir(exist_ok=True)
    with (REGISTROS / "consola.log").open("ab") as log:
        proceso = subprocess.Popen([sys.executable, "-m", "assessment.ui"], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
    limite = time.monotonic() + 30
    while time.monotonic() < limite and proceso.poll() is None:
        if _responde(CONSOLA + "/"):
            return proceso
        time.sleep(0.3)
    detener_consola(proceso)
    raise Abortar(f"la consola no arrancó; revisa {REGISTROS / 'consola.log'}.")


def detener_consola(proceso: subprocess.Popen) -> None:
    # SIGINT, como Ctrl+C: el finally de assessment.ui detiene el sandbox que haya lanzado.
    if proceso.poll() is None:
        proceso.send_signal(signal.SIGINT)
    try:
        proceso.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=5)


def resumen_reinicio(r: dict) -> str:
    boards = r.get("boards") or {}
    if boards.get("disponible"):
        metodos = (boards.get("metodo_por_tarea") or {}).values()
        papelera = sum(m == "papelera" for m in metodos)
        tablero = f"Boards: {len(boards.get('tareas_retiradas') or [])} tareas retiradas ({papelera} a la papelera)"
    else:
        tablero = f"Boards: {boards.get('motivo') or 'no disponible'}"
    return " · ".join([
        f"{(r.get('corridas') or {}).get('archivadas', 0)} corridas archivadas",
        f"{len(r.get('codigo_revertido') or [])} archivos revertidos",
        tablero,
    ])


def reiniciar_por_http() -> dict:
    # 600 s: si hay una evaluación en curso, el servidor responde al soltar EVAL_LOCK
    try:
        return _consola("POST", "/api/demo/reiniciar", REINICIO_COMPLETO, timeout=600).get("reinicio") or {}
    except (RuntimeError, OSError) as exc:
        raise Abortar(f"el reinicio de la demo falló ({exc}).") from None


def reiniciar_en_proceso() -> dict:
    from assessment.demo_reset import execute_demo_reset
    return execute_demo_reset(REPO, RUNS, reset_runs=True, reset_sandbox=True, reset_boards=True,
                              reset_code=True, reset_github_prs=True)


# ---------- Revisión previa ----------

def ping_foundry() -> str:
    endpoint, modelo, clave = (_ajuste(k) for k in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_CHAT_COMPLETION_MODEL", "AZURE_OPENAI_API_KEY"))
    sugerencia = "Lanza la demo con --motor solo-evidencia."
    if not (endpoint and modelo and clave):
        raise Abortar(f"faltan AZURE_OPENAI_* en assessment/.env. {sugerencia}")
    pedido = urllib.request.Request(
        f"{endpoint.rstrip('/')}/openai/deployments/{modelo}/chat/completions?api-version=2024-10-21",
        data=json.dumps({"messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}).encode("utf-8"),
        method="POST",
        headers={"api-key": clave, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=30):
            return modelo
    except urllib.error.HTTPError as exc:
        raise Abortar(f"Foundry respondió HTTP {exc.code}. {sugerencia}") from None
    except OSError as exc:
        raise Abortar(f"Foundry no responde ({type(exc).__name__}). {sugerencia}") from None


def revision_previa(motor: str) -> None:
    sucias = rutas_sucias(REPO)
    if sucias:
        raise Abortar("el reinicio no dejó limpias las rutas de la demo:\n" + "\n".join(f"      {l}" for l in sucias))
    _ok("Git limpio en " + " ".join(RUTAS_DEMO))
    if not puerto_libre(PUERTO_SANDBOX):
        raise Abortar(f"algo sigue escuchando en :{PUERTO_SANDBOX} tras el reinicio; ciérralo (lsof -i :{PUERTO_SANDBOX})"
                      " y vuelve a lanzar la demo.")

    from assessment.demo_reset import clean_sandbox_data, wiql_tareas_demo
    for version in ("v1", "v2", "v3"):  # ya compiladas, cada arranque del sandbox tarda segundos
        try:
            hecho = subprocess.run(["dotnet", "build", str(REPO / version / "src" / "Contratos"), "-nologo", "-v", "q"],
                                   capture_output=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Abortar(f"no se pudo compilar {version} ({type(exc).__name__})") from None
        if hecho.returncode:
            raise Abortar(f"{version} no compila; revisa «dotnet build {version}/src/Contratos»")
    _ok(f"v1–v3 compiladas para el sandbox :{PUERTO_SANDBOX}")
    borrados = clean_sandbox_data(REPO)
    _ok("Sandbox sin datos" + (f" (borrados: {', '.join(borrados)})" if borrados else ""))

    from assessment.integrations import (ADO_RESOURCE, ARM_RESOURCE, _ado_headers, _az_token, _http_json,
                                         fetch_azure_runtime, load_settings)
    if not (_az_token(ADO_RESOURCE) and _az_token(ARM_RESOURCE)):
        raise Abortar("la sesión de Azure CLI no está vigente. Ejecuta «az login» y vuelve a lanzar la demo.")
    _ok("Sesión de Azure CLI vigente (Boards, Defender y Resource Graph)")

    if motor == "agente":
        _ok(f"Foundry responde ({ping_foundry()})")

    if trivy_vigente(TRIVY_META, datetime.now(timezone.utc)):
        _ok("Base de Trivy vigente")
    else:
        try:
            subprocess.run(["trivy", "fs", "--download-db-only"], check=True, capture_output=True, timeout=600)
            _ok("Base de Trivy actualizada")
        except (OSError, subprocess.SubprocessError):
            _aviso("No se pudo actualizar la base de Trivy: la Etapa 3 tardará más en cargar")

    cfg = load_settings()
    try:
        url = (fetch_azure_runtime(cfg).get("despliegue") or {}).get("url")
    except Exception:  # solo informa: la demo puede seguir
        url = None
    # Con minReplicas 0, el primer pedido despierta la réplica: medido, 29 s en frío y 0,4 s ya despierta.
    if url and _responde(url + "/api/salud", timeout=45):
        _ok("Ingreso de ACA encendido")
    else:
        _aviso("Ingreso de ACA apagado o sin respuesta: las etapas 5–7 saldrán con evidencia degradada. Para encenderlo:\n"
               f"      az containerapp ingress enable -n {cfg['AZURE_CONTAINER_APP']} -g {cfg['AZURE_RESOURCE_GROUP']}"
               " --type external --target-port 8080 --transport auto")

    try:
        org, proyecto = cfg["AZURE_DEVOPS_ORG_URL"].rstrip("/"), cfg["AZURE_DEVOPS_PROJECT"]
        hallado = _http_json("POST", f"{org}/{urllib.parse.quote(proyecto)}/_apis/wit/wiql?api-version=7.1",
                             _ado_headers(cfg), wiql_tareas_demo(proyecto))
        abiertas = [f"AB#{w['id']}" for w in hallado.get("workItems") or []]
        if abiertas:
            _aviso("Siguen abiertas tareas de demo en Boards: " + ", ".join(abiertas))
        else:
            _ok("Sin tareas de demo abiertas en Boards")
    except Exception as exc:  # solo informa: la demo puede seguir
        _aviso(f"No se pudo consultar Boards ({type(exc).__name__})")

    try:
        _consola("GET", "/api/vulnerabilidades", timeout=600)
        _ok("Escaneo de Trivy en caché para la Etapa 3")
    except (OSError, RuntimeError, ValueError) as exc:
        _aviso(f"No se pudo calentar el escaneo de vulnerabilidades ({exc})")


def preparar_powerbi() -> str:
    """Respalda el dataset y comprueba la sesión del perfil; devuelve el tenant con que se inserta el reporte."""
    try:
        inquilino = powerbi.inquilino(powerbi.token())
        report_id = json.loads(powerbi.ESTADO.read_text(encoding="utf-8"))["report_id"]
        filas = powerbi.respaldar()
    except (RuntimeError, OSError, ValueError, KeyError) as exc:  # HTTPError y URLError son OSError
        raise Abortar(f"no se pudo respaldar el dataset de Power BI ({exc}); sin respaldo la demo no lo sincroniza")
    _ok(f"Dataset de Power BI respaldado ({filas} filas): al restaurar vuelve a quedar como estaba")
    problema = powerbi.problema_sesion(powerbi.url_embebida(report_id, inquilino), CONSOLA)
    if problema:
        raise Abortar(f"{problema}. Inicia sesión una vez con «python -m demo --iniciar-sesion» y vuelve a lanzar la demo.")
    _ok("Sesión de Power BI vigente en el perfil de la demo")
    return inquilino


def preparar_actions() -> dict:
    """Captura la corrida verde más reciente del pipeline en main; sin ella la escena de CI/CD no tiene qué mostrar."""
    try:
        corrida = actions.corrida_verde(actions.repo_origen())
        with sync_playwright() as pw:
            captura = actions.capturar(corrida, REGISTROS, pw)
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError, ErrorPlaywright) as exc:
        raise Abortar(f"no se pudo capturar la corrida de GitHub Actions ({exc})")
    _ok(f"GitHub Actions capturado: corrida verde de main en {corrida['sha'][:7]}, con sus {len(captura['cajas'])} jobs")
    return {"src": f"/__demo/captura/{captura['imagen'].name}", "ancho": captura["ancho"], "alto": captura["alto"],
            "cajas": captura["cajas"], "titulo": f"Corrida verde de main · commit {corrida['sha'][:7]}"}


def preparar_voz(g: dict, sin_voz: bool) -> dict:
    """Tu voz de ElevenLabs si assessment/.env tiene ELEVENLABS_VOICE_ID; si no, la voz neural del guion."""
    voz_propia = _ajuste("ELEVENLABS_VOICE_ID")
    if voz_propia:
        nombre, variable, rotulo = voz.ELEVEN + voz_propia, "ELEVENLABS_API_KEY", "tu voz de ElevenLabs"
    else:
        nombre, variable, rotulo = g["voz"], "AZURE_OPENAI_API_KEY", g["voz"]
    clave = None if sin_voz else (_ajuste(variable) or None)
    if not sin_voz and clave is None:
        raise Abortar(f"falta {variable} en assessment/.env. Usa --sin-voz para presentar solo con subtítulos.")
    textos = guion.lineas(g)
    nuevas = sum(not (CACHE_VOZ / f"{voz.clave_clip(nombre, t)}.mp3").is_file() for t in textos)
    try:
        clips = voz.preparar(textos, nombre, CACHE_VOZ, clave)
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        raise Abortar(f"no se pudo generar la voz: {exc} Usa --sin-voz para presentar solo con subtítulos.") from None
    if sin_voz:
        _ok(f"Sin voz: subtítulos con la duración de {rotulo} ({len(textos) - nuevas}/{len(textos)} clips en caché)")
    else:
        _ok(f"Voz: {rotulo} · {len(textos)} líneas ({nuevas} generadas ahora)")
    return clips


def puede_grabar() -> bool:
    try:
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
        return bool(cg.CGPreflightScreenCaptureAccess()) and shutil.which("screencapture") is not None
    except (OSError, AttributeError):
        return False


# ---------- Grabación (pantalla y audio del sistema) ----------

def grabar(destino: Path) -> subprocess.Popen | None:
    try:
        # Sesión propia: el Ctrl+C de la terminal no le llega; la detiene el runner con un único SIGINT.
        proceso = subprocess.Popen(["screencapture", "-v", "-A", f"-V{TOPE_GRABACION_S}", str(destino)],
                                   stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
    except OSError:
        _aviso("No se pudo iniciar la grabación")
        return None
    time.sleep(1.2)  # tarda en arrancar: así la portada entra completa
    if proceso.poll() is not None:
        _aviso("screencapture terminó sin grabar")
        return None
    return proceso


def detener_grabacion(proceso: subprocess.Popen) -> None:
    if proceso.poll() is None:
        proceso.send_signal(signal.SIGINT)  # como Ctrl+C: cierra el .mov
    try:
        proceso.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proceso.kill()


# ---------- Presentación ----------

def servir_voz(route) -> None:
    nombre = urllib.parse.urlparse(route.request.url).path.rsplit("/", 1)[-1]
    archivo = CACHE_VOZ / nombre
    if re.fullmatch(r"[0-9a-f]{40}\.mp3", nombre) and archivo.is_file():
        route.fulfill(path=archivo)
    else:
        route.fulfill(status=404, body="")


def servir_captura(route) -> None:
    nombre = urllib.parse.urlparse(route.request.url).path.rsplit("/", 1)[-1]
    archivo = REGISTROS / nombre
    if re.fullmatch(r"actions-\d+\.png", nombre) and archivo.is_file():
        route.fulfill(path=archivo)
    else:
        route.fulfill(status=404, body="")


# Unión de las cajas nombradas de la slide, medida cuando la captura ya terminó de entrar.
UNION_CAJAS_JS = """async (nombres) => {
    const raiz = document.querySelector('#demo-director').shadowRoot;
    const lienzo = raiz.querySelector('.s-captura .lienzo');
    if (lienzo) await Promise.all(lienzo.getAnimations().filter((a) => a.effect.getTiming().iterations !== Infinity).map((a) => a.finished));
    const cajas = [...raiz.querySelectorAll('.s-captura .caja')];
    const els = nombres.map((n) => cajas.find((el) => el.dataset.caja === n));
    if (els.some((el) => !el)) return null;
    const r = els.map((el) => el.getBoundingClientRect());
    const x = Math.min(...r.map((b) => b.left)), y = Math.min(...r.map((b) => b.top));
    return {x, y, width: Math.max(...r.map((b) => b.right)) - x, height: Math.max(...r.map((b) => b.bottom)) - y};
}"""


class Corrida:
    """Recorre el guion en la página y lleva el registro de tiempos por escena."""

    def __init__(self, g: dict, clips: dict, sin_voz: bool, ensayo: bool):
        self.escenas = g["escenas"]
        self.planos = [p for e in self.escenas for p in e.get("pasos") or []]
        self.clips = clips
        self.duraciones = {t: c["duracion"] for t, c in clips.items()}
        self.sin_voz = sin_voz
        self.ensayo = ensayo
        self.page = None
        self.terminar = False
        self.filas: list[dict] = []
        self.omitidas: list[str] = []
        self.fallos: list[str] = []
        self.total_s = 0.0
        self.k = -1
        self.donde = ""
        self.ultimo_clic = time.monotonic()
        self.inquilino: str | None = None  # tenant de Entra para insertar el reporte de Power BI
        self.actions: dict = {}  # captura de GitHub Actions de la revisión previa: src, ancho, alto, cajas y titulo
        self.marco = None  # Frame del portal :5080 mientras hay un paso «app» abierto: clic, narrar y esperar van dentro

    def previsto(self) -> dict[str, float]:
        """Total estimado por velocidad: las opcionales suenan mientras el total no pase de LIMITE_S."""
        totales = {}
        for v in (0.75, 1, 1.25):
            con = guion.proyectar(self.planos, self.duraciones, v, "nominal", True)
            sin = guion.proyectar(self.planos, self.duraciones, v, "nominal", False)
            totales[str(v)] = round(min(con, max(sin, guion.LIMITE_S)), 1)
        return totales

    def al_evento(self, _origen, evento) -> None:
        if (evento or {}).get("tipo") == "terminar":
            self.terminar = True

    def js(self, codigo: str, arg=None, en=None):
        resultado = (en or self.page).evaluate(codigo, arg)
        if self.terminar:
            raise Terminar()
        return resultado

    def estado(self) -> dict:
        est = self.js("() => __director.estado()")
        self.total_s = est["transcurrido_s"]
        return est

    def turno(self) -> None:
        est = self.js("async () => { await __director.turno(); return __director.estado(); }")
        self.total_s = est["transcurrido_s"]
        if est.get("terminado"):
            raise Terminar()

    def fallo(self, texto: str) -> None:
        self.fallos.append(f"{self.donde}: {texto}")
        _aviso(f"{self.donde}: {texto}")

    def recorrer(self) -> None:
        for i, escena in enumerate(self.escenas):
            print(f"  ▸ {i + 1}/{len(self.escenas)} {escena['titulo']}", flush=True)
            self.js("(i) => __director.escena(i)", i)
            fila = {"id": escena["id"], "titulo": escena["titulo"], "narracion_s": 0.0, "espera_s": 0.0}
            self.filas.append(fila)
            for j, paso in enumerate(escena.get("pasos") or [], 1):
                self.k += 1
                self.donde = f"{escena['id']} · paso {j}"
                self.turno()
                getattr(self, "_" + paso["tipo"])(paso, fila)
            fila["transcurrido_s"] = self.estado()["transcurrido_s"]

    # --- piezas comunes ---

    def decir(self, textos, fila: dict) -> None:
        for texto in guion.lista(textos):
            clip = self.clips[texto]
            url = None if self.sin_voz or not clip["archivo"] else f"{CONSOLA}/__demo/voz/{clip['archivo'].name}"
            fila["narracion_s"] += self.js(
                "async ([t, u, d]) => { const a = __director.estado().transcurrido_s;"
                " await __director.decir(t, u, d); return __director.estado().transcurrido_s - a; }",
                [texto, url, clip["duracion"]],
            )

    def objetivo(self, selector: str):
        """El primer elemento del selector, ya en pantalla, y su caja; (None, None) si no aparece."""
        loc = (self.marco or self.page).locator(selector).first  # la caja sale en coordenadas de página
        try:
            loc.scroll_into_view_if_needed(timeout=ESPERA_ELEMENTO_MS)
            caja = loc.bounding_box()
        except TiempoAgotado:
            caja = None
        if not caja:
            self.fallo(f"no apareció «{selector}»")
            return None, None
        return loc, caja

    def apuntar(self, caja: dict) -> None:
        self.js("([x, y]) => __director.cursor(x, y)", [caja["x"] + caja["width"] / 2, caja["y"] + caja["height"] / 2])
        self.js("() => __director.clic()")

    def pulsar(self, selector: str, confirmar: bool = False) -> None:
        self.js("() => __director.foco(null)")
        loc, caja = self.objetivo(selector)
        if not loc:
            return
        self.apuntar(caja)
        if self.marco:  # un evento del propio frame: el iframe no toma el foco y el teclado sigue siendo del director
            loc.dispatch_event("click")
        else:
            loc.click(timeout=ESPERA_ELEMENTO_MS)
        self.ultimo_clic = time.monotonic()
        if confirmar:
            self.page.wait_for_timeout(600)
            # La consola arma con data-armed lo que pide una segunda pulsación; si no armó, ya actuó.
            if loc.get_attribute("data-armed") == "true":
                self.js("() => __director.clic()")
                loc.click(timeout=ESPERA_ELEMENTO_MS)
                self.ultimo_clic = time.monotonic()

    def cabe(self, paso: dict) -> bool:
        est = self.estado()
        v = est["velocidad"]
        resto = guion.proyectar(self.planos[self.k + 1:], self.duraciones, v, "nominal", False)
        return guion.sonar_opcional(est["transcurrido_s"], resto, guion.proyectar([paso], self.duraciones, v))

    # --- un ejecutor por tipo de paso ---

    def _slide(self, paso: dict, fila: dict) -> None:
        datos = {c: v for c, v in paso.items() if c not in ("tipo", "plantilla", "voz", "motor", "focos", "informe", "secciones")}
        if paso["plantilla"] == "captura":
            datos = {**self.actions, **datos}
        if paso.get("informe"):
            md = informe_reciente(paso["informe"])
            if md is None:
                self.fallo(f"no hay ningún informe de {paso['informe']} en assessment/runs")
                return
            datos["html"] = documento.a_html(md, paso.get("secciones"))
        self.js("() => __director.foco(null)")
        self.js("([p, d]) => __director.slide(p, d)", [paso["plantilla"], datos])
        focos = paso.get("focos") or []
        for i, texto in enumerate(guion.lista(paso["voz"])):  # cada frase con su foco, si lo tiene
            if i < len(focos):
                self.enfocar_cajas(focos[i])
            self.decir(texto, fila)
        if focos:
            self.js("() => __director.foco(null)")
        if self.k < len(self.planos) - 1:  # la última slide queda en pantalla para las preguntas
            self.js("() => __director.ocultarSlide()")

    def _narrar(self, paso: dict, fila: dict) -> None:
        if paso.get("opcional") and not self.cabe(paso):
            self.omitidas.append(guion.lista(paso["voz"])[0][:60])
            return
        opciones = {"etiqueta": paso.get("etiqueta")}
        if self.marco and paso.get("foco"):  # dentro del portal el foco va por caja: el director no ve el iframe por dentro
            _, caja = self.objetivo(paso["foco"])
            if caja:
                self.js("([c, o]) => __director.foco(c, o)", [caja, opciones])
            self.decir(paso["voz"], fila)
            return
        lupa = False
        if paso.get("foco"):
            try:  # como clic y lupa: la pieza puede aparecer tras una llamada al servidor
                self.page.locator(paso["foco"]).first.wait_for(state="visible", timeout=ESPERA_ELEMENTO_MS)
            except TiempoAgotado:
                pass  # foco() devolverá false y quedará como fallo
        if paso.get("lupa"):
            self.js("() => __director.foco(null)")
            lupa = self.lupa(paso["lupa"], opciones)
        elif not self.js("([s, o]) => __director.foco(s, o)", [paso.get("foco"), opciones]) and paso.get("foco"):
            self.fallo(f"el foco «{paso['foco']}» no encontró nada")
        self.decir(paso["voz"], fila)
        if lupa:
            self.js("() => __director.lupa(null)")

    def enfocar_cajas(self, nombres) -> None:
        """Enfoca la unión de las cajas nombradas de la slide (jobs de la captura); sin nombres apaga el foco."""
        nombres = guion.lista(nombres)
        caja = self.js(UNION_CAJAS_JS, nombres) if nombres else None
        if caja or not nombres:
            self.js("(c) => __director.foco(c)", caja)
        else:
            self.fallo("la slide no tiene la caja «" + "», «".join(nombres) + "»")

    def lupa(self, selector: str, opciones: dict) -> bool:
        loc, caja = self.objetivo(selector)
        if not loc:
            return False
        try:
            png = loc.screenshot(style=OCULTAR_DIRECTOR, timeout=ESPERA_ELEMENTO_MS)
        except TiempoAgotado:
            self.fallo(f"no se pudo capturar «{selector}» para la lupa")
            return False
        url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        return bool(self.js("([u, r, o]) => __director.lupa(u, r, o)", [url, caja, opciones]))

    def _clic(self, paso: dict, fila: dict) -> None:
        if paso.get("voz"):
            self.decir(paso["voz"], fila)
        self.pulsar(paso["selector"], bool(paso.get("confirmar")))

    def _elegir(self, paso: dict, fila: dict) -> None:
        self.js("() => __director.foco(null)")
        loc, caja = self.objetivo(paso["selector"])
        if loc:
            self.apuntar(caja)
            loc.select_option(str(paso["valor"]), timeout=ESPERA_ELEMENTO_MS)

    def _escribir(self, paso: dict, fila: dict) -> None:
        self.js("() => __director.foco(null)")
        loc, caja = self.objetivo(paso["selector"])
        if not loc:
            return
        self.apuntar(caja)
        loc.click(timeout=ESPERA_ELEMENTO_MS)
        loc.fill("")
        loc.press_sequentially(str(paso["texto"]), delay=guion.TECLEO_S * 1000 / self.estado()["velocidad"])

    def _esperar(self, paso: dict, fila: dict, listo=None,
                 aviso: str = "La consola sigue trabajando · Espacio para continuar") -> None:
        inicio = self.estado()["transcurrido_s"]
        if listo is None:
            condicion = f"() => {{ try {{ return Boolean({paso['condicion']}); }} catch (e) {{ return false; }} }}"
            listo = lambda: self.js(condicion, en=self.marco)
        relleno = guion.lista(paso.get("relleno"))
        reintentos = 0

        def reintentar() -> None:
            nonlocal reintentos
            selector = paso.get("si_error")
            if selector and reintentos < MAX_REINTENTOS and self.page.locator(selector).first.is_visible():
                reintentos += 1
                self.js("() => __director.aviso('Una entrega respondió con error: se reintenta con Solo evidencia')")
                self.pulsar(selector)

        self.js("(t) => __director.enVivo(t)", paso.get("en_vivo") or "la consola está trabajando")
        for texto in guion.lista(paso.get("voz_mientras")):
            reintentar()
            self.decir(texto, fila)
        while not listo():
            reintentar()
            if time.monotonic() - self.ultimo_clic >= paso["max_s"]:
                if self.ensayo:
                    self.fallo(f"la condición siguió pendiente {paso['max_s']} s")
                    break
                # Nunca se cancela una evaluación: la demo se pausa y el presentador decide cuándo seguir.
                self.js("(a) => { __director.pausar(); __director.aviso(a); }", aviso)
                self.turno()
                break
            if relleno:
                self.decir(relleno.pop(0), fila)
            else:
                self.js("() => __director.esperar(500)")
        self.js("() => __director.enVivo(null)")
        fila["espera_s"] += self.estado()["transcurrido_s"] - inicio

    def _app(self, paso: dict, fila: dict) -> None:
        """El portal del sandbox dentro de la demo; los pasos hasta {cerrar: true} actúan dentro de él."""
        self.js("() => __director.foco(null)")
        if paso.get("cerrar"):
            self.marco = None
            self.js("() => __director.ocultarSlide()")
            return
        if paso.get("limpiar"):  # el portal lee datos.json en cada petición: la bandeja empieza vacía
            from assessment.demo_reset import clean_sandbox_data
            clean_sandbox_data(REPO)
        self.js("([u, t]) => __director.slide('app', {url: u, titulo: t})", [PORTAL + "/", paso["titulo"]])
        self.marco = self.page.locator("#demo-director .marco-app").element_handle(timeout=ESPERA_ELEMENTO_MS).content_frame()
        try:
            self.marco.wait_for_url(lambda url: url.startswith(PORTAL), timeout=ESPERA_ELEMENTO_MS)
        except TiempoAgotado:
            self.fallo(f"el portal {PORTAL} no cargó")

    def url_reporte(self) -> str:
        return powerbi.url_embebida(json.loads(powerbi.ESTADO.read_text(encoding="utf-8"))["report_id"], self.inquilino)

    def _reporte(self, paso: dict, fila: dict) -> None:
        """Power BI dentro de la demo: la slide inserta el reporte que la consola acaba de sincronizar."""
        url = self.url_reporte()
        self.js("() => __director.foco(null)")
        self.js("([u, t]) => __director.slide('reporte', {url: u, titulo: t})", [url, paso.get("titulo") or "Reporte de Power BI"])
        self.ultimo_clic = time.monotonic()  # max_s cuenta desde que se pide el reporte
        visual = self.page.frame_locator("#demo-director .marco-reporte").locator(powerbi.VISUAL).first

        def dibujado() -> bool:
            try:
                return visual.is_visible()
            except ErrorPlaywright:  # el iframe todavía navega
                return False

        self._esperar({**paso, "en_vivo": paso.get("en_vivo") or "Power BI dibuja el reporte"}, fila, listo=dibujado,
                      aviso="Power BI no termina de dibujar el reporte · Espacio para continuar")
        self.decir(paso["voz"], fila)
        self.js("() => __director.ocultarSlide()")


def presentar(corrida: Corrida, velocidad: float, paso_a_paso: bool, ventana: bool, grabacion: Path | None) -> None:
    css = (DEMO / "director.css").read_text(encoding="utf-8")
    director = (DEMO / "director.js").read_text(encoding="utf-8")
    argumentos = ["--autoplay-policy=no-user-gesture-required", "--window-size=1440,900" if ventana else "--kiosk"]
    grabadora = None
    with sync_playwright() as pw:
        contexto = powerbi.abrir_perfil(pw, argumentos)  # persistente: conserva la sesión de Power BI
        try:
            contexto.route("**/__demo/voz/*", servir_voz)
            contexto.route("**/__demo/captura/*", servir_captura)
            contexto.add_init_script(ATAJOS_APAGADOS)
            contexto.add_init_script(SIN_VENTANAS)
            contexto.add_init_script(f"window.__DIRECTOR_CSS = {json.dumps(css)};")
            contexto.add_init_script(director)
            contexto.expose_binding("__demoEvento", corrida.al_evento)
            corrida.page = contexto.pages[0] if contexto.pages else contexto.new_page()
            # La sesión de Power BI vale por pestaña: el reporte se abre aquí antes que la consola que lo inserta.
            if corrida.inquilino and not powerbi.entrar(corrida.page, corrida.url_reporte()):
                _aviso("Power BI no abrió la sesión en la pestaña de la demo: el reporte pedirá iniciar sesión")
            # Como en un perfil nuevo: la consola arranca sin nada guardado de corridas anteriores.
            cdp = contexto.new_cdp_session(corrida.page)
            cdp.send("Storage.clearDataForOrigin", {"origin": CONSOLA, "storageTypes": "all"})
            cdp.detach()
            corrida.page.goto(CONSOLA + "/", wait_until="load")
            try:
                corrida.page.wait_for_load_state("networkidle", timeout=15_000)
            except TiempoAgotado:
                pass  # la consola sigue consultando: basta con la carga
            if grabacion:
                grabadora = grabar(grabacion)
            corrida.js("(o) => __director.iniciar(o)", {
                "escenas": [{"id": e["id"], "titulo": e["titulo"],
                             "dur_s": round(guion.proyectar(e.get("pasos") or [], corrida.duraciones, 1), 1)}
                            for e in corrida.escenas],
                "velocidad": velocidad,
                "pasoAPaso": paso_a_paso,
                "total_s": corrida.previsto(),
            })
            corrida.recorrer()
            if not corrida.ensayo:
                corrida.js("() => __director.aviso('Demo terminada · Q para salir')")
                while not corrida.terminar:
                    corrida.page.wait_for_timeout(500)
        finally:
            if grabadora:
                detener_grabacion(grabadora)
            try:
                contexto.close()
            except ErrorPlaywright:
                pass


# ---------- Limpieza y registro ----------

def limpiar(consola: subprocess.Popen | None, tocado: bool) -> None:
    if tocado:
        print("\nRestaurando el entorno…", flush=True)
        try:  # primero el sandbox, mientras vive la consola que lo lanzó
            _consola("POST", "/api/sandbox", {"accion": "detener"})
        except (OSError, RuntimeError, ValueError) as exc:
            _aviso(f"No se pudo detener el sandbox :{PUERTO_SANDBOX} ({exc})")
        try:
            from assessment.demo_reset import clean_sandbox_data
            clean_sandbox_data(REPO)
        except OSError as exc:
            _aviso(f"No se pudieron borrar los datos del sandbox ({exc})")
    if consola is not None:
        detener_consola(consola)
    if not tocado:
        return
    try:
        resumen = reiniciar_en_proceso() if consola is not None else reiniciar_por_http()
        _ok("Reinicio · " + resumen_reinicio(resumen))
        reiniciado = True
    except Exception as exc:  # se informa y se sigue: la próxima corrida empieza reiniciando
        _aviso(f"El reinicio falló ({exc}). Vuelve a lanzar la demo: su reinicio previo lo completa.")
        reiniciado = False
    try:
        repuestas = powerbi.reponer()
        if repuestas is not None:
            _ok(f"Power BI repuesto: el dataset vuelve a sus {repuestas} filas")
    except Exception as exc:  # el respaldo queda en disco y la próxima corrida lo repone
        _aviso(f"No se pudo reponer Power BI ({exc}). El respaldo sigue en "
               f"{powerbi.RESPALDO.relative_to(REPO)}: la próxima demo lo repone al terminar.")
        reiniciado = False
    sucias = rutas_sucias(REPO)
    if sucias:
        _aviso("Quedan cambios en las rutas de la demo:\n" + "\n".join(f"      {l}" for l in sucias))
    if not puerto_libre(PUERTO_SANDBOX):
        _aviso(f"Algo sigue escuchando en :{PUERTO_SANDBOX}; ciérralo antes de la próxima demo (lsof -i :{PUERTO_SANDBOX}).")
    elif reiniciado and not sucias:
        print("Demo lista para volver a ejecutarse.", flush=True)


def escribir_registro(corrida: Corrida, args, sello: str, grabacion: Path | None) -> Path:
    REGISTROS.mkdir(exist_ok=True)
    redondear = lambda fila: {c: round(v, 1) if isinstance(v, float) else v for c, v in fila.items()}
    datos = {
        "fecha": sello,
        "velocidad": VELOCIDAD_ENSAYO if args.ensayo else args.velocidad,
        "motor": args.motor,
        "ensayo": args.ensayo,
        "sin_voz": args.sin_voz or args.ensayo,
        "grabacion": str(grabacion) if grabacion and grabacion.is_file() else None,
        "escenas": [redondear({"transcurrido_s": corrida.total_s, **fila}) for fila in corrida.filas],
        "total_s": round(corrida.total_s, 1),
        "previsto_s": corrida.previsto(),
        "opcionales_omitidas": corrida.omitidas,
        "fallos": corrida.fallos,
    }
    ruta = REGISTROS / f"{sello}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m demo", description="Demo narrada de la consola NextGen DevSecOps (REN-001).")
    p.add_argument("--velocidad", type=float, choices=(0.75, 1.0, 1.25), default=1.0, help="velocidad inicial; en vivo, < y >")
    p.add_argument("--paso-a-paso", action="store_true", help="espera «Siguiente» (→ o N) en cada escena")
    p.add_argument("--motor", choices=guion.MOTORES, default="agente", help="motor de la evaluación")
    p.add_argument("--sin-voz", action="store_true", help="solo subtítulos, sin audio")
    p.add_argument("--sin-grabar", action="store_true", help="no grabar pantalla y audio en ~/Movies")
    p.add_argument("--ensayo", action="store_true",
                   help="recorrido rápido (×6, solo evidencia, sin audio ni grabación); genera los clips que falten salvo con --sin-voz")
    p.add_argument("--ventana", action="store_true", help="ventana de 1440×900 en vez de pantalla completa")
    p.add_argument("--guion", type=Path, default=DEMO / "guion.yaml")
    p.add_argument("--iniciar-sesion", action="store_true",
                   help="abre el reporte de Power BI en el perfil de la demo para iniciar sesión una vez (con MFA), lo comprueba y sale")
    return p.parse_args(argv)


def _como_ctrl_c(_signum, _frame):
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    if args.iniciar_sesion:
        try:
            problema = powerbi.iniciar_sesion(CONSOLA)
        except (RuntimeError, OSError, KeyError, ValueError) as exc:
            problema = f"no se pudo abrir el reporte insertado ({type(exc).__name__}: {exc})"
        print(f"✗ {problema}" if problema else "✓ El reporte insertado se dibuja con la sesión del perfil: la demo ya puede mostrarlo.")
        return 1 if problema else 0
    if args.ensayo:
        args.motor, args.sin_grabar = "solo-evidencia", True  # la voz se genera (salvo --sin-voz) pero no suena
    g = guion.cargar(args.guion)
    errores = guion.validar(g)
    if errores:
        print("El guion tiene errores:\n" + "\n".join(f"  - {e}" for e in errores))
        return 2
    g = guion.filtrar(g, args.motor)
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    grabacion = None
    signal.signal(signal.SIGTERM, _como_ctrl_c)
    consola, tocado, corrida, codigo = None, False, None, 1
    print("Demo REN-001 · revisión previa", flush=True)
    try:
        consola = asegurar_consola()
        _ok("Consola lanzada por la demo en :8050" if consola else "Consola ya en marcha en :8050")
        tocado = True
        _ok("Reinicio previo · " + resumen_reinicio(reiniciar_por_http()))
        revision_previa(args.motor)
        inquilino = preparar_powerbi()
        captura_actions = preparar_actions()
        clips = preparar_voz(g, args.sin_voz)
        if not args.sin_grabar:
            if puede_grabar():
                grabacion = GRABACIONES / f"demo-ren-001-{sello}.mov"
                _ok(f"Grabará pantalla y audio en {grabacion} (activa «No molestar» para que no salgan notificaciones)")
            else:
                _aviso("Sin permiso de Grabación de pantalla para esta terminal: la demo no se grabará "
                       "(Ajustes del Sistema → Privacidad y seguridad → Grabación de pantalla y audio del sistema)")
        corrida = Corrida(g, clips, args.sin_voz or args.ensayo, args.ensayo)
        corrida.inquilino, corrida.actions = inquilino, captura_actions
        print("Presentando · Espacio pausa · → siguiente · < > velocidad · P paso a paso · Q Q terminar", flush=True)
        presentar(corrida, VELOCIDAD_ENSAYO if args.ensayo else args.velocidad, args.paso_a_paso, args.ventana, grabacion)
        if args.ensayo:
            print(f"Ensayo terminado: {len(corrida.fallos)} fallos de selectores o esperas.", flush=True)
        codigo = 1 if corrida.fallos and args.ensayo else 0
    except Abortar as exc:
        print(f"\nRevisión previa detenida: {exc}", flush=True)
    except Terminar:
        codigo = 0
    except KeyboardInterrupt:
        print("\nInterrumpida con Ctrl+C.", flush=True)
        codigo = 130
    except ErrorPlaywright as exc:
        if "closed" not in str(exc):
            raise
        print("\nLa ventana de la demo se cerró.", flush=True)
        codigo = 0
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # un segundo Ctrl+C no corta la restauración
        limpiar(consola, tocado)
        if corrida and corrida.filas:
            print(f"Registro de tiempos: {escribir_registro(corrida, args, sello, grabacion).relative_to(REPO)}", flush=True)
        if grabacion and grabacion.is_file():
            print(f"Grabación: {grabacion}", flush=True)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
