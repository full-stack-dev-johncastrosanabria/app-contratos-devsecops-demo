# Demo automatizada con Playwright — Diseño

Fecha: 2026-11-27 · Rama: `feat/demo-automatizada`

## 1. Intención

El usuario presenta la consola **NextGen DevSecOps Assessment** en vivo, compartiendo pantalla, ante VP de Ingeniería, arquitectos cloud, QA leads y CISOs, y la ensaya muchas veces. Quiere una demo que se ejecute sola, con narración consultiva y slides de transición que den contexto. Debe enfocar las etapas y los datos clave, verse muy cuidada y durar de 8 a 12 minutos. El presentador puede pausarla y cambiar la velocidad (0,75×, 1×, 1,25×), y la demo se puede repetir sin dejar rastro.

## 2. Objetivos, no objetivos y anti-objetivos

**Objetivos**
- Un solo comando ejecuta la revisión previa y el reinicio, abre Chrome **a pantalla completa** y reproduce la demo narrada. Al terminar deja el estado final en pantalla para las preguntas y, al salir, limpia todo.
- La duración medida queda entre **8 y 12 min** a 0,75×, 1× y 1,25×.
- Controles: pausa/reanudar, velocidad 0,75/1/1,25, «Siguiente» y modo **paso a paso**, que avanza escena por escena a mano.
- Narración con voz neural de Azure (**Dalia**, `es-MX-DaliaMultilingualNeural`) pre-renderizada en caché y con **subtítulos siempre visibles**.
- Foco visual: un spotlight sobre elementos vivos y una «lupa» sobre datos pequeños, más slides de transición.
- Reversible: nada queda fuera del Mac, salvo tareas de Boards en la papelera, que se pueden recuperar. El código local se revierte y las corridas se archivan.

**No objetivos**
- No se modifica el diseño de la consola (`assessment/static`, mejor nota de crítica 34/40). El overlay se inyecta desde Playwright.
- No se abren PR reales: el repo es público y GitHub no permite borrar PR.
- No se abren pestañas de terceros (Boards, GitHub, Power BI Web), porque piden login o MFA.
- No se graba ni exporta video. No hay retroceso ni salto a escenas anteriores, porque los pasos cambian estado.
- No se cambia la infraestructura de Azure de forma automática: el ingreso de ACA solo se verifica.

**Anti-objetivos** (fracaso aunque «funcione»)
- Que la narración cite texto libre de los agentes, que no es determinista, o invente métricas, clientes o certificaciones (lo prohíbe `PRODUCT.md`).
- Que quede el repo sucio, por ejemplo con el `.cs` corregido de v3 commiteado por error, o tareas de demo abiertas en Boards.
- Que el overlay tape de forma permanente la etiqueta «Escenario:» o bloquee la consola.

## 3. Restricciones

- **CSP de la consola** (`ui.py`): `default-src 'self'; style-src 'self'; script-src 'self'`. Para cumplirla, el contexto se crea con `bypass_csp=True` y el audio se sirve desde el mismo origen mediante `page.route("**/__demo/voz/*")`, leyendo del disco.
- **Autoplay**: Chrome se lanza con `--autoplay-policy=no-user-gesture-required`, porque la primera línea suena antes de cualquier gesto.
- **Atajos de la consola**: R, D, 1–8, V, ? y Esc (dos Esc cancelan la evaluación).
  - Al empezar, el runner desmarca `#shortcuts-toggle`. El contexto de Playwright es efímero, así que no hace falta restaurarlo.
  - El director captura sus propias teclas en fase de captura y no usa ninguna de las de la consola.
- **Botones armados**, que piden una segunda pulsación en menos de 8 s: ejecutar en modo agente, «Aplicar en local y reevaluar» y «Revertir». Se pulsan dos veces a propósito.
- **Velocidad**: el rango 1,25/0,75 = 1,67× es mayor que la ventana 12/8 = 1,5×. Solo cabe porque hay ~2,5 min de esperas reales (MAF, `dotnet test`) que no escalan con la velocidad.
- **Python 3.14** en `assessment/.venv`. Se usa Playwright para Python con `channel="chrome"` (el Google Chrome instalado), sin descargar navegadores.

## 4. Enfoques considerados

| Enfoque | Ventaja | Costo | Veredicto |
|---|---|---|---|
| **A. Runner Python + «director» inyectado en la página** (Shadow DOM) | El reloj, la pausa y la velocidad viven en la página, junto al audio. Python solo secuencia acciones y espera promesas. Reutiliza el venv, `demo_reset` y las convenciones de CLI. | Un overlay JS propio. | **Elegido** |
| B. Script Node con `@playwright/test` | Es la herramienta canónica. | Suma un segundo toolchain al repo Python y necesita otro canal para pausa y velocidad. | Descartado |
| C. Grabar un video una vez y reproducirlo | Pausa y velocidad nativas. | Deja de ser en vivo y no ejecuta el sistema real, así que pierde credibilidad. Para repetirlo hay que regrabar. | Descartado |

## 5. Decisiones tomadas

Decidió el usuario el 27 nov 2026:
- **Motor: agentes MAF en las tres entregas**, con un solo clic en «Ejecutar». El producto ya absorbe los fallos de un agente:
  - Cada agente tiene un tope de 90 s (`workflow.py`).
  - Ante un 429, un 401 o ese tope, responde HTTP 200 con `ERROR_AGENTE` y el mismo veredicto determinista. La demo sigue con esa tarjeta degradada.
  - El botón «Reintentar vN con Solo evidencia · 0 tokens» solo aparece si `/api/evaluar` falla a nivel HTTP. En ese caso, la demo lo pulsa.
- **Aprobación: la pulsa siempre Playwright.** La narración aclara que en la operación real ese clic lo da una persona.
- **Boards: las tareas de demo van a la papelera al reiniciar** (`DELETE`, recuperable). Si no hay permiso, se recurre a `Removed`, como hoy.
- **Voz: Dalia multilingüe.**
- **Pantalla completa.**

Consenso del consejo, con las 4 voces:
- Cero PR reales: la remediación de C# y de Trivy se hace en disco y se revierte.
- Todo ocurre dentro de la consola, apoyado en slides.
- Subtítulos siempre, porque Teams y Zoom no comparten el audio del navegador por defecto.
- El guion avanza por eventos del DOM y nunca usa esperas fijas.
- La narración solo nombra datos deterministas: veredictos, número de pruebas, IDs y conteos.

Decisiones mías (las puedes corregir):
- **Parche C#** con «Plantilla de contingencia · 0 tokens», no con el borrador de IA.
- **Mitigación SEC-DOCKER-001** sin pulsar «Investigar con Agente SecOps (Foundry)». Ninguna escena depende de texto generado en vivo, salvo la evaluación MAF.
- **Power BI**: se enfoca el botón y los KPI sin abrirlo, porque abrirlo pide login. Queda para las preguntas.
- **Reevaluación tras el parche (escena 12) con «Solo evidencia»**, no con agentes. Antes de aplicar el parche, se cambia `#mode-select` a la vista del público y se narra: «verificar el parche no necesita IA». Evita una cuarta corrida MAF y su riesgo de 429, y tarda ~25 s en vez de 30–65 s.
- **Se cierra el ciclo en Boards**: cuando v3 queda Verificado, se pulsa «Cerrar AB#n en Azure Boards». El KPI «Ciclo Azure Boards» de la escena 13 lo refleja, y la pantalla de preguntas no queda con una acción pendiente. El reinicio también envía esa tarea a la papelera.
- **La ventana de 8–12 min se cumple en cada corrida**, no solo en las de aceptación. Las tres evaluaciones MAF varían entre ~150 y ~210 s, y con un texto fijo no cabe en ambos extremos. Por eso hay líneas `opcional: true`: se omiten si el total proyectado pasaría de 11,5 min (§6.4).
- **Si la evaluación sigue en curso al llegar al tope**: no se cancela, porque cancelar desde el navegador no detiene el servidor y `EVAL_LOCK` dejaría en cola cualquier reintento. El director se pausa solo y muestra un aviso al presentador: «La evaluación sigue en curso · Siguiente para continuar · Terminar».

## 6. Diseño

### 6.1 Archivos

```
demo/
  __init__.py
  __main__.py        CLI y runner: revisión previa, servidor, reinicio, navegador, guion y limpieza
  voz.py             Azure TTS → caché demo/.voz/<sha1>.mp3 (gitignored), duración por clip
  guion.yaml         escenas, pasos y texto de narración (lo edita el usuario sin tocar código)
  director.js        overlay en la página: reloj, subtítulos, foco, lupa, cursor, slides y barra de control
  director.css       estilos del overlay (paleta de marca)
  requirements.txt   playwright==<versión estable fijada>
assessment/tests/test_demo.py   valida guion.yaml y el modelo de tiempo; prueba DELETE→fallback en Boards
```

Uso: `assessment/.venv/bin/python -m demo [--velocidad 1|0.75|1.25] [--paso-a-paso] [--motor agente|solo-evidencia] [--sin-voz] [--ensayo] [--ventana]`.

### 6.2 Flujo de una corrida

1. **Revisión previa** (§6.7). Aborta con un mensaje claro si falla un chequeo bloqueante.
2. **Servidor**: usa `:8050` si ya responde. Si no, lanza `python -m assessment.ui` y lo detiene al salir.
3. **Reinicio previo**: `POST /api/demo/reiniciar` con `{corridas, sandbox, boards, codigo, prs}` todos en `true`. Va por HTTP para que el estado en memoria del servidor quede coherente.
4. **Calentamiento**: `GET /api/vulnerabilidades` deja en caché el escaneo de Trivy del servidor, para que la Etapa 3 cargue al instante.
5. **Navegador**: `chromium.launch(channel="chrome", headless=False)`.
   - Argumentos de lanzamiento: `--kiosk` (pantalla completa, sin barra ni pestañas; el constructor verifica en macOS si funciona mejor con `--start-fullscreen`), `--autoplay-policy=no-user-gesture-required` e `ignore_default_args=["--enable-automation"]`.
   - Contexto: `no_viewport=True` y `bypass_csp=True`.
   - `--ventana` desactiva la pantalla completa para depurar.
6. **Inyección**: `add_init_script` con el CSS embebido (`window.__DIRECTOR_CSS = …`) y `director.js`. Solo se activa en el frame superior. Rutas: `/__demo/voz/*`. Python ↔ página:
   - `page.evaluate("…__director.decir(...)")` devuelve una promesa que resuelve al terminar la línea.
   - `expose_binding("__demoEvento")` avisa a Python de cambios de pausa, velocidad o modo y de la petición «Terminar».
7. **Guion**: escenas en orden (§6.5). Antes de cada paso se espera `__director.turno()`, que resuelve cuando no hay pausa. En modo paso a paso, además, espera «Siguiente» en cada frontera de escena.
8. **Final**: la última slide queda en pantalla y la consola conserva su estado final para las preguntas. El runner espera a que el presentador pulse «Terminar», cierre la ventana o pulse Ctrl+C.
9. **Limpieza** (en `finally`, también si algo falla): reinicio completo con Boards, verificación de git limpio y cierre del servidor si lo lanzó el runner. Escribe el registro de tiempos (§6.10).

### 6.3 Director en la página

Shadow root colgado de `document.documentElement`. Todas las capas usan `pointer-events: none`, salvo la barra de control y las slides, que bloquean la página mientras se ven.

- **Reloj**: `velocidad` (0,75/1/1,25) y `pausado`.
  - `decir(texto, urlAudio, duracion)`: muestra el subtítulo y reproduce el audio con `playbackRate = velocidad` (el tono se conserva). Sin audio, por ejemplo con `--sin-voz`, espera `duracion / velocidad`.
  - `esperar(ms)` descuenta solo el tiempo sin pausa. «Siguiente» resuelve la línea en curso.
  - Las animaciones (cursor, slides) escalan con `--demo-velocidad`.
- **Subtítulos**: tercio inferior, sobre la barra; texto de 24–28 px con fondo navy translúcido y fundido entre líneas.
- **Spotlight**: capa navy translúcida con un recorte redondeado que sigue en vivo el `getBoundingClientRect()` del objetivo con `requestAnimationFrame`. Lleva un anillo cian (`--brand-cyan`) y una etiqueta opcional. Antes de enfocar hace scroll suave hasta el objetivo. Cuando el foco está en la matriz, el recorte incluye la cabecera de la columna, para que «Escenario:» siga visible.
- **Lupa**: Python toma `locator.screenshot()` (nítido a DPR 2) y el director lo muestra como tarjeta ampliada, hasta 2× y como máximo el 70 % del viewport. La tarjeta anima desde la posición original del elemento hasta el centro y vuelve (técnica FLIP). No se escala la página: el inspector de etapas es `position: fixed` y un `transform` sobre `body` lo desplazaría.
- **Cursor falso**: flecha SVG que se desliza hasta el elemento (600–900 ms / velocidad) con una onda de clic. Después, Playwright hace el clic real. Se oculta durante las slides.
- **Slides**: plantillas HTML/SVG dentro del director, con fondo degradado navy (`#081c3a → #0d2b59`), tipografía de la consola, acentos cian y el monograma de marca (`/brand-mark.png`). Entran con fade-up escalonado. Plantillas: `portada`, `pregunta`, `caso`, `maf`, `etapas`, `gobernanza`, `cierre`.
- **Barra de control**: píldora inferior centrada que se oculta tras 3 s sin mover el ratón y está siempre visible en pausa.
  - Pausa (Espacio o K).
  - Siguiente (→ o N).
  - Velocidad 0,75× · 1× · 1,25× (`<` y `>`).
  - Modo paso a paso (P).
  - Terminar (Q).
  - Progreso: escena «3/14 · El caso», barra con marcas por escena y tiempo transcurrido / total estimado a la velocidad actual.
  - Un chip «● En vivo: …» durante las esperas reales.
- **Accesibilidad**: con `prefers-reduced-motion`, cursor y slides pasan a fundidos. Los subtítulos tienen contraste AA.

### 6.4 Guion (`guion.yaml`) y tipos de paso

Una escena tiene `id`, `titulo` y `pasos`. Tipos de paso:

| Tipo | Campos | Efecto |
|---|---|---|
| `slide` | `plantilla`, campos de la plantilla, `voz` | Muestra la slide, narra y la oculta. |
| `narrar` | `voz`, `foco?` o `lupa?` (selector), `etiqueta?` | Narra con spotlight o lupa opcionales. |
| `clic` | `selector`, `confirmar?` (doble pulsación), `voz?` | Mueve el cursor y hace clic. |
| `elegir` | `selector`, `valor` | Elige una opción de un `<select>`. |
| `escribir` | `selector`, `texto` | Teclea de forma visible. |
| `esperar` | `condicion` (expresión JS), `max_s`, `voz_mientras: [...]`, `relleno: [...]`, `si_error` | Narra `voz_mientras` mientras espera la condición. Si la condición sigue pendiente, encadena líneas de `relleno`. Termina cuando la condición se cumple y acaba la línea en curso. Si aparece un error HTTP en una tarjeta, ejecuta `si_error`: pulsar «Reintentar vN con Solo evidencia» y seguir esperando. Al llegar a `max_s`, se pausa solo (§5). |

**Líneas opcionales.** Un paso `narrar` con `opcional: true` solo se reproduce si el total proyectado, sumando esa línea, no pasa de 11,5 min. El total proyectado se calcula así:
- tiempo transcurrido sin pausas;
- más la narración obligatoria restante dividida por la velocidad;
- más las esperas reales restantes, con valores nominales hasta que se miden en la propia corrida.

A 1,25× suenan todas; a 0,75× se omiten las necesarias. Así la ventana se cumple en cada corrida.

### 6.5 Escenas y presupuesto (narración a 1×)

| # | Escena | Qué se ve | Narración |
|---|---|---|---|
| 1 | Portada | Slide `portada` | 15 s |
| 2 | La pregunta | Slide `pregunta`: checks en verde no equivalen a evidencia; evidencia fragmentada entre Boards, GitHub, pipelines y Azure | 35 s |
| 3 | La consola | Foco en la marca, en las píldoras del ecosistema y en los controles | 25 s |
| 4 | El caso | Slide `caso`: AppContratos, REN-001 y REN-002, y las tres entregas, cada una con su «Escenario:» | 35 s |
| 5 | Ejecutar | `#scope-select` = todas, `#mode-select` = agente, `#run-btn` con doble pulsación | 8 s |
| 6 | Mientras corre | Slide `maf` (recolector SHA-256, tres agentes en paralelo y fan-in a la política REN-001.v2), luego foco en la matriz que se llena en vivo. Una línea fija y neutra: «si un agente no responde a tiempo, la consola lo registra como diagnóstico operativo y el dictamen no cambia: lo decide la política». Espera hasta que `#ledger[data-running="false"]` y las tres tarjetas tengan dictamen, con máximo de 420 s; luego se pausa solo | 80 s + relleno |
| 7 | Dictamen | Lupa sobre la fila de dictámenes (v1 verde, v2 rojo, v3 ámbar) y luego «Solo brechas» (`#filter-diff-btn`) | 30 s |
| 8 | Momento clave v3 | Inspector de la Etapa 4 de v3 (`.ledger-cell-btn[data-stage="4"][data-ver="v3"]`): pruebas en verde y ninguna vinculada a REN-001 ni con un contrato cancelado | 40 s |
| 9 | Las 8 etapas | Slide `etapas`, luego un recorrido por el inspector con `#inspector-next-btn` (~7 s por etapa) | 70 s |
| 10 | Seguridad en origen | Reporte de la Etapa 3 y lupa sobre SEC-DOCKER-001 (Trivy DS002 HIGH). Pasos: «Corregir en Etapa 8 →» y «Aplicar mitigación y reauditar Etapa 3», que bajan Trivy HIGH a 0 | 35 s |
| 11 | Gobernanza | Slide `gobernanza`, luego la pestaña v3 del expediente. Pasos: escribir la nota, «Aprobar en Azure Boards» y confirmar. Lupa sobre el enlace `AB#n`. Frase neutra: «la aprobación queda registrada en Azure Boards» | 35 s |
| 12 | Remediación | «Plantilla de contingencia · 0 tokens». Luego `#mode-select` a «Solo evidencia», narrado, y «Aplicar en local y reevaluar» con doble pulsación. Espera a que v3 pase a Verificado (~25 s), foco en la columna v3 ya en verde y, al final, «Cerrar AB#n en Azure Boards» | 35 s |
| 13 | Valor continuo | Foco en `#value-kpis` y en el botón de Power BI, sin abrirlo | 15 s |
| 14 | Cierre | Slide `cierre`: las 3 tesis y el siguiente paso («una aplicación crítica, sus dos últimas entregas, dos semanas») | 30 s |

- **Presupuesto de narración a 1×** (Dalia lee ~17 caracteres por segundo):
  - ~5,7 min obligatorios, unos 5.800 caracteres;
  - ~1,2 min de líneas `opcional`;
  - en la escena 6, 80 s obligatorios más relleno.
- **Modelo de tiempo**: el total es la narración dividida por la velocidad más, en cada escena con espera real, el mayor entre esa espera y la narración que la cubre. Las esperas son la evaluación MAF (150–210 s), la reauditoría de Trivy, la aprobación, la reevaluación (~25 s) y el cierre en Boards.
- **Extremos que debe cumplir**:
  - 1,25× con 150 s de evaluación y todas las opcionales: ≥ 8 min;
  - 0,75× con 210 s y sin opcionales: ≤ 12 min.
- **Esto es una estimación**: la aceptación se mide (§6.10).
- **Fuente del contenido**: los textos parten de los actos de `GUION_DEMO.md`, con tono consultivo y tratando a la audiencia de «ustedes».

### 6.6 Voz

- `voz.py` genera un clip por línea con SSML: `<voice name="es-MX-DaliaMultilingualNeural">` y formato `audio-48khz-96kbitrate-mono-mp3`.
- Usa el endpoint `https://westus3.tts.speech.microsoft.com/cognitiveservices/v1` con la clave del recurso AIServices `jcastros-0808-resource` (S0, westus3). Es la misma clave que `AZURE_OPENAI_API_KEY` en `assessment/.env`, y nunca se imprime.
- **Caché**: un clip por línea en `demo/.voz/<sha1(voz+texto)>.mp3`, con su duración leída por `afinfo`. Solo se regeneran las líneas que cambian.
- **Si la generación falla y falta algún clip**, la revisión previa aborta y sugiere `--sin-voz`.

### 6.7 Revisión previa

| Chequeo | Si falla |
|---|---|
| `git status --porcelain -- v1 v2 v3 Dockerfile deploy .github` vacío (son las rutas que la demo modifica) | Aborta |
| Consola responde, o se puede lanzar | Aborta |
| Token de `az` vigente (Boards, Defender, Resource Graph) | Aborta |
| Con `--motor agente`: ping mínimo a Foundry (1 token) sin 401 ni 429 | Aborta y sugiere `--motor solo-evidencia` |
| BD de Trivy vigente (`metadata.json` → `NextUpdate` en el futuro); si no, se calienta con `trivy fs --download-db-only` | Si falla el calentamiento, avisa |
| Ingreso de ACA encendido (`GET https://<fqdn>/api/salud`) | Avisa e imprime `az containerapp ingress enable …` (las etapas 5–7 saldrían con evidencia degradada) |
| Tras el reinicio, ninguna tarea de demo abierta bajo AB#1 (WIQL) | Avisa |
| Clips de voz completos | Los genera; si falla, aborta |

### 6.8 Reversibilidad

- **Antes de empezar**: reinicio completo, incluida la limpieza de Boards. Así la corrida es idempotente aunque la anterior se haya cortado.
- **Al salir**, en `finally`, otro reinicio completo:
  - revierte el `.cs` de v3 y las mitigaciones en `Dockerfile`, `deploy/` y `.github/`;
  - manda las tareas de demo a la papelera y restaura AB#1;
  - archiva las corridas en `assessment/runs/_archivo_demos/<stamp>/`.
- **Comprobación final**: se verifica que git quedó limpio en las rutas de la demo y se imprime «Demo lista para volver a ejecutarse».
- **Estado actual de Boards**: hay **2 tareas de demo abiertas (New)** de sesiones anteriores. El primer reinicio las enviará a la papelera, de donde se pueden recuperar.

### 6.9 Cambio en el producto: Boards a la papelera

- **Nuevo comportamiento de `reset_boards_demo_state`** (`assessment/demo_reset.py`): para cada tarea de demo intenta primero `DELETE {org}/{proyecto}/_apis/wit/workitems/{id}?api-version=7.1`, que la manda a la papelera sin `destroy`. Si responde 401 o 403, recurre al `PATCH` a `Removed` de hoy.
- **Qué devuelve**: el método usado en cada tarea.
- **WIQL**: no cambia.
- **Textos que lo mencionan**: se ajustan la etiqueta de `#reset-boards-chk` en `index.html` (solo el texto, sin cambio de diseño) y las menciones a «Removed» en `GUION_DEMO.md`.
- **Pruebas**: se cubren ambos caminos con `_http_json` simulado.

### 6.10 Pruebas y aceptación

- **`assessment/tests/test_demo.py`** (`unittest`, como las pruebas existentes) comprueba:
  - que `guion.yaml` es válido: tipos de paso conocidos, campos obligatorios y voz no vacía;
  - que el modelo de tiempo da totales dentro de 8–12 min en los dos extremos de §6.5, aplicando las reglas de líneas opcionales;
  - el `DELETE` con fallback en Boards.
- **`--ensayo`** recorre toda la coreografía rápido para validar los selectores de punta a punta:
  - motor `solo-evidencia`;
  - sin audio, pero con las duraciones de los clips;
  - reloj ×6.
- **Registro**: cada corrida escribe `demo/.registro/<stamp>.json` (gitignored) con la narración, la espera real y el tiempo transcurrido por escena, el total, y los totales previstos a 0,75×, 1× y 1,25×.
- **Aceptación**: dos corridas reales con agentes y voz, una a **0,75×** y otra a **1,25×** (los extremos), ambas con un total medido entre 8 y 12 min, y git limpio después de cada una.

## 7. Queda a criterio del constructor

- Redacción exacta de la narración, dentro del presupuesto de §6.5 y sin datos inventados.
- Detalle visual de las slides y del overlay, siempre con la paleta y la tipografía de la consola.
- Si `--kiosk` o `--start-fullscreen` funciona mejor en macOS con Playwright.
- Selectores exactos de los botones renderizados por `app.js` (hoy se ubican por texto: «Aprobar en Azure Boards», «Plantilla de contingencia · 0 tokens», «Aplicar en local y reevaluar», «Corregir en Etapa 8 →», «Aplicar mitigación y reauditar Etapa 3»).
- Versión exacta de `playwright`: la estable más reciente con al menos dos semanas de publicada.

## 8. Riesgos

- **Latencia o 429 de Foundry en la escena 6.** El producto lo absorbe con `ERROR_AGENTE` y el mismo veredicto. Se suman el ping previo, el `relleno`, el reintento ante un error HTTP y la pausa automática al llegar al tope.
- **Ventana de tiempo ajustada en los extremos.** Las líneas opcionales la protegen en cada corrida, y la aceptación la mide.
- **Cambios en el DOM de la consola rompen selectores.** `--ensayo` los detecta antes de presentar.
- **Permiso de borrado en Boards sin verificar.** Si no lo hay, se recurre a `Removed`, que no es peor que hoy.
