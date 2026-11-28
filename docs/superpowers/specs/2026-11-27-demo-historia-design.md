# Demo con historia — diseño (adenda)

Fecha: 27 nov 2026 · Rama: `feat/demo-automatizada`; la consola va en `feat/consola-casos`, creada desde `main`.
Amplía `2026-11-27-demo-automatizada-design.md`. Todo lo que esta adenda no menciona sigue igual: voz, controles, pantalla completa, reversibilidad, Power BI y las reglas de narración.

## Intención

Lo que pidió el usuario, en sus palabras:

- «que la demo cuente una historia»;
- «que la app no parezca una app de renovaciones sino que parezca como que se escoge el caso aún que por ahora haya solo uno»;
- «que se muestre el comportamiento de las apps v1 a v3 con datos para demostrar el bug y su solución»;
- «que todo se vea bonito, ejemplo si se va a ver un md que se vea bien con formato»;
- «me gustaría que la demo muestre un github actions»;
- «quizás algo de ci cd».

Mi lectura, que el usuario no ha confirmado: el público debe ver un caso real de punta a punta (síntoma, evidencia y solución) y entender que el evaluador sirve también para su propio caso.

## Decisiones del usuario (27 nov)

- **Se cambia la consola.** Lleva un título genérico y un selector de caso. Se trabaja en una rama propia desde `main` y solo se conserva si una nueva crítica saca al menos 34/40, la mejor nota registrada. Después de cada cambio, el usuario reinicia :8050 desde Antigravity.
- **La demostración con datos reemplaza el recorrido de las 8 etapas.** Se mantienen los 8–12 min a cualquier velocidad y se recorta lo que haga falta.
- **Trivy ya está corregido y subido a `main`** (`a1014f6`; en esta rama está copiado como `bf15ebd`). `trivy-action` queda fijada por SHA a v0.36.0. La corrida 46092876122 salió en verde en sus 7 jobs.

## Metas, no metas y anti-metas

**Metas**
- Una historia con conflicto y resolución.
- La consola se presenta como un evaluador de casos.
- El bug y su solución se ven con datos reales en las apps.
- El CI/CD real se ve en GitHub Actions.
- Todo lo que se muestra tiene formato.

**No metas**
- **Casos adicionales.** No existen y no se inventan.
- **Que el pipeline despliegue.** Hoy prueba, escanea y publica la imagen en GHCR; el despliegue en Azure Container Apps no lo hace este workflow.
- **Insertar github.com.** Responde con `X-Frame-Options: deny`.

**Anti-metas**
- **Narrar el check de v2 como prueba del bug.** Los jobs xUnit validan la evidencia esperada para cada versión (`assessment/ci.py`), así que el de v2 sale en verde precisamente porque REN-001 falla. No se narra que «debería salir en rojo».
- Dejar texto crudo en pantalla, como Markdown o JSON.
- Dejar datos, procesos o cambios de la demo al terminar.

## La historia: actos y escenas

1. **Portada.** «NextGen DevSecOps Assessment», sin «renovaciones».
2. **La pregunta.** ¿Un pipeline en verde equivale a evidencia? Se recorta.
3. **El caso.** En la consola se abre el selector y se elige «Portal de Contratos · REN-001: un contrato cancelado nunca debe recibir un aviso de renovación». Esta escena une las actuales «La consola» y «El caso».
4. **Ejecutar.** Los agentes MAF evalúan v1, v2 y v3, como hoy.
5. **Mientras corre.** Se aprovecha la espera de 150–210 s.
   - El grafo MAF, recortado.
   - **CI/CD en GitHub Actions:**
     - Se muestra una captura real de la corrida verde más reciente del pipeline en `main`.
     - El foco recorre los jobs: pruebas de v1, v2 y v3, CodeQL y Trivy, y luego la imagen OCI en GHCR.
     - La narración cuenta qué hace cada etapa y remata con que v3 sale en verde con todas sus pruebas pasando, aunque ninguna demuestra REN-001.
   - **La app con datos:**
     - Se lanza v1 en el sandbox :5080 y se ejecuta «Ejecutar simulación REN-001». El contrato cancelado no recibe aviso.
     - Luego v2, con la misma simulación. El contrato cancelado sí recibe un aviso: es el bug.
     - v3 no se muestra en la app. Su código es el de v1 y su brecha es de evidencia, no de comportamiento.
6. **El dictamen.** v1 VERIFICADO, v2 INCUMPLIDO y v3 EVIDENCIA_INSUFICIENTE. Se muestra el informe de v2 con formato, con el foco en la matriz de criterios.
7. **Momento v3 y Seguridad.** Como hoy, recortadas si el presupuesto lo exige.
8. **Gobernanza y remediación de v2.** Cambia respecto de hoy, que hace las dos sobre v3.
   - Mismo flujo, ahora sobre v2: aprobación humana en Boards, la corrección del código (`Renovaciones.cs`) como parche local y la reevaluación con «Solo evidencia».
   - Durante la reevaluación se borran los datos de v2 en el sandbox (`datos.json`, que git ignora) para que la bandeja empiece vacía. Luego v2 se relanza y la simulación ya no emite aviso: la solución, con datos.
   - v3 no se remedia. Su brecha (falta la prueba de REN-001) la cuentan las capturas de Actions, el dictamen y el «Momento v3».
9. **Valor (Power BI) y Cierre.** El selector de caso vuelve a verse: «el siguiente caso es el suyo».

Se elimina la escena «Las 8 etapas».

## Cómo se construye

### Consola

Rama `feat/consola-casos`, con crítica ≥ 34/40.

- **Título.** El título y el `<title>` pasan a ser genéricos («Evaluador de entregas»).
- **Selector de caso.** Va junto al título. La lista de casos está en un solo lugar de `app.js` y hoy tiene uno. La regla que se ve sale del caso elegido.
- **Agente.** «QA de renovaciones» (`workflow.py`) pasa a llamarse «QA funcional».
- **Corrida de CI.** La evidencia de CI toma la corrida del workflow del pipeline: la del commit evaluado si existe y, si no, la última de ese workflow en `main`. Hoy toma la última de cualquier workflow, Dependabot incluido. Se cubre con una prueba.
- **Crítica.** Se usa la crítica de impeccable, con la misma rúbrica sobre 40 de R6–R8. Se corre una vez, al final del lote de la consola, y solo se hace commit si saca ≥ 34/40.
- **Integración.** Si el lote pasa, `feat/consola-casos` se integra en `feat/demo-automatizada` con un merge local; `main` no se toca. Si no pasa, se descarta y la demo usa la consola actual con una slide «Elige el caso». Habrá un solo guion, decidido en ese momento.

### Demo

- **Capturas de GitHub Actions.**
  - Se toman en la revisión previa con Chrome sin ventana; la página es pública y no necesita sesión.
  - Se usa la corrida verde más reciente del pipeline en `main`.
  - Se guardan en `demo/.registro` junto con la caja de cada job, que sirve para el foco.
  - Si no hay una corrida verde, la revisión previa aborta.
- **Plantillas nuevas de slide.**
  - «captura»: una imagen con foco por caja.
  - «app»: un iframe de `http://127.0.0.1:5080` con marco de navegador y etiqueta de versión. Igual que el de Power BI, no recibe punteros ni foco.
- **Clics dentro del portal.** Se hacen con eventos del propio frame para no quitarle el teclado al director. El foco y el cursor del director aceptan una caja en coordenadas de página.
- **Sandbox.**
  - Se lanza desde la propia consola (Gestionar :5080 → Iniciar vN), y la demo espera a que el indicador marque activo.
  - La revisión previa compila v1–v3 para que cada arranque tarde segundos.
  - Las pruebas del evaluador compilan con `--artifacts-path`, así que no chocan con el `dotnet run` del sandbox.
- **Informe con formato.**
  - Un conversor pequeño de Markdown a HTML en `demo/`, que cubre lo que usa `informe.md`: títulos, tablas, listas, negrita y código. Escapa el HTML.
  - Se muestra con la plantilla «documento».
  - La descarga de la consola sigue siendo el `.md`.
- **Pasada visual.**
  - En el ensayo se captura cada superficie que ve el público y se corrige cualquier texto crudo que aparezca.
  - Cuenta como texto crudo el Markdown o el JSON que se muestran como texto plano. Hoy la consola no muestra JSON: sus `JSON.stringify` solo arman peticiones.
  - El código y los parches en monoespaciado ya tienen su formato correcto. Si en la pasada se ven planos, se les da color de sintaxis dentro del lote de la consola.
- **Reversibilidad.**
  - La revisión previa empieza con el sandbox sin datos: borra los `datos.json`, igual que el paso del sandbox del reinicio.
  - El reinicio con `sandbox: true` ya borra `datos.json`, y con `codigo: true` restaura el código, incluido el parche de v2.
  - El ensayo verifica que git queda limpio y que no queda nada escuchando en :5080. Si el reinicio en proceso no puede detener el sandbox de la consola, se usa su endpoint.
- **Presupuesto.**
  - Los límites siguen igual: a 0,75× sin opcionales ≤ 720 s, y a 1,25× con opcionales ≥ 480 s.
  - La voz total queda en ≤ 11.500 caracteres; quedan 13.548 en ElevenLabs.

## Lo que queda al constructor

- **Narración:**
  - los textos exactos, en tono consultivo y hablando de «ustedes»;
  - sin texto libre de los agentes;
  - sin métricas inventadas;
  - cada afirmación de CI/CD comprobada contra la corrida real y la evidencia de las etapas 4 y 5.
- Los recortes concretos para cumplir el presupuesto.
- Los selectores y los tiempos de espera.
- El estilo de las plantillas nuevas, dentro de la identidad actual del director.

## Riesgos

- **CPU.** El sandbox corre mientras los agentes ejecutan `dotnet test`. Si la evaluación se alarga, la espera lo absorbe hasta `max_s`.
- **Captura estática.** La captura de Actions muestra la corrida tal como estaba en la revisión previa.
- **Nota de la crítica.** Si la consola baja de 34/40, el lote se descarta y la demo usa la consola actual con una slide «Elige el caso».
