# Instrucciones de gobernanza para GitHub Copilot · NextGen DevSecOps Assessment

Este repositorio audita entregas de software mediante evidencia determinista (`dotnet test` + TRX firmado con SHA-256) y agentes paralelos en Microsoft Agent Framework. Al sugerir o refactorizar código en Visual Studio Code o GitHub, respetá estrictamente estas reglas:

## 1. Trazabilidad obligatoria entre historias y pruebas xUnit (`C#`)
- Toda prueba que certifique un criterio de aceptación de Azure Boards (`AB#`) **debe** declarar explícitamente `[Trait("Criterio", "REN-XXX")]` (por ejemplo, `[Trait("Criterio", "REN-001")]` o `[Trait("Criterio", "REN-002")]`).
- Usá siempre fechas deterministas con `DateOnly` fijo en las pruebas (`static readonly DateOnly Hoy = new(2026, 11, 26);`). Nunca uses `DateTime.Now` ni `DateTime.UtcNow` en aserciones de dominio.
- Mantené las pruebas puras, sin directivas de preprocesador (`#if`), reflexión ni acceso a red.

## 2. Reglas del dominio de renovaciones (`src/Contratos`)
- **REN-001:** Un contrato con `Cancelado == true` jamás debe generar un `Aviso` al ejecutar `Renovaciones.Evaluar(datos, hoy)`.
- **REN-002:** Un contrato activo (`Cancelado == false`) a `30`, `7` o `1` día de su fecha de renovación debe generar exactamente un `Aviso` idempotente aunque `Renovaciones.Evaluar` se invoque múltiples veces el mismo día.
- Persistí `datos.json` únicamente mediante escritura atómica (`.tmp` + `File.Move(..., overwrite: true)`) y nunca escribas en disco cuando el endpoint devuelva un código HTTP `>= 400`.

## 3. Seguridad desde el origen y consola evaluadora (`assessment/`)
- Nunca codifiques secretos, tokens PAT, claves de API ni cadenas de conexión en código fuente, manifiestos YAML o pruebas.
- En expresiones regulares de Python (`assessment/policy.py`), evitá cuantificadores anidados ambiguos susceptibles a backtracking polinomial (`py/redos`).
- En la consola web (`assessment/static/`), respetá la Content-Security-Policy estricta (`default-src 'self'; style-src 'self'; script-src 'self'`): cero `<script>` en línea, cero atributos `style="..."` en HTML y cero dependencias de CDN externas.
