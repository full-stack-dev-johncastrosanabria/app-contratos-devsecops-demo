# Demo con historia — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la demo cuente la historia de REN-001 sobre una consola presentada como evaluador de casos: el bug de v2 y su arreglo se ven con datos, el CI/CD real se ve en GitHub Actions y todo lo que se muestra tiene formato.

**Architecture:**
- **Consola.** Los cambios van en `feat/consola-casos` (desde `main`), en un worktree aparte. Se integran en `feat/demo-automatizada` solo si la crítica saca ≥ 34/40.
- **Director.** Gana tres plantillas de slide (app, captura y documento) y un foco por caja que se dibuja sobre la slide.
- **Runner.** Gana un paso «app» que actúa dentro del iframe del portal, la captura de Actions en la revisión previa y un conversor de Markdown.
- **Guion.** Se reescribe con la historia de la adenda.

**Tech Stack:** Python 3 (unittest), Playwright 1.65 sync sobre Chrome, JS/CSS sin dependencias, PyYAML, ASP.NET minimal API (sandbox :5080) y la REST de GitHub sin token (repo público).

**Spec:** `docs/superpowers/specs/2026-11-27-demo-historia-design.md`, adenda de `docs/superpowers/specs/2026-11-27-demo-automatizada-design.md`.

## Global Constraints

**Secretos**
- No imprimir la clave de Azure ni valores de `.env`.
- No leer ni imprimir la clave de ElevenLabs.
- No imprimir tokens de Power BI ni de Azure.

**Efectos externos**
- Sin PR reales en GitHub.
- En Boards: DELETE sin destroy, con Removed como respaldo.
- Sin merge a `main` ni push sin preguntar.
- No matar procesos del usuario. Tras cambiar `assessment/`, pedir que reinicie :8050 desde Antigravity.

**Narración y contenido**
- Mantener visible «Escenario:», separado del dictamen.
- Sin métricas, clientes ni casos inventados.
- Sin texto libre de agentes en la narración.
- Hablar a la audiencia de «ustedes».
- No narrar que el job de v2 «debería salir en rojo»: los jobs xUnit validan la evidencia esperada (`assessment/ci.py`).
- Toda afirmación sobre CI/CD se comprueba contra la corrida real.

**Ensayos y voz**
- Cada ensayo se hace con `--sin-voz` hasta que el usuario cierre el texto.
- Antes de generar voz, revisar la cuota de ElevenLabs (13.548 caracteres).

**Presupuesto**
- A 0,75× sin opcionales, ≤ 720 s.
- A 1,25× con opcionales, ≥ 480 s.
- Voz total ≤ 11.500 caracteres.

**Commits y consola**
- Los commits terminan con `Claude-Session: https://claude.ai/code/session_01CcXd1F6gcMcYSrzRbgrBQo`.
- En la consola solo se integra a la rama de la demo lo que saque ≥ 34/40 en la crítica de impeccable. Los commits en `feat/consola-casos` están permitidos: si la nota no llega, la rama se descarta.

## Review Focus

1. **:5080 ocupado o un `dotnet run` que no arranca.** La revisión previa lo detecta antes de empezar. En plena demo, la espera del sandbox muestra el aviso y se continúa con Espacio. Prueba: `test_revision_previa_detecta_puerto_5080_ocupado` (tarea 6).
2. **GitHub cambia la página de la corrida, o sale un banner que tapa los jobs.** La captura comprueba que encontró todos los jobs esperados y, si falta alguno, aborta con un mensaje. Prueba: `test_captura_aborta_si_falta_un_job` (tarea 6).
3. **Ctrl+C con el portal en pantalla o tras el parche de v2.** Al restaurar se detiene el sandbox, se borran los `datos.json` y se restaura el código. Prueba: `test_limpiar_detiene_el_sandbox_y_borra_sus_datos` (tarea 7).
4. **Teclado después de actuar dentro del portal.** Espacio, flechas y Q siguen controlando la demo, porque el iframe nunca recibe el foco. Prueba: `test_app_actua_dentro_del_portal_sin_robar_el_teclado` (tarea 7).
5. **v2 se relanza en el sandbox mientras se reevalúa.** El evaluador compila con `--artifacts-path`, así que no comparte `bin/obj` con el sandbox. Se verifica en el ensayo de la tarea 8; si hay bloqueos, el relanzamiento pasa a después de la reevaluación.

---

### Task 1: Caso elegible en la consola

Trabajo en el worktree `../AppContratos-consola`, rama `feat/consola-casos` desde `main`. Los tests se corren con el venv del repo principal.

**Files:**
- Modify: `assessment/static/index.html` (cabecera, líneas ~121-131), `assessment/static/app.js`, `assessment/static/style.css`
- Test: `assessment/tests/test_ui.py`

**Interfaces:**
- Produces:
  - `CASOS` en `app.js`: `[{id: "contratos-ren-001", nombre: "Portal de Contratos", regla: "REN-001", enunciado: "Un contrato cancelado nunca debe recibir un aviso de renovación.", entregas: ["v1", "v2", "v3"]}]`.
  - Botón `#case-btn` con `aria-expanded` y `aria-controls="case-list"`, que muestra «Portal de Contratos · REN-001».
  - Lista `#case-list` (`role="listbox"`) con un `role="option"` por caso.
  - Al elegir, `.deck-rule` muestra la regla y el enunciado del caso.
  - Escape cierra la lista y devuelve el foco al botón.
  - Título y `<h1>`: «Evaluador de entregas».

- [ ] **Step 1: Actualizar la aserción vieja y escribir la prueba nueva**

En `test_local_web_contract`, `b'Evaluador de renovaciones'` pasa a `b'Evaluador de entregas'`.

Prueba nueva: la consola se sirve con `DemoHandler` en un puerto libre y se abre en Chrome headless. `page.route("**/api/**")` responde `{}`, así la prueba no toca ninguna integración real. Ya pasó una vez que una suite pisó el dataset de Power BI.

```python
def test_consola_elige_el_caso(self):
    # título y h1 genéricos
    self.assertIn("Evaluador de entregas", page.title()); self.assertEqual(page.inner_text("h1#title"), "Evaluador de entregas")
    self.assertNotIn("renovaciones", page.title() + page.inner_text("h1#title"))
    btn = page.locator("#case-btn"); self.assertIn("Portal de Contratos · REN-001", btn.inner_text())
    btn.click(); self.assertEqual(btn.get_attribute("aria-expanded"), "true")
    self.assertEqual(page.locator("#case-list [role=option]").count(), 1)
    page.locator("#case-list [role=option]").first.click()
    self.assertEqual(btn.get_attribute("aria-expanded"), "false")
    self.assertIn("Un contrato cancelado nunca debe recibir un aviso de renovación.", page.inner_text(".deck-rule"))
    btn.click(); page.keyboard.press("Escape")
    self.assertEqual(btn.get_attribute("aria-expanded"), "false"); self.assertEqual(page.evaluate("document.activeElement.id"), "case-btn")
```

- [ ] **Step 2: Ejecutarla.** Run: `assessment/.venv/bin/python -m unittest assessment.tests.test_ui -v`. Expected: FAIL (no existe `#case-btn`).
- [ ] **Step 3: Implementar el selector.** Seguir el craft floor de impeccable; el componente es una divulgación con listbox, como los demás controles de la consola. Cambiar «QA de renovaciones» por «QA funcional» en `assessment/workflow.py:229`.
- [ ] **Step 4: Ejecutar la suite completa.** Run: `assessment/.venv/bin/python -m unittest assessment.tests.test_assessment assessment.tests.test_ui`. Expected: OK.
- [ ] **Step 5: Commit en `feat/consola-casos`**: `feat(consola): evaluador de entregas con selector de caso`.

### Task 2: La evidencia de CI toma la corrida del pipeline

**Files:**
- Modify: `assessment/integrations.py:284-297`
- Test: `assessment/tests/test_assessment.py`

**Interfaces:**
- Produces: `WORKFLOW_CI = "devsecops.yml"` en `integrations.py`. `pipeline_ci` sale de `GET {base}/actions/workflows/devsecops.yml/runs?head_sha={sha}&per_page=1`; si no hay, de `...?branch=main&per_page=1`. Las claves de `pipeline_ci` no cambian.

- [ ] **Step 1: Prueba**

```python
def test_ci_toma_la_corrida_del_pipeline_y_no_la_de_dependabot(self):
    # _http_json simulado por URL: ?head_sha= devuelve {"workflow_runs": []}; ?branch=main devuelve run 7 (devsecops, success)
    ctx = fetch_github_context({"GITHUB_REPO": "o/r"}, "abc123")
    self.assertEqual(ctx["pipeline_ci"]["run_id"], 7)
    self.assertTrue(any("/actions/workflows/devsecops.yml/runs?head_sha=abc123" in u for u in pedidas))
    self.assertFalse(any(u.endswith("/actions/runs?per_page=10") for u in pedidas))
```

- [ ] **Step 2: Ejecutarla.** Run: `assessment/.venv/bin/python -m unittest assessment.tests.test_assessment -k pipeline`. Expected: FAIL (pide `/actions/runs?per_page=10`).
- [ ] **Step 3: Implementar la selección** en `fetch_github_context`.
- [ ] **Step 4: Ejecutar la suite completa de `assessment`.** Expected: OK.
- [ ] **Step 5: Commit en `feat/consola-casos`**: `fix(consola): la evidencia de CI toma la corrida del pipeline`.

### Task 3: Crítica de la consola e integración

- [ ] **Step 1: Levantar la consola del worktree en :8051.** Run: `assessment/.venv/bin/python -m assessment.ui --puerto 8051` desde el worktree, sin tocar :8050.
- [ ] **Step 2: Correr la crítica de impeccable** con la rúbrica /40 de R6–R8, sobre la consola en :8051. La nota se anota en el ledger.
- [ ] **Step 3a: Si saca ≥ 34/40:**
  - Detener la consola de :8051.
  - Hacer merge local de `feat/consola-casos` en `feat/demo-automatizada` y resolver conflictos (la etiqueta `#reset-boards-chk`).
  - Correr la suite completa: `assessment/.venv/bin/python -m unittest assessment.tests.test_assessment assessment.tests.test_ui assessment.tests.test_demo assessment.tests.test_demo_director`.
  - Actualizar la memoria `console-best-score-branch` con la nota nueva.
  - Pedirle al usuario que reinicie :8050.
- [ ] **Step 3b: Si saca < 34/40:**
  - Descartar la rama.
  - Anotar en el ledger un Ruling.
  - La tarea 8 usa la consola actual y una slide `caso` como «Elige el caso».
- [ ] **Step 4: Borrar el worktree.**

### Task 4: Plantillas «app», «captura» y «documento», y foco por caja

**Files:**
- Modify: `demo/director.js` (PLANTILLAS, `enfocar`), `demo/director.css`
- Test: `assessment/tests/test_demo_director.py`

**Interfaces:**
- Produces:
  - `__director.slide('app', {url, titulo})`: el iframe `.marco-app` tiene un marco de navegador con la URL visible, `tabindex=-1` y `pointer-events: none`.
  - `__director.slide('captura', {src, titulo, ancho, alto, cajas: {nombre: [x, y, w, h]}})`: una imagen con capas `.caja[data-caja="nombre"]` posicionadas en % del tamaño natural.
  - `__director.slide('documento', {titulo, html})`: un `article.s-documento` con el HTML ya escapado por la tarea 5.
  - `__director.foco({x, y, width, height}, opciones)`: con una caja en coordenadas de página, el velo se dibuja sobre la slide (z-index > 30 mientras haya una slide visible).
  - En la caja del grafo MAF, «QA de renovaciones» pasa a «QA funcional».

- [ ] **Step 1: Pruebas**, a 1440×900 y 1920×1080:
  - `test_app_ocupa_la_pantalla_sin_tapar_la_barra`: misma forma que la del reporte. El iframe no toma el foco ni recibe punteros, y la URL se ve en el marco.
  - `test_captura_marca_cada_job`: dos cajas; la caja «b» en pantalla está dentro de la imagen y escalada a su tamaño mostrado (±2 px).
  - `test_documento_muestra_el_html_con_formato`: el `<table>` queda dentro del área visible y por encima de la barra.
  - `test_foco_por_caja_sobre_una_slide`: con la slide `captura` abierta, `foco(caja)` deja el velo visible, con z-index mayor que el de la slide y el hueco en la caja (±2 px).
- [ ] **Step 2: Ejecutarlas.** Run: `assessment/.venv/bin/python -m unittest assessment.tests.test_demo_director`. Expected: FAIL (plantillas inexistentes).
- [ ] **Step 3: Implementar** las plantillas y el foco por caja, en la identidad del director.
- [ ] **Step 4: Ejecutar la suite del director.** Expected: OK.
- [ ] **Step 5: Commit**: `feat(demo): slides de app, captura y documento con foco por caja`.

### Task 5: Markdown con formato

**Files:**
- Create: `demo/documento.py`
- Test: `assessment/tests/test_demo.py`

**Interfaces:**
- Produces: `a_html(md: str, secciones: list[str] | None = None) -> str`.
  - Admite títulos `#` a `###`, tablas con barras (cabecera, separador y filas), listas `- `, párrafos, `**negrita**` y `` `código` ``.
  - Escapa el HTML antes de aplicar el formato.
  - Con `secciones`, conserva el `#` inicial y solo las secciones `##` nombradas.

- [ ] **Step 1: Pruebas**
  - `test_tabla_markdown_a_html`: `"| a | b |\n|---|---|\n| 1 | **2** |"` produce `<table><thead><tr><th>a</th><th>b</th></tr></thead><tbody><tr><td>1</td><td><strong>2</strong></td></tr></tbody></table>`.
  - `test_escapa_html`: `"<script>x</script>"` se convierte en `&lt;script&gt;`.
  - `test_secciones_elegidas`: con un informe de tres secciones `##`, `secciones=["Matriz de criterios evaluados"]` conserva el `<h1>` y solo esa sección.
- [ ] **Step 2: Ejecutarlas.** Run: `assessment/.venv/bin/python -m unittest assessment.tests.test_demo`. Expected: FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implementar `a_html`.**
- [ ] **Step 4: Ejecutarlas.** Expected: OK.
- [ ] **Step 5: Commit**: `feat(demo): informe en Markdown con formato`.

### Task 6: Capturas de GitHub Actions y revisión previa

**Files:**
- Create: `demo/actions.py`
- Modify: `demo/__main__.py` (`revision_previa`, `main`, ruta `**/__demo/captura/*`)
- Test: `assessment/tests/test_demo.py` y `assessment/tests/test_demo_director.py`

**Interfaces:**
- Produces:
  - `repo_origen() -> str`: `owner/repo` de `git remote get-url origin`.
  - `corrida_verde(repo: str) -> dict`: `{id, url, sha, fecha}` de `GET /repos/{repo}/actions/workflows/devsecops.yml/runs?branch=main&status=success&per_page=1`. Lanza RuntimeError si no hay ninguna.
  - `JOBS = ("Evidencia xUnit (v1)", "Evidencia xUnit (v2)", "Evidencia xUnit (v3)", "Seguridad en origen (CodeQL)", "Escaneo IaC, contenedor y SCA (Trivy)", "Construir imagen OCI (GHCR)")`.
  - `capturar(corrida: dict, destino: Path, pw) -> dict`: `{imagen, ancho, alto, cajas: {job: [x, y, w, h]}}` a 1600×1000 con device scale 2. Lanza RuntimeError si falta un job de `JOBS`. El selector de los jobs se fija tras sondear la página real.
  - `preparar_actions() -> dict`, que llama `main` tras `preparar_powerbi`. Se guarda en `Corrida.actions`.
  - `puerto_libre(puerto: int) -> bool`. La revisión previa aborta si :5080 está ocupado, compila v1–v3 con `dotnet build` y borra los `datos.json` con `assessment.demo_reset.clean_sandbox_data`.

- [ ] **Step 1: Pruebas**
  - `test_corrida_verde_elige_la_de_main` con `urlopen` simulado; si no hay corridas, `RuntimeError`.
  - `test_captura_aborta_si_falta_un_job`: página falsa servida por `route` a la que le falta Trivy.
  - `test_captura_devuelve_una_caja_por_job`: página falsa completa.
  - `test_revision_previa_detecta_puerto_5080_ocupado`: socket abierto en :5080 o puerto simulado.
- [ ] **Step 2: Ejecutarlas.** Expected: FAIL (módulo inexistente).
- [ ] **Step 3: Sondear la página real** de la corrida 46092876122 en headless. El sondeo fija el selector de jobs y también los nombres de `JOBS`: CodeQL es una matriz con dos jobs, «(csharp, autobuild)» y «(python, none)». Implementar `demo/actions.py` y conectarlo en la revisión previa. Si falla `corrida_verde` o `capturar`, la revisión previa lanza `Abortar` con el motivo.
- [ ] **Step 4: Ejecutar las suites de la demo.** Expected: OK.
- [ ] **Step 5: Commit**: `feat(demo): capturas reales de GitHub Actions en la revisión previa`.

### Task 7: El paso «app» en el runner

**Files:**
- Modify: `demo/guion.py` (TIPOS, OVERHEAD, `validar`), `demo/__main__.py` (`Corrida._app`; `objetivo`, `pulsar`, `_narrar` y `_esperar` con `self.marco`; `limpiar`)
- Test: `assessment/tests/test_demo.py` y `assessment/tests/test_demo_director.py`

**Interfaces:**
- Consumes: la plantilla `app` y `foco(caja)` de la tarea 4.
- Produces:
  - Pasos `{tipo: app, titulo, limpiar?: bool}` para abrir y `{tipo: app, cerrar: true}` para cerrar. Entre los dos, `clic`, `narrar` y `esperar` actúan dentro del portal y no se admite otro tipo.
  - `OVERHEAD["app"] = 1.5`.
  - Con `limpiar: true` se borran los `datos.json` antes de cargar el portal.
  - `self.marco` es el Frame cuya URL empieza por `http://127.0.0.1:5080`. Los clics se hacen con `dispatch_event("click")`, el foco va por caja y la condición se evalúa con `frame.evaluate`.
  - `limpiar()` detiene el sandbox con `_consola("POST", "/api/sandbox", {"accion": "detener"})` antes del reinicio.

- [ ] **Step 1: Pruebas**
  - `test_app_sin_cerrar_es_error`.
  - `test_dentro_de_app_solo_clic_narrar_esperar`. El mensaje exacto es «a · paso N: dentro de «app» solo van clic, narrar y esperar.».
  - `test_app_actua_dentro_del_portal_sin_robar_el_teclado`: portal falso en `http://127.0.0.1:5080/**` con `#btn-simular` y `#estado`. Se comprueban `clic`, `esperar` sobre `#estado` y `narrar` con foco; después se pulsa Espacio y `__director.estado().pausado` es `true`, sin fallos.
  - `test_limpiar_detiene_el_sandbox_y_borra_sus_datos`, con `_consola` y `clean_sandbox_data` simulados.
- [ ] **Step 2: Ejecutarlas.** Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Ejecutar la suite completa.** Expected: OK.
- [ ] **Step 5: Commit**: `feat(demo): el portal del sandbox dentro de la demo`.

### Task 8: El guion con la historia

**Files:**
- Modify: `demo/guion.yaml`
- Test: `assessment/tests/test_demo.py` (`GuionReal`)

**Interfaces:**
- Consumes: todas las tareas anteriores.
  - Selectores de la consola: `#case-btn`, `#sandbox-toggle` y `[data-launch="vN"]`.
  - Espera del sandbox: `#sandbox-pill` con `dataset.active === 'true'` y `dataset.version === 'vN'`.
  - El portal escribe «✓ CUMPLIMIENTO REN-001 OBSERVADO…» o «✕ INCUMPLIMIENTO REN-001 OBSERVADO…» en `#estado`.

- [ ] **Step 1: Prueba** `test_guion_real_caracteres`: el total a sintetizar es ≤ 11.500. Junto con `test_guion_real_valido` y `test_guion_real_ventana`, deben fallar contra el guion nuevo hasta cuadrarlo.
- [ ] **Step 2: Reescribir el guion** con las escenas de la adenda:
  - sale `etapas`;
  - `consola` y `caso` se unen en la elección del caso;
  - en `mientras-corre` van el grafo, Actions y la app (v1 y v2);
  - `dictamen` muestra el informe de v2;
  - `gobernanza` y `remediacion` pasan a v2, con relanzamiento y `limpiar`;
  - el `cierre` vuelve al selector.
- [ ] **Step 3: Cuadrar el presupuesto** con `presupuesto.py` y ejecutar `GuionReal`. Expected: OK.
- [ ] **Step 4: Ensayo y pasada visual.**
  - Run: `assessment/.venv/bin/python -m demo --ensayo --sin-voz --ventana`.
  - Expected: 0 fallos; git limpio; nada escuchando en :5080; el dataset de Power BI repuesto a sus 59 filas.
  - Capturar cada superficie que ve el público y corregir cualquier texto crudo.
- [ ] **Step 5: Commit**: `feat(demo): la demo cuenta la historia de REN-001`.
- [ ] **Step 6: Generar `narracion-para-revisar.txt`** con `lectura.py` y entregarlo al usuario para que cierre el texto.

Después siguen, del plan original, la tarea 7 (aceptación a 0,75× y 1,25×, y `GUION_DEMO.md`) y la revisión final de toda la rama.
