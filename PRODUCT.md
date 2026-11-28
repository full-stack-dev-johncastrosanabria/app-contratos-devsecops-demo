# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Ingeniería ejecutiva y gobierno técnico (VP de Ingeniería, Arquitectos Cloud, QA Leads y CISOs):** evalúan en sesiones en vivo o revisiones de entrega si una versión candidata cumple reglas críticas de negocio, seguridad en origen y postura cloud antes o después de un despliegue.
- **Ingenieros de QA y SecOps:** inspeccionan trazabilidad extremo a extremo entre historias de usuario, código fuente C#, reportes xUnit TRX, análisis estático y telemetría operativa antes de aprobar o descartar tareas de remediación.

## Product Purpose

**NextGen DevSecOps Assessment** audita y certifica de forma continua entregas de software a lo largo de las 8 etapas del ciclo de vida DevSecOps (Planificar, Crear código, Asegurar desde el origen, Integrar y probar, Desplegar, Operar, Observar y aprender, Optimizar con IA).

El éxito del producto consiste en demostrar en segundos —con trazabilidad determinista verificada por SHA-256— la diferencia entre una entrega conforme (`VERIFICADO`), una regresión funcional (`INCUMPLIDO`) y un pipeline falsamente en verde que carece de cobertura sobre la regla crítica de negocio (`EVIDENCIA_INSUFICIENTE`), gobernando las acciones resultantes en Azure Boards mediante aprobación humana idempotente.

## Positioning

Dos agentes especializados sobre **Microsoft Agent Framework (MAF)** y **Azure AI Foundry** investigan en paralelo (*QA/Trazabilidad* y *Seguridad/Operación*), pero nunca inventan el dictamen: una política determinista versionada (`REN-001.v2`) contrasta cada referencia contra el árbol fuente y el XML del TRX antes de emitir el veredicto, y sincroniza tareas en Azure Boards con huella idempotente WIQL (`devsecops-fp-...`) únicamente tras confirmación humana (HITL).

## Operating Context

- **Superficie principal remodelada:** Consola web local del evaluador servida en `http://127.0.0.1:8050` (`assessment/static/index.html`, `assessment/static/style.css`, `assessment/static/app.js`) por `assessment/ui.py`.
- **Puente interoperable:** lanza y detiene bajo demanda instancias reales de las tres versiones sujetas a prueba (`v1`, `v2`, `v3`) en `http://127.0.0.1:5080`.
- **Ecosistema conectado:** enlaza evidencia real con Azure Boards (`AB#1` multi-criterio e ítems hijos), GitHub (`PR #1`, GitHub Copilot en VS Code, GitHub Actions, Azure Pipelines espejo, CodeQL, Dependabot, Secret Scanning y SBOM SPDX), Azure Container Apps (`ca-appcontratos`) + postura Kubernetes (`deploy/aks/`), Microsoft Defender for Cloud (Secure Score + Managed Identity), Application Insights, conectores tabulares para Power BI / Microsoft Fabric y manifiesto OpenAPI para Microsoft Security Copilot.
- **Uso habitual:** demostraciones ejecutivas repetibles en vivo (con reinicio y restauración 100 % reversibles entre sesiones, zoom de presentación y lectura rápida de estados comparados) y auditorías técnicas locales con o sin consumo de tokens (`agente` vs. `solo-evidencia`).

## Capabilities and Constraints

- **Política de seguridad HTTP estricta (CSP):** `assessment/ui.py` sirve recursos con `default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'`. No se permiten hojas de estilo inline, scripts inline ni carga de fuentes o iconos desde CDNs externos.
- **Contratos HTTP y pruebas automatizadas:** deben preservarse intactos los endpoints locales (`GET /`, `GET /api/ecosistema`, `POST /api/evaluar`, `POST /api/acciones`, `POST /api/sandbox`, `GET /informes/<id>/<archivo>`) y el contrato verificado en `assessment/tests/test_ui.py` (incluyendo el texto `Evaluador de entregas` en `GET /`).
- **Alcance confirmado:** remodelación focalizada exclusivamente en la Consola Evaluador principal (`:8050`); los portales sujetos de prueba (`v1`, `v2`, `v3` en `:5080`) se conservan sin cambios de diseño.
- **Idioma:** español técnico claro y consistente en toda la interfaz, etiquetas, estados y mensajes de recuperación.

## Brand Commitments

- **Nombre del producto:** `NextGen DevSecOps Assessment`.
- **Símbolo de marca oficial:** monograma vectorial **«N» de nodos conectados** sobre fondo azul marino (tres vértices blancos unidos por aristas azul aciano y nodo superior derecho activo en cian con nodo satélite diagonal), incorporado en la cabecera y el favicon (`assessment/static/favicon.svg` y `assessment/static/brand-mark.png`).
- **Identidad cromática vinculante:** azul institucional únicamente en tema claro (superficies en blanco y azul hielo con cabecera y rieles estructurales en azul marino profundo). No se implementa modo oscuro.

## Evidence on Hand

- Tres versiones reales evaluables en el repositorio: `v1` (`VERIFICADO`, 4 pruebas aprobadas con vínculo explícito `REN-001`), `v2` (`INCUMPLIDO`, fallo funcional deliberado en contratos cancelados) y `v3` (`EVIDENCIA_INSUFICIENTE`, 3 pruebas aprobadas solo sobre contratos activos).
- Historial real de ejecuciones auditables bajo `assessment/runs/<id>/` (`informe.md`, `informe.json`, `resultados.trx`, `dotnet-test.log`, `checkpoint_aprobacion.json`).
- Integraciones reales configurables con Azure Boards (`AB#1`), GitHub (`full-stack-dev-johncastrosanabria/nextgen-devsecops-assessment`), Azure Container Apps (`ca-appcontratos`), Defender CSPM y Application Insights. No deben fabricarse métricas comerciales, clientes ficticios ni certificaciones externas inexistentes.

## Product Principles

1. **Evidencia verificable antes que opinión generativa:** la interfaz distingue siempre entre la explicación asistida por agentes y el veredicto determinista respaldado por artefactos auditables.
2. **Contraste inmediato entre las tres entregas:** un líder técnico debe distinguir en un vistazo por qué `v1` aprueba, `v2` falla y `v3` queda retenida pese a tener pruebas en verde.
3. **Trazabilidad de 8 etapas con alcance explícito:** cada hallazgo comunica con claridad si pertenece a la `version` (código), al `recurso` (contenedor) o al `ambiente` (suscripción/telemetría).
4. **Gobernanza humana deliberada:** ninguna tarea entra al backlog sin contexto visible, huella de idempotencia explícita y confirmación o descarte consciente.

## Accessibility & Inclusion

- Cumplimiento mínimo WCAG 2.1 AA en contraste (≥ 4.5:1 para texto normal, ≥ 3:1 para texto grande y controles), navegación completa por teclado, foco visible de alto contraste, estados no dependientes únicamente del color y soporte respetuoso de `prefers-reduced-motion`.
