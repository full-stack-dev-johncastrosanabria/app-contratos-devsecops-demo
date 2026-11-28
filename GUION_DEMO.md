# Guía Completa de Demo: NextGen DevSecOps Assessment

Este documento es tu manual operativo de bolsillo para preparar, presentar y cerrar la demostración en vivo de **NextGen DevSecOps Assessment** (construida con **Microsoft Agent Framework**, **Azure AI Foundry (`gpt-4.1-mini`)**, **Azure Boards**, **GitHub Advanced Security / Actions**, **Azure Container Apps**, **Defender for Cloud** y **Application Insights**).

---

## 0. Idea Fuerza de la Demo (Qué estamos demostrando)

- **Audiencia objetivo:** VP de Ingeniería, Líderes Técnicos, Arquitectos Cloud, QA Leads y CISOs.
- **Problema real que ataca:** Los equipos ya tienen herramientas en las 8 etapas de DevSecOps, pero la evidencia está fragmentada. Demostrar antes o después de un pase a producción que una versión cumple los criterios funcionales y controles de seguridad/operación toma horas de revisión manual.
- **Tesis técnica diferencial (por qué genera confianza):**
  1. **Orquestación Multi-Agente completa con barandillas deterministas:** Tres agentes especializados corren en paralelo sobre MAF (*QA & Trazabilidad*, *SecOps · SonarQube y Trivy* y *SRE, Observabilidad & Gobernanza de Release*), acompañados por agentes dedicados de **Triaje AppSec (Etapa 3)**, **Análisis SRE/Power BI (Etapa 7)**, **Ingeniería de Parches C# con autovalidación** y **Remediación + Verificación Post-Mitigación SecOps (Etapa 8)**; una **política determinista versionada** valida cada referencia y parche antes de emitir el estado (`VERIFICADO`, `INCUMPLIDO`, `EVIDENCIA_INSUFICIENTE`).
  2. **Un pipeline en verde no equivale a cumplimiento:** Una suite puede pasar al 100 % cubriendo solo el camino feliz (`v3`) sin probar la regla crítica del negocio (`REN-001`).
  3. **Gobernanza humana sin ruido en el backlog:** El agente nunca crea tickets a ciegas; guarda un checkpoint, espera aprobación humana y sincroniza en Azure Boards con una huella idempotente (`devsecops-fp-...`) que evita duplicar tareas en futuras reevaluaciones.

---

## 1. ANTES DE LA DEMO (T-10 minutos · Preparación Técnica)

Ejecutá estos pasos **10 minutos antes** de entrar a la llamada para despertar los servicios serverless y dejar listas las pestañas.

### Paso 1.1 — Verificar sesiones locales (30 segundos)

Desde una terminal en la raíz del proyecto:

```bash
cd /Users/johnbenjamincastrosanabria/Developer/AppContratos
az account show --query "{suscripcion:name, estado:state, tenant:tenantDisplayName}" -o table
gh auth status
```
> Si `az` pide renovar token, ejecutá `az login` con tu cuenta de `NOVACOMP`.

### Paso 1.2 — Encender la aplicación en Azure Container Apps y generar telemetría fresca (1 minuto)

Como dejamos el ingreso público apagado fuera de horario de demos para proteger tus créditos (\$0.00/hora), reactivalo y enviá un par de peticiones para despertar la réplica y registrar tráfico fresco en Application Insights:

```bash
az containerapp ingress enable -g rg-jcastros-2718 -n ca-appcontratos --type external --target-port 8080

FQDN=$(az containerapp show -g rg-jcastros-2718 -n ca-appcontratos --query "properties.configuration.ingress.fqdn" -o tsv)
echo "App activa en: https://$FQDN"

curl -sf "https://$FQDN/api/salud" && echo ""
curl -sf "https://$FQDN/api/contratos" && echo ""
```

### Paso 1.3 — Iniciar la Consola Web del Evaluador (15 segundos)

En esa misma terminal, dejá corriendo el servidor local de evaluación:

```bash
assessment/.venv/bin/python -m assessment.ui
```
Verás en consola: `Demo REN-001 · http://127.0.0.1:8050`.

### Paso 1.4 — Preparar las 4 pestañas del navegador (en este orden)

Dejá abiertas estas 4 pestañas en una ventana limpia (con zoom al `110%`–`125%` para que se lea perfecto al compartir pantalla):

1. **Pestaña 1 (Evaluador MAF):** `http://127.0.0.1:8050`
2. **Pestaña 2 (Etapa 1 · Azure Boards `AB#1`):** `https://dev.azure.com/jcastros0696/AppContratos/_workitems/edit/1`
3. **Pestaña 3 (Etapas 2, 3 y 4 · GitHub PR y Seguridad):** `https://github.com/full-stack-dev-johncastrosanabria/nextgen-devsecops-assessment/pull/1`
4. **Pestaña 4 (Etapa 5 · AppContratos en vivo en Azure):** la URL `https://$FQDN` que imprimió el Paso 1.2 (`https://ca-appcontratos.salmonglacier-8930e016.westus3.azurecontainerapps.io`)

### Paso 1.5 — Plan B de contingencia (por si fallara internet o cuota de modelo en plena reunión)

- **Si quisieras cambiar de proveedor IA en caliente** (de Azure AI Foundry a Claude Sonnet 4.6 sin reiniciar el servidor web, ya que `.env` se lee en cada corrida):
  ```bash
  sed -i '' 's/^ASSESSMENT_PROVIDER=.*/ASSESSMENT_PROVIDER=anthropic/' assessment/.env
  ```
  *(Para volver a Azure AI Foundry: `sed -i '' 's/^ASSESSMENT_PROVIDER=.*/ASSESSMENT_PROVIDER=azure/' assessment/.env`).*
- **Si estuvieras completamente sin salida al proveedor IA:** en el desplegable **Modo** de `http://127.0.0.1:8050`, elegí **Solo evidencia determinista**. Sigue ejecutando xUnit, calculando el veredicto y armando la matriz sin consumir tokens.

---

## 2. DURANTE LA DEMO (Guion Explicado Paso a Paso · 6 a 8 minutos)

### Acto 1 — Apertura: La pregunta que hoy nadie responde rápido *(1 minuto)*

- **Pantalla visible:** Pestaña 1 (`http://127.0.0.1:8050`), aún sin pulsar el botón.
- **Qué decir:**
  > *"Cuando un equipo despliega una nueva versión, normalmente vemos checks verdes en el pipeline y damos por hecho que todo está cubierto. Pero si un líder de ingeniería o auditor pregunta: **'¿Qué evidencia concreta tenemos de que esta versión cumple los criterios de negocio acordados, pasó controles de seguridad en código y nube, y no degradó el ambiente?'**, reconstruir esa historia entre Azure Boards, GitHub, reportes de pruebas y Azure Monitor suele llevar horas.*
  >
  > *Lo que van a ver hoy es un **Agente de Evaluación Continua DevSecOps** construido sobre **Microsoft Agent Framework** y **Azure AI Foundry**. Recorre las 8 etapas del ciclo DevSecOps, investiga la evidencia como lo haría un ingeniero de QA y SecOps, y prepara acciones de mejora gobernadas por aprobación humana."*

---

### Acto 2 — El escenario de negocio en vivo *(1 minuto y medio)*

- **Cambiá a Pestaña 4 (`AppContratos` en Azure Container Apps):**
  - **Acción:** Mostrá brevemente la pantalla de `Contratos · Renovaciones`.
  - **Qué decir:**
    > *"Nuestro sujeto de prueba es `AppContratos`, una API en .NET 10 desplegada en Azure Container Apps que genera avisos de renovación a 30, 7 y 1 día del vencimiento."*
- **Cambiá a Pestaña 2 (`Azure Boards · AB#1`):**
  - **Acción:** Señalá el título de `AB#1` y la sección **Acceptance Criteria**.
  - **Qué decir:**
    > *"En la etapa de **Planificación**, el negocio definió la historia `AB#1` con un criterio crítico, **REN-001**: **al evaluar renovaciones, un contrato cancelado nunca debe generar un aviso** (para no contactar por error a exclientes)."*
- **Cambiá a Pestaña 3 (`GitHub PR #1`):**
  - **Acción:** Señalá la referencia `AB#1` en la descripción del PR y mencioná el pipeline con CodeQL y Dependabot.
  - **Qué decir:**
    > *"En **Código, Seguridad e Integración**, el equipo entregó el cambio mediante el `PR #1` vinculado a `AB#1`, corrió pruebas xUnit generando archivos `.trx`, análisis estático con CodeQL y desplegó en Azure. Ahora evaluemos tres entregas candidatas de esta aplicación."*

---

### Acto 3 — Ejecución paralela en Microsoft Agent Framework *(2 minutos y medio)*

- **Volvé a Pestaña 1 (`http://127.0.0.1:8050`):**
  - **Acción:** Verificá que esté seleccionado **Las tres versiones** + **Con agentes MAF (QA + SecOps)** y hacé clic en **Ejecutar evaluación →**.
  - **Qué explicar mientras las tarjetas pasan por *"En curso"* (~20 segundos):**
    > *"Fíjense lo que ocurre tras bambalinas con `WorkflowBuilder` de Microsoft Agent Framework:*
    > *1. Primero, un ejecutor recopila de forma aislada la evidencia inmutable (hashes SHA-256, commit, artefacto `.trx` y estado en Boards, GitHub y Azure).*
    > *2. Luego, el grafo se abre en **dos ramas paralelas (`fan-out`)** sobre `gpt-4.1-mini` en Azure AI Foundry: por un lado el **Agente de QA y Trazabilidad** decide qué pruebas inspeccionar; por el otro, el **Agente de Seguridad y Operación** consulta CodeQL, postura en Defender for Cloud y métricas en Application Insights.*
    > *3. Finalmente, convergen (`fan-in`) en un **evaluador determinista**: el modelo explica y propone correlaciones, pero una política en código valida que ningún ID haya sido alucinado antes de emitir el veredicto."*

- **Cuando aparecen las 3 tarjetas, recorrelas de izquierda a derecha:**

  1. **Tarjeta 1 · Versión 1 (`Verificado` — Verde):**
     > *"En la Versión 1 todo cierra: desde `AB#1` en Boards y el `PR #1` hasta la prueba `CanceladoNoGeneraAviso` marcada con el criterio `REN-001`, que ejecutó el escenario cancelado y pasó en el TRX."*

  2. **Tarjeta 2 · Versión 2 (`Incumplido` — Rojo):**
     > *"En la Versión 2 hay una regresión funcional real: la prueba vinculada existe, se ejecutó y falló porque el motor generó un aviso para un contrato cancelado. Queda inmediatamente bloqueada como `Incumplido`."*

  3. **Tarjeta 3 · Versión 3 (`Evidencia insuficiente` — Ámbar · EL MOMENTO CLAVE DE LA DEMO):**
     - **Acción:** Desplegá **Evidencia y traza Agente QA** en la tarjeta de Versión 3.
     - **Qué decir:**
       > *"Presten especial atención a la **Versión 3**. Si miran las pruebas xUnit: **3 aprobadas, 0 fallidas; el pipeline terminó 100 % en verde**. En un proceso tradicional esto pasa derecho a producción.*
       > *¿Qué hizo aquí nuestro agente de QA? Buscó vínculos explícitos y no encontró ninguno; entonces inspeccionó el código de las pruebas existentes y descubrió que todas llaman a `Caso(false, dias)`: solo prueban contratos activos. Nadie probó un contrato cancelado. Por eso el sistema dictamina **Evidencia insuficiente**: código en verde sin evidencia del criterio no se certifica."*

  4. **Demostración de la rama SecOps (en cualquiera de las tarjetas):**
     - **Acción:** Desplegá **Recorrido DevSecOps (8 etapas)** y **Postura y traza Agente SecOps**.
     - **Qué decir:**
       > *"Y miren cómo la rama de Seguridad y Operación clasifica cada hallazgo con su **alcance exacto** para no mezclar responsabilidades:*
       > *- Alcance **`version`**: alertas detectadas por **CodeQL** en el código fuente del repositorio.*
       > *- Alcance **`recurso`**: **Defender for Cloud** confirma que HTTPS exclusivo está activo, pero advierte que al Container App le falta habilitar *Managed Identity*.*
       > *- Alcance **`ambiente`**: **Application Insights** reporta las solicitudes reales servidas con `0%` de errores `5xx` y su latencia promedio."*

---

### Acto 4 — Aprobación humana e idempotencia en Azure Boards *(1 minuto y medio)*

- **Acción en la tarjeta de Versión 3 (o Versión 2):**
  1. Señalá el recuadro **Gobernanza · Azure Boards** y el código `devsecops-fp-...`.
  2. Escribí en el campo de nota: `Aprobado en comité de release: cubrir caso cancelado antes de prod`.
  3. Hacé clic en **Aprobar en Azure Boards**.
  4. Cuando aparece el enlace **`AB#<id>`** (ej. `AB#2` o `AB#3`), hacé clic para abrirlo en vivo en Azure Boards.
- **Qué decir:**
  > *"Para cerrar la etapa 8 (**Optimizar con IA**), el workflow no ensucia Azure Boards de forma autónoma. Persiste un checkpoint y espera la decisión del líder.*
  > *Al aprobar, crea la tarea en Azure Boards ya vinculada como hija de la historia `AB#1`, con el commit exacto, la brecha detectada y el criterio para reevaluarla.*
  > *¿Y qué pasa si mañana corremos de nuevo el assessment y el equipo todavía no cerró la tarea? Gracias a esa huella determinista (`devsecops-fp-...`), el ejecutor consulta por WIQL, detecta que la tarea sigue abierta y **agrega un comentario de seguimiento sobre el mismo Work Item sin duplicarlo**."*

---

### Respuestas cortas para preguntas difíciles (Q&A de bolsillo)

- **¿Qué pasa si el modelo alucina que una prueba existe o pasó?**
  > *"No puede alterar el resultado: `validate_references` contrasta cada archivo, línea y `execution_id` devuelto por el modelo contra el árbol fuente con SHA-256 y el XML del TRX. El veredicto lo decide código determinista, nunca el LLM."*
- **¿Un desarrollador malicioso podría poner instrucciones en un comentario del código para engañar al agente o leer las API keys?**
  > *"Tenemos doble aislamiento: al ejecutar `dotnet test` se purgan del entorno todas las credenciales de IA, se recalculan hashes SHA-256 post-ejecución para detectar cambios en caliente, y las herramientas del agente tratan código y TRX estrictamente como datos acotados de solo lectura."*
- **¿Esto solo sirve para .NET y GitHub?**
  > *"No. El grafo en Microsoft Agent Framework desacopla los ejecutores de recolección: la misma arquitectura evalúa JUnit/PyTest, Azure Pipelines o repositorios en Azure Repos cambiando únicamente el adaptador de lectura."*

---

## 2.5 Capacidades de las 8 Etapas que podés mostrar en vivo (Cobertura Completa del Loop)

1. **Etapa 1 · Planificar (`Azure Boards`):** Historia `AB#1` con criterios estructurados múltiples (`REN-001` cancelados y `REN-002` ventanas activas idempotentes 30/7/1 días).
2. **Etapa 2 · Crear código (`GitHub + VS Code + GitHub Copilot`):** Trazabilidad bidireccional `PR #1 ↔ AB#1` y verificación automática de reglas de autoría en `.github/copilot-instructions.md`.
3. **Etapa 3 · Asegurar desde el origen (`SonarQube Cloud · Aqua Trivy · CodeQL · Dependabot · SBOM`):** Conecta en vivo el **Quality Gate y ratings `A`–`E` de SonarQube Cloud** (`sonarcloud.io`), ejecuta **Aqua Trivy CLI** en tiempo real sobre contenedores/IaC/SCA (además de subir SARIF en GitHub Actions y Azure Pipelines) y consolida un **Reporte Formal de Vulnerabilidades** interactivo (`SEC-CI-001` permisos globales de Actions, `SEC-DOCKER-001` imagen sin `USER $APP_UID` correlacionada con `Trivy DS002`, `SEC-K8S-001` ausencia de `ephemeral-storage` en AKS y `SEC-WEB-001` cabeceras HTTP defensivas en API .NET) junto con CodeQL, 5 PRs reales de Dependabot y SBOM SPDX. Desde cada fila podés pulsar **«Corregir en Etapa 8 →»** y ver cómo Trivy baja `HIGH` a `0` al mitigar `SEC-DOCKER-001`.
4. **Etapa 4 · Integrar y probar (`Azure Pipelines + GitHub Actions + xUnit`):** Matriz multi-criterio (`2/2` en `v1`, `1/2` en `v2` y `v3`), cobertura de escenarios/Cobertura XML y pipelines espejo en `.github/workflows/devsecops.yml` y `azure-pipelines.yml`.
5. **Etapa 5 · Desplegar (`Azure Container Apps + AKS Ready`):** Verificación de revisión activa/commit en Container Apps más auditoría determinista de 6 controles de endurecimiento Kubernetes en `deploy/aks/` (`runAsNonRoot`, `readOnlyRootFilesystem`, `drop: ALL`, `NetworkPolicy`).
6. **Etapa 6 · Operar (`Microsoft Defender for Cloud`):** Consulta en vivo del **Secure Score (%)** en Azure Resource Graph, HTTPS exclusivo e identidad administrada `SystemAssigned` habilitada en `ca-appcontratos`.
7. **Etapa 7 · Observar y aprender (`Azure Monitor + App Insights + Log Analytics + Power BI`):** Comparación KQL reciente (`1h`) vs línea base (`23h previas`) y botón **«Sincronizar y abrir en Power BI Web»**, que empuja las corridas en tiempo real vía Power BI Push API, genera automáticamente el reporte visual `.pbix` conectado en vivo (4 tarjetas DAX, gráfico de columnas por entrega/dictamen, anillo de veredictos y tabla auditable) y abre `https://app.powerbi.com/groups/me/reports/...` directo en el navegador (además de mantener `CSV local` y `JSON Fabric`).
8. **Etapa 8 · Optimizar con IA (`Fabric + Azure AI Foundry + Microsoft Security Copilot`):**
   - **Mesa de Remediación SecOps con Agente IA (Etapa 3 → Etapa 8):** investiga cualquiera de las vulnerabilidades detectadas en la Etapa 3 con el Agente SecOps en Azure AI Foundry (o plantilla `0 tokens`), aplica el endurecimiento en disco (o en lote sobre las 4) y **reaudita al instante la Etapa 3 pasándola a `Verificado` (verde)**, o abre un **PR SecOps en GitHub** (`secops/fix-...`), todo 100 % reversible.
   - **Remediación ejecutable de código C# y GitOps (100 % reversible):** en cada expediente con brecha (`v2` o `v3`), podés generar el código con `0 tokens` o con `Azure AI Foundry` y elegir en vivo:
     1. **«Aplicar en local y reevaluar»:** guarda respaldo del `.cs` original, escribe la corrección, vuelve a correr `dotnet test` y pasa la tarjeta en vivo a **`Verificado` (verde)** (habilitando además **«Cerrar tarea en Azure Boards»**). Con un clic en **«Revertir código original y reevaluar»** vuelve al fallo original.
     2. **«Crear rama y PR en GitHub»:** crea una rama efímera `demo/remediacion-...` y abre un **Pull Request real en GitHub** vinculado a `AB#1` sin tocar tu rama `main` local; con **«Cerrar PR y borrar rama»** (o **«Reiniciar demo»**) limpia todo en GitHub.
   - **Manifiesto OpenAPI y plugin para Microsoft Security Copilot** (`/copilot/security-copilot-skill.yaml`).
   - **Gobernanza WIQL idempotente + cierre de ciclo** cuando una entrega alcanza `VERIFICADO`.

---

## 2.6 ENTRE MÚLTIPLES DEMOS (Reinicio 100 % Reversible en 5 segundos)

Todo lo que hagas durante una sesión (evaluaciones, contratos de prueba en `:5080`, aprobaciones, descartes o cierres en Azure Boards) es **completamente reversible** para repetir la demo cuantas veces quieras:

### Opción A — Desde la Consola Web (`http://127.0.0.1:8050`)
1. **Para repetir una sola aprobación/descarte sin volver a correr `dotnet test`:** dentro de la tarjeta de gobernanza de `v2` o `v3`, hacé doble clic en **«Reabrir para otra demo»**. La tarjeta vuelve a `Pendiente de aprobación` y retira (`Removed`) la tarea previa en Azure Boards para que el próximo clic vuelva a decir *«Tarea creada»*.
2. **Para dejar toda la sala limpia antes de la siguiente audiencia:** hacé clic arriba a la derecha en **«Reiniciar demo»**:
   - **Archivar corridas y reiniciar KPIs:** mueve las corridas actuales a `assessment/runs/_archivo_demos/<timestamp>/` (no se pierden).
   - **Limpiar contratos locales en `:5080`:** elimina los `datos.json` efímeros de `v1`, `v2` y `v3`.
   - **Reiniciar tareas demo en Azure Boards** *(opcional)*: envía a la papelera de Boards las tareas `devsecops-fp-*` (se pueden restaurar; si el token no tiene permiso de borrado, quedan en `Removed`) y restaura `AB#1` a su estado canónico.
3. **¿Querés recuperar la sesión anterior?** Abrí de nuevo **«Reiniciar demo»** y pulsá **«Restaurar última sesión archivada»**.

### Opción B — Desde Terminal (CLI)
```bash
# Reinicio local + Azure Boards (archiva corridas, limpia :5080 y retira tareas demo en Boards)
assessment/.venv/bin/python -m assessment reiniciar-demo --con-boards

# Deshacer el último reinicio y restaurar las corridas archivadas
assessment/.venv/bin/python -m assessment restaurar-demo

# Reabrir una decisión individual por su ID de ejecución
assessment/.venv/bin/python -m assessment reabrir --ejecucion <id_32_hex>
```

---

## 2.7 DEMO AUTOMATIZADA (Playwright · 8 a 12 minutos con narración)

Playwright maneja la consola en Chrome de punta a punta: slides de transición, foco sobre cada etapa importante, narración consultiva con tu voz de ElevenLabs, pausa, paso a paso y velocidad 0,75×, 1× o 1,25×. Cuenta la historia de REN-001 con las tres entregas y, al terminar, deja todo como estaba para volver a ejecutarla.

### Una sola vez: sesión de Power BI y voz
- **Power BI.** `assessment/.venv/bin/python -m demo --iniciar-sesion` abre el reporte en el perfil de Chrome de la demo (`demo/.perfil`, fuera de git). Si Power BI lo pide, iniciá sesión y elegí mantenerla iniciada; cuando veas el reporte, cerrá la ventana y el comando comprueba que se dibuje. Solo hace falta repetirlo cuando la revisión previa avise que la sesión caducó.
- **Voz.** Con `ELEVENLABS_VOICE_ID` y `ELEVENLABS_API_KEY` en `assessment/.env`, la demo narra con tu voz; si faltan, usa la voz neural del guion. Cada línea queda en `demo/.voz/` y solo se regeneran las que cambian (ElevenLabs cobra por carácter).

### Ensayo (sin tokens, sin audio, sin grabación)
```bash
assessment/.venv/bin/python -m demo --ensayo --sin-voz --ventana
```
Recorre todo a ×6 con el motor «solo evidencia» en una ventana de 1440×900 y termina con «Ensayo terminado: N fallos de selectores o esperas». Sin `--sin-voz`, el ensayo además genera los clips de voz que falten.

### Recorrido de revisión (capturas y PDF)
```bash
assessment/.venv/bin/python -m demo --sin-voz --sin-grabar
```
Corre en pantalla completa, como la presentación, para que las capturas tengan su alto real; al terminar, Q la cierra. Con `--ventana` la vista mide 1440×757: la barra de Chrome le quita alto y los subtítulos tapan cosas que en la presentación quedan libres.

Con `--sin-voz`, la demo toma una captura a mitad de cada frase, con su subtítulo en pantalla, y otra por cada fallo. Al final arma `demo/.registro/<fecha>/recorrido.pdf`: una captura por página con su paso, el minuto, el tamaño de la vista y la frase, y los fallos en rojo. Sirve para encontrar errores y lo que podría verse mejor sin gastar clips de voz. Las capturas no alargan las frases. Si la corrida se corta antes de armarlo, cada captura ya quedó anotada en `capturas.jsonl` y el PDF se arma con:
```bash
assessment/.venv/bin/python -c "from pathlib import Path; from demo.__main__ import armar_pdf; print(armar_pdf(Path('demo/.registro/<fecha>')))"
```

### En vivo
```bash
assessment/.venv/bin/python -m demo                          # pantalla completa, agentes MAF, voz y grabación en ~/Movies
assessment/.venv/bin/python -m demo --velocidad 1.25         # velocidad inicial: 0.75, 1 o 1.25
assessment/.venv/bin/python -m demo --motor solo-evidencia   # plan B: sin modelo ni tokens
```
Otras opciones: `--paso-a-paso` (espera «Siguiente» en cada escena), `--sin-voz` (solo subtítulos, con capturas y PDF), `--sin-grabar` y `--ventana`. Si la consola no está en marcha en `:8050`, la demo la lanza y la apaga al final.

| Tecla | Acción |
|---|---|
| Espacio o K | Pausa / continuar |
| → o N | Siguiente paso |
| `<` o `-` · `>` o `+` | Velocidad 0,75× · 1× · 1,25× |
| P | Paso a paso |
| Q dos veces | Terminar y restaurar el entorno |
| Esc | Nada: no llega a la consola, donde dos seguidos cancelarían la evaluación en vivo |

Mover el mouse muestra la barra de control. Al grabar, no lo muevas: la barra saldría en el video.

### Revisión previa: lo que comprueba antes de presentar
Consola en `:8050` · cambios sin commit en esas rutas que no dejó una demo (si los hay, se detiene antes de revertirlos: haz commit o stash) · reinicio previo (archiva corridas y revierte archivos de una demo anterior) · git limpio en `v1`, `v2`, `v3`, `Dockerfile`, `deploy` y `.github` · `v1`–`v3` compiladas para `:5080` · sesión de Azure CLI · base y escaneo de Trivy · ingreso de ACA (espera hasta 45 s, porque la app escala a cero) · Boards sin tareas de demo abiertas · respaldo del dataset de Power BI · sesión de Power BI · captura de la última corrida verde de GitHub Actions · voz. Si algo imprescindible falla, se detiene con «Revisión previa detenida: …» antes de presentar.

> En pantalla completa, Power BI se ve unos segundos antes que la consola: la demo abre el reporte en su propia pestaña para heredar la sesión, antes de que empiece la grabación.

### Al terminar (o si la cortás)
Al final, con Q dos veces, con Ctrl+C o al cerrar la ventana o la terminal, la demo detiene `:5080` y borra sus datos, archiva las corridas, revierte la remediación, manda a la papelera de Boards las tareas de la demo y repone el dataset de Power BI. Termina con «Demo lista para volver a ejecutarse.» y deja el registro de tiempos en `demo/.registro/<fecha>.json`; si algo quedó pendiente (por ejemplo, Boards no respondió), lo avisa con «!» en vez de esa línea. Con la terminal cerrada, lo que imprime la restauración queda en `demo/.registro/salida.log`.

### Presentar por Teams o Zoom
Ninguno comparte el audio del navegador por defecto: al compartir pantalla, activá **«Incluir sonido»** en Teams o **«Compartir sonido»** en Zoom, o la audiencia no oirá la narración. Con `--sin-voz` no hace falta, porque van subtítulos.

---

## 3. DESPUÉS DE LA DEMO (Cierre Comercial + Apagado Seguro a \$0.00/hora)

### Paso 3.1 — Cierre comercial sugerido antes de colgar *(30 segundos)*

> *"Para aterrizarlo en su contexto sin fricción: elijamos **una aplicación crítica** y sus **últimas dos entregas**. Medimos cuánto tiempo les toma hoy reunir la trazabilidad de punta a punta, conectamos este mismo workflow en modo lectura sobre su Boards, su pipeline y su suscripción Azure, y en dos semanas tienen su línea base objetiva de controles verificados."*

### Paso 3.2 — Qué entregar si el cliente pide material de muestra

Cada corrida que ejecutaste durante la reunión ya dejó guardados sus artefactos auditables en `assessment/runs/<id_ejecucion>/`:
- `informe.md` *(resumen ejecutivo legible para compartir en PDF/Markdown)*
- `informe.json` *(evidencia completa firmada con SHA-256, trazas de herramientas y las 8 etapas)*
- `resultados.trx` y `checkpoint_aprobacion.json`

### Paso 3.3 — Apagado seguro para cuidar tus \$200 USD de crédito *(1 minuto)*

Apenas termines la llamada:

1. **Detené el servidor web local:** presioná `Ctrl + C` en la terminal donde corre `assessment.ui`.
2. **Desactivá el ingreso público del Container App** (evita que bots en internet despierten réplicas o envíen logs, bajando tu gasto en reposo a **\$0.00/hora** sin borrar ningún recurso):

```bash
az containerapp ingress disable -g rg-jcastros-2718 -n ca-appcontratos
```

3. **Verificación rápida de que quedó en 0 réplicas y sin tráfico:**

```bash
az containerapp revision list -g rg-jcastros-2718 -n ca-appcontratos \
  --query "[].{revision:name, activa:properties.active, replicas:properties.replicas}" -o table
```
*(Deberás ver `Replicas: 0`. Tu despliegue `gpt-4.1-mini-1` en `GlobalStandard`, Log Analytics hasta 5 GB/mes, Defender Foundational CSPM y Azure Boards hasta 5 usuarios no tienen ningún cargo por hora mientras están sin uso).*
