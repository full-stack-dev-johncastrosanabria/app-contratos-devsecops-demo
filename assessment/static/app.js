"use strict";

const form = document.querySelector("#controls");
const results = document.querySelector("#results");
const status = document.querySelector("#status");
const statusBanner = document.querySelector("#status-banner");
const runBtn = document.querySelector("#run-btn");
const cancelBtn = document.querySelector("#cancel-btn");
const filterDiffBtn = document.querySelector("#filter-diff-btn");
const loadLatestBtn = document.querySelector("#load-latest");
const helpToggleBtn = document.querySelector("#help-toggle-btn");
const helpDrawer = document.querySelector("#help-drawer");
const helpCloseBtn = document.querySelector("#help-close-btn");
const demoResetToggleBtn = document.querySelector("#demo-reset-toggle-btn");
const demoResetPanel = document.querySelector("#demo-reset-panel");
const demoResetCloseBtn = document.querySelector("#demo-reset-close-btn");
const demoResetApplyBtn = document.querySelector("#demo-reset-apply-btn");
const demoRestoreBtn = document.querySelector("#demo-restore-btn");
const resetRunsChk = document.querySelector("#reset-runs-chk");
const resetSandboxChk = document.querySelector("#reset-sandbox-chk");
const resetBoardsChk = document.querySelector("#reset-boards-chk");
const resetCodePrsChk = document.querySelector("#reset-code-prs-chk");
const openPowerBiWebBtn = document.querySelector("#open-powerbi-web-btn");

const sandboxPill = document.querySelector("#sandbox-pill");
const sandboxText = document.querySelector("#sandbox-text");
const sandboxOpenLink = document.querySelector("#sandbox-open-link");
const stopSandboxBtn = document.querySelector("#stop-sandbox");
const sandboxAlertWrap = document.querySelector("#sandbox-alert-wrap");
const sandboxAlertMsg = document.querySelector("#sandbox-alert-msg");
const sandboxRetryBtn = document.querySelector("#sandbox-retry-btn");

const stageInspector = document.querySelector("#stage-inspector");
const stageInspectorTitle = document.querySelector("#stage-inspector-title");
const stageInspectorMeta = document.querySelector("#stage-inspector-meta");
const stageInspectorBody = document.querySelector("#stage-inspector-body");
const inspectorVersionTabs = document.querySelector("#inspector-version-tabs");
const inspectorPrevBtn = document.querySelector("#inspector-prev-btn");
const inspectorNextBtn = document.querySelector("#inspector-next-btn");
const inspectorCloseBtn = document.querySelector("#inspector-close-btn");

const versions = ["v1", "v2", "v3"];
// Neutral identity only: the verdict comes from the run, never from the card.
// Demo scenario each folder was built to represent; shown as intent, never as the verdict.
const versionRoles = {
  v1: "Escenario: código excluye cancelados · con prueba REN-001",
  v2: "Escenario: regresión funcional en cancelados",
  v3: "Escenario: suite en verde sin prueba vinculada a REN-001",
};

const STAGE_CATALOG = [
  {
    numero: 1, bloque: "DevSec", etapa: "Planificar", herramienta: "Azure Boards",
    pregunta: "¿Qué debía resolver esta entrega y bajo qué criterios formales se acepta?",
    descripcion: "Audita la historia de usuario en Azure Boards (AB#1) y sus criterios estructurados (REN-001, REN-002).",
  },
  {
    numero: 2, bloque: "DevSec", etapa: "Crear código", herramienta: "GitHub + VS Code + Copilot",
    pregunta: "¿Qué cambio implementó la historia y bajo qué reglas de autoría se integró?",
    descripcion: "Conecta el commit evaluado con el Pull Request en GitHub, vínculo AB#1 y gobernanza de GitHub Copilot en VS Code.",
  },
  {
    numero: 3, bloque: "DevSec", etapa: "Asegurar origen", herramienta: "SonarQube · Trivy · CodeQL · Dependabot",
    pregunta: "¿Qué vulnerabilidades reportan SonarQube, Trivy, CodeQL y Dependabot sobre la entrega?",
    descripcion: "Integra Quality Gate y métricas de SonarQube Cloud, escaneo Trivy (IaC/contenedor/SCA), CodeQL, Dependabot y SBOM SPDX.",
  },
  {
    numero: 4, bloque: "DevSec", etapa: "Integrar y probar", herramienta: "Azure Pipelines + Actions + xUnit",
    pregunta: "¿Qué pruebas pasaron y cuáles certifican explícitamente los criterios de aceptación?",
    descripcion: "Cruza el XML del TRX contra la sintaxis C#, evalúa la matriz multi-criterio y verifica pipelines CI/CD.",
  },
  {
    numero: 5, bloque: "CloudOps", etapa: "Desplegar", herramienta: "Container Apps + AKS Ready",
    pregunta: "¿Qué artefacto inmutable y postura cloud-native respaldan el despliegue?",
    descripcion: "Verifica la revisión activa en Azure Container Apps y audita los controles de endurecimiento Kubernetes en deploy/aks/.",
  },
  {
    numero: 6, bloque: "CloudOps", etapa: "Operar", herramienta: "Defender for Cloud",
    pregunta: "¿Cuál es el puntaje de postura CSPM y existen brechas en el recurso desplegado?",
    descripcion: "Consulta Secure Score y evaluaciones de Microsoft Defender en Resource Graph, HTTPS exclusivo y Managed Identity.",
  },
  {
    numero: 7, bloque: "CloudOps", etapa: "Observar y aprender", herramienta: "Monitor · App Insights · Power BI",
    pregunta: "¿Cambió la tasa de errores 5xx frente a la línea base y qué reflejan los KPIs en Power BI?",
    descripcion: "Compara telemetría KQL reciente vs línea base en Log Analytics y alimenta datasets para Power BI y Fabric.",
  },
  {
    numero: 8, bloque: "CloudOps", etapa: "Optimizar con IA", herramienta: "Fabric · AI Foundry · Security Copilot",
    pregunta: "¿Qué remediación o cierre de ciclo proponemos con trazabilidad e idempotencia?",
    descripcion: "Integra remediación asistida por IA, manifiesto OpenAPI para Security Copilot y cierre idempotente en Azure Boards.",
  },
];

// One vocabulary for every stage state; backend enums never reach the screen.
const STATE_LABELS = {
  verificado: "Verificado",
  incumplido: "Incumplido",
  pendiente: "Sin confirmar",
  atencion: "Atención requerida",
  informativo: "Informativo",
};

const STATE_BADGE = {
  verificado: "pass",
  incumplido: "fail",
  pendiente: "pending",
  atencion: "attention",
  informativo: "idle",
};

// Pips carry shape as well as colour (WCAG 1.4.1).
const PIP_GLYPHS = {
  verificado: "pass",
  incumplido: "fail",
  pendiente: "dots",
  atencion: "bang",
  informativo: "dash",
};

const ENUM_TEXT = {
  EVIDENCIA_INSUFICIENTE: "Evidencia insuficiente",
  INCUMPLIDO: "Incumplido",
  VERIFICADO: "Verificado",
  PENDIENTE_APROBACION: "Pendiente de aprobación",
  LISTA_PARA_CERRAR: "Lista para cierre en Boards",
  CERRADA_VERIFICADA: "Cerrada y verificada",
  APROBADA: "Aprobada",
  DESCARTADA: "Descartada",
  COMPLETADA: "Completada",
  SOLO_EVIDENCIA: "Solo evidencia",
  NO_SOLICITADA: "No solicitada",
};

function humanize(text) {
  return String(text ?? "")
    .replace(/\b[A-Z][A-Z_]{4,}\b/g, (m) => ENUM_TEXT[m] || m)
    .replace(/\b(\d+) observación\(es\)/g, (_, n) => `${n} ${n === "1" ? "observación" : "observaciones"}`);
}

const SCOPE_LABELS = { version: "versión", recurso: "recurso", ambiente: "ambiente" };

// Severity gets its own scale so an "Alta" finding never looks like an informative note.
function severityLevel(raw) {
  const v = String(raw || "").toLowerCase();
  if (v.startsWith("cr") || v === "alta" || v === "high") return "high";
  if (v === "media" || v === "medium") return "medium";
  if (v === "baja" || v === "low") return "low";
  return "info";
}

function highFindings(report) {
  return (report?.investigacion_secops?.hallazgos || []).filter((h) => severityLevel(h.severidad) === "high").length;
}

// "CanceladoNoGeneraAviso" -> "cancelado no genera aviso", for readers who do not read C#.
const testWords = (name) => name.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();

// "RenovacionesTests.CanceladoNoGeneraAviso evaluó…" → "La prueba «cancelado no genera aviso» evaluó…"
function readableReason(text) {
  const out = String(text || "").replace(/\b[A-Z]\w*Tests\.([A-Z]\w+)\b/g, (_, name) => `la prueba «${testWords(name)}»`);
  return out.charAt(0).toUpperCase() + out.slice(1);
}

// Facts an "Informativo" stage should not bury: open SAST alerts, a high 5xx rate with no baseline.
function stageNote(stage) {
  const datos = stage?.datos || {};
  if (stage?.numero === 3) {
    const open = Number(datos["Alertas SAST abiertas"]);
    if (open > 0) return `${open} alertas SAST abiertas · fuera del alcance de REN-001: revísalas antes de desplegar.`;
  }
  if (stage?.numero === 5 && datos["Versión desplegada"] && datos["Versión evaluada"]) {
    const deployed = datos["Versión desplegada"];
    if (deployed !== datos["Versión evaluada"]) return `Desplegada en Azure: ${deployed}, no esta entrega (${datos["Versión evaluada"]}).`;
    return datos["Cambios locales"] === "Sí"
      ? `Desplegada en Azure: ${deployed}, pero el repositorio tiene cambios locales sin publicar: no se puede confirmar que sea el mismo código.`
      : null;
  }
  if (stage?.numero === 7) {
    const pct = Number(String(datos["Errores servidor (5xx)"] || "").match(/([\d.]+)%/)?.[1]);
    if (pct >= 5) return `Tasa 5xx del ${pct} % sin línea base previa al despliegue: esta corrida no puede responder si empeoró.`;
  }
  return null;
}

// The state already shows as a badge or tag; drop it from the start of a summary.
const stripState = (text) => humanize(text).replace(/^(Verificado|Incumplido|Evidencia insuficiente|Sin confirmar)\s·\s/, "");

function stageName(numero, fallback) {
  return STAGE_CATALOG.find((m) => m.numero === numero)?.etapa || fallback;
}

const STATE_RANK = {
  incumplido: 4,
  atencion: 3,
  pendiente: 2,
  verificado: 1,
  informativo: 0,
};

const VERDICT_META = {
  VERIFICADO: { state: "pass", label: "Verificado" },
  INCUMPLIDO: { state: "fail", label: "Incumplido" },
  EVIDENCIA_INSUFICIENTE: { state: "unknown", label: "Evidencia insuficiente" },
};

const OUTCOME_LABELS = {
  Passed: ["aprobada", "aprobadas"],
  Failed: ["fallida", "fallidas"],
  NotExecuted: ["omitida", "omitidas"],
};

const TOOL_LABELS = {
  listar_resultados: "QA · Listó ejecuciones individuales del TRX",
  buscar_pruebas_vinculadas: "QA · Buscó pruebas marcadas con Trait REN-001",
  inspeccionar_prueba: "QA · Inspeccionó el código C# y la aserción de la prueba",
  obtener_historia_boards: "QA · Consultó historia y criterios en Azure Boards",
  consultar_cambio_github: "QA · Consultó Pull Request y pipeline en GitHub",
  consultar_seguridad_origen: "SecOps · Consultó SonarQube, CodeQL y Dependabot",
  consultar_despliegue_y_defender: "SecOps · Consultó Container App y Defender CSPM",
  consultar_telemetria_appinsights: "SecOps · Consultó métricas KQL en Application Insights",
};

const FIELD_LABELS = {
  historia: "Historia de usuario",
  historia_id: "ID de historia",
  referencia: "Referencia Boards",
  estado: "Estado",
  titulo: "Título",
  criterios: "Criterios de aceptación",
  repositorio: "Repositorio GitHub",
  pull_request: "Pull Request",
  estado_pr: "Estado del PR",
  vinculos_boards: "Vínculos Boards",
  pipeline_run: "Ejecución CI",
  conclusion_ci: "Conclusión CI",
  dependabot: "Dependabot",
  codeql_estado: "Estado CodeQL",
  alertas_abiertas: "Alertas abiertas",
  suite_xunit: "Suite xUnit",
  casos_aprobados: "Casos aprobados",
  casos_fallidos: "Casos fallidos",
  vinculos_ren001: "Vínculos REN-001",
  politica: "Política aplicada",
  recurso: "Recurso cloud",
  grupo_recursos: "Grupo de recursos",
  revision_activa: "Revisión activa",
  version_desplegada: "Versión desplegada",
  commit_desplegado: "Commit desplegado",
  https_exclusivo: "HTTPS exclusivo",
  identidad_administrada: "Identidad administrada",
  evaluaciones_rg: "Evaluaciones Defender",
  no_saludables: "Recursos con alerta",
  ventana: "Ventana observada",
  total_solicitudes: "Solicitudes medidas",
  fallos_5xx: "Errores 5xx",
  errores_4xx: "Errores 4xx",
  tasa_error_pct: "Tasa de fallo 5xx",
  latencia_promedio_ms: "Latencia promedio",
  accion_estado: "Estado de acción",
  fingerprint: "Huella WIQL",
  tag_idempotencia: "Etiqueta de idempotencia",
  work_item: "Tarea sincronizada",
};

const cards = new Map();
const reportsByVersion = new Map();
const provenanceByVersion = new Map();

let cachedLatest = {};
let activeRemediationState = { parches_locales: {}, prs_efimeros: {} };
let vulnerabilitiesByVersion = {};
let sonarCloudCache = null;
let selectedVulnForStage8 = "SEC-CI-001";
let activeController = null;
let filterDiffOnly = false;
let inspectedStage = null;
let inspectedVersion = null;
let activeDossier = null;
let lastSandboxAttempt = null;
let sandboxBusy = false;
let escArmedUntil = 0;
const SHORTCUTS_KEY = "nextgen.atajos";
let shortcutsEnabled = true;
try {
  shortcutsEnabled = localStorage.getItem(SHORTCUTS_KEY) !== "off";
} catch {
  // Storage blocked (private mode or site-data policy): keep shortcuts on for this visit.
}
let helpOrigin = null;
let helpReturnY = 0;

const ledger = document.querySelector("#ledger");
const ledgerHead = document.querySelector("#ledger-head");
const ledgerFoot = document.querySelector("#ledger-foot");
const ledgerBodies = { DevSec: document.querySelector("#ledger-devsec"), CloudOps: document.querySelector("#ledger-cloudops") };
const ledgerHubCell = document.querySelector("#ledger-hub-cell");
const ledgerHeadline = document.querySelector("#ledger-headline");
const ledgerFilterNote = document.querySelector("#ledger-filter-note");
const dossierTabs = document.querySelector("#dossier-tabs");
const ledgerPin = document.querySelector("#ledger-pin");
const deckVerdict = document.querySelector("#deck-verdict");
const runBtnLabel = runBtn.querySelector("span");
const hubLine = document.querySelector("#hub-line");
const hubLineDefault = hubLine.textContent;
const announcer = document.querySelector("#announcer");
const shortcutsToggle = document.querySelector("#shortcuts-toggle");
const sandboxToggle = document.querySelector("#sandbox-toggle");
const sandboxBar = document.querySelector(".sandbox-bar");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const EASE_OUT_EXPO = "cubic-bezier(0.16, 1, 0.3, 1)";

// Restarts a one-shot CSS animation class; the timer outlives the longest keyframe set.
function replayClass(node, className, durationMs) {
  node.classList.remove(className);
  void node.offsetWidth;
  node.classList.add(className);
  clearTimeout(node[`_${className}Timer`]);
  node[`_${className}Timer`] = setTimeout(() => node.classList.remove(className), durationMs);
}

function animateIn(node, { dx = 0, dy = 4, delay = 0, duration = 240 } = {}) {
  if (!node.animate) return;
  const frames = reducedMotion.matches
    ? [{ opacity: 0.4 }, { opacity: 1 }]
    : [{ opacity: 0, transform: `translate(${dx}px, ${dy}px)` }, { opacity: 1, transform: "none" }];
  node.animate(frames, { duration, delay, easing: EASE_OUT_EXPO, fill: "backwards" });
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return { error: `El servidor local respondió ${response.status} sin un cuerpo JSON válido.` };
  }
}

// fetch() rejects with a TypeError (English, browser-specific text) when the local server is unreachable.
function describeFetchError(err, fallback) {
  if (err instanceof TypeError) {
    return `${fallback} No hay conexión con el servidor local del evaluador: confirma que «python -m assessment.ui» sigue en ejecución y vuelve a intentarlo.`;
  }
  return err?.message || fallback;
}

function setRunning(running) {
  ledger.dataset.running = String(running);
  runBtn.dataset.busy = String(running);
  runBtnLabel.textContent = running ? "Evaluando…" : "Ejecutar evaluación";
  for (const btn of document.querySelectorAll("[data-eval], [data-launch]")) btn.disabled = running;
  if (!running) {
    clearInterval(markRunningVersion.timer);
    delete ledger.dataset.runningVersion;
    hubLine.textContent = hubLineDefault;
  }
}

// The ledger names the delivery in flight: its column head ticks and the interchange states it.
function markRunningVersion(version, index, total) {
  ledger.dataset.runningVersion = version;
  const started = Date.now();
  const chip = cards.get(version)?.querySelector(".provenance-chip");
  const tick = () => {
    const secs = Math.floor((Date.now() - started) / 1000);
    const clock = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
    hubLine.textContent = `Evaluando ${version} · ${index + 1} de ${total} · ${clock}`;
    if (chip && cards.get(version).dataset.verdict === "busy") {
      chip.textContent = `Ejecutando ahora · ${clock} · compilación, xUnit${form.elements.modo.value === "agente" ? " y agentes" : ""}`;
      const head = ledgerHead.querySelector(`[data-ver="${version}"] .ver-prov`);
      if (head) head.textContent = `Ejecutando ahora · ${clock}`;
    }
  };
  clearInterval(markRunningVersion.timer);
  tick();
  markRunningVersion.timer = setInterval(tick, 1000);
}

// Transient confirmations go to a polite screen-reader region; the status banner keeps provenance.
function announce(message) {
  announcer.textContent = "";
  requestAnimationFrame(() => { announcer.textContent = message; });
}

function svgIcon(kind, size = 14) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.85");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");

  const paths = {
    pass: ["M3 8.5 6.4 12 13 4.5"],
    fail: ["M4.2 4.2 11.8 11.8", "M11.8 4.2 4.2 11.8"],
    warn: ["M8 2.2 14.2 13.2H1.8L8 2.2Z", "M8 6.4v3.2", "M8 11.5h.01"],
    info: ["M8 2a6 6 0 1 0 0 12A6 6 0 0 0 8 2Z", "M8 7.2v3.8", "M8 4.9h.01"],
    chevron: ["M4.5 6.2 8 9.8l3.5-3.6"],
    copy: ["M6 5.5h6.5v8H6z", "M3.5 10.5v-8H10"],
    ext: ["M6 3.5H3.5v9h9V10", "M9.5 3.5h3v3", "M12.5 3.5 7.5 8.5"],
    play: ["M5 3.5 12.5 8 5 12.5V3.5Z"],
    doc: ["M4 2.5h5.5L12.5 5.5v8H4z", "M9.2 2.5v3.2h3.3"],
    question: ["M5.9 5.9a2.2 2.2 0 1 1 3.1 2c-.6.3-1 .8-1 1.5v.3", "M8 12.3h.01"],
    dots: ["M4 8h.01", "M8 8h.01", "M12 8h.01"],
    bang: ["M8 3.4v5.8", "M8 12.4h.01"],
    dash: ["M4.4 8h7.2"],
  };

  if (kind === "dots") svg.setAttribute("stroke-width", "3");
  for (const d of paths[kind] || paths.info) {
    const p = document.createElementNS(ns, "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}

function stateToIconKind(state) {
  if (state === "verificado" || state === "pass" || state === "Passed") return "pass";
  if (state === "incumplido" || state === "fail" || state === "error" || state === "Failed") return "fail";
  if (state === "pendiente" || state === "pending") return "dots";
  if (state === "unknown") return "question";
  if (state === "atencion") return "bang";
  if (state === "informativo") return "dash";
  return "info";
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function setStatus(message, tone = "idle") {
  status.textContent = message;
  statusBanner.dataset.tone = tone;
}

function formatTimestamp(ms) {
  if (!ms) return "";
  try {
    return new Intl.DateTimeFormat("es", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "short",
    }).format(new Date(ms));
  } catch {
    return "";
  }
}

function formatFieldKey(rawKey) {
  if (FIELD_LABELS[rawKey]) return FIELD_LABELS[rawKey];
  return String(rawKey)
    .replace(/_/g, " ")
    .replace(/^\w/, (ch) => ch.toUpperCase());
}

function formatFieldValue(key, val) {
  // Python/JSON nulls can arrive serialized as text from the evidence collectors.
  if (val === null || val === undefined || val === "" || val === "None" || val === "null") return "No registrado";
  if (typeof val === "boolean") return val ? "Sí" : "No";
  if (Array.isArray(val)) return val.length ? val.join(", ") : "Ninguno";
  if (key.endsWith("_pct")) return `${val} %`;
  if (key.endsWith("_ms")) return `${val} ms`;
  if (key.includes("commit") && typeof val === "string" && val.length > 12) return val.slice(0, 10);
  return humanize(val);
}

async function copyTextWithFeedback(button, text, originalLabel) {
  try {
    await navigator.clipboard.writeText(text);
    const labelSpan = button.querySelector("span") || button;
    const originalAria = button.getAttribute("aria-label");
    // Hold the width so "Copiado" does not reflow the governance header.
    button.style.minInlineSize = `${button.offsetWidth}px`;
    labelSpan.textContent = "Copiado";
    button.setAttribute("aria-label", `Copiado: ${text}`);
    button.querySelector("svg")?.replaceWith(svgIcon("pass", 13));
    button.classList.add("is-copied");
    announce(`Copiado: ${text}`);
    clearTimeout(button._copyTimer);
    button._copyTimer = setTimeout(() => {
      labelSpan.textContent = originalLabel;
      button.setAttribute("aria-label", originalAria);
      button.querySelector("svg")?.replaceWith(svgIcon("copy", 13));
      button.classList.remove("is-copied");
    }, 1600);
  } catch {
    // Keep the value next to the control that failed instead of in an off-screen banner.
    let field = button.nextElementSibling?.classList.contains("copy-fallback") ? button.nextElementSibling : null;
    if (!field) {
      field = document.createElement("input");
      field.className = "copy-fallback";
      field.readOnly = true;
      field.setAttribute("aria-label", "Valor para copiar manualmente");
      button.after(field);
    }
    field.value = text;
    field.focus();
    field.select();
    announce("El navegador bloqueó el portapapeles: el valor está seleccionado junto al botón; cópialo con Cmd o Ctrl + C.");
  }
}

function createCopyButton(value, displayText, ariaLabel) {
  const btn = element("button", null, "copy-btn");
  btn.type = "button";
  btn.setAttribute("aria-label", ariaLabel);
  btn.append(svgIcon("copy", 13), element("span", displayText));
  btn.addEventListener("click", () => copyTextWithFeedback(btn, value, displayText));
  return btn;
}

// Invoker Commands (--copy) for code blocks with live-region bubble outside the button.
const copyTimers = new WeakMap();
let lastCopyAnnouncement = "";

function reportBlockCopy(button, ok) {
  const tip = button.nextElementSibling;
  clearTimeout(copyTimers.get(button));
  button.removeAttribute("data-copied");
  button.removeAttribute("data-failed");
  let message = ok ? "Copiado" : "Error al copiar";
  if (message === lastCopyAnnouncement) message += "\u00A0";
  lastCopyAnnouncement = message;
  if (tip) tip.textContent = "";
  const iconSlot = button.querySelector(".icon");
  if (iconSlot) iconSlot.replaceChildren(svgIcon(ok ? "pass" : "fail", 13));
  void button.offsetWidth;
  button.setAttribute(ok ? "data-copied" : "data-failed", "");
  if (tip) requestAnimationFrame(() => { tip.textContent = message; });
  copyTimers.set(button, setTimeout(() => {
    button.removeAttribute("data-copied");
    button.removeAttribute("data-failed");
    if (iconSlot) iconSlot.replaceChildren(svgIcon("copy", 13));
    if (tip) tip.textContent = "";
  }, 2000));
}

async function copyTargetElement(button, target) {
  const text = target.matches("input, textarea") ? target.value : target.innerText.trim();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    reportBlockCopy(button, true);
  } catch {
    reportBlockCopy(button, false);
  }
}

if ("CommandEvent" in window) {
  document.addEventListener("command", (event) => {
    if (event.command.startsWith("--copy") && event.target) {
      copyTargetElement(event.source, event.target);
    }
  }, true);
} else {
  document.addEventListener("click", (event) => {
    if (event.defaultPrevented) return;
    const button = event.target.closest('button[command^="--copy"]');
    if (!button) return;
    const target = document.getElementById(button.getAttribute("commandfor"));
    if (target) copyTargetElement(button, target);
  });
}

function renderValueKpis(kpis) {
  if (!kpis) return;
  const set = (sel, text) => {
    const el = document.querySelector(sel);
    if (el) el.textContent = text;
  };
  set("#kpi-runs", `${kpis.corridas_totales ?? 0} (${kpis.entregas_monitoreadas ?? 0}/3 entregas)`);
  set("#kpi-evidence", `${kpis.controles_con_evidencia_pct ?? 0} %`);
  set(
    "#kpi-criteria",
    kpis.criterios_vigentes_totales
      ? `${kpis.criterios_vigentes_verificados}/${kpis.criterios_vigentes_totales} (${kpis.criterios_vigentes_pct} %)`
      : "Sin corridas"
  );
  set(
    "#kpi-boards",
    `${kpis.acciones_boards_aprobadas ?? 0} aprob. · ${kpis.acciones_boards_cerradas ?? 0} cerr. · ${kpis.acciones_boards_pendientes ?? 0} pend.`
  );
}

async function refreshAnalyticsStrip() {
  try {
    const res = await fetch("/api/metricas-powerbi.json");
    if (!res.ok) return;
    const data = await readJson(res);
    if (data?.kpis) renderValueKpis(data.kpis);
  } catch {
    // Analytics strip degrades silently when offline.
  }
}

function updatePowerBiNavLink(reportUrl) {
  const navPbi = document.querySelector("#nav-powerbi");
  if (!navPbi || !reportUrl) return;
  navPbi.href = reportUrl;
  const lbl = document.querySelector("#nav-powerbi-label");
  if (lbl) lbl.textContent = "Power BI · Reporte Web";
}

openPowerBiWebBtn?.addEventListener("click", async () => {
  openPowerBiWebBtn.disabled = true;
  const popup = window.open("about:blank", "nextgen_powerbi_web");
  setStatus("Sincronizando corridas en tiempo real y abriendo reporte ejecutivo en app.powerbi.com…", "busy");
  try {
    const res = await fetch("/api/powerbi/publicar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ regenerar: false }),
    });
    const data = await readJson(res);
    if (!res.ok) throw new Error(data.error || "No se pudo sincronizar el reporte en Power BI Service.");
    if (data.analitica) renderValueKpis(data.analitica);
    const targetUrl = data.powerbi?.report_url || data.powerbi?.dataset_url;
    if (targetUrl) {
      updatePowerBiNavLink(targetUrl);
      if (popup && !popup.closed) popup.location.href = targetUrl;
    }
    setStatus(
      `Reporte ejecutivo actualizado en Power BI Web (${data.powerbi?.filas_sincronizadas ?? 0} corridas sincronizadas).`,
      "pass"
    );
  } catch (err) {
    if (popup && !popup.closed) popup.close();
    setStatus(describeFetchError(err, "No se pudo publicar el reporte en Power BI Service."), "error");
  } finally {
    openPowerBiWebBtn.disabled = false;
  }
});

function createSummary(labelText) {
  const summary = document.createElement("summary");
  const label = element("span", labelText, "summary-label");
  const chev = svgIcon("chevron", 14);
  chev.classList.add("summary-chevron");
  summary.append(label, chev);
  return summary;
}

function setPip(pip, state) {
  pip.dataset.state = state;
  pip.replaceChildren(svgIcon(PIP_GLYPHS[state] || "dash", 10));
}

const LINES = {
  DevSec: ["DS", "Línea DevSec · Código y evidencia"],
  CloudOps: ["CO", "Línea CloudOps · Nube y gobierno"],
};
const joinList = (list) => list.join(", ").replace(/, ([^,]*)$/, " y $1");

function initLedger() {
  for (const pip of document.querySelectorAll("#help-states .ver-pip[data-state]")) setPip(pip, pip.dataset.state);
  const key = document.querySelector("#ledger-key");
  for (const [state, text] of [
    ["verificado", "Verificado"],
    ["incumplido", "Incumplido"],
    ["pendiente", "Sin confirmar: falta un dato"],
    ["atencion", "Atención requerida: alguien debe revisar"],
    ["informativo", "Informativo"],
  ]) {
    const item = element("li", null, "key-item");
    item.dataset.state = state;
    item.append(svgIcon(stateToIconKind(state), 12), element("span", text));
    key.append(item);
  }
  renderLedger();
}

// The cell a stage and delivery live in; a stage shared by every delivery has one cell for all.
function ledgerCell(stage, ver) {
  return ledger.querySelector(`.ledger-cell-btn[data-stage="${stage}"][data-ver="${ver}"]`)
    || ledger.querySelector(`.ledger-cell-btn[data-stage="${stage}"]`);
}

function markInspecting() {
  for (const btn of ledger.querySelectorAll(".ledger-cell-btn")) {
    const on = !stageInspector.hidden && Number(btn.dataset.stage) === inspectedStage
      && (btn.dataset.ver === "todas" || btn.dataset.ver === inspectedVersion);
    btn.classList.toggle("is-inspecting", on);
    btn.setAttribute("aria-expanded", String(on));
  }
}

function cellButton(meta, stage, ver, shown) {
  const btn = element("button", null, "ledger-cell-btn");
  btn.type = "button";
  btn.dataset.stage = String(meta.numero);
  btn.dataset.ver = ver;
  const where = ver === "todas" ? `igual en ${joinList(shown)}` : ver;
  btn.append(element("span", `Etapa ${meta.numero}, ${meta.etapa}, ${where}: `, "sr-only"));
  btn.setAttribute("aria-controls", "stage-inspector");
  btn.setAttribute("aria-expanded", "false");
  if (!stage) {
    btn.dataset.state = "idle";
    const busy = cards.get(ver)?.dataset.verdict === "busy";
    btn.append(element("span", busy ? "Evaluando…" : "Sin datos", "cell-empty"));
  } else {
    btn.dataset.state = stage.estado;
    btn.dataset.review = String(needsReview(stage));
    const note = stageNoteShort(stage);
    if (note && stage.estado === "informativo") btn.dataset.flagged = "true";
    if (ver !== "todas" && cards.get(ver)?.dataset.stale === "true") btn.dataset.stale = "true";
    const head = element("span", null, "cell-state");
    head.append(svgIcon(stateToIconKind(stage.estado), 13), element("span", stageStateLabel(stage)));
    if (ver === "todas") head.append(element("span", `Igual en ${joinList(shown)}`, "cell-shared-tag"));
    btn.append(head, termText("span", stripState(stage.resumen), "cell-summary"));
    if (note) {
      const noteEl = element("span", null, "cell-note");
      noteEl.append(svgIcon("bang", 12), element("span", note));
      btn.append(noteEl);
    }
  }
  btn.addEventListener("click", () => {
    const target = ver === "todas" ? null : ver;
    const same = !stageInspector.hidden && inspectedStage === meta.numero && (target === null || inspectedVersion === target);
    if (same) closeStageInspector();
    else openStageInspector(meta.numero, target);
  });
  return btn;
}

// Stage × delivery ledger: the transit line runs down the first column, one tab stop per cell.
function renderLedger() {
  const focused = ledger.contains(document.activeElement) ? document.activeElement : null;
  const shown = versions.filter((v) => !cards.get(v).hidden);
  const finished = finishedVersions();
  // A stage collapses into one cell only when every delivery on screen has a result and they agree.
  const shared = finished.length === shown.length ? computeSharedStages(finished) : new Set();
  const span = shown.length + 1;
  ledgerHubCell.colSpan = span;
  ledger.dataset.cols = String(shown.length);
  ledger.dataset.filter = String(filterDiffOnly);

  const headRow = element("tr", null, "ledger-head-row");
  headRow.setAttribute("role", "row");
  const corner = element("th", "Etapa", "ledger-corner");
  corner.scope = "col";
  corner.setAttribute("role", "columnheader");
  headRow.append(corner);
  for (const v of shown) {
    const card = cards.get(v);
    const report = reportsByVersion.get(v);
    const th = element("th", null, "ledger-ver");
    th.scope = "col";
    th.setAttribute("role", "columnheader");
    th.dataset.ver = v;
    th.dataset.verdict = card.dataset.verdict || "idle";
    th.abbr = `${v} ${card.querySelector(".badge").textContent}`;
    const held = card.dataset.stale === "true";
    if (held) th.dataset.stale = "true";
    const top = element("span", null, "ver-head-row");
    const cardBadge = card.querySelector(".badge");
    const badge = element("span", null, "badge");
    setBadge(badge, cardBadge.dataset.state, cardBadge.textContent);
    top.append(element("span", v, "ver-id"), badge);
    th.append(top, element("span", versionRoles[v], "ver-scenario"));
    if (report) th.append(element("span", `${held ? "Corrida anterior: " : ""}${decidingReason(report)}`, "ver-why"));
    const prov = card.querySelector(".provenance-chip").textContent
      .replace("Corrida previa en caché", "En caché").replace("Ejecución en vivo", "En vivo");
    th.append(element("span", prov, "ver-prov"));
    headRow.append(th);
  }
  ledgerHead.replaceChildren(headRow);

  let hiddenRows = 0;
  for (const [bloque, body] of Object.entries(ledgerBodies)) {
    const [bullet, lineName] = LINES[bloque];
    const lineRow = element("tr", null, "ledger-line");
    lineRow.setAttribute("role", "row");
    lineRow.dataset.line = bloque.toLowerCase();
    const lineHead = element("th", null, "ledger-line-head");
    lineHead.scope = "rowgroup";
    lineHead.setAttribute("role", "rowheader");
    lineHead.colSpan = span;
    const bulletEl = element("span", bullet, "line-bullet");
    bulletEl.setAttribute("aria-hidden", "true");
    lineHead.append(bulletEl, element("span", lineName));
    lineRow.append(lineHead);
    const rows = [lineRow];
    for (const meta of STAGE_CATALOG.filter((m) => m.bloque === bloque)) {
      const perVer = shown.map((v) => [v, reportsByVersion.get(v)?.etapas_devsecops?.find((x) => x.numero === meta.numero)]);
      if (filterDiffOnly && finished.length && !perVer.some(([, st]) => st && needsReview(st))) {
        hiddenRows++;
        continue;
      }
      const tr = element("tr", null, "ledger-row");
      tr.setAttribute("role", "row");
      tr.dataset.stage = String(meta.numero);
      if (meta.numero === DECISIVE_STAGE) tr.dataset.scope = "decide";
      else if (CONTEXT_STAGES.has(meta.numero)) tr.dataset.scope = "contexto";
      const present = perVer.filter(([, st]) => st);
      const worst = present.reduce((w, [, st]) => ((STATE_RANK[st.estado] ?? 0) > (STATE_RANK[w] ?? 0) ? st.estado : w), "informativo");
      const th = element("th", null, "ledger-stage");
      th.scope = "row";
      th.setAttribute("role", "rowheader");
      th.dataset.state = present.length ? worst : "idle";
      const ring = element("span", String(meta.numero), "station-ring");
      ring.setAttribute("aria-hidden", "true");
      const label = element("span", null, "stage-label");
      label.append(
        element("span", `Etapa ${meta.numero}: `, "sr-only"),
        element("span", meta.etapa, "stage-name"),
        termText("span", meta.herramienta, "stage-tool")
      );
      if (tr.dataset.scope === "decide") label.append(element("span", "Decide REN-001", "scope-tag is-decisive"));
      else if (tr.dataset.scope === "contexto") label.append(element("span", "Contexto · fuera de REN-001", "scope-tag"));
      th.append(ring, label);
      // Pointer shortcut: the station opens its stage; keyboards use the cells or 1–8.
      th.addEventListener("click", () => openStageInspector(meta.numero, null));
      tr.append(th);
      if (shared.has(meta.numero)) {
        const td = element("td", null, "ledger-cell is-shared");
        td.setAttribute("role", "cell");
        td.colSpan = shown.length;
        td.append(cellButton(meta, perVer[0][1], "todas", shown));
        tr.append(td);
      } else {
        for (const [v, st] of perVer) {
          const td = element("td", null, "ledger-cell");
          td.setAttribute("role", "cell");
          td.dataset.ver = v;
          td.append(cellButton(meta, st, v, shown));
          tr.append(td);
        }
      }
      rows.push(tr);
    }
    if (rows.length === 1) {
      const empty = element("tr", null, "ledger-empty-row");
      empty.setAttribute("role", "row");
      const td = element("td", "Sin brechas en esta línea.", "stage-filter-empty");
      td.setAttribute("role", "cell");
      td.colSpan = span;
      empty.append(td);
      rows.push(empty);
    }
    body.replaceChildren(...rows);
  }
  ledgerFilterNote.hidden = !filterDiffOnly;
  ledgerFilterNote.textContent = hiddenRows
    ? `Filtro «Solo brechas»: ${hiddenRows} ${hiddenRows === 1 ? "etapa sin nada que revisar oculta" : "etapas sin nada que revisar ocultas"}. Pulsa D o el botón para verlas.`
    : "Filtro «Solo brechas»: todas las etapas tienen algo que revisar.";

  renderLedgerFoot(shown);
  renderLedgerHeadline(shown);
  renderVerdictEchoes(shown);
  markInspecting();
  renderDossierTabs();
  if (focused && !document.contains(focused)) {
    const again = focused.dataset.decision
      ? ledgerFoot.querySelector(`[data-decision="${focused.dataset.decision}"]`)
      : ledgerCell(focused.dataset.stage, focused.dataset.ver);
    again?.focus({ preventScroll: true });
  }
}

// The ledger ends on the human decision each delivery still needs.
function renderLedgerFoot(shown) {
  const row = element("tr", null, "ledger-foot-row");
  row.setAttribute("role", "row");
  const th = element("th", null, "ledger-stage ledger-foot-head");
  th.scope = "row";
  th.setAttribute("role", "rowheader");
  const label = element("span", null, "stage-label");
  label.append(element("span", "Decisión humana", "stage-name"), element("span", "Azure Boards", "stage-tool"));
  th.append(label);
  row.append(th);
  for (const v of shown) {
    const report = reportsByVersion.get(v);
    const action = report?.accion_propuesta;
    let text = "Sin corrida todavía";
    let tone = "idle";
    if (report && !action) {
      text = "Sin acción correctiva";
      tone = "pass";
    } else if (action?.estado === "PENDIENTE_APROBACION") {
      text = "Acción pendiente";
      tone = "attention";
    } else if (action) {
      const ref = action.boards_resultado?.referencia;
      text = `${ENUM_TEXT[action.estado] || humanize(action.estado)}${ref ? ` · ${ref}` : ""}`;
      tone = action.estado === "DESCARTADA" ? "idle" : "pass";
    }
    const td = element("td", null, "ledger-decision");
    td.setAttribute("role", "cell");
    td.dataset.ver = v;
    td.dataset.tone = tone;
    const btn = element("button", null, "ledger-decision-btn");
    btn.type = "button";
    btn.dataset.decision = v;
    btn.append(
      element("span", text, "decision-state"),
      element("span", tone === "attention" ? `Decidir en el expediente de ${v}` : `Abrir expediente de ${v}`, "decision-go")
    );
    btn.addEventListener("click", () => selectDossier(v, { focus: tone === "attention" ? "decision" : "panel", scroll: true }));
    td.append(btn);
    row.append(td);
  }
  ledgerFoot.replaceChildren(row);
}

// Compact copies of the column heads: a pinned bar while the ledger scrolls, a strip under the title on phones.
function renderVerdictEchoes(shown) {
  const chip = (v) => {
    const card = cards.get(v);
    const item = element("span", null, "echo-ver");
    item.dataset.verdict = card.dataset.verdict || "idle";
    const badge = element("span", null, "badge");
    const cardBadge = card.querySelector(".badge");
    setBadge(badge, cardBadge.dataset.state, cardBadge.textContent);
    item.append(element("span", v, "ver-id"), badge);
    return item;
  };
  ledgerPin.replaceChildren(element("span", "Etapa", "echo-corner"), ...shown.map(chip));
  ledgerPin.dataset.cols = String(shown.length);
  const touched = shown.filter((v) => cards.get(v).querySelector(".badge").textContent !== "Sin ejecutar");
  deckVerdict.hidden = !touched.length;
  deckVerdict.replaceChildren(...touched.map(chip));
  placeLedgerPin();
}

function placeLedgerPin() {
  const head = ledgerHead.getBoundingClientRect();
  const table = ledger.getBoundingClientRect();
  const show = head.bottom < 0 && table.bottom > 120 && ledger.offsetParent !== null;
  ledgerPin.hidden = !show;
  if (!show) return;
  const corner = ledgerHead.querySelector(".ledger-corner")?.getBoundingClientRect();
  ledgerPin.style.insetInlineStart = `${table.left}px`;
  ledgerPin.style.inlineSize = `${table.width}px`;
  ledgerPin.style.setProperty("--corner", `${corner ? corner.width : 0}px`);
}

let pinFrame = 0;
const schedulePin = () => {
  cancelAnimationFrame(pinFrame);
  pinFrame = requestAnimationFrame(placeLedgerPin);
};
window.addEventListener("scroll", schedulePin, { passive: true });
window.addEventListener("resize", schedulePin);

function renderLedgerHeadline(shown) {
  const touched = shown.filter((v) => cards.get(v).querySelector(".badge").textContent !== "Sin ejecutar");
  if (!touched.length) {
    ledgerHeadline.textContent = "Sin corridas todavía: pulsa «Ejecutar evaluación» para llenar la matriz.";
    return;
  }
  const finishedVers = touched.filter((v) => ["pass", "fail", "unknown"].includes(cards.get(v).dataset.verdict));
  if (!finishedVers.length) {
    ledgerHeadline.textContent = "Evaluación en curso: cada columna se completa al terminar su corrida.";
    return;
  }
  const gaps = finishedVers.filter((v) => reportsByVersion.get(v).veredicto !== "VERIFICADO").length;
  const pending = finishedVers.filter((v) => reportsByVersion.get(v).accion_propuesta?.estado === "PENDIENTE_APROBACION").length;
  const liveCount = finishedVers.filter((v) => provenanceByVersion.get(v)?.isLive).length;
  const provenance = liveCount === finishedVers.length
    ? "resultados en vivo"
    : liveCount === 0 ? "corridas en caché (0 tokens)" : "resultados en vivo y en caché";
  const unfinished = touched.length - finishedVers.length;
  ledgerHeadline.textContent = `Dictamen REN-001: ${gaps} de ${finishedVers.length} ${finishedVers.length === 1 ? "entrega" : "entregas"} con brecha${pending ? ` · ${pending} ${pending === 1 ? "acción espera" : "acciones esperan"} decisión humana` : " · ninguna decisión pendiente"}${unfinished ? ` · ${unfinished} sin dictamen` : ""} · ${provenance}`;
}

// One delivery's evidence at a time; the ledger above keeps the comparison.
function renderDossierTabs() {
  const shown = versions.filter((v) => !cards.get(v).hidden);
  if (!shown.includes(activeDossier)) activeDossier = shown[0] || null;
  const hadFocus = dossierTabs.contains(document.activeElement);
  dossierTabs.replaceChildren();
  for (const v of shown) {
    const card = cards.get(v);
    const selected = v === activeDossier;
    const tab = element("button", null, "dossier-tab");
    tab.type = "button";
    tab.id = `tab-${v}`;
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", card.id);
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    tab.dataset.ver = v;
    tab.dataset.verdict = card.dataset.verdict || "idle";
    tab.setAttribute("aria-label", `${v}: ${card.querySelector(".badge").textContent}`);
    tab.append(
      element("span", v, "tab-ver"),
      svgIcon(stateToIconKind(card.dataset.verdict || "idle"), 13),
      element("span", card.querySelector(".badge").textContent, "tab-state")
    );
    tab.addEventListener("click", () => selectDossier(v));
    dossierTabs.append(tab);
  }
  for (const [v, card] of cards) card.dataset.active = String(v === activeDossier);
  if (hadFocus) dossierTabs.querySelector('[aria-selected="true"]')?.focus({ preventScroll: true });
}

function selectDossier(v, { focus = "tab", scroll = false } = {}) {
  // A Boards send in its 5 s grace keeps its Deshacer on screen: no switching away until it settles.
  const graceVer = versions.find((x) => cards.get(x).dataset.grace === "true");
  if (graceVer && graceVer !== v) {
    announce(`Hay un envío de ${graceVer} en cuenta atrás: espera a que termine o pulsa «Deshacer» antes de cambiar de expediente.`);
    cards.get(graceVer).querySelector(".gov-grace-undo")?.focus();
    return;
  }
  activeDossier = v;
  renderDossierTabs();
  const card = cards.get(v);
  if (scroll) card.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "start" });
  const note = card.querySelector(".governance .gov-input");
  if (focus === "decision" && note && note.offsetParent && !note.disabled) note.focus({ preventScroll: true });
  else if (focus === "panel") card.querySelector(".card-version-title").focus({ preventScroll: true });
  else dossierTabs.querySelector(`#tab-${v}`)?.focus({ preventScroll: true });
}

dossierTabs.addEventListener("keydown", (event) => {
  const tabs = [...dossierTabs.querySelectorAll('[role="tab"]')];
  const i = tabs.indexOf(document.activeElement);
  if (i < 0) return;
  const next = { ArrowRight: tabs[(i + 1) % tabs.length], ArrowLeft: tabs[(i - 1 + tabs.length) % tabs.length], Home: tabs[0], End: tabs[tabs.length - 1] }[event.key];
  if (!next) return;
  event.preventDefault();
  event.stopPropagation();
  selectDossier(next.dataset.ver);
});

function pickBestVersionForStage(stageNumber, explicitVersion) {
  if (explicitVersion && reportsByVersion.has(explicitVersion)) return explicitVersion;
  let chosen = null;
  let bestRank = -1;
  for (const ver of versions) {
    const rep = reportsByVersion.get(ver);
    if (!rep) continue;
    const st = rep.etapas_devsecops?.find((s) => s.numero === stageNumber)?.estado || "informativo";
    const rank = STATE_RANK[st] ?? 0;
    if (rank > bestRank) {
      bestRank = rank;
      chosen = ver;
    }
  }
  return chosen || explicitVersion || "v1";
}

// Stage 4 is decided by one test: say which, instead of the generic TRX count.
function stageAnswer(stage, report) {
  if (stage.numero === 4 && report) return decidingReason(report);
  return stripState(stage.resumen || stage.descripcion);
}

// Long URLs and identifiers break at dots, slashes and dashes, never mid-word.
const TERMS = {
  WIQL: "Work Item Query Language: consulta de Azure Boards que evita crear tareas duplicadas",
  TRX: "Visual Studio Test Results: resultados XML de dotnet test",
  HITL: "Human in the loop: una persona aprueba o descarta cada acción",
  "SHA-256": "Huella criptográfica que demuestra que el archivo no cambió",
  CSPM: "Cloud Security Posture Management: postura de seguridad cloud en Defender",
  KQL: "Kusto Query Language: consultas de telemetría en Application Insights",
  SAST: "Análisis estático de seguridad del código fuente (CodeQL)",
  SBOM: "Software Bill of Materials: inventario SPDX de paquetes y dependencias",
  AKS: "Azure Kubernetes Service: orquestación cloud-native de contenedores",
};
const TERM_PATTERN = new RegExp(`\\b(${Object.keys(TERMS).map((t) => t.replace("-", "\\-")).join("|")})\\b`);

// Text with each known acronym wrapped in <abbr title>, so the definition sits where the term is used.
function termText(tag, text, className) {
  const node = element(tag, null, className);
  for (const part of String(text ?? "").split(TERM_PATTERN)) {
    if (TERMS[part]) {
      const abbr = element("abbr", part);
      abbr.title = TERMS[part];
      node.append(abbr);
    } else if (part) {
      node.append(part);
    }
  }
  return node;
}

function appendBreakable(node, text) {
  const str = String(text);
  if (str.length < 28 || /\s/.test(str)) {
    node.textContent = str;
    return;
  }
  for (const part of str.split(/(?<=[./_-])/)) {
    node.append(part, document.createElement("wbr"));
  }
}

function openStageInspector(stageNumber, focusVersion, origin = null, { refresh = false } = {}) {
  const baseMeta = STAGE_CATALOG.find((s) => s.numero === stageNumber) || STAGE_CATALOG[0];
  const wasOpen = !stageInspector.hidden;
  const previousStage = inspectedStage;
  const previousVersion = inspectedVersion;
  const tabHadFocus = inspectorVersionTabs.contains(document.activeElement);
  inspectedStage = baseMeta.numero;
  inspectedVersion = pickBestVersionForStage(baseMeta.numero, focusVersion);

  const report = reportsByVersion.get(inspectedVersion);
  const liveStage = report?.etapas_devsecops?.find((s) => s.numero === baseMeta.numero) || {};
  const merged = { ...baseMeta, ...liveStage, etapa: baseMeta.etapa };

  stageInspectorTitle.textContent = `Etapa ${merged.numero}. ${merged.etapa}`;
  const stateLabel = merged.estado ? stageStateLabel(merged) : "Referencia de etapa";
  if (wasOpen && !refresh) {
    announce(`${inspectorWrapNote}Etapa ${merged.numero}, ${merged.etapa}, ${inspectedVersion}: ${stateLabel}.`);
  }
  inspectorWrapNote = "";
  stageInspectorMeta.textContent = `${merged.bloque} · ${merged.herramienta} · Vista activa: ${inspectedVersion} (${stateLabel})`;

  inspectorVersionTabs.replaceChildren();
  for (const ver of versions) {
    const tab = element("button", ver, "ver-tab-btn");
    tab.type = "button";
    tab.setAttribute("aria-pressed", String(ver === inspectedVersion));
    tab.addEventListener("click", () => openStageInspector(baseMeta.numero, ver));
    if (ver === inspectedVersion) tab.setAttribute("aria-current", "true");
    inspectorVersionTabs.append(tab);
  }

  stageInspectorBody.replaceChildren();

  const leadGrid = element("div", null, "inspector-lead-grid");
  const qBlock = element("div", null, "inspector-question-block");
  qBlock.append(
    element("h4", "Pregunta de gobierno de esta etapa"),
    element("p", merged.pregunta || baseMeta.pregunta)
  );
  const answer = element("div", null, "inspector-answer-block");
  answer.append(
    element("h4", report ? `Respuesta en ${inspectedVersion}` : "Qué revisa esta etapa"),
    element("p", report ? stageAnswer(merged, report) : baseMeta.descripcion, "inspector-desc")
  );
  const note = stageNote(merged);
  if (note) {
    const noteEl = element("p", null, "cell-note");
    noteEl.dataset.state = merged.estado || "";
    noteEl.append(svgIcon("bang", 12), element("span", note));
    answer.append(noteEl);
  }
  leadGrid.append(qBlock, answer);
  stageInspectorBody.append(leadGrid);

  if (merged.datos && Object.keys(merged.datos).length > 0) {
    stageInspectorBody.append(element("h4", `Datos recolectados en ${inspectedVersion}`, "inspector-compare-title"));
    const dl = element("dl", null, "inspector-kv");
    for (const [k, v] of Object.entries(merged.datos)) {
      const wrap = element("div", null, "kv-item");
      const dd = document.createElement("dd");
      const value = formatFieldValue(k, v);
      appendBreakable(dd, value);
      if (String(value).length > 40) wrap.classList.add("kv-wide");
      wrap.append(element("dt", formatFieldKey(k)), dd);
      dl.append(wrap);
    }
    stageInspectorBody.append(dl);
  }

  if (baseMeta.numero === 3) {
    renderStage3VulnReport(stageInspectorBody, inspectedVersion);
  } else if (baseMeta.numero === 8) {
    renderStage8SecOpsWorkbench(stageInspectorBody, inspectedVersion);
  }

  const loaded = versions.filter((ver) => reportsByVersion.get(ver)?.etapas_devsecops?.some((x) => x.numero === baseMeta.numero));
  const signatures = new Set(loaded.map((ver) => {
    const st = reportsByVersion.get(ver).etapas_devsecops.find((x) => x.numero === baseMeta.numero);
    return stageSignature(st);
  }));
  if (loaded.length > 1 && signatures.size === 1) {
    const st = reportsByVersion.get(loaded[0]).etapas_devsecops.find((x) => x.numero === baseMeta.numero);
    stageInspectorBody.append(element("h4", `Mismo resultado en ${loaded.join(", ").replace(/, ([^,]*)$/, " y $1")}`, "inspector-compare-title"));
    const same = element("div", null, "inspector-compare-col inspector-compare-same");
    const b = element("span", null, "badge");
    b.dataset.state = STATE_BADGE[st.estado] || "idle";
    b.append(svgIcon(stateToIconKind(st.estado), 12), element("span", stageStateLabel(st)));
    same.append(b, element("p", stripState(st.resumen)));
    stageInspectorBody.append(same);
  } else if (reportsByVersion.size > 0) {
    stageInspectorBody.append(element("h4", "Estado comparado en las tres entregas", "inspector-compare-title"));
    const grid = element("div", null, "inspector-compare-grid");
    for (const ver of versions) {
      const col = element("div", null, "inspector-compare-col");
      const rep = reportsByVersion.get(ver);
      const st = rep?.etapas_devsecops?.find((s) => s.numero === baseMeta.numero);
      const headRow = element("div", null, "card-title-row");
      headRow.append(element("strong", ver));
      if (st) {
        const b = element("span", null, "badge");
        b.dataset.state = STATE_BADGE[st.estado] || "idle";
        b.append(svgIcon(stateToIconKind(st.estado), 12), element("span", stageStateLabel(st)));
        headRow.append(b);
        col.append(headRow, element("p", stageAnswer(st, rep)));
      } else {
        col.append(headRow, element("p", "Sin datos evaluados aún en esta sesión."));
      }
      grid.append(col);
    }
    stageInspectorBody.append(grid);
  }

  const actions = element("div", null, "inspector-actions");
  if (report) {
    const go = element("button", `Abrir expediente de ${inspectedVersion}`, "btn-secondary");
    go.type = "button";
    const target = inspectedVersion;
    go.addEventListener("click", () => {
      closeStageInspector();
      selectDossier(target, { focus: "panel", scroll: true });
    });
    actions.append(go);
  }
  if (merged.url) {
    const ext = element("a", null, "btn-ghost");
    ext.href = merged.url;
    ext.target = "_blank";
    ext.rel = "noopener";
    ext.append(
      element("span", merged.etiqueta_url || "Abrir evidencia en sistema origen"),
      svgIcon("ext", 13),
      element("span", " (se abre en una nueva pestaña)", "sr-only")
    );
    actions.append(ext);
  }

  if (actions.childElementCount) stageInspectorBody.append(actions);

  stageInspector.hidden = false;
  // The cell under the sheet stays visibly selected.
  markInspecting();

  // Continuity: stepping between stations slides the detail in the travel direction.
  if (wasOpen && (previousStage !== inspectedStage || previousVersion !== inspectedVersion)) {
    const forward = previousStage === inspectedStage ? 0 : (inspectedStage > previousStage ? 1 : -1);
    animateIn(stageInspectorBody, { dx: forward * 14, dy: 0, duration: 260 });
  }

  // A data refresh repaints in place: no scroll, no focus theft.
  if (refresh) return;
  syncHash();

  // The sheet covers the bottom of the page: bring the inspected row above it.
  const sheetTop = window.innerHeight - stageInspector.getBoundingClientRect().height;
  const row = ledgerCell(inspectedStage, inspectedVersion)?.getBoundingClientRect();
  if (row && (row.bottom > sheetTop - 8 || row.top < 0)) {
    window.scrollBy({ top: row.top - Math.max(16, (sheetTop - row.height) / 2), behavior: reducedMotion.matches ? "auto" : "smooth" });
  }
  if (tabHadFocus) {
    inspectorVersionTabs.querySelector('[aria-pressed="true"]')?.focus({ preventScroll: true });
  } else if (!stageInspector.contains(document.activeElement)) {
    stageInspector.focus({ preventScroll: true });
  }
}

// #etapa=4&version=v2&filtro=brechas makes a view shareable in a review thread.
function syncHash() {
  const params = new URLSearchParams();
  if (!stageInspector.hidden && inspectedStage) {
    params.set("etapa", String(inspectedStage));
    params.set("version", inspectedVersion);
  }
  if (filterDiffOnly) params.set("filtro", "brechas");
  const hash = params.toString();
  history.replaceState(null, "", hash ? `#${hash}` : `${location.pathname}${location.search}`);
}

function applyHash() {
  const params = new URLSearchParams(location.hash.slice(1));
  if (params.get("filtro") === "brechas" && !filterDiffOnly) filterDiffBtn.click();
  const stage = Number(params.get("etapa"));
  if (stage >= 1 && stage <= 8) {
    const ver = versions.includes(params.get("version")) ? params.get("version") : null;
    openStageInspector(stage, ver);
  }
}

function closeStageInspector() {
  const prevStage = inspectedStage;
  stageInspector.hidden = true;
  inspectedStage = null;
  markInspecting();
  syncHash();
  // After stepping with ←/→ the visitor is "at" the last inspected cell, not where they started.
  ledgerCell(prevStage, inspectedVersion)?.focus();
}

let inspectorWrapNote = "";

function stepInspector(delta) {
  const current = inspectedStage || 1;
  const loaded = versions.filter((v) => reportsByVersion.has(v));
  const reviewable = (n) => loaded.some((v) => {
    const st = reportsByVersion.get(v).etapas_devsecops?.find((x) => x.numero === n);
    return st && needsReview(st);
  });
  let next = current;
  for (let i = 0; i < 8; i++) {
    next = ((next - 1 + delta + 8) % 8) + 1;
    if (!filterDiffOnly || !loaded.length || reviewable(next)) break;
  }
  inspectorWrapNote = next < current === delta > 0 ? "Vuelta al inicio del recorrido. " : "";
  openStageInspector(next, inspectedVersion);
}

inspectorPrevBtn.addEventListener("click", () => stepInspector(-1));
inspectorNextBtn.addEventListener("click", () => stepInspector(1));

inspectorCloseBtn.addEventListener("click", closeStageInspector);

// Contextual Help Toggle
function setHelpOpen(open, { restore = false } = {}) {
  if (open && helpDrawer.hidden) {
    helpOrigin = document.activeElement !== document.body ? document.activeElement : null;
    helpReturnY = window.scrollY;
  }
  helpDrawer.hidden = !open;
  helpToggleBtn.setAttribute("aria-expanded", String(open));
  if (open) {
    helpDrawer.focus({ preventScroll: true });
  } else if (restore) {
    // Closing puts the visitor back where they pressed "?".
    if (helpOrigin && helpOrigin !== helpToggleBtn && document.contains(helpOrigin)) {
      helpOrigin.focus();
    } else if (helpOrigin === helpToggleBtn) {
      helpToggleBtn.focus({ preventScroll: true });
    } else {
      window.scrollTo({ top: helpReturnY, behavior: "auto" });
      helpToggleBtn.focus({ preventScroll: true });
    }
    helpOrigin = null;
  }
}

helpDrawer.addEventListener("focusout", (event) => {
  const next = event.relatedTarget;
  if (!helpDrawer.hidden && next && !helpDrawer.contains(next) && next !== helpToggleBtn) setHelpOpen(false);
});

shortcutsToggle.checked = shortcutsEnabled;
shortcutsToggle.addEventListener("change", () => {
  shortcutsEnabled = shortcutsToggle.checked;
  try {
    localStorage.setItem(SHORTCUTS_KEY, shortcutsEnabled ? "on" : "off");
  } catch {
    // Preference lasts for this visit only when storage is blocked.
  }
  announce(shortcutsEnabled ? "Atajos de una tecla activados." : "Atajos de una tecla desactivados. Esc sigue cerrando paneles.");
});

helpToggleBtn.addEventListener("click", () => setHelpOpen(helpDrawer.hidden));
helpCloseBtn.addEventListener("click", () => setHelpOpen(false, { restore: true }));

function syncArchiveRestoreButton(archivedList) {
  if (!demoRestoreBtn) return;
  const count = Array.isArray(archivedList) ? archivedList.length : 0;
  demoRestoreBtn.hidden = count === 0;
  if (count > 0) {
    demoRestoreBtn.textContent = `Restaurar última sesión archivada (${count} ${count === 1 ? "respaldo" : "respaldos"})`;
  }
}

function setDemoResetOpen(open) {
  if (!demoResetPanel || !demoResetToggleBtn) return;
  demoResetPanel.hidden = !open;
  demoResetToggleBtn.setAttribute("aria-expanded", String(open));
  if (!open) disarm(demoResetApplyBtn);
}

demoResetToggleBtn?.addEventListener("click", () => setDemoResetOpen(demoResetPanel.hidden));
demoResetCloseBtn?.addEventListener("click", () => {
  setDemoResetOpen(false);
  demoResetToggleBtn.focus();
});

function clearAllCardsToIdle() {
  reportsByVersion.clear();
  provenanceByVersion.clear();
  cachedLatest = {};
  for (const [ver, card] of cards) {
    card.hidden = false;
    resetCardBands(
      card,
      "idle",
      "Sin ejecutar",
      "Selecciona «Ejecutar evaluación» para compilar de forma aislada, correr xUnit y auditar las 8 etapas de esta entrega.",
      "Pendiente de corrida",
      false
    );
  }
  loadLatestBtn.hidden = true;
  closeStageInspector();
  syncVisibleCardGrid();
  refreshStageViews();
}

demoResetApplyBtn?.addEventListener("click", async () => {
  if (activeController) return;
  const resetCodeAndPrs = Boolean(resetCodePrsChk?.checked);
  const resetRuns = Boolean(resetRunsChk?.checked);
  const resetSb = Boolean(resetSandboxChk?.checked);
  const resetBd = Boolean(resetBoardsChk?.checked);
  if (!resetCodeAndPrs && !resetRuns && !resetSb && !resetBd) {
    setStatus("Selecciona al menos un componente para reiniciar la demostración.", "warn");
    return;
  }
  if (demoResetApplyBtn.dataset.armed !== "true") {
    arm(
      demoResetApplyBtn,
      resetBd ? "Confirmar reinicio local + GitHub + Boards" : "Confirmar reinicio reversible"
    );
    announce("Pulsa otra vez para confirmar el reinicio reversible de la demostración.");
    return;
  }
  disarm(demoResetApplyBtn);
  demoResetApplyBtn.disabled = true;
  setStatus("Preparando entorno limpio para nueva sesión de demostración…", "busy");
  try {
    const res = await fetch("/api/demo/reiniciar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        corridas: resetRuns,
        sandbox: resetSb,
        boards: resetBd,
        codigo: resetCodeAndPrs,
        prs: resetCodeAndPrs,
        powerbi: resetRuns,
      }),
    });
    const data = await readJson(res);
    if (!res.ok) throw new Error(data.error || "No se pudo reiniciar el entorno de demostración.");
    if (data.remediacion_activa) activeRemediationState = data.remediacion_activa;
    if (data.vulnerabilidades) vulnerabilitiesByVersion = data.vulnerabilidades;
    if (resetRuns) {
      clearAllCardsToIdle();
    } else {
      for (const ver of versions) {
        const rep = reportsByVersion.get(ver);
        if (rep) renderRemediation(cards.get(ver), ver, rep);
      }
    }
    if (data.analitica) renderValueKpis(data.analitica);
    if (data.sandbox) updateSandboxBanner(data.sandbox);
    syncArchiveRestoreButton(data.reinicio?.archivos_disponibles || []);
    const archivedCount = data.reinicio?.corridas?.archivadas || 0;
    const revertedFiles = data.reinicio?.codigo_revertido?.length || 0;
    const closedPrs = data.reinicio?.prs_cerrados?.length || 0;
    const boardsRemoved = data.reinicio?.boards?.cantidad_tareas_retiradas;
    const extras = [];
    if (revertedFiles) extras.push(`${revertedFiles} archivo(s) C# restaurados`);
    if (closedPrs) extras.push(`${closedPrs} PR(s) demo cerrados`);
    if (typeof boardsRemoved === "number") extras.push(`${boardsRemoved} tarea(s) demo retiradas en Boards`);
    setStatus(
      `Entorno listo para nueva demo (${archivedCount} corrida(s) archivadas${extras.length ? ` · ${extras.join(" · ")}` : ""}).`,
      "pass"
    );
    setDemoResetOpen(false);
  } catch (err) {
    setStatus(describeFetchError(err, "No se pudo completar el reinicio de demostración."), "error");
  } finally {
    demoResetApplyBtn.disabled = false;
  }
});

demoRestoreBtn?.addEventListener("click", async () => {
  if (activeController) return;
  demoRestoreBtn.disabled = true;
  setStatus("Restaurando la última sesión de demostración archivada…", "busy");
  try {
    const res = await fetch("/api/demo/restaurar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await readJson(res);
    if (!res.ok) throw new Error(data.error || "No se pudo restaurar la sesión archivada.");
    cachedLatest = data.ultimos || {};
    if (data.analitica) renderValueKpis(data.analitica);
    syncArchiveRestoreButton(data.restauracion?.archivos_disponibles || []);
    restoreCachedRuns({ stamp: true });
    setStatus(
      `Sesión restaurada (${data.restauracion?.corridas_restauradas || 0} corrida(s) recuperadas).`,
      "pass"
    );
    setDemoResetOpen(false);
  } catch (err) {
    setStatus(describeFetchError(err, "No se pudo restaurar la sesión archivada."), "error");
  } finally {
    demoRestoreBtn.disabled = false;
  }
});

// Sandbox Bridge (:5080) with popup-blocker resilience & inline retry
const launchLabel = (ver, active) => (active ? `${ver} activa en :5080` : `Iniciar ${ver} en :5080`);

// Two deliberate clicks within 4 s for anything that stops or replaces a live process.
function arm(btn, prompt) {
  const label = btn === runBtn ? runBtnLabel : (btn.querySelector("span") || btn);
  if (!btn.dataset.label) btn.dataset.label = label.textContent;
  btn.dataset.armed = "true";
  label.textContent = prompt;
  clearTimeout(btn._armTimer);
  btn._armTimer = setTimeout(() => disarm(btn), 8000);
}

function disarm(btn) {
  clearTimeout(btn._armTimer);
  const label = btn === runBtn ? runBtnLabel : (btn.querySelector("span") || btn);
  if (btn.dataset.armed === "true" && btn.dataset.label) label.textContent = btn.dataset.label;
  delete btn.dataset.armed;
  delete btn.dataset.label;
}

// Spending Azure AI tokens takes a second, deliberate press; the 0-token engine runs at once.
function confirmPaidRun(btn, versionsCount, mode = form.elements.modo.value) {
  if (mode !== "agente" || btn.dataset.armed === "true") {
    disarm(btn);
    return true;
  }
  arm(btn, `Confirmar: consume tokens en ${versionsCount} ${versionsCount === 1 ? "entrega" : "entregas"}`);
  announce("La evaluación con agentes consume tokens de Azure AI. Pulsa otra vez para confirmar o elige «Solo evidencia · 0 tokens».");
  return false;
}

function requestLaunch(btn, version) {
  if (sandboxBusy) return;
  const running = sandboxPill.dataset.active === "true" ? sandboxPill.dataset.version : null;
  if (running === version) return;
  if (running && btn.dataset.armed !== "true") {
    arm(btn, `¿Reemplazar ${running} por ${version}? Pulsa otra vez`);
    return;
  }
  disarm(btn);
  launchSandbox(version, true);
}

function updateSandboxBanner(sandbox) {
  const activeVer = sandbox?.activo ? sandbox.version : null;
  sandboxPill.dataset.active = String(Boolean(sandbox?.activo));
  sandboxPill.dataset.version = activeVer || "";
  delete sandboxPill.dataset.booting;

  for (const btn of document.querySelectorAll("[data-launch]")) {
    const ver = btn.dataset.launch;
    // The running version is a state, not an action: it stays focusable and announced, but does nothing.
    btn.disabled = Boolean(activeController);
    btn.setAttribute("aria-disabled", String(activeVer === ver));
    btn.dataset.current = String(activeVer === ver);
    disarm(btn);
    btn.textContent = launchLabel(ver, activeVer === ver);
  }

  if (sandbox && sandbox.activo) {
    const targetHref = sandbox.url_interoperable || `${sandbox.url}/?evaluador=${encodeURIComponent(window.location.origin)}&version=${encodeURIComponent(sandbox.version || "v1")}`;
    sandboxText.textContent = `Sujeto activo (${sandbox.version}) en 127.0.0.1:5080`;
    sandboxOpenLink.href = targetHref;
    sandboxOpenLink.hidden = false;
    stopSandboxBtn.hidden = false;
  } else {
    disarmStop();
    sandboxText.textContent = "Sandbox local :5080 detenido";
    sandboxOpenLink.hidden = true;
    stopSandboxBtn.hidden = true;
  }
}

function showSandboxError(message, retryFn) {
  sandboxAlertMsg.textContent = message;
  sandboxAlertWrap.hidden = false;
  lastSandboxAttempt = retryFn;
}

sandboxRetryBtn.addEventListener("click", () => {
  if (typeof lastSandboxAttempt === "function") lastSandboxAttempt();
});

async function launchSandbox(version, openTab = true) {
  if (sandboxBusy) return;
  sandboxBusy = true;
  sandboxAlertWrap.hidden = true;
  sandboxPill.dataset.booting = "true";
  sandboxText.textContent = `Iniciando instancia ${version} en 127.0.0.1:5080…`;
  setStatus(`Iniciando instancia real ${version} en 127.0.0.1:5080…`, "busy");

  for (const btn of document.querySelectorAll("[data-launch]")) {
    btn.disabled = true;
    disarm(btn);
    if (btn.dataset.launch === version) btn.textContent = `Iniciando ${version}…`;
  }

  const popup = openTab ? window.open("about:blank", "nextgen_sandbox_5080") : null;

  try {
    const res = await fetch("/api/sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accion: "iniciar", version }),
    });
    const data = await readJson(res);
    if (!res.ok) throw new Error(data.error || `No se pudo iniciar la instancia ${version} en el puerto 5080.`);

    updateSandboxBanner(data.sandbox);
    const targetUrl = data.sandbox.url_interoperable || data.sandbox.url;
    if (popup && !popup.closed) {
      popup.location.href = targetUrl;
    }
    setStatus(`Instancia ${version} en línea en ${data.sandbox.url}. Usa «Abrir portal activo (:5080)» si tu navegador bloqueó la pestaña.`, "pass");
  } catch (err) {
    if (popup && !popup.closed) popup.close();
    updateSandboxBanner(null);
    const message = describeFetchError(err, `No se pudo iniciar la instancia ${version} en el puerto 5080.`);
    setStatus(message, "error");
    showSandboxError(
      err instanceof TypeError ? message : `${message} Verifica que .NET SDK 10 esté disponible y que el puerto 5080 no esté ocupado por otro proceso.`,
      () => launchSandbox(version, openTab)
    );
  } finally {
    sandboxBusy = false;
  }
}

const disarmStop = () => disarm(stopSandboxBtn);

stopSandboxBtn.addEventListener("click", () => {
  if (sandboxBusy) return;
  if (stopSandboxBtn.dataset.armed !== "true") {
    arm(stopSandboxBtn, "¿Detener :5080? Pulsa otra vez");
    return;
  }
  disarm(stopSandboxBtn);
  stopSandbox();
});

sandboxToggle.addEventListener("click", () => {
  const open = sandboxBar.dataset.open !== "true";
  sandboxBar.dataset.open = String(open);
  sandboxToggle.setAttribute("aria-expanded", String(open));
});

async function stopSandbox() {
  if (sandboxBusy) return;
  sandboxBusy = true;
  stopSandboxBtn.disabled = true;
  sandboxAlertWrap.hidden = true;
  try {
    const res = await fetch("/api/sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accion: "detener" }),
    });
    const data = await readJson(res);
    if (!res.ok) throw new Error(data.error || "No se pudo detener la instancia local.");
    updateSandboxBanner(data.sandbox);
    setStatus("Instancia local en 127.0.0.1:5080 detenida.", "idle");
  } catch (err) {
    const message = describeFetchError(err, "No se pudo detener la instancia local en el puerto 5080.");
    setStatus(message, "error");
    showSandboxError(message, stopSandbox);
  } finally {
    stopSandboxBtn.disabled = false;
    sandboxBusy = false;
  }
}

for (const btn of document.querySelectorAll("[data-launch]")) {
  btn.addEventListener("click", () => requestLaunch(btn, btn.dataset.launch));
}

// Initialize 3 Comparison Columns
for (const version of versions) {
  const card = document.querySelector("#version-card").content.firstElementChild.cloneNode(true);
  const titleId = `card-title-${version}`;
  card.dataset.version = version;
  card.id = `card-${version}`;
  card.setAttribute("role", "tabpanel");
  card.setAttribute("aria-labelledby", titleId);
  const h3 = card.querySelector(".card-version-title");
  h3.id = titleId;
  h3.textContent = `Expediente de ${version}`;
  h3.tabIndex = -1;
  renderCardQuickActions(card, version);
  cards.set(version, card);
  results.append(card);
}

// The paid action names the engine it will spend.
function evalLabel(version) {
  return `Evaluar ${version} · ${form.elements.modo.value === "agente" ? "agentes" : "0 tokens"}`;
}

function renderCardQuickActions(card, version) {
  const box = card.querySelector(".card-quick-actions");
  box.replaceChildren();

  const evalSingleBtn = element("button", evalLabel(version), "btn-ghost card-eval-btn");
  evalSingleBtn.type = "button";
  evalSingleBtn.dataset.eval = version;
  evalSingleBtn.addEventListener("click", () => {
    if (activeController) return;
    const previous = provenanceByVersion.get(version);
    if (previous && form.elements.modo.value !== "agente" && evalSingleBtn.dataset.armed !== "true") {
      arm(evalSingleBtn, `¿Reemplazar la corrida de ${version}? Pulsa otra vez`);
      announce(`Volver a evaluar ${version} reemplaza su corrida guardada (${previous.label}). Pulsa otra vez para confirmar.`);
      return;
    }
    if (!confirmPaidRun(evalSingleBtn, 1)) return;
    executeAssessment([version], form.elements.modo.value, { preserveVisible: true });
  });

  box.append(evalSingleBtn);
}

function setBadge(badge, state, labelText) {
  badge.dataset.state = state;
  badge.replaceChildren(svgIcon(stateToIconKind(state), 13), element("span", labelText));
}

// Running again over a finished card: keep its evidence, say it is the previous run, lock its decisions.
function holdCard(card, state, label, reasonText, provenanceText) {
  card.dataset.verdict = state;
  card.dataset.stale = "true";
  setBadge(card.querySelector(".badge"), state, label);
  const prov = card.querySelector(".provenance-chip");
  prov.dataset.live = "false";
  prov.textContent = provenanceText;
  card.querySelector(".reason").textContent = `${reasonText} Debajo sigue la corrida anterior hasta que termine.`;
  card.querySelector(".card-alert").hidden = true;
  card.querySelector(".card-footer-band").inert = true;
}

function resetCardBands(card, state, label, reasonText, provenanceText = "Pendiente de corrida", isLive = false) {
  delete card.dataset.stale;
  card.querySelector(".card-footer-band").inert = false;
  card.dataset.verdict = state;
  setBadge(card.querySelector(".badge"), state, label);

  const prov = card.querySelector(".provenance-chip");
  prov.dataset.live = String(isLive);
  prov.textContent = provenanceText;

  card.querySelector(".reason").textContent = readableReason(reasonText);
  const nextStep = card.querySelector(".next-step");
  nextStep.hidden = true;
  nextStep.textContent = "";

  const cardAlert = card.querySelector(".card-alert");
  cardAlert.hidden = true;
  cardAlert.replaceChildren();

  card.querySelector(".card-proof-band").replaceChildren();
  card.querySelector(".evidence").replaceChildren();
  card.querySelector(".governance").replaceChildren();
  card.querySelector(".remediation")?.replaceChildren();
  card.querySelector(".downloads").replaceChildren();
}

function renderDeterministicProof(card, report) {
  const band = card.querySelector(".card-proof-band");
  band.replaceChildren();

  const head = element("div", null, "proof-header");
  head.append(element("h4", `Prueba determinista (${report.politica_version || "REN-001.v2"})`, "band-heading"));

  const metaStrip = element("div", null, "proof-meta-strip");
  const commit = report.ejecucion?.commit;
  if (commit) {
    const folder = report.ejecucion?.version || "la entrega";
    metaStrip.append(createCopyButton(commit, `commit ${commit.slice(0, 8)} · carpeta ${folder}/`, `commit ${commit.slice(0, 8)} · carpeta ${folder}/: copiar hash completo del repositorio`));
  }
  if (typeof report.ejecucion?.archivos_firmados === "number" && report.ejecucion.archivos_firmados > 0) {
    metaStrip.append(termText("span", `${report.ejecucion.archivos_firmados} archivos firmados con SHA-256`, "meta-pill"));
  }
  const cob = report.cobertura;
  if (cob && typeof cob.escenarios_dominio_pct === "number") {
    const xmlPart = cob.cobertura_xml ? ` · Cobertura líneas ${cob.cobertura_xml.lineas_pct}%` : "";
    metaStrip.append(element("span", `Escenarios verificados: ${cob.escenarios_dominio_verificados}/${cob.escenarios_dominio_totales} (${cob.escenarios_dominio_pct}%)${xmlPart}`, "meta-pill"));
  }
  band.append(head);
  if (metaStrip.childElementCount) band.append(metaStrip);

  const evaluatedCriteria = report.criterios_evaluados || [];
  if (evaluatedCriteria.length > 0) {
    const critList = element("ul", null, "criteria-list");
    for (const item of evaluatedCriteria) {
      const li = element("li", null, "criteria-item");
      const copy = element("div", null, "criteria-copy");
      const roleTag = item.rol === "primario" ? "Criterio primario" : item.rol === "secundario" ? "Criterio secundario" : "Backlog Boards";
      copy.append(
        element("strong", `${item.id} · ${roleTag}`),
        element("span", item.texto)
      );
      const b = element("span", null, "badge");
      const meta = VERDICT_META[item.veredicto] || { state: "unknown", label: humanize(item.veredicto) };
      setBadge(b, meta.state, meta.label);
      li.append(copy, b);
      critList.append(li);
    }
    band.append(critList);
  }

  const linkedRefs = report.referencias || [];
  const linkedMethods = new Set(linkedRefs.map((r) => (r.metodo || "").split(".").pop()).filter(Boolean));
  const trxRows = report.resultados_trx || [];

  if (trxRows.length) {
    const counts = new Map();
    for (const row of trxRows) {
      const key = row.outcome === "Skipped" ? "NotExecuted" : row.outcome;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    const summaryParts = [...counts].map(([name, count]) => {
      const word = OUTCOME_LABELS[name]?.[count === 1 ? 0 : 1] || name;
      return `${count} ${word}`;
    });
    band.append(element("p", `Suite xUnit ejecutada: ${summaryParts.join(" · ")}`, "source-ref-line"));

    const baseOf = (row) => ((row.name || "").split(".").pop() || "").split("(")[0];
    const shown = trxRows.filter((row) => linkedMethods.has(baseOf(row)) || row.outcome === "Failed");
    const folded = trxRows.filter((row) => !shown.includes(row));
    const trxList = (rows) => {
    const ul = element("ul", null, "trx-list");
    for (const row of rows) {
      const li = element("li", null, "trx-row");
      li.dataset.outcome = row.outcome || "Unknown";
      const rawName = row.name || "Caso de prueba xUnit";
      const shortName = rawName.includes(".") ? rawName.split(".").pop() : rawName;
      const baseMethod = shortName.split("(")[0];

      const left = element("span", null, "trx-name");
      left.append(svgIcon(stateToIconKind(row.outcome), 13), element("span", shortName));
      const srOutcome = element("span", ` (${row.outcome === "Passed" ? "Aprobada" : "Fallida"})`, "sr-only");
      left.append(srOutcome);
      li.append(left);

      if (linkedMethods.has(baseMethod)) {
        li.append(element("span", "REN-001", "trx-tag"));
      }
      ul.append(li);
    }
    return ul;
    };
    if (shown.length) band.append(trxList(shown));
    if (folded.length) {
      const more = document.createElement("details");
      more.className = "trx-more";
      more.append(createSummary(shown.length
        ? `+${folded.length} ${folded.length === 1 ? "prueba aprobada" : "pruebas aprobadas"} sin vínculo REN-001`
        : `${folded.length} ${folded.length === 1 ? "prueba" : "pruebas"} sin vínculo REN-001`));
      const body = element("div", null, "detail-content");
      body.append(trxList(folded));
      more.append(body);
      band.append(more);
    }
  }

  for (const ref of linkedRefs) {
    band.append(element("p", `Fuente verificada: ${ref.id} (${ref.metodo})`, "source-ref-line"));
  }
  for (const diag of report.diagnosticos || []) {
    band.append(element("p", `Diagnóstico: ${diag.detalle}`, "source-ref-line"));
  }
}

// One label and one identity per stage result, shared by matrix rows, the shared band and the inspector.
function stageStateLabel(s) {
  const base = STATE_LABELS[s.estado] || s.estado;
  if (s.estado !== "informativo" || !stageNote(s)) return base;
  return `${base}${s.numero === 7 ? " · sin línea base" : " · por revisar"}`;
}
const stageSignature = (s) => `${s.estado}|${s.resumen}|${JSON.stringify(s.datos || {})}|${stageNote(s) || ""}`;

const DECISIVE_STAGE = 4;
const CONTEXT_STAGES = new Set([3, 5, 6, 7]);

// The ledger keeps a short warning; the inspector carries the full sentence.
function stageNoteShort(stage) {
  if (stage.numero !== 5) return stageNote(stage);
  const datos = stage.datos || {};
  const deployed = datos["Versión desplegada"];
  const evaluated = datos["Versión evaluada"];
  if (!deployed || !evaluated) return stageNote(stage);
  if (deployed !== evaluated) return `Azure ejecuta ${deployed}, no ${evaluated}.`;
  return datos["Cambios locales"] === "Sí" ? `Azure ejecuta ${deployed}, con cambios locales sin publicar.` : null;
}

const isGapState = (estado) => ["incumplido", "atencion", "pendiente"].includes(estado);
// "Solo brechas" keeps what someone must look at: gaps plus informative stages that carry a warning.
const needsReview = (s) => isGapState(s.estado) || (s.estado === "informativo" && Boolean(stageNote(s)));

// Only cards that are visible and hold a finished verdict take part in the comparison.
function finishedVersions() {
  return versions.filter((v) => {
    const card = cards.get(v);
    return card && !card.hidden && reportsByVersion.has(v)
      && (["pass", "fail", "unknown"].includes(card.dataset.verdict) || card.dataset.stale === "true");
  });
}

function computeSharedStages(vers) {
  const shared = new Set();
  if (vers.length < 2) return shared;
  for (const meta of STAGE_CATALOG) {
    const signatures = new Set(vers.map((v) => {
      const s = reportsByVersion.get(v).etapas_devsecops?.find((x) => x.numero === meta.numero);
      return s ? stageSignature(s) : null;
    }));
    if (signatures.size === 1 && !signatures.has(null)) shared.add(meta.numero);
  }
  return shared;
}

function refreshStageViews() {
  renderLedger();
}

// Deterministic deciding reason: outcome of the TRX row linked to REN-001, if any.
function decidingReason(report) {
  const linked = new Set((report.referencias || []).map((r) => (r.metodo || "").split(".").pop()).filter(Boolean));
  const rows = (report.resultados_trx || []).filter((row) => linked.has((row.name || "").split(".").pop().split("(")[0]));
  if (rows.length) {
    const row = rows.find((r) => r.outcome === "Failed") || rows[0];
    const name = row.name.split(".").pop().split("(")[0];
    const outcome = row.outcome === "Passed" ? "aprobada" : row.outcome === "Failed" ? "fallida" : "sin ejecutar";
    return `Prueba «${testWords(name)}»: ${outcome}`;
  }
  if (report.veredicto === "EVIDENCIA_INSUFICIENTE") return "Ninguna prueba vinculada a REN-001";
  return humanize(report.justificacion || "").split(". ")[0];
}

function renderAgentInvestigation(card, report) {
  const evidence = card.querySelector(".evidence");
  evidence.replaceChildren();

  const qa = report.investigacion || {};
  const qaHasBody = Boolean(qa.detalle || qa.explicacion || (qa.llamadas && qa.llamadas.length));
  if (qaHasBody) {
    const detail = document.createElement("details");
    const title = qa.proveedor ? "Investigación Agente QA (MAF)" : "Traza de análisis QA";
    detail.append(createSummary(title));
    const content = element("div", null, "detail-content");
    content.append(element("p", "Contexto del agente: no decide el dictamen, que lo emite la política determinista REN-001.v2.", "agent-scope-note"));
    if (qa.detalle) content.append(element("p", qa.detalle));
    if (qa.explicacion) content.append(element("p", qa.explicacion));
    if (qa.llamadas && qa.llamadas.length) {
      const ul = element("ul", null, "tool-trace-list");
      for (const call of qa.llamadas) {
        ul.append(element("li", `Herramienta invocada: ${TOOL_LABELS[call.herramienta] || call.herramienta}`));
      }
      content.append(ul);
    }
    detail.append(content);
    evidence.append(detail);
  }

  const secops = report.investigacion_secops;
  if (secops && secops.estado && secops.estado !== "NO_SOLICITADA") {
    const findings = secops.hallazgos || [];
    const detail = document.createElement("details");
    const high = highFindings(report);
    const label = findings.length
      ? `Agente SecOps · ${findings.length} ${findings.length === 1 ? "hallazgo" : "hallazgos"}${high ? ` (${high} de severidad alta según el agente)` : ""}`
      : "Postura y telemetría · Agente SecOps";
    detail.append(createSummary(label));
    detail.classList.add("secops-detail");

    const content = element("div", null, "detail-content");
    content.append(element("p", "Contexto del agente: estos hallazgos no cambian el dictamen REN-001; cada uno indica su alcance.", "agent-scope-note"));
    if (secops.detalle) content.append(element("p", secops.detalle));
    if (secops.resumen) content.append(element("p", secops.resumen));
    for (const h of findings) {
      const box = element("div", null, "finding-item");
      const tags = element("div", null, "scope-tags");
      const sev = element("span", null, "severity-badge");
      sev.dataset.level = severityLevel(h.severidad);
      sev.append(
        svgIcon({ high: "bang", medium: "warn", low: "dash", info: "info" }[sev.dataset.level], 12),
        element("span", `Severidad ${String(h.severidad || "sin dato").toLowerCase()}`)
      );
      tags.append(sev, element("span", `Alcance: ${SCOPE_LABELS[h.alcance] || h.alcance}`, "scope-badge"));
      box.append(tags, termText("strong", h.titulo), termText("p", h.evidencia));
      content.append(box);
    }
    if (secops.llamadas && secops.llamadas.length) {
      const ul = element("ul", null, "tool-trace-list");
      for (const call of secops.llamadas) {
        ul.append(element("li", `Herramienta invocada: ${TOOL_LABELS[call.herramienta] || call.herramienta}`));
      }
      content.append(ul);
    }
    if (content.childElementCount) {
      detail.append(content);
      evidence.append(detail);
    }
  }
}

function createReopenDecisionButton(card, version, runId) {
  const reopenBtn = element("button", "Reabrir para otra demo", "btn-ghost");
  reopenBtn.type = "button";
  reopenBtn.addEventListener("click", async () => {
    if (reopenBtn.dataset.armed !== "true") {
      arm(reopenBtn, "¿Revertir decisión? Pulsa otra vez");
      return;
    }
    disarm(reopenBtn);
    reopenBtn.disabled = true;
    setStatus(`Reabriendo punto de control de ${version} para repetir demostración…`, "busy");
    try {
      const res = await fetch("/api/acciones", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ejecucion: runId, decision: "reabrir", sincronizar_boards: true }),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.error || "No se pudo reabrir la decisión.");
      const currentReport = reportsByVersion.get(version);
      if (currentReport) {
        currentReport.accion_propuesta = data.accion_propuesta;
        currentReport.cierre_ciclo_boards = data.cierre_ciclo_boards;
        if (data.etapas_devsecops?.length) currentReport.etapas_devsecops = data.etapas_devsecops;
      }
      renderGovernance(card, version, runId, data.accion_propuesta, true, data.cierre_ciclo_boards);
      refreshStageViews();
      refreshAnalyticsStrip();
      setStatus(`Decisión de ${version} reabierta y lista para otra demostración.`, "pass");
    } catch (err) {
      reopenBtn.disabled = false;
      setStatus(describeFetchError(err, "No se pudo reabrir la decisión."), "error");
    }
  });
  return reopenBtn;
}

// REN-001 certifies one rule; high-severity SecOps findings are surfaced next to it, never folded away.
function renderGovernance(card, version, runId, action, focusResult = false, closure = null) {
  const box = card.querySelector(".governance");
  box.replaceChildren();

  if (!action && closure) {
    const panel = element("div", null, "gov-panel");
    panel.dataset.state = closure.estado === "CERRADA_VERIFICADA" ? "APROBADA" : "PENDIENTE_APROBACION";
    const header = element("div", null, "gov-head");
    const heading = element("span", null, "gov-heading");
    heading.append(svgIcon("doc", 14), element("span", "Cierre de ciclo · Azure Boards"));
    header.append(heading);
    panel.append(header);
    if (closure.estado === "CERRADA_VERIFICADA") {
      const br = closure.boards_resultado || closure;
      const row = element("div", null, "gov-resolved-row");
      const msg = element("p", "Tarea cerrada tras verificación determinista: ", "gov-result");
      const link = document.createElement("a");
      link.href = br.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.append(element("span", br.referencia), element("span", " (se abre en una nueva pestaña)", "sr-only"));
      msg.append(link);
      row.append(msg, createReopenDecisionButton(card, version, runId));
      panel.append(row);
      box.append(panel);
      return;
    }
    panel.append(element("p", `${closure.titulo}. El dictamen VERIFICADO permite cerrar la tarea abierta en Boards.`, "gov-title"));
    const closeBtn = element("button", `Cerrar ${closure.referencia} en Azure Boards`, "btn-approve");
    closeBtn.type = "button";
    closeBtn.addEventListener("click", async () => {
      closeBtn.disabled = true;
      setStatus(`Cerrando ${closure.referencia} en Azure Boards…`, "busy");
      try {
        const res = await fetch("/api/acciones", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ejecucion: runId, decision: "cerrar", nota: `Certificado en verde (${version})` }),
        });
        const data = await readJson(res);
        if (!res.ok) throw new Error(data.error || "No se pudo cerrar la tarea en Azure Boards.");
        const currentReport = reportsByVersion.get(version);
        if (currentReport) {
          currentReport.cierre_ciclo_boards = data.cierre_ciclo_boards;
          if (data.etapas_devsecops?.length) currentReport.etapas_devsecops = data.etapas_devsecops;
        }
        renderGovernance(card, version, runId, null, true, data.cierre_ciclo_boards);
        refreshStageViews();
        refreshAnalyticsStrip();
        setStatus(`Tarea ${closure.referencia} cerrada en Azure Boards con evidencia certificada.`, "pass");
      } catch (err) {
        closeBtn.disabled = false;
        setStatus(describeFetchError(err, "No se pudo cerrar la tarea en Azure Boards."), "error");
      }
    });
    panel.append(closeBtn);
    box.append(panel);
    return;
  }

  if (!action) {
    box.append(element("p", "Conforme con REN-001: no requiere acción correctiva en Azure Boards.", "gov-clean-note"));
    return;
  }

  const panel = element("div", null, "gov-panel");
  panel.dataset.state = action.estado;

  const header = element("div", null, "gov-head");
  const heading = element("span", null, "gov-heading");
  heading.append(svgIcon("doc", 14), element("span", "Gobernanza · Azure Boards"));
  header.append(heading);
  if (action.tag_idempotencia) {
    const fp = element("span", null, "gov-fingerprint");
    fp.append(
      termText("span", "Huella anti-duplicados (WIQL)", "gov-fingerprint-label"),
      createCopyButton(action.tag_idempotencia, action.tag_idempotencia, `${action.tag_idempotencia}: copiar huella anti-duplicados de ${version}`)
    );
    header.append(fp);
  }
  panel.append(header);
  if (action.titulo) panel.append(element("p", action.titulo, "gov-title"));

  if (action.estado === "APROBADA" && action.boards_resultado) {
    const br = action.boards_resultado;
    const row = element("div", null, "gov-resolved-row");
    const msg = element("p", `Tarea ${br.operacion} sin duplicados en Boards: `, "gov-result");
    msg.tabIndex = -1;
    const link = document.createElement("a");
    link.href = br.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.append(element("span", br.referencia), element("span", " (se abre en una nueva pestaña)", "sr-only"));
    msg.append(link);
    row.append(msg, createReopenDecisionButton(card, version, runId));
    panel.append(row);
    box.append(panel);
    if (focusResult) msg.focus({ preventScroll: true });
    return;
  }

  if (action.estado === "DESCARTADA") {
    const row = element("div", null, "gov-resolved-row");
    const msg = element("p", `Recomendación descartada. Motivo registrado: ${action.nota_humana || "Sin nota adicional"}`, "gov-result");
    msg.tabIndex = -1;
    row.append(msg, createReopenDecisionButton(card, version, runId));
    panel.append(row);
    box.append(panel);
    if (focusResult) msg.focus({ preventScroll: true });
    return;
  }

  const inputId = `gov-note-${version}`;
  const fieldWrap = element("div", null, "gov-field");
  const label = element("label", "Nota de auditoría o justificación (obligatoria para descartar)");
  label.htmlFor = inputId;
  const noteInput = document.createElement("input");
  noteInput.type = "text";
  noteInput.id = inputId;
  noteInput.className = "gov-input";
  noteInput.maxLength = 300;
  noteInput.placeholder = "Ej. Cubrir el caso cancelado este sprint";
  fieldWrap.append(label, noteInput);

  const errorBox = element("div", null, "gov-error");
  errorBox.id = `gov-error-${version}`;
  errorBox.hidden = true;
  errorBox.setAttribute("role", "alert");
  noteInput.setAttribute("aria-describedby", errorBox.id);
  noteInput.addEventListener("input", () => {
    if (noteInput.value.trim() && noteInput.getAttribute("aria-invalid") === "true") {
      noteInput.removeAttribute("aria-invalid");
      errorBox.hidden = true;
    }
  });

  const actionsRow = element("div", null, "gov-buttons");
  const approveBtn = element("button", "Aprobar en Azure Boards", "btn-approve");
  approveBtn.type = "button";
  const dismissBtn = element("button", "Descartar", "btn-dismiss");
  dismissBtn.type = "button";
  actionsRow.append(approveBtn, dismissBtn);

  const confirmBox = element("div", null, "gov-confirm-box");
  confirmBox.hidden = true;
  confirmBox.setAttribute("role", "group");
  confirmBox.setAttribute("aria-label", "Confirmación de decisión de gobernanza");
  confirmBox.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    event.stopPropagation();
    confirmBox.querySelector(".btn-dismiss")?.click();
  });

  let pendingDecision = null;

  const submitDecision = async (decision) => {
    errorBox.hidden = true;
    const progress = element("p", null, "gov-progress");
    progress.append(svgIcon("dots", 14), element("span", decision === "aprobar"
      ? `Enviando a Azure Boards bajo AB#${action.historia_padre || 1}${action.tag_idempotencia ? ` · huella ${action.tag_idempotencia}` : ""}…`
      : "Registrando el descarte en el punto de control…"));
    confirmBox.replaceChildren(progress);
    confirmBox.hidden = false;
    panel.setAttribute("aria-busy", "true");
    approveBtn.disabled = true;
    dismissBtn.disabled = true;
    noteInput.disabled = true;
    setStatus(
      decision === "aprobar"
        ? `Sincronizando tarea en Azure Boards para ${version}…`
        : `Registrando descarte permanente para ${version}…`,
      "busy"
    );

    try {
      const res = await fetch("/api/acciones", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ejecucion: runId, decision, nota: noteInput.value.trim() }),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.error || "No se pudo actualizar la decisión en el punto de control.");

      const currentReport = reportsByVersion.get(version);
      if (currentReport) {
        currentReport.accion_propuesta = data.accion_propuesta;
        if (data.etapas_devsecops?.length) currentReport.etapas_devsecops = data.etapas_devsecops;
      }
      renderGovernance(card, version, runId, data.accion_propuesta, true);
      refreshStageViews();
      refreshAnalyticsStrip();
      setStatus(
        decision === "aprobar"
          ? `Tarea sincronizada en Azure Boards (${data.accion_propuesta?.boards_resultado?.referencia || "OK"})`
          : `Recomendación descartada y firmada en el punto de control de ${version}.`,
        "pass"
      );
    } catch (err) {
      panel.removeAttribute("aria-busy");
      confirmBox.hidden = true;
      approveBtn.disabled = false;
      dismissBtn.disabled = false;
      noteInput.disabled = false;
      actionsRow.hidden = false;
      const message = describeFetchError(err, "No se pudo registrar la decisión en el punto de control; tu nota se conservó.");
      errorBox.replaceChildren(element("span", message));
      const retry = element("button", "Reintentar", "btn-inline-action");
      retry.type = "button";
      retry.addEventListener("click", () => submitDecision(decision));
      errorBox.append(retry);
      errorBox.hidden = false;
      setStatus(message, "error");
    }
  };

  const startGrace = (decision) => {
    let left = 5;
    confirmBox.replaceChildren();
    const msg = element("p", null, "gov-grace-text");
    const undoBtn = element("button", "Deshacer", "btn-dismiss gov-grace-undo");
    undoBtn.type = "button";
    card.dataset.grace = "true";
    const say = () => {
      msg.textContent = decision === "aprobar"
        ? `Se enviará a Azure Boards en ${left} s.`
        : `El descarte se registrará en ${left} s.`;
    };
    say();
    const timer = setInterval(() => {
      left -= 1;
      if (left > 0) return say();
      clearInterval(timer);
      delete card.dataset.grace;
      submitDecision(decision);
    }, 1000);
    undoBtn.addEventListener("click", () => {
      clearInterval(timer);
      delete card.dataset.grace;
      confirmBox.hidden = true;
      actionsRow.hidden = false;
      (decision === "aprobar" ? approveBtn : dismissBtn).focus();
      pendingDecision = null;
      announce("Decisión deshecha: no se envió nada a Azure Boards.");
    });
    confirmBox.append(msg, undoBtn);
    undoBtn.focus();
    announce(`${msg.textContent} Pulsa Deshacer para cancelar.`);
  };

  const askConfirmation = (decision) => {
    errorBox.hidden = true;
    if (decision === "descartar" && !noteInput.value.trim()) {
      errorBox.replaceChildren(element("span", "Escribe un motivo en el campo de nota antes de descartar permanentemente esta brecha."));
      errorBox.hidden = false;
      noteInput.setAttribute("aria-invalid", "true");
      noteInput.focus();
      return;
    }
    noteInput.removeAttribute("aria-invalid");
    pendingDecision = decision;
    actionsRow.hidden = true;
    confirmBox.replaceChildren();
    const promptText = decision === "aprobar"
      ? `¿Confirmas sincronizar en Azure Boards bajo la historia AB#${action.historia_padre || 1}? Si ya existe una tarea con la huella ${action.tag_idempotencia || "idempotente"}, se actualiza; si no, se crea una nueva.`
      : "¿Confirmas descartar esta acción? Esta resolución bloquea permanentemente el punto de control de esta corrida.";
    const bar = element("div", null, "gov-confirm-bar");
    const confirmBtn = element(
      "button",
      decision === "aprobar" ? "Confirmar envío a Boards" : "Confirmar descarte",
      decision === "aprobar" ? "btn-approve" : "btn-danger"
    );
    confirmBtn.type = "button";
    confirmBtn.addEventListener("click", () => startGrace(pendingDecision));

    const cancelConfirmBtn = element("button", "Cancelar", "btn-dismiss");
    cancelConfirmBtn.type = "button";
    cancelConfirmBtn.addEventListener("click", () => {
      confirmBox.hidden = true;
      actionsRow.hidden = false;
      (pendingDecision === "aprobar" ? approveBtn : dismissBtn).focus();
      pendingDecision = null;
    });

    bar.append(confirmBtn, cancelConfirmBtn);
    const prompt = element("p", promptText);
    prompt.id = `gov-confirm-${version}`;
    confirmBtn.setAttribute("aria-describedby", prompt.id);
    cancelConfirmBtn.setAttribute("aria-describedby", prompt.id);
    confirmBox.append(prompt, bar);
    confirmBox.hidden = false;
    // Safe default: a stray Enter cancels instead of writing to Boards.
    cancelConfirmBtn.focus();
  };

  approveBtn.addEventListener("click", () => askConfirmation("aprobar"));
  dismissBtn.addEventListener("click", () => askConfirmation("descartar"));

  panel.append(fieldWrap, errorBox, actionsRow, confirmBox);
  box.append(panel);
}

function syncVulnPayload(data, currentVer) {
  if (data.sonarqube) {
    sonarCloudCache = data.sonarqube;
  }
  if (data.vulnerabilidades) {
    vulnerabilitiesByVersion = data.vulnerabilidades;
  } else if (data.reporte_vulnerabilidades && currentVer) {
    vulnerabilitiesByVersion[currentVer] = data.reporte_vulnerabilidades;
  }
  if (data.ultimos) {
    cachedLatest = data.ultimos;
    for (const [ver, rep] of Object.entries(data.ultimos)) {
      if (rep.sonarqube) sonarCloudCache = rep.sonarqube;
      if (reportsByVersion.has(ver)) {
        const current = reportsByVersion.get(ver);
        current.reporte_vulnerabilidades = rep.reporte_vulnerabilidades;
        if (rep.sonarqube) current.sonarqube = rep.sonarqube;
        if (rep.etapas_devsecops?.length) current.etapas_devsecops = rep.etapas_devsecops;
      }
    }
  }
  refreshStageViews();
}

function renderStage3VulnReport(parent, version) {
  const vscan = vulnerabilitiesByVersion[version] || reportsByVersion.get(version)?.reporte_vulnerabilidades;
  if (!vscan || !Array.isArray(vscan.hallazgos)) return;

  const section = element("div", null, "vuln-section");
  const headBar = element("div", null, "vuln-head-bar");
  headBar.append(
    element("h4", `Reporte formal de vulnerabilidades · ${vscan.abiertas} abiertas · ${vscan.mitigadas}/${vscan.total} mitigadas`, "inspector-compare-title")
  );
  if (vscan.abiertas > 0) {
    const jumpAllBtn = element("button", "Ir a Etapa 8 · Remediación con Agente SecOps →", "btn-primary");
    jumpAllBtn.type = "button";
    jumpAllBtn.addEventListener("click", () => {
      const firstOpen = vscan.hallazgos.find((h) => h.estado === "abierta");
      if (firstOpen) selectedVulnForStage8 = firstOpen.id;
      openStageInspector(8, version);
    });
    headBar.append(jumpAllBtn);
  }
  section.append(headBar);

  const wrapper = element("div", null, "table-wrapper vuln-table-wrap");
  wrapper.tabIndex = 0;
  wrapper.setAttribute("role", "region");
  wrapper.setAttribute("aria-labelledby", "vuln-table-caption");

  const table = element("table", null, "vuln-table");
  const caption = element("caption", `Hallazgos correlacionados (SonarQube · Trivy · OWASP) en ${version}`);
  caption.id = "vuln-table-caption";
  table.append(caption);

  const curRep = reportsByVersion.get(version);
  const sonarReport = curRep?.sonarqube || curRep?.devsecops?.sonarqube || sonarCloudCache;
  const trivyData = vscan.trivy;
  if (sonarReport?.disponible || trivyData) {
    const enginesGrid = element("div", null, "scanner-engines-grid");
    if (sonarReport?.disponible) {
      const sCard = element("div", null, "scanner-card");
      sCard.append(
        element("strong", `SonarQube Cloud · Quality Gate: ${sonarReport.quality_gate}`),
        element(
          "span",
          `Seguridad ${sonarReport.rating_seguridad} (${sonarReport.vulnerabilidades} vuln) · Confiabilidad ${sonarReport.rating_confiabilidad} (${sonarReport.bugs} bugs) · Mantenibilidad ${sonarReport.rating_mantenibilidad} · Dup. ${sonarReport.duplicacion_pct}%`
        )
      );
      if (sonarReport.url) {
        const sLink = document.createElement("a");
        sLink.href = sonarReport.url;
        sLink.target = "_blank";
        sLink.rel = "noopener";
        sLink.append(element("span", "Abrir dashboard en SonarCloud"), element("span", " (se abre en una nueva pestaña)", "sr-only"));
        sCard.append(sLink);
      }
      enginesGrid.append(sCard);
    }
    if (trivyData) {
      const tCard = element("div", null, "scanner-card");
      tCard.append(
        element("strong", `Aqua Trivy · ${trivyData.disponible ? "Escaneo CLI en vivo" : "Pipeline SARIF"}`),
        element(
          "span",
          trivyData.disponible
            ? `${trivyData.misconfiguraciones_totales} misconfiguraciones IaC/Docker (${trivyData.misconfiguraciones_altas} HIGH) · ${trivyData.cves_sca} CVEs en paquetes`
            : trivyData.modo
        )
      );
      enginesGrid.append(tCard);
    }
    section.append(enginesGrid);
  }

  const thead = document.createElement("thead");
  const htr = document.createElement("tr");
  for (const colTitle of ["Vulnerabilidad / Motor", "Severidad", "Ubicación", "Estado", "Acción"]) {
    const th = element("th", colTitle);
    th.scope = "col";
    htr.append(th);
  }
  thead.append(htr);

  const tbody = document.createElement("tbody");
  for (const item of vscan.hallazgos) {
    const tr = document.createElement("tr");
    const rowTh = document.createElement("th");
    rowTh.scope = "row";
    const titleWrap = element("div", null, "vuln-row-title");
    const topLine = element("div", null, "scope-tags");
    topLine.append(
      element("strong", `${item.id} · ${item.categoria}`),
      element("span", item.motor || "SecOps", "motor-pill")
    );
    titleWrap.append(
      topLine,
      element("span", `${item.titulo} (${item.regla})`)
    );
    rowTh.append(titleWrap);

    const tdSev = document.createElement("td");
    const sevBadge = element("span", null, "severity-badge");
    sevBadge.dataset.level = severityLevel(item.severidad);
    sevBadge.append(
      svgIcon(sevBadge.dataset.level === "high" ? "bang" : "warn", 12),
      element("span", item.severidad)
    );
    tdSev.append(sevBadge);

    const tdLoc = document.createElement("td");
    tdLoc.append(element("code", `${item.archivo}:${item.linea}`));

    const tdState = document.createElement("td");
    const stBadge = element("span", null, "badge");
    setBadge(stBadge, item.estado === "mitigada" ? "pass" : "fail", item.estado === "mitigada" ? "Mitigada" : "Abierta");
    tdState.append(stBadge);

    const tdAct = document.createElement("td");
    const goBtn = element(
      "button",
      item.estado === "abierta" ? "Corregir en Etapa 8 →" : "Gestionar en Etapa 8",
      item.estado === "abierta" ? "btn-secondary" : "btn-ghost"
    );
    goBtn.type = "button";
    goBtn.addEventListener("click", () => {
      selectedVulnForStage8 = item.id;
      openStageInspector(8, version);
    });
    tdAct.append(goBtn);

    tr.append(rowTh, tdSev, tdLoc, tdState, tdAct);
    tbody.append(tr);
  }

  table.append(thead, tbody);
  wrapper.append(table);
  section.append(wrapper);
  parent.append(section);
}

function renderStage8SecOpsWorkbench(parent, version) {
  const vscan = vulnerabilitiesByVersion[version] || reportsByVersion.get(version)?.reporte_vulnerabilidades;
  if (!vscan || !Array.isArray(vscan.hallazgos)) return;

  const bench = element("div", null, "secops-workbench");
  const headBar = element("div", null, "vuln-head-bar");
  headBar.append(
    element(
      "h4",
      `Mesa de remediación SecOps con Agente IA (Etapa 3 → Etapa 8) · ${vscan.abiertas} abiertas · ${vscan.mitigadas}/${vscan.total} mitigadas`,
      "inspector-compare-title"
    )
  );
  const backStage3Btn = element("button", "← Ver reporte en Etapa 3", "btn-ghost");
  backStage3Btn.type = "button";
  backStage3Btn.addEventListener("click", () => openStageInspector(3, version));
  headBar.append(backStage3Btn);
  bench.append(headBar);

  const controlsRow = element("div", null, "secops-controls-grid");
  const selectWrap = element("div", null, "field-group");
  const selectLabel = element("label", "Vulnerabilidad detectada en Etapa 3");
  selectLabel.htmlFor = "secops-vuln-select";
  const selectEl = document.createElement("select");
  selectEl.id = "secops-vuln-select";
  for (const h of vscan.hallazgos) {
    const opt = document.createElement("option");
    opt.value = h.id;
    opt.textContent = `[${h.estado === "mitigada" ? "Mitigada" : "Abierta · " + h.severidad}] ${h.id} — ${h.titulo} (${h.archivo})`;
    if (h.id === selectedVulnForStage8) opt.selected = true;
    selectEl.append(opt);
  }
  selectWrap.append(selectLabel, selectEl);

  const quickButtons = element("div", null, "rem-actions");
  const agentDraftBtn = element("button", "Investigar con Agente SecOps (Foundry)", "btn-primary");
  agentDraftBtn.type = "button";
  const detDraftBtn = element("button", "Parche determinista · 0 tokens", "btn-secondary");
  detDraftBtn.type = "button";
  quickButtons.append(agentDraftBtn, detDraftBtn);

  if (vscan.abiertas > 1) {
    const fixAllBtn = element("button", `Mitigar las ${vscan.abiertas} abiertas en lote`, "btn-ghost");
    fixAllBtn.type = "button";
    fixAllBtn.addEventListener("click", async () => {
      if (fixAllBtn.dataset.armed !== "true") {
        arm(fixAllBtn, "Confirmar mitigación en lote + reauditoría");
        return;
      }
      disarm(fixAllBtn);
      fixAllBtn.disabled = true;
      setStatus("Aplicando endurecimiento SecOps en lote y reauditando Etapa 3…", "busy");
      try {
        const res = await fetch("/api/vulnerabilidades/aplicar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: "TODAS", version, origen: "lote_secops" }),
        });
        const data = await readJson(res);
        if (!res.ok) throw new Error(data.error || "No se pudo aplicar la mitigación en lote.");
        syncVulnPayload(data, version);
        openStageInspector(8, version, null, { refresh: true });
        setStatus("Las 4 vulnerabilidades fueron mitigadas y la Etapa 3 quedó en estado Verificado.", "pass");
      } catch (err) {
        fixAllBtn.disabled = false;
        setStatus(describeFetchError(err, "No se pudo completar la mitigación en lote."), "error");
      }
    });
    quickButtons.append(fixAllBtn);
  }

  controlsRow.append(selectWrap, quickButtons);
  bench.append(controlsRow);

  const statusSlot = element("div");
  const outBox = element("div", null, "rem-output");
  outBox.hidden = true;
  bench.append(statusSlot, outBox);

  const refreshSelectedStatus = () => {
    statusSlot.replaceChildren();
    const current = vscan.hallazgos.find((x) => x.id === selectEl.value) || vscan.hallazgos[0];
    if (!current) return;
    selectedVulnForStage8 = current.id;

    if (current.estado === "mitigada") {
      const b = element("div", null, "rem-state-banner");
      b.dataset.tone = "pass";
      b.append(element("span", `${current.id} mitigada en ${current.archivo} · Etapa 3 verificada para este control`));
      const revBtn = element("button", "Revertir mitigación", "btn-secondary");
      revBtn.type = "button";
      revBtn.addEventListener("click", async () => {
        if (revBtn.dataset.armed !== "true") {
          arm(revBtn, "¿Restaurar estado vulnerable? Pulsa otra vez");
          return;
        }
        disarm(revBtn);
        revBtn.disabled = true;
        setStatus(`Restaurando archivo original de ${current.id}…`, "busy");
        try {
          const res = await fetch("/api/vulnerabilidades/revertir", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: current.id, version }),
          });
          const data = await readJson(res);
          if (!res.ok) throw new Error(data.error || "No se pudo revertir la mitigación.");
          syncVulnPayload(data, version);
          openStageInspector(8, version, null, { refresh: true });
          setStatus(`Mitigación de ${current.id} revertida para nueva demostración.`, "pass");
        } catch (err) {
          revBtn.disabled = false;
          setStatus(describeFetchError(err, "No se pudo revertir la mitigación."), "error");
        }
      });
      b.append(revBtn);
      statusSlot.append(b);
    }

    if (current.pr_activo) {
      const prB = element("div", null, "rem-state-banner");
      const prSpan = element("span", "PR SecOps abierto en GitHub: ");
      const prLink = document.createElement("a");
      prLink.href = current.pr_activo.url;
      prLink.target = "_blank";
      prLink.rel = "noopener";
      prLink.append(
        element("span", `PR #${current.pr_activo.numero} (${current.pr_activo.rama})`),
        element("span", " (se abre en una nueva pestaña)", "sr-only")
      );
      prSpan.append(prLink);
      const closePrBtn = element("button", "Cerrar PR SecOps", "btn-ghost");
      closePrBtn.type = "button";
      closePrBtn.addEventListener("click", async () => {
        if (closePrBtn.dataset.armed !== "true") {
          arm(closePrBtn, "¿Cerrar PR SecOps? Pulsa otra vez");
          return;
        }
        disarm(closePrBtn);
        closePrBtn.disabled = true;
        try {
          const res = await fetch("/api/vulnerabilidades/pr/cerrar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: current.id, version }),
          });
          const data = await readJson(res);
          if (!res.ok) throw new Error(data.error || "No se pudo cerrar el PR SecOps.");
          syncVulnPayload(data, version);
          openStageInspector(8, version, null, { refresh: true });
          setStatus(`PR SecOps #${current.pr_activo.numero} cerrado y rama eliminada.`, "pass");
        } catch (err) {
          closePrBtn.disabled = false;
          setStatus(describeFetchError(err, "No se pudo cerrar el PR SecOps."), "error");
        }
      });
      prB.append(prSpan, closePrBtn);
      statusSlot.append(prB);
    }
  };

  selectEl.addEventListener("change", () => {
    outBox.hidden = true;
    refreshSelectedStatus();
  });
  refreshSelectedStatus();

  const requestVulnDraft = async (useAi, btn) => {
    if (useAi && !confirmPaidRun(btn, 1, "agente")) return;
    const chosenId = selectEl.value;
    agentDraftBtn.disabled = true;
    detDraftBtn.disabled = true;
    setStatus(
      useAi
        ? `Agente SecOps (Azure AI Foundry) inspeccionando ${chosenId} y diseñando mitigación…`
        : `Generando parche determinista de seguridad para ${chosenId}…`,
      "busy"
    );
    try {
      const res = await fetch("/api/vulnerabilidades/remediar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: chosenId, version, usar_ia: useAi }),
      });
      const draft = await readJson(res);
      if (!res.ok) throw new Error(draft.error || "No se pudo generar la propuesta SecOps.");
      outBox.replaceChildren();
      const originLabel = draft.origen === "agente_secops_ia"
        ? `Agente SecOps IA (${draft.proveedor || "Foundry"})`
        : "Política determinista SecOps (0 tokens)";
      outBox.append(
        element("p", `${originLabel} · ${draft.id} (${draft.regla}) · ${draft.archivo}`, "rem-file"),
        element("p", `Riesgo: ${draft.analisis_riesgo}`, "source-ref-line"),
        element("p", `Mitigación: ${draft.estrategia_mitigacion}`, "source-ref-line")
      );
      if (draft.traza_herramientas?.length) {
        outBox.append(element("p", `Herramientas invocadas por el agente: ${draft.traza_herramientas.join(" → ")}`, "rem-disclaimer"));
      }
      if (draft.nota_ia) outBox.append(element("p", draft.nota_ia, "rem-disclaimer"));

      const snippetId = `secops-code-${chosenId.toLowerCase()}`;
      const copyWrap = element("div", null, "copyable");
      const copySpan = element("span", null, "copy");
      const copyBtn = element("button", null, "copy-button");
      copyBtn.type = "button";
      copyBtn.setAttribute("command", "--copy");
      copyBtn.setAttribute("commandfor", snippetId);
      copyBtn.setAttribute("aria-label", `Copiar parche SecOps para ${chosenId}`);
      const iconSpan = element("span", null, "icon");
      iconSpan.setAttribute("aria-hidden", "true");
      iconSpan.append(svgIcon("copy", 13));
      copyBtn.append(iconSpan, element("span", "Copiar parche"));
      const tip = element("span", "", "tip");
      tip.setAttribute("role", "status");
      copySpan.append(copyBtn, tip);

      const pre = element("pre", null, "rem-pre");
      pre.tabIndex = 0;
      const code = element("code", draft.codigo_sugerido);
      code.id = snippetId;
      pre.append(code);
      copyWrap.append(copySpan, pre);
      outBox.append(copyWrap);

      const execBar = element("div", null, "rem-exec-bar");
      const applySecBtn = element("button", "Aplicar mitigación y reauditar Etapa 3", "btn-approve");
      applySecBtn.type = "button";
      applySecBtn.addEventListener("click", async () => {
        if (applySecBtn.dataset.armed !== "true") {
          arm(applySecBtn, `Confirmar endurecimiento en ${draft.archivo}`);
          return;
        }
        disarm(applySecBtn);
        applySecBtn.disabled = true;
        prSecBtn.disabled = true;
        setStatus(`Aplicando mitigación de ${chosenId} y reauditando Etapa 3…`, "busy");
        try {
          const r2 = await fetch("/api/vulnerabilidades/aplicar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: chosenId, version, origen: draft.origen }),
          });
          const d2 = await readJson(r2);
          if (!r2.ok) throw new Error(d2.error || "No se pudo aplicar la mitigación.");
          syncVulnPayload(d2, version);
          openStageInspector(8, version, null, { refresh: true });
          const leftOpen = d2.reporte_vulnerabilidades?.abiertas ?? 0;
          setStatus(
            `${chosenId} mitigada y verificada en Etapa 3 (${leftOpen} vulnerabilidad(es) restantes).`,
            "pass"
          );
        } catch (err) {
          applySecBtn.disabled = false;
          prSecBtn.disabled = false;
          setStatus(describeFetchError(err, "No se pudo aplicar la mitigación."), "error");
        }
      });

      const prSecBtn = element("button", "Abrir PR SecOps en GitHub", "btn-secondary");
      prSecBtn.type = "button";
      prSecBtn.addEventListener("click", async () => {
        if (prSecBtn.dataset.armed !== "true") {
          arm(prSecBtn, "Confirmar creación de rama + PR SecOps");
          return;
        }
        disarm(prSecBtn);
        prSecBtn.disabled = true;
        applySecBtn.disabled = true;
        setStatus(`Creando rama y Pull Request SecOps en GitHub para ${chosenId}…`, "busy");
        try {
          const r3 = await fetch("/api/vulnerabilidades/pr", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: chosenId, version }),
          });
          const d3 = await readJson(r3);
          if (!r3.ok) throw new Error(d3.error || "No se pudo abrir el PR SecOps.");
          syncVulnPayload(d3, version);
          openStageInspector(8, version, null, { refresh: true });
          setStatus(`PR SecOps #${d3.pr?.numero} abierto en GitHub para ${chosenId}.`, "pass");
        } catch (err) {
          prSecBtn.disabled = false;
          applySecBtn.disabled = false;
          setStatus(describeFetchError(err, "No se pudo crear el PR SecOps."), "error");
        }
      });

      execBar.append(applySecBtn, prSecBtn);
      outBox.append(execBar);
      outBox.hidden = false;
      setStatus(`Propuesta SecOps lista para ${chosenId}.`, "pass");
    } catch (err) {
      setStatus(describeFetchError(err, "No se pudo obtener la propuesta SecOps."), "error");
    } finally {
      agentDraftBtn.disabled = false;
      detDraftBtn.disabled = false;
    }
  };

  agentDraftBtn.addEventListener("click", () => requestVulnDraft(true, agentDraftBtn));
  detDraftBtn.addEventListener("click", () => requestVulnDraft(false, detDraftBtn));

  parent.append(bench);
}

function renderStage8PlaceholderHook() {}

function renderRemediation(card, version, report) {
  const container = card.querySelector(".remediation");
  if (!container) return;
  container.replaceChildren();
  const runId = report.ejecucion?.id;
  const localPatch = activeRemediationState.parches_locales?.[version];
  const ephemeralPr = activeRemediationState.prs_efimeros?.[version];
  const hasGap = Boolean(runId && report.veredicto !== "VERIFICADO");

  if (!hasGap && !localPatch && !ephemeralPr) return;

  const panel = element("div", null, "rem-panel");
  const head = element("div", null, "rem-head");
  const title = element("span", null, "gov-heading");
  title.append(svgIcon("info", 14), element("span", "Remediación de código · C# / GitOps"));
  head.append(title);
  panel.append(head);

  if (localPatch) {
    const patchBanner = element("div", null, "rem-state-banner");
    patchBanner.dataset.tone = "pass";
    patchBanner.append(
      element("span", `Código aplicado en local (${localPatch.archivo}) · respaldo original guardado`)
    );
    const revertBtn = element("button", "Revertir código original y reevaluar", "btn-secondary");
    revertBtn.type = "button";
    revertBtn.addEventListener("click", async () => {
      if (activeController) return;
      if (revertBtn.dataset.armed !== "true") {
        arm(revertBtn, "¿Restaurar C# original? Pulsa otra vez");
        return;
      }
      disarm(revertBtn);
      revertBtn.disabled = true;
      setStatus(`Restaurando archivo C# original de ${version} y reevaluando con dotnet test…`, "busy");
      try {
        const res = await fetch("/api/remediacion/revertir", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version, modo: form.elements.modo.value, reevaluar: true }),
        });
        const data = await readJson(res);
        if (!res.ok) throw new Error(data.error || "No se pudo revertir el archivo C#.");
        if (data.remediacion_activa) activeRemediationState = data.remediacion_activa;
    if (data.vulnerabilidades) vulnerabilitiesByVersion = data.vulnerabilidades;
        if (data.analitica) renderValueKpis(data.analitica);
        if (data.informe) {
          cachedLatest[version] = { ...data.informe, registrado_ms: Date.now() };
          showReport(card, version, data.informe, { isLive: true, timestampMs: Date.now(), stamp: true });
        }
        setStatus(`Código original de ${version} restaurado y reevaluado (${data.informe?.veredicto || "OK"}).`, "pass");
      } catch (err) {
        revertBtn.disabled = false;
        setStatus(describeFetchError(err, "No se pudo revertir la remediación local."), "error");
      }
    });
    patchBanner.append(revertBtn);
    panel.append(patchBanner);
  }

  if (ephemeralPr) {
    const prBanner = element("div", null, "rem-state-banner");
    const prCopy = element("span");
    prCopy.append("Pull Request efímero abierto en GitHub: ");
    const prLink = document.createElement("a");
    prLink.href = ephemeralPr.url;
    prLink.target = "_blank";
    prLink.rel = "noopener";
    prLink.append(
      element("span", `PR #${ephemeralPr.numero} (${ephemeralPr.rama})`),
      element("span", " (se abre en una nueva pestaña)", "sr-only")
    );
    prCopy.append(prLink);
    const closePrBtn = element("button", "Cerrar PR y borrar rama", "btn-ghost");
    closePrBtn.type = "button";
    closePrBtn.addEventListener("click", async () => {
      if (closePrBtn.dataset.armed !== "true") {
        arm(closePrBtn, "¿Cerrar PR demo? Pulsa otra vez");
        return;
      }
      disarm(closePrBtn);
      closePrBtn.disabled = true;
      setStatus(`Cerrando PR #${ephemeralPr.numero} y eliminando rama ${ephemeralPr.rama} en GitHub…`, "busy");
      try {
        const res = await fetch("/api/remediacion/pr/cerrar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version }),
        });
        const data = await readJson(res);
        if (!res.ok) throw new Error(data.error || "No se pudo cerrar el PR en GitHub.");
        if (data.remediacion_activa) activeRemediationState = data.remediacion_activa;
    if (data.vulnerabilidades) vulnerabilitiesByVersion = data.vulnerabilidades;
        renderRemediation(card, version, report);
        setStatus(`PR #${ephemeralPr.numero} cerrado y rama efímera eliminada de GitHub.`, "pass");
      } catch (err) {
        closePrBtn.disabled = false;
        setStatus(describeFetchError(err, "No se pudo cerrar el PR efímero en GitHub."), "error");
      }
    });
    prBanner.append(prCopy, closePrBtn);
    panel.append(prBanner);
  }

  if (!hasGap) {
    container.append(panel);
    return;
  }

  const actions = element("div", null, "rem-actions");
  const detBtn = element("button", "Ver borrador · 0 tokens", "btn-secondary");
  detBtn.type = "button";
  const aiBtn = element("button", "Generar con Azure AI Foundry", "btn-ghost");
  aiBtn.type = "button";
  actions.append(detBtn, aiBtn);

  const outBox = element("div", null, "rem-output");
  outBox.hidden = true;
  let latestSnippet = null;
  let latestUsedAi = false;

  const buildExecutionBar = () => {
    const execBar = element("div", null, "rem-exec-bar");
    const applyLocalBtn = element("button", "Aplicar en local y reevaluar", "btn-approve");
    applyLocalBtn.type = "button";
    applyLocalBtn.addEventListener("click", async () => {
      if (activeController) return;
      if (applyLocalBtn.dataset.armed !== "true") {
        arm(applyLocalBtn, `Confirmar escritura en ${version} y dotnet test`);
        return;
      }
      disarm(applyLocalBtn);
      applyLocalBtn.disabled = true;
      openPrBtn.disabled = true;
      setStatus(`Aplicando cambio C# en ${version} con respaldo reversible y ejecutando dotnet test…`, "busy");
      try {
        const res = await fetch("/api/remediacion/aplicar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ejecucion: runId,
            modo: form.elements.modo.value,
            usar_ia: latestUsedAi,
            codigo: latestSnippet,
          }),
        });
        const data = await readJson(res);
        if (!res.ok) throw new Error(data.error || "No se pudo aplicar la remediación local.");
        if (data.remediacion_activa) activeRemediationState = data.remediacion_activa;
    if (data.vulnerabilidades) vulnerabilitiesByVersion = data.vulnerabilidades;
        if (data.analitica) renderValueKpis(data.analitica);
        if (data.informe) {
          cachedLatest[version] = { ...data.informe, registrado_ms: Date.now() };
          showReport(card, version, data.informe, { isLive: true, timestampMs: Date.now(), stamp: true });
        }
        setStatus(
          `Remediación aplicada en ${data.aplicacion?.archivo || version}: nuevo dictamen ${data.informe?.veredicto || "VERIFICADO"}.`,
          "pass"
        );
      } catch (err) {
        applyLocalBtn.disabled = false;
        openPrBtn.disabled = false;
        setStatus(describeFetchError(err, "No se pudo aplicar la remediación ni reevaluar."), "error");
      }
    });

    const openPrBtn = element("button", "Crear rama y PR en GitHub", "btn-secondary");
    openPrBtn.type = "button";
    openPrBtn.addEventListener("click", async () => {
      if (openPrBtn.dataset.armed !== "true") {
        arm(openPrBtn, "Confirmar creación de rama + PR en GitHub");
        return;
      }
      disarm(openPrBtn);
      openPrBtn.disabled = true;
      applyLocalBtn.disabled = true;
      setStatus(`Creando rama efímera y Pull Request real en GitHub para ${version}…`, "busy");
      try {
        const res = await fetch("/api/remediacion/pr", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ejecucion: runId,
            usar_ia: latestUsedAi,
            codigo: latestSnippet,
          }),
        });
        const data = await readJson(res);
        if (!res.ok) throw new Error(data.error || "No se pudo abrir el Pull Request en GitHub.");
        if (data.remediacion_activa) activeRemediationState = data.remediacion_activa;
    if (data.vulnerabilidades) vulnerabilitiesByVersion = data.vulnerabilidades;
        renderRemediation(card, version, report);
        setStatus(
          `Pull Request #${data.pr?.numero} (${data.operacion}) en GitHub con vínculo AB#1.`,
          "pass"
        );
      } catch (err) {
        openPrBtn.disabled = false;
        applyLocalBtn.disabled = false;
        setStatus(describeFetchError(err, "No se pudo crear el Pull Request en GitHub."), "error");
      }
    });

    execBar.append(applyLocalBtn, openPrBtn);
    return execBar;
  };

  const loadDraft = async (useAi, triggerBtn) => {
    if (useAi && !confirmPaidRun(triggerBtn, 1, "agente")) return;
    detBtn.disabled = true;
    aiBtn.disabled = true;
    setStatus(
      useAi ? `Generando borrador C# con Azure AI Foundry para ${version}…` : `Preparando plantilla determinista C# para ${version}…`,
      "busy"
    );
    try {
      const res = await fetch("/api/remediacion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ejecucion: runId, usar_ia: useAi }),
      });
      const draft = await readJson(res);
      if (!res.ok) throw new Error(draft.error || "No se pudo generar el borrador de remediación.");
      latestSnippet = draft.codigo_sugerido;
      latestUsedAi = useAi;
      outBox.replaceChildren();
      const sourceLabel = draft.origen === "agente_ia"
        ? `Generado por IA (${draft.proveedor || "Foundry"})`
        : "Plantilla determinista verificada (0 tokens)";
      outBox.append(
        element("p", `${sourceLabel} · Archivo objetivo: ${draft.archivo_objetivo}`, "rem-file"),
        element("p", draft.explicacion, "source-ref-line")
      );
      if (draft.nota_ia) outBox.append(element("p", draft.nota_ia, "rem-disclaimer"));

      const codeId = `rem-snippet-${version}`;
      const copyWrap = element("div", null, "copyable");
      const copySpan = element("span", null, "copy");
      const copyBtn = element("button", null, "copy-button");
      copyBtn.type = "button";
      copyBtn.setAttribute("command", "--copy");
      copyBtn.setAttribute("commandfor", codeId);
      copyBtn.setAttribute("aria-label", `Copiar código C# sugerido para ${version}`);
      const iconSpan = element("span", null, "icon");
      iconSpan.setAttribute("aria-hidden", "true");
      iconSpan.append(svgIcon("copy", 13));
      copyBtn.append(iconSpan, element("span", "Copiar C#"));
      const tip = element("span", "", "tip");
      tip.setAttribute("role", "status");
      copySpan.append(copyBtn, tip);

      const pre = element("pre", null, "rem-pre");
      pre.tabIndex = 0;
      const code = element("code", draft.codigo_sugerido);
      code.id = codeId;
      pre.append(code);
      copyWrap.append(copySpan, pre);

      outBox.append(copyWrap, buildExecutionBar(), element("p", draft.advertencia, "rem-disclaimer"));
      outBox.hidden = false;
      setStatus(`Borrador listo para ${version}: podés copiarlo, aplicarlo en local o crear PR en GitHub.`, "pass");
    } catch (err) {
      setStatus(describeFetchError(err, "No se pudo generar el borrador de remediación."), "error");
    } finally {
      detBtn.disabled = false;
      aiBtn.disabled = false;
    }
  };

  detBtn.addEventListener("click", () => loadDraft(false, detBtn));
  aiBtn.addEventListener("click", () => loadDraft(true, aiBtn));

  panel.append(actions, outBox);
  container.append(panel);
}

function renderDownloads(card, report) {
  const downloads = card.querySelector(".downloads");
  downloads.replaceChildren();
  const runId = report.ejecucion?.id;
  if (!runId) return;

  const files = [
    ["informe.md", "Informe", "Informe en Markdown"],
    ["informe.json", "JSON", "Evidencia completa en JSON"],
  ];
  if (report.ejecucion?.trx) files.push(["resultados.trx", "TRX", "Resultados de pruebas en TRX"]);
  if (report.ejecucion?.log) files.push(["dotnet-test.log", "Registro", "Registro de ejecución de dotnet test"]);
  if (report.accion_propuesta) files.push(["checkpoint_aprobacion.json", "Punto de control", "Punto de control de la decisión humana en JSON"]);

  downloads.append(element("span", "Artefactos", "artifact-label"));
  const list = element("ul", null, "artifact-list");
  for (const [file, label, full] of files) {
    const li = document.createElement("li");
    const link = element("a", null, "artifact-link");
    link.href = `/informes/${runId}/${file}`;
    link.target = "_blank";
    link.rel = "noopener";
    link.title = full;
    link.append(element("span", label), element("span", `: ${full} (se abre en una nueva pestaña)`, "sr-only"));
    li.append(link);
    list.append(li);
  }
  downloads.append(list);
}

function showReport(card, version, report, options = {}) {
  const isLive = Boolean(options.isLive);
  const ts = formatTimestamp(options.timestampMs || report.registrado_ms || Date.now());
  const provenanceLabel = isLive
    ? `Ejecución en vivo${ts ? ` · ${ts}` : ""}`
    : `Corrida previa en caché${ts ? ` · ${ts}` : ""}`;

  reportsByVersion.set(version, report);
  if (report.reporte_vulnerabilidades) vulnerabilitiesByVersion[version] = report.reporte_vulnerabilidades;
  provenanceByVersion.set(version, { label: provenanceLabel, isLive });

  const verdictInfo = VERDICT_META[report.veredicto] || { state: "unknown", label: report.veredicto };
  resetCardBands(card, verdictInfo.state, verdictInfo.label, report.justificacion, provenanceLabel, isLive);

  const nextStep = card.querySelector(".next-step");
  if (report.siguiente_paso) {
    nextStep.textContent = `Siguiente paso recomendado: ${report.siguiente_paso}`;
    nextStep.hidden = false;
  }

  renderDeterministicProof(card, report);
  renderAgentInvestigation(card, report);
  renderGovernance(card, version, report.ejecucion?.id, report.accion_propuesta, false, report.cierre_ciclo_boards);
  renderRemediation(card, version, report);
  renderDownloads(card, report);
  refreshStageViews();
  if (options.stamp) replayClass(card, "is-stamped", 820);

  if (!stageInspector.hidden && inspectedStage) {
    openStageInspector(inspectedStage, inspectedVersion, null, { refresh: true });
  }

  const qaState = report.investigacion?.estado;
  return (report.diagnosticos && report.diagnosticos.length > 0)
    || !["COMPLETADA", "SOLO_EVIDENCIA"].includes(qaState);
}

function syncVisibleCardGrid() {
  renderDossierTabs();
}

form.elements.modo.addEventListener("change", () => {
  disarm(runBtn);
  for (const btn of document.querySelectorAll(".card-eval-btn")) {
    disarm(btn);
    btn.textContent = evalLabel(btn.dataset.eval);
  }
  document.querySelector("#mode-help").textContent = form.elements.modo.value === "agente"
    ? "Ejecuta en paralelo los agentes de QA y Seguridad/Operación sobre Azure AI Foundry; el dictamen lo decide siempre la política determinista."
    : "Evalúa la evidencia local y cloud aplicando únicamente la política determinista sin consumir tokens de IA.";
});

filterDiffBtn.addEventListener("click", () => {
  // Remember where focus was so the re-render does not drop it to <body>.
  const active = document.activeElement;
  const focusedStage = ledger.contains(active) ? active.dataset.stage : null;

  filterDiffOnly = !filterDiffOnly;
  filterDiffBtn.setAttribute("aria-pressed", String(filterDiffOnly));
  refreshStageViews();
  syncHash();
  // Row re-entry: short stagger, capped so the whole ledger lands within ~0.4 s.
  ledger.querySelectorAll(".ledger-row, .ledger-empty-row").forEach((node, i) => {
    animateIn(node, { dy: 6, delay: Math.min(i * 40, 200), duration: 220 });
  });
  if (focusedStage) (ledger.querySelector(`.ledger-cell-btn[data-stage="${focusedStage}"]`) || filterDiffBtn).focus();
  announce(filterDiffOnly
    ? "Filtro activo: la matriz muestra solo las etapas incumplidas, sin confirmar, con atención requerida o con una señal por revisar."
    : "Vista completa: las 8 etapas en la matriz.");
});

cancelBtn.addEventListener("click", () => {
  if (activeController) activeController.abort();
});

async function executeAssessment(selectedVersions, mode, options = {}) {
  if (activeController) return;
  activeController = new AbortController();

  const preserveVisible = Boolean(options.preserveVisible);
  const formControls = [...form.querySelectorAll("select, button[type='submit']")];
  formControls.forEach((el) => { el.disabled = true; });
  cancelBtn.hidden = false;
  cancelBtn.disabled = false;
  loadLatestBtn.hidden = true;
  results.setAttribute("aria-busy", "true");
  setRunning(true);

  for (const [version, card] of cards) {
    if (!preserveVisible) {
      card.hidden = !selectedVersions.includes(version);
    } else if (selectedVersions.includes(version)) {
      card.hidden = false;
    }
    if (selectedVersions.includes(version)) {
      const queuedReason = "Preparando entorno aislado de compilación y recolección de artefactos…";
      if (reportsByVersion.has(version)) holdCard(card, "idle", "En cola", queuedReason, "Ejecución en preparación…");
      else resetCardBands(card, "idle", "En cola", queuedReason, "Ejecución en preparación…", false);
    }
  }
  syncVisibleCardGrid();
  refreshStageViews();

  let issues = 0;
  let aborted = false;
  let reachedIndex = -1;

  try {
    for (const [index, version] of selectedVersions.entries()) {
      if (activeController.signal.aborted) {
        aborted = true;
        break;
      }
      reachedIndex = index;
      const card = cards.get(version);
      markRunningVersion(version, index, selectedVersions.length);
      setStatus(`Evaluando ${version} (${index + 1} de ${selectedVersions.length}) · ${mode === "agente" ? "Agentes MAF" : "Solo evidencia"}…`, "busy");
      const runningReason = mode === "agente"
        ? "Ejecutando pruebas xUnit y consultando en paralelo a los agentes de QA y SecOps…"
        : "Ejecutando pruebas xUnit y verificando integridad de fuentes con SHA-256…";
      if (card.dataset.stale === "true") holdCard(card, "busy", "Evaluando", runningReason, "Ejecutando ahora…");
      else resetCardBands(card, "busy", "Evaluando", runningReason, "Ejecutando ahora…", false);
      refreshStageViews();

      try {
        const response = await fetch("/api/evaluar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version, modo: mode }),
          signal: activeController.signal,
        });
        const data = await readJson(response);
        if (!response.ok) throw new Error(data.error || `La evaluación de ${version} no pudo completarse.`);
        cachedLatest[version] = { ...data, registrado_ms: Date.now() };
        if (showReport(card, version, data, { isLive: true, timestampMs: Date.now(), stamp: true })) issues++;
      } catch (error) {
        if (error.name === "AbortError") {
          aborted = true;
          if (cachedLatest[version]) {
            showReport(card, version, cachedLatest[version], { isLive: false });
          } else {
            resetCardBands(card, "idle", "Cancelada", "Evaluación detenida por el usuario.", "Cancelada", false);
          }
          break;
        }
        issues++;
        const message = describeFetchError(error, `La evaluación de ${version} no pudo completarse.`);
        // A failed re-run must not cost the evidence that was on screen: fall back to the last good run.
        if (cachedLatest[version]) showReport(card, version, cachedLatest[version], { isLive: false });
        else resetCardBands(card, "error", "Error de ejecución", message, "Fallo de ejecución", false);
        const alertEl = card.querySelector(".card-alert");
        const offline = error instanceof TypeError;
        const viaAgents = mode === "agente" && !offline;
        const kept = cachedLatest[version] ? " Debajo sigue la última corrida guardada." : "";
        const cause = offline
          ? `El servidor de la consola no respondió durante la evaluación de ${version}.${kept} Comprueba que siga en marcha y reintenta.`
          : viaAgents
            ? `Falló la corrida de ${version} con agentes (${message.replace(/\.$/, "")}).${kept} Puedes repetirla con la evidencia determinista, que no consume tokens.`
            : `La corrida de ${version} no terminó (${message.replace(/\.$/, "")}).${kept} Revisa el registro de la consola y reintenta.`;
        alertEl.replaceChildren(element("span", cause));
        const retryMode = viaAgents ? "solo-evidencia" : mode;
        const retryBtn = element("button", viaAgents ? `Reintentar ${version} con Solo evidencia · 0 tokens` : `Reintentar ${version}`, "btn-inline-action");
        retryBtn.type = "button";
        retryBtn.dataset.eval = version;
        retryBtn.addEventListener("click", () => {
          if (activeController || !confirmPaidRun(retryBtn, 1, retryMode)) return;
          executeAssessment([version], retryMode, { preserveVisible: true });
        });
        alertEl.append(retryBtn);
        alertEl.hidden = false;
      }
    }

    if (aborted) {
      // Deliveries still queued when the run stopped go back to their last cached run, or say plainly they were not evaluated.
      const fromCache = [];
      const notRun = [];
      // The in-flight delivery is settled by its own catch; only the ones never reached are handled here.
      for (const v of selectedVersions.slice(reachedIndex + 1)) {
        const queuedCard = cards.get(v);
        if (cachedLatest[v]) {
          showReport(queuedCard, v, cachedLatest[v], { isLive: false });
          fromCache.push(v);
        } else {
          resetCardBands(queuedCard, "idle", "No evaluada", "La evaluación se detuvo antes de llegar a esta entrega.", "Sin corrida", false);
          notRun.push(v);
        }
      }
      refreshStageViews();
      const parts = ["Evaluación detenida por el usuario."];
      if (fromCache.length) parts.push(`${fromCache.join(" y ")} ${fromCache.length === 1 ? "muestra su" : "muestran su"} última corrida en caché.`);
      if (notRun.length) parts.push(`${notRun.join(" y ")} ${notRun.length === 1 ? "quedó" : "quedaron"} sin evaluar.`);
      setStatus(parts.join(" "), "warn");
    } else if (issues) {
      setStatus(`Evaluación completada con ${issues} ${issues === 1 ? "diagnóstico operativo" : "diagnósticos operativos"}.`, "warn");
    } else {
      const nonPass = selectedVersions.filter((v) => reportsByVersion.get(v)?.veredicto !== "VERIFICADO").length;
      setStatus(
        `Evaluación en vivo completada (${selectedVersions.length} ${selectedVersions.length === 1 ? "entrega" : "entregas"} · ${nonPass} con brecha detectada).`,
        nonPass ? "warn" : "pass"
      );
    }
  } finally {
    activeController = null;
    cancelBtn.hidden = true;
    results.setAttribute("aria-busy", "false");
    formControls.forEach((el) => { el.disabled = false; });
    setRunning(false);
    refreshStageViews();
    refreshAnalyticsStrip();
    loadLatestBtn.hidden = Object.keys(cachedLatest).length === 0;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const mode = form.elements.modo.value;
  const chosen = form.elements.version.value === "todas" ? versions : [form.elements.version.value];
  if (!confirmPaidRun(runBtn, chosen.length)) return;
  await executeAssessment(chosen, mode, { preserveVisible: false });
});

function restoreCachedRuns({ stamp = false } = {}) {
  let count = 0;
  for (const ver of versions) {
    const card = cards.get(ver);
    card.hidden = false;
    if (cachedLatest[ver]) {
      showReport(card, ver, cachedLatest[ver], { isLive: false, timestampMs: cachedLatest[ver].registrado_ms, stamp });
      count++;
    }
  }
  syncVisibleCardGrid();
  loadLatestBtn.hidden = true;
  if (count) {
    setStatus("Mostrando la última corrida guardada de cada entrega. Pulsa «Ejecutar evaluación» para auditar en vivo.", "info");
  } else {
    setStatus("No hay corridas previas almacenadas. Pulsa «Ejecutar evaluación» para auditar las entregas.", "idle");
  }
}

loadLatestBtn.addEventListener("click", () => restoreCachedRuns({ stamp: true }));

// Global Keyboard Accelerators
// Esc peels the topmost layer first; stopping a paid run needs a second Esc within 3 s.
function handleEscape(event) {
  if (!stageInspector.hidden) {
    event.preventDefault();
    closeStageInspector();
    return;
  }
  if (demoResetPanel && !demoResetPanel.hidden) {
    event.preventDefault();
    setDemoResetOpen(false);
    demoResetToggleBtn?.focus();
    return;
  }
  if (!helpDrawer.hidden) {
    event.preventDefault();
    setHelpOpen(false, { restore: true });
    return;
  }
  if (!activeController) return;
  event.preventDefault();
  if (Date.now() < escArmedUntil) {
    escArmedUntil = 0;
    activeController.abort();
    return;
  }
  escArmedUntil = Date.now() + 3000;
  const previous = [status.textContent, statusBanner.dataset.tone];
  const armMessage = "Pulsa Esc otra vez para detener la evaluación en curso.";
  setStatus(armMessage, "warn");
  setTimeout(() => {
    if (status.textContent === armMessage) setStatus(...previous);
  }, 3000);
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    handleEscape(event);
    return;
  }

  const tag = document.activeElement?.tagName;
  if (!shortcutsEnabled || tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || event.metaKey || event.ctrlKey || event.altKey) {
    return;
  }

  if (event.key === "?") {
    event.preventDefault();
    setHelpOpen(helpDrawer.hidden, { restore: true });
  } else if (event.key === "r" || event.key === "R") {
    // R only moves focus to the run button; starting a token-spending run always takes an explicit Enter or click.
    event.preventDefault();
    runBtn.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "nearest" });
    runBtn.focus({ preventScroll: true });
  } else if (event.key === "d" || event.key === "D") {
    event.preventDefault();
    filterDiffBtn.click();
  } else if (event.key >= "1" && event.key <= "8") {
    event.preventDefault();
    openStageInspector(Number(event.key), inspectedVersion);
  } else if ((event.key === "v" || event.key === "V") && !stageInspector.hidden) {
    event.preventDefault();
    const next = versions[(versions.indexOf(inspectedVersion) + 1) % versions.length];
    openStageInspector(inspectedStage, next);
  } else if ((event.key === "ArrowLeft" || event.key === "ArrowRight") && !stageInspector.hidden) {
    event.preventDefault();
    stepInspector(event.key === "ArrowLeft" ? -1 : 1);
  }
});

function reportEcosystemFailure(message) {
  sandboxPill.dataset.active = "false";
  sandboxText.textContent = "Estado de :5080 desconocido";
  sandboxOpenLink.hidden = true;
  stopSandboxBtn.hidden = true;
  setStatus(message, "warn");
  showSandboxError(`${message} Pulsa «Reintentar» para volver a leerlo.`, initEcosystem);
}

async function initEcosystem() {
  initLedger();
  sandboxAlertWrap.hidden = true;
  try {
    const res = await fetch("/api/ecosistema");
    if (!res.ok) {
      reportEcosystemFailure("No se pudo leer el estado del ecosistema; puedes ejecutar una evaluación igualmente.");
      return;
    }
    const data = await readJson(res);
    const eco = data.ecosistema || {};
    cachedLatest = data.ultimos || {};
    for (const rep of Object.values(cachedLatest)) {
      if (rep?.sonarqube) sonarCloudCache = rep.sonarqube;
    }
    if (data.remediacion_activa) activeRemediationState = data.remediacion_activa;
    if (data.vulnerabilidades) vulnerabilitiesByVersion = data.vulnerabilidades;
    if (!sonarCloudCache) {
      fetch("/api/vulnerabilidades")
        .then((r) => (r.ok ? r.json() : null))
        .then((vdata) => {
          if (vdata?.sonarqube) {
            sonarCloudCache = vdata.sonarqube;
            if (inspectedStage === 3) openStageInspector(3, inspectedVersion, null, { refresh: true });
          }
        })
        .catch(() => {});
    }
    if (data.analitica) renderValueKpis(data.analitica);
    syncArchiveRestoreButton(data.archivos_demo || []);

    const navMap = [
      ["#nav-boards", eco.boards_url],
      ["#nav-pr", eco.github_pr_url],
      ["#nav-sec", eco.github_security_url],
      ["#nav-sonar", eco.sonarqube_url],
      ["#nav-powerbi", eco.powerbi_web_url || data.powerbi?.report_url],
    ];
    for (const [sel, url] of navMap) {
      const link = document.querySelector(sel);
      if (!link) continue;
      if (url) {
        link.href = url;
        link.hidden = false;
      }
    }

    if (eco.powerbi_web_url || data.powerbi?.report_url) {
      updatePowerBiNavLink(eco.powerbi_web_url || data.powerbi.report_url);
    }
    updateSandboxBanner(eco.sandbox);

    const params = new URLSearchParams(window.location.search);
    const autoVer = params.get("autoevaluar");
    if (Object.keys(cachedLatest).length > 0) {
      loadLatestBtn.hidden = false;
      if (!versions.includes(autoVer)) {
        form.elements.modo.value = "solo-evidencia";
        form.elements.modo.dispatchEvent(new Event("change"));
        document.querySelector("#mode-help").textContent = "Elegido porque ya hay corridas guardadas: revisarlas no consume tokens. Cambia a «Agentes MAF» para auditar con IA.";
      }
    }

    if (versions.includes(autoVer)) {
      form.elements.version.value = autoVer;
      await executeAssessment([autoVer], form.elements.modo.value, { preserveVisible: false });
    } else if (Object.keys(cachedLatest).length > 0) {
      restoreCachedRuns();
    }
    applyHash();
  } catch (err) {
    reportEcosystemFailure(describeFetchError(err, "No se pudo cargar el estado inicial."));
  }
}

initEcosystem();
