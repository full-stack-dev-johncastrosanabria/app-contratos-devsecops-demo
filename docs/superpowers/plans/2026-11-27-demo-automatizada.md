# Demo automatizada con Playwright — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `python -m demo` reproduzca a pantalla completa una demo narrada de 8–12 min de la consola, con slides, foco, pausa y velocidad. La demo debe quedar lista para repetirse sin dejar rastro.

**Architecture:** Un runner en Python con Playwright (`demo/__main__.py`) secuencia los pasos de `demo/guion.yaml`. Un «director» inyectado en la página (`demo/director.js`, Shadow DOM) es dueño del reloj (pausa, velocidad, «Siguiente»), los subtítulos, el foco, la lupa, el cursor, las slides y la barra de control. Python espera las promesas del director.

**Tech Stack:** Python 3.14 (`assessment/.venv`), `playwright==1.65.1` con `channel="chrome"`, PyYAML (ya instalado), Azure Speech REST, JS y CSS sin dependencias, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-27-demo-automatizada-design.md`

## Global Constraints

- Voz `es-MX-DaliaMultilingualNeural`, formato `audio-48khz-96kbitrate-mono-mp3` y endpoint `https://westus3.tts.speech.microsoft.com/cognitiveservices/v1`. La clave es `AZURE_OPENAI_API_KEY` de `assessment/.env` y nunca se imprime.
- Velocidades válidas: 0.75, 1 y 1.25. Ventana: 480–720 s. Una línea opcional se omite si el total proyectado pasa de 690 s.
- Tope de la evaluación: 420 s. Al llegar, el director se pausa solo. Nunca se cancela una evaluación.
- No hay PR reales ni pestañas de terceros. Power BI no se abre.
- En `assessment/static` solo cambia el texto de la etiqueta de `#reset-boards-chk`.
- Chrome se lanza con `--kiosk` y `--autoplay-policy=no-user-gesture-required`, y con `ignore_default_args=["--enable-automation"]`. El contexto usa `no_viewport=True` y `bypass_csp=True`.
- Los atajos de la consola se apagan con `localStorage["nextgen.atajos"] = "off"` mediante un init script. El director no usa R, D, 1–8, V, ? ni Esc.
- Los POST a la consola llevan `Host: 127.0.0.1:8050` y `Origin: http://127.0.0.1:8050`.
- La demo modifica estas rutas: `v1 v2 v3 Dockerfile deploy .github`.
- La narración solo nombra datos deterministas, no inventa métricas ni clientes y trata a la audiencia de «ustedes». La etiqueta «Escenario:» queda visible cuando hay foco en la matriz.

## Review Focus

1. **Repetir tras un corte que dejó aplicado el parche de v3 o una mitigación.** Primero se reinicia y después se verifica que git esté limpio, así la corrida arranca. *Se comprueba en la tarea 7, paso 3.*
2. **El presentador o Playwright teclean en un input con espacios** (la nota de gobernanza). El director no se pausa ni avanza. *Prueba `test_teclas_en_input_no_controlan` en la tarea 4.*
3. **Ctrl+C o ventana cerrada en plena evaluación MAF.** La limpieza corre igual. Si el runner lanzó el servidor, lo termina primero y luego reinicia en el mismo proceso, sin quedar esperando a `EVAL_LOCK`. *Se comprueba en la tarea 7, paso 4.*
4. **Pausa o cambio de velocidad durante una línea.** El reloj descuenta solo el tiempo sin pausa. *Prueba `test_pausa_descuenta` en la tarea 4.*
5. **Pantalla de laptop (1440×900).** Los subtítulos, la barra y las slides no se tapan entre sí. *Prueba `test_layout_sin_solapes` en la tarea 4.*

---

### Task 1: Boards a la papelera en el reinicio

**Files:**
- Modify: `assessment/demo_reset.py` (`reset_boards_demo_state`, bucle de tareas)
- Modify: `assessment/static/index.html:160` (solo el texto de la etiqueta)
- Modify: `GUION_DEMO.md` (§2.6: «pasa las tareas … a Removed» → papelera)
- Test: `assessment/tests/test_assessment.py`

**Interfaces:**
- Produces: `reset_boards_demo_state(settings)` conserva sus claves y suma `metodo_por_tarea: dict[str, str]`, con valor `"papelera"` o `"removed"` para cada `"AB#<id>"`.

- [ ] **Step 1: Escribir las pruebas que fallan.** `test_reset_boards_papelera_y_fallback`. Se simula `assessment.demo_reset._http_json`:
  - WIQL devuelve las tareas 11 y 12.
  - `DELETE …/workitems/11` responde `{}`.
  - `DELETE …/workitems/12` lanza `urllib.error.HTTPError(url, 403, "Forbidden", {}, None)`.
  - El PATCH de AB#1 responde `{}`.
  - Se pasa `settings={"AZURE_DEVOPS_ORG_URL": "https://dev.azure.com/o", "AZURE_DEVOPS_PROJECT": "P", "AZURE_DEVOPS_WORK_ITEM_ID": "1"}` y se parchea `_ado_headers` para que devuelva `{"Authorization": "x"}`.
  - Se espera `res["metodo_por_tarea"] == {"AB#11": "papelera", "AB#12": "removed"}` y `res["tareas_retiradas"] == ["AB#11", "AB#12"]`.
  - No debe haber PATCH a `/workitems/11` y sí uno a `/workitems/12` con `System.State = Removed`.
- [ ] **Step 2: Ejecutar** `assessment/.venv/bin/python -m unittest assessment.tests.test_assessment -k papelera`. Esperado: FAIL (falta `metodo_por_tarea`).
- [ ] **Step 3: Implementar.** Cada tarea intenta `DELETE {org}/{proj}/_apis/wit/workitems/{id}?api-version=7.1`, sin `destroy`. Si la respuesta es `HTTPError` 401 o 403, recurre al PATCH a `Removed` de hoy. Cualquier otro error se propaga.
- [ ] **Step 4: Actualizar los textos.**
  - Etiqueta de `#reset-boards-chk`: «Reiniciar tareas demo en Azure Boards (envía a la papelera las tareas `devsecops-fp-*` y restaura AB#1)».
  - `GUION_DEMO.md` §2.6: decir lo mismo.
- [ ] **Step 5: Ejecutar** `assessment/.venv/bin/python -m unittest assessment.tests.test_assessment assessment.tests.test_ui`. Esperado: OK, con 13 pruebas.
- [ ] **Step 6: Commit** `feat(demo): reinicio envía tareas demo de Boards a la papelera`.

### Task 2: Modelo de guion y tiempo (`demo/guion.py`)

**Files:**
- Create: `demo/__init__.py` (vacío), `demo/guion.py`
- Test: `assessment/tests/test_demo.py`

**Interfaces:**
- Produces:
  - `TIPOS: dict[str, tuple[str, ...]]`, con los campos obligatorios de cada tipo:
    - `slide`: `plantilla`, `voz`
    - `narrar`: `voz`
    - `clic`: `selector`
    - `elegir`: `selector`, `valor`
    - `escribir`: `selector`, `texto`
    - `esperar`: `condicion`, `max_s`, `espera_s`
  - Constantes `VENTANA_S = (480, 720)`, `LIMITE_S = 690` y `CARACTERES_POR_S = 17`.
  - `cargar(ruta: Path) -> dict`: `yaml.safe_load`.
  - `validar(guion: dict) -> list[str]`: lista de errores legibles, vacía si el guion es válido.
  - `voces(paso: dict) -> list[str]`: normaliza `voz` (str o lista) y suma `voz_mientras` y `relleno`.
  - `lineas(guion: dict) -> list[str]`: todas las líneas, sin duplicados y en orden.
  - `duracion_estimada(texto: str) -> float`: `len(texto) / CARACTERES_POR_S`.
  - `proyectar(pasos: list[dict], duraciones: dict[str, float], velocidad: float, esperas: str = "nominal", opcionales: bool = True) -> float`.
  - `sonar_opcional(transcurrido_s: float, restante_s: float, linea_s: float, limite_s: float = LIMITE_S) -> bool`: devuelve `transcurrido_s + restante_s + linea_s <= limite_s`.
- Estructura de `guion.yaml`:
  - `{voz: str, escenas: [{id, titulo, pasos: [ {tipo, …} ]}]}`.
  - `voz` puede ser un str o una lista de str, una línea por clip.
  - `opcional: true` solo se admite en `narrar`.
  - `espera_s` es `[min, max]`.

- [ ] **Step 1: Escribir las pruebas que fallan**, sobre un guion mínimo en un diccionario dentro de la prueba:
  - `test_validar_detecta_errores`: un tipo desconocido, un `elegir` sin `valor` y `opcional` en un `clic` producen 3 errores. El guion mínimo válido da `[]`.
  - `test_proyectar_modelo`. Pasos de ejemplo:
    - un `narrar` de 34 caracteres (2 s);
    - un `esperar` con `espera_s: [10, 20]` y `voz_mientras` de 17 caracteres (1 s);
    - un `narrar` opcional de 17 caracteres.

    Valores esperados:
    - `proyectar(..., 1, "min", False) == 2 + 10 + OVERHEAD["narrar"]` (overhead calculado igual que en el código);
    - `proyectar(..., 0.5, "max", True)` usa `max(20, 1/0.5)` y suma la opcional dividida por 0,5.
  - `test_sonar_opcional`: `sonar_opcional(600, 80, 9) is True` y `sonar_opcional(600, 85, 9) is False`.
- [ ] **Step 2: Ejecutar** `assessment/.venv/bin/python -m unittest assessment.tests.test_demo`. Esperado: FAIL (no existe `demo.guion`).
- [ ] **Step 3: Implementar `demo/guion.py`.**
  - `proyectar` aplica este modelo:
    - en un paso que no es `esperar`, suma `(narración + OVERHEAD[tipo]) / velocidad`;
    - en un `esperar`, suma `max(espera, voz_mientras / velocidad)`, donde la espera es `min`, `max` o el punto medio según `esperas`.
  - `OVERHEAD = {"slide": 1.5, "narrar": 0.6, "clic": 1.2, "elegir": 1.0, "escribir": 0.0, "esperar": 0.0}`.
  - `escribir` suma `0.06 s` por carácter.
- [ ] **Step 4: Ejecutar** el comando del paso 2. Esperado: OK.
- [ ] **Step 5: Commit** `feat(demo): modelo de guion y proyección de tiempo`.

### Task 3: Voz con caché (`demo/voz.py`)

**Files:**
- Create: `demo/voz.py`, `demo/requirements.txt` (`playwright==1.65.1`)
- Modify: `.gitignore` (agregar `demo/.voz/` y `demo/.registro/`)
- Test: `assessment/tests/test_demo.py`

**Interfaces:**
- Consumes: `demo.guion.duracion_estimada`.
- Produces:
  - `VOZ = "es-MX-DaliaMultilingualNeural"`.
  - `clave_clip(voz: str, texto: str) -> str`: sha1 hex de `f"{voz}|{texto}"`.
  - `ssml(texto: str, voz: str) -> str`: texto escapado para XML, con `xml:lang` igual a `voz[:5]`.
  - `duracion_mp3(ruta: Path) -> float`: lee la línea `estimated duration` de `afinfo`.
  - `preparar(lineas: list[str], voz: str, cache: Path, clave: str | None) -> dict[str, dict]`:
    - devuelve `texto → {"archivo": Path | None, "duracion": float}`;
    - genera solo los clips que faltan;
    - con `clave=None` no genera nada y usa la duración estimada;
    - si una síntesis falla, lanza `RuntimeError` con el código HTTP y sin la clave.

- [ ] **Step 1: Escribir las pruebas que fallan.**
  - `test_clave_clip_estable`: misma entrada, misma clave; cambiar el texto cambia la clave.
  - `test_ssml_escapa`: `ssml("A & B <x>", VOZ)` contiene `A &amp; B &lt;x&gt;` y `xml:lang="es-MX"`.
  - `test_preparar_sin_clave`: `preparar(["hola mundo"], VOZ, tmp, None)` da `{"hola mundo": {"archivo": None, "duracion": duracion_estimada("hola mundo")}}`.
  - `test_duracion_mp3`: solo en darwin. Genera con `say -o x.aiff "hola"` y comprueba que `0 < duracion_mp3(x) < 3`.
- [ ] **Step 2: Ejecutar** `assessment/.venv/bin/python -m unittest assessment.tests.test_demo`. Esperado: FAIL.
- [ ] **Step 3: Implementar.** La síntesis hace un POST con `urllib.request`, con los encabezados `Ocp-Apim-Subscription-Key`, `Content-Type: application/ssml+xml`, `X-Microsoft-OutputFormat` y `User-Agent: demo-tts`.
- [ ] **Step 4: Instalar la dependencia** con `assessment/.venv/bin/python -m pip install -r demo/requirements.txt`. Ejecutar las pruebas: OK.
- [ ] **Step 5: Commit** `feat(demo): voz neural con caché por línea`.

### Task 4: Director en la página (`demo/director.js`, `demo/director.css`)

**Files:**
- Create: `demo/director.js`, `demo/director.css`
- Test: `assessment/tests/test_demo_director.py`. Usa Playwright headless con `channel="chrome"` y `page.set_content(...)` más el init script, así que no necesita servidor. Se omite si Playwright o Chrome no están.

**Interfaces:**
- Consumes: `window.__DIRECTOR_CSS` (string), inyectado antes que el JS.
- Produces: `window.__director` con estos métodos.
  - `iniciar({escenas:[{id,titulo}], velocidad, pasoAPaso, total_s})`.
  - `escena(indice)`.
  - `turno() → Promise`: resuelve cuando no hay pausa. En paso a paso, si `escena()` marcó una frontera, también espera «Siguiente».
  - `decir(texto, url|null, duracion_s) → Promise`: resuelve al terminar el audio o el tiempo `duracion_s / velocidad` sin pausas, o al pulsar «Siguiente».
  - `esperar(ms) → Promise`.
  - `foco(selector|null, {etiqueta}) → Promise`.
  - `lupa(dataUrl|null, rect, {etiqueta}) → Promise`.
  - `cursor(x, y) → Promise`.
  - `clic()`.
  - `slide(plantilla, datos) → Promise`.
  - `ocultarSlide() → Promise`.
  - `enVivo(texto|null)`.
  - `aviso(texto)`.
  - `pausar()`.
  - `estado() → {velocidad, pausado, pasoAPaso, transcurrido_s}`.
- Eventos hacia Python: `window.__demoEvento({tipo})`, con `tipo` igual a `"terminar"` o `"estado"`, si la función existe.
- Plantillas de slide, con estos campos de `datos`:
  - `portada{titulo, subtitulo}`
  - `pregunta{pregunta, fuentes[], remate}`
  - `caso{regla, entregas[{version, escenario, tono}]}`
  - `maf{}`
  - `etapas{etapas[8]}`
  - `gobernanza{pasos[]}`
  - `cierre{tesis[3], cta}`
- Teclas, capturadas en fase de captura e ignoradas si el objetivo es editable:
  - Espacio o K: pausa;
  - → o N: siguiente;
  - `<` o `-`: más lento;
  - `>` o `+`: más rápido;
  - P: paso a paso;
  - Q: terminar.

- [ ] **Step 1: Escribir las pruebas que fallan.**
  - `test_pausa_descuenta`: `decir("x", null, 1.0)`, pausar a los 0,3 s, reanudar a los 1,3 s. La promesa resuelve entre 1,9 y 2,3 s después de empezar.
  - `test_velocidad_escala`: a 1.25, `esperar(1000)` resuelve en 0,8 s ± 0,15 s.
  - `test_siguiente_corta`: `decir(..., 5)` más la tecla N resuelve en menos de 0,5 s.
  - `test_teclas_en_input_no_controlan`: con foco en `<input>`, `keyboard.type("a b")` deja `estado().pausado` en `false` y el input con el valor `"a b"`.
  - `test_layout_sin_solapes`: a 1440×900 y a 1920×1080, `iniciar` más `decir("línea larga …")`. Los rectángulos de los subtítulos y de la barra no se intersecan y caben en el viewport.
- [ ] **Step 2: Ejecutar** `assessment/.venv/bin/python -m unittest assessment.tests.test_demo_director`. Esperado: FAIL.
- [ ] **Step 3: Implementar el director.**
  - Shadow root sobre `document.documentElement`, con `pointer-events: none` salvo en la barra y las slides.
  - El reloj usa `performance.now()` y acumula solo el tiempo sin pausa.
  - El audio usa `playbackRate = velocidad`.
  - El spotlight sigue el rectángulo del objetivo con `requestAnimationFrame`.
  - La lupa anima con FLIP.
  - Los estilos viven en `director.css`: paleta navy y cian de la marca, `clamp()` para los tamaños, `prefers-reduced-motion` y contraste AA.
- [ ] **Step 4: Revisar el aspecto visual.** Con un script en el scratchpad, mostrar las 7 slides, el spotlight, la lupa y la barra sobre la consola real (`:8050`) a 1440×900. Guardar las capturas y revisarlas. Corregir hasta que se vean cuidadas y alineadas con la marca.
- [ ] **Step 5: Ejecutar** el comando del paso 2. Esperado: OK.
- [ ] **Step 6: Commit** `feat(demo): director en página con reloj, foco, lupa y slides`.

### Task 5: Runner (`demo/__main__.py`)

**Files:**
- Create: `demo/__main__.py`
- Test: `assessment/tests/test_demo.py`

**Interfaces:**
- Consumes: Tasks 2–4, `assessment.demo_reset.execute_demo_reset`, `assessment.ui.stop_sandbox`, `assessment.ui.ROOT` y `OUTPUT`, `assessment.integrations.load_settings`, `_az_token`, `ADO_RESOURCE` y `fetch_azure_runtime`.
- Produces: la CLI.

  ```
  python -m demo [--velocidad {0.75,1,1.25}] [--paso-a-paso] [--motor {agente,solo-evidencia}]
                 [--sin-voz] [--ensayo] [--ventana] [--guion RUTA]
  ```

  - `rutas_sucias(repo: Path) -> list[str]`: ejecuta `git status --porcelain -- v1 v2 v3 Dockerfile deploy .github`.
  - `trivy_vigente(metadata: Path, ahora: datetime) -> bool`: compara con `NextUpdate`.
  - `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Escribir las pruebas que fallan.**
  - `test_rutas_sucias`: en un repo git temporal con `Dockerfile` commiteado y luego modificado, devuelve `[" M Dockerfile"]` (un archivo fuera de las rutas no cuenta).
  - `test_trivy_vigente`: con un `metadata.json` cuyo `NextUpdate` está en el futuro, `True`; en el pasado, `False`; si el archivo no existe, `False`.
- [ ] **Step 2: Ejecutar** `… -m unittest assessment.tests.test_demo`. Esperado: FAIL.
- [ ] **Step 3: Implementar el runner**, en este orden (spec §6.2):
  1. Servidor: lanzarlo si no responde y dejarlo como propio.
  2. `POST /api/demo/reiniciar` con todo en `true`.
  3. Comprobar `rutas_sucias == []`; si no, abortar con la lista.
  4. Token de `az`.
  5. Ping a Foundry, solo con el motor `agente`. Es un POST a `{endpoint}/openai/deployments/{modelo}/chat/completions?api-version=2024-10-21` con `max_tokens: 1`.
  6. Trivy vigente, o calentarlo.
  7. Ingreso de ACA (`fetch_azure_runtime → despliegue.url` + `/api/salud`): solo avisa.
  8. Ninguna tarea de demo abierta: solo avisa.
  9. `GET /api/vulnerabilidades`.
  10. Voz (`voz.preparar`).
  11. Navegador y contexto (Global Constraints).
  12. Rutas `**/__demo/voz/*`.
  13. Init scripts (atajos apagados, CSS y director), `expose_binding("__demoEvento")`.
  14. `goto(":8050")` e `iniciar`.

  Ejecutores, uno por tipo:
  - **`clic`**: `locator.scroll_into_view_if_needed`, `cursor` al centro, `clic` y `click`. Si `confirmar`, una segunda pulsación tras 600 ms.
  - **`narrar` con `lupa`**: `locator.screenshot()` en base64.
  - **`esperar`**:
    - sondea la `condicion` cada 500 ms mientras reproduce `voz_mientras` y luego `relleno`;
    - si aparece `si_error`, pulsa los botones de reintento;
    - al llegar a `max_s`, `pausar()` y un `aviso`.
  - **Líneas opcionales**: antes de cada una se evalúa `guion.sonar_opcional(transcurrido, proyectar(resto, …, velocidad, "nominal", False), dur)`.
  - **`--ensayo`**: fuerza `solo-evidencia` y `--sin-voz`, y empieza a velocidad 6 (valor interno, fuera del menú).

  Final: `aviso("Demo terminada · Q para salir")` y esperar el evento `terminar` o el cierre.

  `finally`:
  - Si el servidor es propio: terminarlo y llamar a `stop_sandbox()` y a `execute_demo_reset(ROOT, OUTPUT, reset_boards=True, …)` en el mismo proceso.
  - Si no: el POST de reinicio con un timeout de 600 s.
  - Comprobar `rutas_sucias` y escribir `demo/.registro/<stamp>.json` con, por escena, `narracion_s`, `espera_s` y `transcurrido_s`, más `total_s` y los totales proyectados a 0,75, 1 y 1,25.
- [ ] **Step 4: Ejecutar las pruebas.** Esperado: OK.
- [ ] **Step 5: Hacer una prueba de humo** con un guion mínimo de 3 pasos (slide, clic en `#help-toggle-btn`, narrar con foco): `… -m demo --ensayo --ventana --guion /tmp/…/mini.yaml`. Esperado: recorre los 3 pasos, la limpieza imprime «Demo lista para volver a ejecutarse» y git queda limpio.
- [ ] **Step 6: Commit** `feat(demo): runner con revisión previa, ejecución por eventos y limpieza`.

### Task 6: Guion completo y narración (`demo/guion.yaml`)

**Files:**
- Create: `demo/guion.yaml`
- Test: `assessment/tests/test_demo.py`

**Interfaces:**
- Consumes: el esquema de la Task 2, las plantillas de la Task 4 y los selectores de la consola. Los botones creados por `app.js` se ubican por rol y nombre, por ejemplo `role=button[name="Aprobar en Azure Boards"]`.

- [ ] **Step 1: Escribir las pruebas que fallan.**
  - `test_guion_real_valido`: `validar(cargar("demo/guion.yaml")) == []`, con 14 escenas cuyos `id` aparecen en el orden de spec §6.5.
  - `test_guion_real_ventana`, con `duraciones = duracion_estimada`:
    - `proyectar(pasos, d, 1.25, "min", True) >= 480`;
    - `proyectar(pasos, d, 0.75, "max", False) <= 720`.
- [ ] **Step 2: Escribir el guion.**
  - Las 14 escenas de spec §6.5.
  - Narración a partir de los actos de `GUION_DEMO.md`: unos 5.800 caracteres obligatorios y unos 1.200 opcionales, más la escena 6 (80 s obligatorios y relleno).
  - Incluye la línea neutra de diagnóstico operativo y la aclaración de que en la operación real la aprobación la da una persona.
  - La escena 12 cambia `#mode-select` a `solo-evidencia` y cierra con «Cerrar AB#n en Azure Boards».
  - Cada `esperar` lleva su `espera_s`: evaluación `[150, 210]`, reauditoría `[3, 15]`, aprobación `[2, 10]`, reevaluación `[18, 35]` y cierre `[2, 10]`.
- [ ] **Step 3: Ejecutar las pruebas.** Esperado: OK.
- [ ] **Step 4: Ensayar** con `… -m demo --ensayo`. Esperado: llega a la escena 14 sin pasos omitidos, el registro lista todas las escenas y git queda limpio después.
- [ ] **Step 5: Generar la voz** con `… -m demo --ensayo` sin `--sin-voz` (el ensayo genera los clips aunque no los reproduzca). Esperado: hay `demo/.voz/*.mp3` para todas las líneas.
- [ ] **Step 6: Commit** `feat(demo): guion narrado de 14 escenas`.

### Task 7: Aceptación y documentación

**Files:**
- Modify: `GUION_DEMO.md`: sección nueva «Demo automatizada (Playwright)» con el comando, los controles, la revisión previa y la limpieza.

- [ ] **Step 1: Hacer una corrida real a 0,75×** con `… -m demo --velocidad 0.75`. Esperado: `total_s` entre 480 y 720 en `demo/.registro/*.json` y git limpio después.
- [ ] **Step 2: Hacer una corrida real a 1,25×** con `… -m demo --velocidad 1.25`. Mismo criterio.
- [ ] **Step 3: Comprobar Review Focus 1.** En un ensayo, Ctrl+C justo después de la escena 12 (parche aplicado) y volver a ejecutar `--ensayo`. Esperado: arranca, porque el reinicio previo revierte, y termina limpio.
- [ ] **Step 4: Comprobar Review Focus 3.** En un ensayo, cerrar la ventana durante la escena 6. Esperado: la limpieza termina en menos de 60 s y git queda limpio.
- [ ] **Step 5: Documentar** en `GUION_DEMO.md` y ejecutar toda la suite: `… -m unittest assessment.tests.test_assessment assessment.tests.test_ui assessment.tests.test_demo assessment.tests.test_demo_director`. Esperado: OK.
- [ ] **Step 6: Commit** `docs(demo): guía de la demo automatizada`. Después, una revisión fresca de toda la rama.
