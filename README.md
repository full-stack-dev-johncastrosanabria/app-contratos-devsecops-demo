# AppContratos
Requiere .NET SDK 10. Cada carpeta v1, v2 o v3 es un proyecto autónomo con su propia cartera local. Desde la carpeta de la versión elegida:
```sh
dotnet run --project src/Contratos --urls http://localhost:5080
```
Abrir http://localhost:5080. Para simular avisos, crear un contrato que renueve siete días después de la fecha elegida para la evaluación. Cancelarlo antes de evaluar. La bandeja local representa el envío simulado. Los avisos generados previamente se conservan como historial.

## Evidencia REN-001
El criterio exige que un contrato cancelado no genere nuevos avisos. Ejecutar desde cada versión:
```sh
dotnet test tests/Contratos.Tests --logger "trx;LogFileName=resultados.trx" --results-directory evidencia
```
- v1: 4 casos aprobados, incluido CanceladoNoGeneraAviso, vinculado a REN-001.
- v2: 3 aprobados y 1 fallo deliberado. Un cancelado a siete días recibe un aviso.
- v3: 3 aprobados sobre contratos activos. El código excluye cancelados, pero la suite carece de evidencia para REN-001.

Cada versión incluye un workflow de GitHub Actions para usarla como raíz de un repositorio. Conserva el TRX incluso si fallan pruebas. La app es local, de un solo proceso, con persistencia JSON y sin credenciales externas. Los tres proyectos son las entradas de la demo de evaluación en `assessment/`.

## Demo local de evaluación

Los comandos se ejecutan desde la raíz del ZIP extraído. Esta demo se verificó en macOS con .NET SDK 10.0.404, Python 3.14.7, xUnit 2.9.3 y el adaptador VSTest de xUnit 3.0.2. Si faltan los SDK, una opción en macOS con Homebrew es ejecutar `brew install python@3.14` y `brew install --cask dotnet-sdk`, y comprobar que `dotnet --list-sdks` incluya 10.0.x.

```sh
cd /Users/johnbenjamincastrosanabria/Developer/AppContratos
dotnet --list-sdks
python3.14 -m venv assessment/.venv
assessment/.venv/bin/python -m pip install -r assessment/requirements.txt
assessment/.venv/bin/python -m unittest discover -s assessment/tests -v
assessment/.venv/bin/python -m assessment v2 --modo solo-evidencia
assessment/.venv/bin/python -m assessment todas --modo solo-evidencia
```

La primera restauración puede requerir acceso a PyPI y NuGet. El modo **solo evidencia** es el predeterminado y funciona sin credenciales de modelo. Cada comando imprime la ruta del informe. También se puede pasar la ruta de una carpeta renombrada con la misma estructura `src/Contratos` y `tests/Contratos.Tests`. El comando `todas` sigue con v3 después del fallo esperado de xUnit en v2.

### Abrir la demo web

```sh
assessment/.venv/bin/python -m assessment.ui
```

Con el servidor en marcha, abrí [la demo local](http://127.0.0.1:8050/). Elegí una versión o las tres, seleccioná el modo y ejecutá la evaluación. Cada resultado muestra el veredicto, su explicación y los enlaces a los informes. En modo agente podés desplegar la traza de QA. El servidor escucha en la máquina local.

### Ejecutar con el agente

La plantilla selecciona Anthropic y Claude Sonnet 4.6. Si todavía no existe `assessment/.env`, copiala. Abrí el archivo, completá `ANTHROPIC_API_KEY` con una clave de Anthropic Console y guardalo. [Conector oficial de Anthropic en MAF](https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/model-providers/anthropic)

```sh
test -f assessment/.env || cp -n assessment/.env.example assessment/.env
nano assessment/.env
assessment/.venv/bin/python -m assessment v2 --modo agente
assessment/.venv/bin/python -m assessment todas --modo agente
```

Para usar Azure OpenAI, elegí `ASSESSMENT_PROVIDER=azure` y completá las tres variables `AZURE_OPENAI_*` de la plantilla. Usá un despliegue compatible con Chat Completions, llamadas a funciones y salidas estructuradas, como GPT-4.1. [Capacidades de GPT-4.1](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure)

Las variables exportadas en el entorno tienen prioridad sobre `assessment/.env`. La CLI muestra las herramientas invocadas y los informes guardan sus referencias. La evidencia consultada por las herramientas se envía al despliegue configurado. Si falta la configuración o falla el proveedor, el informe registra el estado de la investigación y conserva el veredicto local y la evidencia. El modo agente usa el SDK oficial fijado en `requirements.txt`. [WorkflowBuilder y ejecución](https://learn.microsoft.com/en-us/agent-framework/concepts/workflows/builder-and-execution?pivots=programming-language-python) · [Herramientas de función en MAF](https://learn.microsoft.com/en-us/agent-framework/agents/tools/function-tools) · [Conector oficial para Azure OpenAI](https://pypi.org/project/agent-framework-openai/1.18.2/)

### Evidencia y alcance

- `WorkflowBuilder` encadena recopilación, investigación de QA y evaluación. QA puede listar el TRX, buscar el vínculo explícito e inspeccionar la prueba y su preparación por ID. El evaluador contrasta las referencias del agente y decide de forma determinista con la captura local.
- Cada evaluación compila y ejecuta el proyecto de pruebas en un directorio nuevo bajo `assessment/runs/<id>/`. Guarda `informe.json`, `informe.md`, `dotnet-test.log`, el TRX cuando existe y los artefactos aislados de compilación. El JSON incluye el código de salida de `dotnet test`, el proyecto, el commit y el estado local del proyecto cuando Git está disponible, y los SHA-256 de los archivos de aplicación y pruebas.
- El evaluador une el resultado, la entrada y la definición TRX por `testId` y `executionId` y verifica el ensamblado xUnit de la ejecución. Las variantes de `ActivoGeneraUnSoloAviso` tienen IDs y nombres visibles distintos, como `ActivoGeneraUnSoloAviso(dias: 7)`, y comparten el nombre del método base. Para certificar REN-001, el evaluador reconoce la forma del `Fact` actual, su `Trait("Criterio", "REN-001")`, la preparación de un contrato cancelado con bandeja vacía, la invocación y `Assert.Empty`. Las teorías y otras formas de C# quedan fuera de la certificación automática de este MVP. El diagnóstico de incumplimiento exige el mensaje de colección no vacía con un aviso y la ubicación de la aserción en la pila.
- La CLI devuelve `0` cuando completa la evaluación, incluso con un incumplimiento o falta de cobertura. Devuelve `2` cuando hay diagnósticos de ejecución o falló la investigación solicitada. Un código distinto de cero de `dotnet test` se conserva y se interpreta con el TRX.

### Ejemplo de informe

Fragmento generado al evaluar v2 en modo solo evidencia.

> **INCUMPLIDO**
>
> RenovacionesTests.CanceladoNoGeneraAviso falló en Assert.Empty(datos.Avisos). El TRX registra un aviso generado.
>
> - Ejecución `e70b3e66267f482e9ae066d79cd664aa`
> - Código de salida de dotnet test · 1
> - Fuente `tests/Contratos.Tests/RenovacionesTests.cs:20`
> - Aserción en línea 26
>
> **Siguiente paso**
>
> Corregir la evaluación de renovaciones para excluir los contratos cancelados y repetir la prueba.

| Validación | Estado | Evidencia |
| --- | --- | --- |
| v1 | Observado · `VERIFICADO` | Pasaron los cuatro casos. El caso cancelado tiene vínculo explícito y pasó. |
| v2 | Observado · `INCUMPLIDO` | Pasaron tres casos y falló la aserción del caso cancelado con un aviso en el TRX. |
| v3 | Observado · `EVIDENCIA_INSUFICIENTE` | Pasaron tres casos de contratos activos. Falta el caso vinculado de cancelación. |
| Investigación MAF | Observado con HTTP simulado | MAF ejecutó las ramas paralelas (QA + SecOps) con checkpoints persistentes y validación de referencias. |
| Anthropic Claude real | Observado · `COMPLETADA` | Claude Sonnet 4.6 ejecutó las herramientas sobre `v1`, `v2` y `v3` con salidas estructuradas validadas. |
| Azure OpenAI real | Observado · `COMPLETADA` | `gpt-4.1-mini` (`GlobalStandard`) ejecutó las herramientas QA + SecOps sobre `v1`, `v2` y `v3`. |
| Ciclo DevSecOps (8 etapas) | Observado en nube real | Integra Azure Boards (`AB#1` + tareas idempotentes), GitHub PR/Actions/CodeQL, Container Apps, Defender CSPM y App Insights. |

### Aprobación humana y registro idempotente en Azure Boards

Cuando una versión queda en `INCUMPLIDO` o `EVIDENCIA_INSUFICIENTE`, el evaluador deja una `accion_propuesta` en `PENDIENTE_APROBACION` con una huella estable (`devsecops-fp-<hash>`) y guarda `checkpoint_aprobacion.json`. Podés aprobarla o descartarla desde las tarjetas de `http://127.0.0.1:8050` o desde la CLI:

```sh
assessment/.venv/bin/python -m assessment aprobar --ejecucion <id_ejecucion> --motivo "Aprobado en revisión de entrega"
assessment/.venv/bin/python -m assessment descartar --ejecucion <id_ejecucion> --motivo "Se cubrirá en el siguiente sprint"
```
Si volvés a evaluar y aprobar la misma brecha, el ejecutor detecta el tag `devsecops-fp-<hash>` mediante WIQL y **actualiza el Work Item existente en Azure Boards en lugar de duplicarlo**.
