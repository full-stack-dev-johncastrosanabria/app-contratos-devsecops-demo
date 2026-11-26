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
const versionRoles = {
  v1: "Código excluye cancelados · Prueba REN-001 presente",
  v2: "Regresión funcional en cancelados · Prueba detecta fallo",
  v3: "Código excluye cancelados · Falta prueba vinculada REN-001",
};

const STAGE_CATALOG = [
  {
    numero: 1, bloque: "DevSec", etapa: "Planificar", herramienta: "Azure Boards",
    pregunta: "¿Qué debía resolver esta entrega y bajo qué criterio formal se acepta?",
    descripcion: "Audita la historia de usuario en Azure Boards (AB#1) y sus criterios de aceptación para REN-001.",
  },
  {
    numero: 2, bloque: "DevSec", etapa: "Crear código", herramienta: "GitHub PR",
    pregunta: "¿Qué cambio implementó la historia y quién lo integró al repositorio?",
    descripcion: "Conecta el commit evaluado con el Pull Request en GitHub y comprueba la trazabilidad bidireccional hacia AB#1.",
  },
  {
    numero: 3, bloque: "DevSec", etapa: "Asegurar origen", herramienta: "CodeQL + Dependabot",
    pregunta: "¿Qué controles SAST y de dependencias se ejecutaron sobre el código?",
    descripcion: "Consulta alertas abiertas de análisis estático (CodeQL) y vigilancia de paquetes (Dependabot).",
  },
  {
    numero: 4, bloque: "DevSec", etapa: "Integrar y probar", herramienta: "Actions + xUnit TRX",
    pregunta: "¿Qué pruebas pasaron y cuáles certifican explícitamente el criterio REN-001?",
    descripcion: "Cruza el XML del TRX por testId y executionId contra la sintaxis C# y aplica la política determinista REN-001.v2.",
  },
  {
    numero: 5, bloque: "CloudOps", etapa: "Desplegar", herramienta: "Container Apps",
    pregunta: "¿Qué artefacto inmutable y revisión están activos en el ambiente cloud?",
    descripcion: "Verifica en Azure Resource Manager la revisión activa del Container App, imagen publicada, commit y red.",
  },
  {
    numero: 6, bloque: "CloudOps", etapa: "Operar", herramienta: "Defender for Cloud",
    pregunta: "¿Existen brechas de postura cloud que afecten al recurso desplegado?",
    descripcion: "Consulta evaluaciones de Microsoft Defender en Resource Graph, HTTPS exclusivo y estado de Managed Identity.",
  },
  {
    numero: 7, bloque: "CloudOps", etapa: "Observar y aprender", herramienta: "App Insights",
    pregunta: "¿Cambió la tasa de errores 5xx o la latencia tras el despliegue?",
    descripcion: "Ejecuta una consulta KQL sobre AppRequests en Log Analytics para medir volumen, fallos de servidor y latencia.",
  },
  {
    numero: 8, bloque: "CloudOps", etapa: "Optimizar con IA", herramienta: "Foundry + Boards",
    pregunta: "¿Qué remediación se propone y cómo se evita duplicar tareas en el backlog?",
    descripcion: "Persiste un punto de control para revisión humana y sincroniza en Azure Boards con huella idempotente WIQL.",
  },
];

const STATE_LABELS = {
  verificado: "Verificado",
  incumplido: "Incumplido",
  atencion: "Atención requerida",
  pendiente: "Pendiente",
  informativo: "Sin evaluar",
};

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
  consultar_seguridad_origen: "SecOps · Consultó alertas de CodeQL y Dependabot",
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
const stationButtons = new Map();
const reportsByVersion = new Map();
const provenanceByVersion = new Map();

let cachedLatest = {};
let activeController = null;
let filterDiffOnly = false;
let inspectedStage = null;
let inspectedVersion = null;
let lastSandboxAttempt = null;
let sandboxBusy = false;

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
  };

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
  if (state === "atencion" || state === "pendiente" || state === "unknown") return "warn";
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
  if (val === null || val === undefined || val === "") return "No registrado";
  if (typeof val === "boolean") return val ? "Sí" : "No";
  if (Array.isArray(val)) return val.length ? val.join(", ") : "Ninguno";
  if (key.endsWith("_pct")) return `${val} %`;
  if (key.endsWith("_ms")) return `${val} ms`;
  if (key.includes("commit") && typeof val === "string" && val.length > 12) return val.slice(0, 10);
  return String(val);
}

async function copyTextWithFeedback(button, text, originalLabel) {
  try {
    await navigator.clipboard.writeText(text);
    const labelSpan = button.querySelector("span") || button;
    labelSpan.textContent = "Copiado";
    setTimeout(() => { labelSpan.textContent = originalLabel; }, 1600);
  } catch {
    setStatus(`Valor para copiar: ${text}`, "info");
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

function createSummary(labelText) {
  const summary = document.createElement("summary");
  const label = element("span", labelText, "summary-label");
  const chev = svgIcon("chevron", 14);
  chev.classList.add("summary-chevron");
  summary.append(label, chev);
  return summary;
}

// Build initial 8-station Transit Corridor once (no repeated DOM teardown)
function initTransitCorridor() {
  const devsecList = document.querySelector("#loop-devsec");
  const cloudList = document.querySelector("#loop-cloudops");
  devsecList.replaceChildren();
  cloudList.replaceChildren();

  for (const meta of STAGE_CATALOG) {
    const li = element("li", null, "station-item");
    const btn = element("button", null, "station-btn");
    btn.type = "button";
    btn.dataset.stage = String(meta.numero);
    btn.dataset.state = "informativo";
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-controls", "stage-inspector");

    const top = element("span", null, "station-top");
    const titleWrap = element("span", null, "station-title-wrap");
    const num = element("span", String(meta.numero), "station-num");
    num.setAttribute("aria-hidden", "true");
    titleWrap.append(num, element("span", meta.etapa));

    const srState = element("span", STATE_LABELS.informativo, "sr-only");
    srState.dataset.role = "sr-state";
    const iconSlot = element("span", null, "station-icon-slot");
    iconSlot.append(svgIcon("info", 14));
    top.append(titleWrap, iconSlot, srState);

    const bottom = element("span", null, "station-bottom");
    const tool = element("span", meta.herramienta, "station-tool");
    const pips = element("span", null, "station-ver-pips");
    pips.setAttribute("aria-hidden", "true");
    for (const ver of versions) {
      const pip = element("span", null, "ver-pip");
      pip.dataset.ver = ver;
      pip.title = `${ver}: sin evaluar`;
      pips.append(pip);
    }
    bottom.append(tool, pips);

    btn.append(top, bottom);
    btn.addEventListener("click", () => {
      if (inspectedStage === meta.numero && !stageInspector.hidden) {
        closeStageInspector();
      } else {
        openStageInspector(meta.numero, null);
      }
    });

    li.append(btn);
    stationButtons.set(meta.numero, btn);
    (meta.bloque === "DevSec" ? devsecList : cloudList).append(li);
  }
}

function updateTransitCorridor() {
  for (const meta of STAGE_CATALOG) {
    const btn = stationButtons.get(meta.numero);
    if (!btn) continue;

    let worstState = "informativo";
    for (const ver of versions) {
      const rep = reportsByVersion.get(ver);
      const st = rep?.etapas_devsecops?.find((x) => x.numero === meta.numero)?.estado || "informativo";
      const pip = btn.querySelector(`.ver-pip[data-ver="${ver}"]`);
      if (pip) {
        pip.dataset.state = st;
        pip.title = `${ver}: ${STATE_LABELS[st] || st}`;
      }
      if ((STATE_RANK[st] || 0) > (STATE_RANK[worstState] || 0)) {
        worstState = st;
      }
    }

    btn.dataset.state = worstState;
    btn.setAttribute("aria-expanded", String(!stageInspector.hidden && inspectedStage === meta.numero));
    const srState = btn.querySelector('[data-role="sr-state"]');
    if (srState) srState.textContent = ` (${STATE_LABELS[worstState] || worstState})`;
    const iconSlot = btn.querySelector(".station-icon-slot");
    if (iconSlot) iconSlot.replaceChildren(svgIcon(stateToIconKind(worstState), 14));
  }
}

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

function openStageInspector(stageNumber, focusVersion) {
  const baseMeta = STAGE_CATALOG.find((s) => s.numero === stageNumber) || STAGE_CATALOG[0];
  inspectedStage = baseMeta.numero;
  inspectedVersion = pickBestVersionForStage(baseMeta.numero, focusVersion);

  const report = reportsByVersion.get(inspectedVersion);
  const liveStage = report?.etapas_devsecops?.find((s) => s.numero === baseMeta.numero) || {};
  const merged = { ...baseMeta, ...liveStage };

  stageInspectorTitle.textContent = `Estación ${merged.numero}. ${merged.etapa}`;
  const stateLabel = STATE_LABELS[merged.estado] || "Referencia de etapa";
  stageInspectorMeta.textContent = `${merged.bloque} · ${merged.herramienta} · Vista activa: ${inspectedVersion.toUpperCase()} (${stateLabel})`;

  inspectorVersionTabs.replaceChildren();
  for (const ver of versions) {
    const tab = element("button", ver.toUpperCase(), "ver-tab-btn");
    tab.type = "button";
    tab.setAttribute("aria-pressed", String(ver === inspectedVersion));
    tab.addEventListener("click", () => openStageInspector(baseMeta.numero, ver));
    inspectorVersionTabs.append(tab);
  }

  stageInspectorBody.replaceChildren();

  const leadGrid = element("div", null, "inspector-lead-grid");
  const qBlock = element("div", null, "inspector-question-block");
  qBlock.append(
    element("h4", "Pregunta de gobierno que responde esta estación"),
    element("p", merged.pregunta || baseMeta.pregunta)
  );
  const descBlock = element("p", merged.resumen || merged.descripcion || baseMeta.descripcion, "inspector-desc");
  leadGrid.append(qBlock, descBlock);
  stageInspectorBody.append(leadGrid);

  if (merged.datos && Object.keys(merged.datos).length > 0) {
    const dl = element("dl", null, "inspector-kv");
    for (const [k, v] of Object.entries(merged.datos)) {
      const wrap = element("div", null, "kv-item");
      wrap.append(element("dt", formatFieldKey(k)), element("dd", formatFieldValue(k, v)));
      dl.append(wrap);
    }
    stageInspectorBody.append(dl);
  }

  if (reportsByVersion.size > 0) {
    stageInspectorBody.append(element("h4", "Estado comparado en las tres entregas", "inspector-compare-title"));
    const grid = element("div", null, "inspector-compare-grid");
    for (const ver of versions) {
      const col = element("div", null, "inspector-compare-col");
      const rep = reportsByVersion.get(ver);
      const st = rep?.etapas_devsecops?.find((s) => s.numero === baseMeta.numero);
      const headRow = element("div", null, "card-title-row");
      headRow.append(element("strong", `Versión ${ver.slice(1)}`));
      if (st) {
        const b = element("span", null, "badge");
        b.dataset.state = st.estado === "verificado" ? "pass" : (st.estado === "incumplido" ? "fail" : "unknown");
        b.append(svgIcon(stateToIconKind(st.estado), 12), element("span", STATE_LABELS[st.estado] || st.estado));
        headRow.append(b);
        col.append(headRow, element("p", st.resumen));
      } else {
        col.append(headRow, element("p", "Sin datos evaluados aún en esta sesión."));
      }
      grid.append(col);
    }
    stageInspectorBody.append(grid);
  }

  const actions = element("div", null, "inspector-actions");
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
  const launchBtn = element("button", null, "btn-secondary");
  launchBtn.type = "button";
  launchBtn.append(svgIcon("play", 13), element("span", `Iniciar sujeto ${inspectedVersion} en :5080`));
  launchBtn.addEventListener("click", () => launchSandbox(inspectedVersion));
  actions.append(launchBtn);
  stageInspectorBody.append(actions);

  stageInspector.hidden = false;
  updateTransitCorridor();
  stageInspector.focus({ preventScroll: true });
}

function closeStageInspector() {
  const prevStage = inspectedStage;
  stageInspector.hidden = true;
  inspectedStage = null;
  updateTransitCorridor();
  if (prevStage && stationButtons.has(prevStage)) {
    stationButtons.get(prevStage).focus({ preventScroll: true });
  }
}

inspectorPrevBtn.addEventListener("click", () => {
  const next = inspectedStage && inspectedStage > 1 ? inspectedStage - 1 : 8;
  openStageInspector(next, inspectedVersion);
});

inspectorNextBtn.addEventListener("click", () => {
  const next = inspectedStage && inspectedStage < 8 ? inspectedStage + 1 : 1;
  openStageInspector(next, inspectedVersion);
});

inspectorCloseBtn.addEventListener("click", closeStageInspector);

// Contextual Help Toggle
function setHelpOpen(open) {
  helpDrawer.hidden = !open;
  helpToggleBtn.setAttribute("aria-expanded", String(open));
  if (open) helpDrawer.focus({ preventScroll: true });
}

helpToggleBtn.addEventListener("click", () => setHelpOpen(helpDrawer.hidden));
helpCloseBtn.addEventListener("click", () => {
  setHelpOpen(false);
  helpToggleBtn.focus({ preventScroll: true });
});

// Sandbox Bridge (:5080) with popup-blocker resilience & inline retry
function updateSandboxBanner(sandbox) {
  const activeVer = sandbox?.activo ? sandbox.version : null;
  sandboxPill.dataset.active = String(Boolean(sandbox?.activo));
  delete sandboxPill.dataset.booting;

  for (const btn of document.querySelectorAll("[data-launch]")) {
    const ver = btn.dataset.launch;
    btn.disabled = false;
    btn.dataset.current = String(activeVer === ver);
    btn.textContent = activeVer === ver ? `v${ver.slice(1)} activa` : `Iniciar ${ver}`;
  }

  if (sandbox && sandbox.activo) {
    const targetHref = sandbox.url_interoperable || `${sandbox.url}/?evaluador=${encodeURIComponent(window.location.origin)}&version=${encodeURIComponent(sandbox.version || "v1")}`;
    sandboxText.textContent = `Sujeto activo (${sandbox.version}) en 127.0.0.1:5080`;
    sandboxOpenLink.href = targetHref;
    sandboxOpenLink.hidden = false;
    stopSandboxBtn.hidden = false;
  } else {
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
    if (btn.dataset.launch === version) btn.textContent = `Iniciando ${version}…`;
  }

  const popup = openTab ? window.open("about:blank", "nextgen_sandbox_5080") : null;

  try {
    const res = await fetch("/api/sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accion: "iniciar", version }),
    });
    const data = await res.json();
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
    setStatus(err.message, "error");
    showSandboxError(`${err.message} Verifica que .NET SDK 10 esté disponible y el puerto 5080 no esté bloqueado.`, () => launchSandbox(version, openTab));
  } finally {
    sandboxBusy = false;
  }
}

stopSandboxBtn.addEventListener("click", async () => {
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
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "No se pudo detener la instancia local.");
    updateSandboxBanner(data.sandbox);
    setStatus("Instancia local en 127.0.0.1:5080 detenida.", "idle");
  } catch (err) {
    setStatus(err.message, "error");
    showSandboxError(err.message, () => stopSandboxBtn.click());
  } finally {
    stopSandboxBtn.disabled = false;
    sandboxBusy = false;
  }
});

for (const btn of document.querySelectorAll("[data-launch]")) {
  btn.addEventListener("click", () => launchSandbox(btn.dataset.launch, true));
}

// Initialize 3 Comparison Columns
for (const version of versions) {
  const card = document.querySelector("#version-card").content.firstElementChild.cloneNode(true);
  const titleId = `card-title-${version}`;
  card.dataset.version = version;
  card.setAttribute("aria-labelledby", titleId);
  const h3 = card.querySelector(".card-version-title");
  h3.id = titleId;
  h3.textContent = `Versión ${version.slice(1)}`;
  card.querySelector(".version-role").textContent = versionRoles[version];
  renderCardQuickActions(card, version);
  cards.set(version, card);
  results.append(card);
}

function renderCardQuickActions(card, version) {
  const box = card.querySelector(".card-quick-actions");
  box.replaceChildren();

  const evalSingleBtn = element("button", `Evaluar ${version}`, "btn-ghost");
  evalSingleBtn.type = "button";
  evalSingleBtn.addEventListener("click", () => {
    if (!activeController) executeAssessment([version], form.elements.modo.value, { preserveVisible: true });
  });

  const sandboxBtn = element("button", `Probar ${version} (:5080)`, "btn-ghost");
  sandboxBtn.type = "button";
  sandboxBtn.addEventListener("click", () => launchSandbox(version, true));

  box.append(evalSingleBtn, sandboxBtn);
}

function setBadge(badge, state, labelText) {
  badge.dataset.state = state;
  badge.replaceChildren(svgIcon(stateToIconKind(state), 13), element("span", labelText));
}

function resetCardBands(card, state, label, reasonText, provenanceText = "Pendiente de corrida", isLive = false) {
  card.dataset.verdict = state;
  setBadge(card.querySelector(".badge"), state, label);

  const prov = card.querySelector(".provenance-chip");
  prov.dataset.live = String(isLive);
  prov.textContent = provenanceText;

  card.querySelector(".reason").textContent = reasonText;
  const nextStep = card.querySelector(".next-step");
  nextStep.hidden = true;
  nextStep.textContent = "";

  const cardAlert = card.querySelector(".card-alert");
  cardAlert.hidden = true;
  cardAlert.replaceChildren();

  card.querySelector(".card-proof-band").replaceChildren();
  card.querySelector(".stages").replaceChildren();
  card.querySelector(".evidence").replaceChildren();
  card.querySelector(".governance").replaceChildren();
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
    metaStrip.append(createCopyButton(commit, `commit ${commit.slice(0, 8)}`, `Copiar hash de commit de ${report.ejecucion?.version || "entrega"}`));
  }
  if (typeof report.ejecucion?.archivos_firmados === "number" && report.ejecucion.archivos_firmados > 0) {
    metaStrip.append(element("span", `${report.ejecucion.archivos_firmados} archivos SHA-256`, "meta-pill"));
  }
  band.append(head);
  if (metaStrip.childElementCount) band.append(metaStrip);

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

    const ul = element("ul", null, "trx-list");
    for (const row of trxRows) {
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
    band.append(ul);
  }

  for (const ref of linkedRefs) {
    band.append(element("p", `Fuente verificada: ${ref.id} (${ref.metodo})`, "source-ref-line"));
  }
  for (const diag of report.diagnosticos || []) {
    band.append(element("p", `Diagnóstico: ${diag.detalle}`, "source-ref-line"));
  }
}

function renderStages(container, stages, version) {
  container.replaceChildren();
  if (!stages || !stages.length) return;

  const nonPassing = stages.filter((s) => s.estado !== "verificado");
  const visibleStages = filterDiffOnly ? nonPassing : stages;

  const details = document.createElement("details");
  details.open = filterDiffOnly || nonPassing.length > 0;
  const summaryLabel = nonPassing.length
    ? `Etapas DevSecOps · ${nonPassing.length} con atención de ${stages.length}`
    : `Etapas DevSecOps · ${stages.length} verificadas`;
  details.append(createSummary(summaryLabel));

  const body = element("div", null, "detail-content");
  if (!visibleStages.length) {
    body.append(element("p", "Sin brechas en esta entrega: las 8 etapas están verificadas.", "stage-filter-empty"));
  } else {
    const list = element("ol", null, "stage-list");
    for (const s of visibleStages) {
      const li = document.createElement("li");
      const btn = element("button", null, "stage-row-btn");
      btn.type = "button";
      btn.dataset.state = s.estado;

      const head = element("div", null, "stage-head");
      const left = element("span", null, "summary-label");
      left.append(
        svgIcon(stateToIconKind(s.estado), 13),
        element("span", `${s.numero}. ${s.etapa}`),
        element("span", ` (${STATE_LABELS[s.estado] || s.estado})`, "sr-only")
      );
      head.append(left, element("span", s.herramienta, "stage-tool-tag"));
      btn.append(head, element("span", s.resumen, "stage-desc"));
      btn.addEventListener("click", () => openStageInspector(s.numero, version));
      li.append(btn);
      list.append(li);
    }
    body.append(list);
  }
  details.append(body);
  container.append(details);
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
    const label = findings.length
      ? `Postura Agente SecOps · ${findings.length} ${findings.length === 1 ? "hallazgo" : "hallazgos"}`
      : "Postura y telemetría · Agente SecOps";
    detail.append(createSummary(label));

    const content = element("div", null, "detail-content");
    if (secops.detalle) content.append(element("p", secops.detalle));
    if (secops.resumen) content.append(element("p", secops.resumen));
    for (const h of findings) {
      const box = element("div", null, "finding-item");
      const tags = element("div", null, "scope-tags");
      tags.append(
        element("span", `Alcance: ${h.alcance}`, "scope-badge"),
        element("span", `Severidad: ${h.severidad}`, "scope-badge")
      );
      box.append(tags, element("strong", h.titulo), element("p", h.evidencia));
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

function renderGovernance(card, version, runId, action, focusResult = false) {
  const box = card.querySelector(".governance");
  box.replaceChildren();

  if (!action) {
    box.append(element("p", "Entrega conforme: no requiere acción correctiva en Azure Boards.", "gov-clean-note"));
    return;
  }

  const panel = element("div", null, "gov-panel");
  panel.dataset.state = action.estado;

  const header = element("div", null, "gov-head");
  const heading = element("span", null, "gov-heading");
  heading.append(svgIcon("info", 14), element("span", "Gobernanza · Azure Boards"));
  header.append(heading);
  if (action.tag_idempotencia) {
    header.append(createCopyButton(action.tag_idempotencia, action.tag_idempotencia, `Copiar huella WIQL para ${version}`));
  }
  panel.append(header);
  if (action.titulo) panel.append(element("p", action.titulo, "gov-title"));

  if (action.estado === "APROBADA" && action.boards_resultado) {
    const br = action.boards_resultado;
    const msg = element("p", `Tarea ${br.operacion} sin duplicados en Boards: `, "gov-result");
    msg.tabIndex = -1;
    const link = document.createElement("a");
    link.href = br.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.append(element("span", br.referencia), element("span", " (se abre en una nueva pestaña)", "sr-only"));
    msg.append(link);
    panel.append(msg);
    box.append(panel);
    if (focusResult) msg.focus({ preventScroll: true });
    return;
  }

  if (action.estado === "DESCARTADA") {
    const msg = element("p", `Recomendación descartada. Motivo registrado: ${action.nota_humana || "Sin nota adicional"}`, "gov-result");
    msg.tabIndex = -1;
    panel.append(msg);
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
  noteInput.placeholder = "Ej. Cubrir escenario cancelado antes del cierre de sprint…";
  fieldWrap.append(label, noteInput);

  const errorBox = element("div", null, "gov-error");
  errorBox.hidden = true;
  errorBox.setAttribute("role", "alert");

  const actionsRow = element("div", null, "gov-buttons");
  const approveBtn = element("button", "Aprobar en Azure Boards", "btn-approve");
  approveBtn.type = "button";
  const dismissBtn = element("button", "Descartar", "btn-dismiss");
  dismissBtn.type = "button";
  actionsRow.append(approveBtn, dismissBtn);

  const confirmBox = element("div", null, "gov-confirm-box");
  confirmBox.hidden = true;

  let pendingDecision = null;

  const submitDecision = async (decision) => {
    errorBox.hidden = true;
    confirmBox.hidden = true;
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
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "No se pudo actualizar la decisión en el punto de control.");

      const currentReport = reportsByVersion.get(version);
      if (currentReport) {
        currentReport.accion_propuesta = data.accion_propuesta;
        if (data.etapas_devsecops?.length) currentReport.etapas_devsecops = data.etapas_devsecops;
      }
      renderGovernance(card, version, runId, data.accion_propuesta, true);
      if (data.etapas_devsecops?.length) {
        renderStages(card.querySelector(".stages"), data.etapas_devsecops, version);
        updateTransitCorridor();
      }
      setStatus(
        decision === "aprobar"
          ? `Tarea sincronizada en Azure Boards (${data.accion_propuesta?.boards_resultado?.referencia || "OK"})`
          : `Recomendación descartada y firmada en el punto de control de ${version}.`,
        "pass"
      );
    } catch (err) {
      approveBtn.disabled = false;
      dismissBtn.disabled = false;
      noteInput.disabled = false;
      actionsRow.hidden = false;
      errorBox.replaceChildren(element("span", err.message));
      const retry = element("button", "Reintentar", "btn-inline-action");
      retry.type = "button";
      retry.addEventListener("click", () => submitDecision(decision));
      errorBox.append(retry);
      errorBox.hidden = false;
      setStatus(err.message, "error");
    }
  };

  const askConfirmation = (decision) => {
    errorBox.hidden = true;
    if (decision === "descartar" && !noteInput.value.trim()) {
      errorBox.replaceChildren(element("span", "Escribe un motivo en el campo de nota antes de descartar permanentemente esta brecha."));
      errorBox.hidden = false;
      noteInput.focus();
      return;
    }
    pendingDecision = decision;
    actionsRow.hidden = true;
    confirmBox.replaceChildren();
    const promptText = decision === "aprobar"
      ? `¿Confirmas sincronizar en Azure Boards (historia padre AB#${action.historia_padre || 1}) usando la huella ${action.tag_idempotencia || "idempotente"}?`
      : "¿Confirmas descartar esta acción? Esta resolución bloquea permanentemente el punto de control de esta corrida.";
    const bar = element("div", null, "gov-confirm-bar");
    const confirmBtn = element(
      "button",
      decision === "aprobar" ? "Confirmar envío a Boards" : "Confirmar descarte",
      decision === "aprobar" ? "btn-approve" : "btn-danger"
    );
    confirmBtn.type = "button";
    confirmBtn.addEventListener("click", () => submitDecision(pendingDecision));

    const cancelConfirmBtn = element("button", "Cancelar", "btn-dismiss");
    cancelConfirmBtn.type = "button";
    cancelConfirmBtn.addEventListener("click", () => {
      confirmBox.hidden = true;
      actionsRow.hidden = false;
      (pendingDecision === "aprobar" ? approveBtn : dismissBtn).focus();
      pendingDecision = null;
    });

    bar.append(confirmBtn, cancelConfirmBtn);
    confirmBox.append(element("p", promptText), bar);
    confirmBox.hidden = false;
    confirmBtn.focus();
  };

  approveBtn.addEventListener("click", () => askConfirmation("aprobar"));
  dismissBtn.addEventListener("click", () => askConfirmation("descartar"));

  panel.append(fieldWrap, errorBox, actionsRow, confirmBox);
  box.append(panel);
}

function renderDownloads(card, report) {
  const downloads = card.querySelector(".downloads");
  downloads.replaceChildren();
  const runId = report.ejecucion?.id;
  if (!runId) return;

  const files = [
    ["informe.md", "Informe MD"],
    ["informe.json", "Evidencia JSON"],
  ];
  if (report.ejecucion?.trx) files.push(["resultados.trx", "TRX XML"]);
  if (report.ejecucion?.log) files.push(["dotnet-test.log", "Registro .log"]);
  if (report.accion_propuesta) files.push(["checkpoint_aprobacion.json", "Punto de control"]);

  for (const [file, label] of files) {
    const link = element("a", null, "artifact-link");
    link.href = `/informes/${runId}/${file}`;
    link.target = "_blank";
    link.rel = "noopener";
    link.append(
      svgIcon("doc", 13),
      element("span", label),
      element("span", " (se abre en una nueva pestaña)", "sr-only")
    );
    downloads.append(link);
  }
}

function showReport(card, version, report, options = {}) {
  const isLive = Boolean(options.isLive);
  const ts = formatTimestamp(options.timestampMs || report.registrado_ms || Date.now());
  const provenanceLabel = isLive
    ? `Ejecución en vivo${ts ? ` · ${ts}` : ""}`
    : `Corrida previa en caché${ts ? ` · ${ts}` : ""}`;

  reportsByVersion.set(version, report);
  provenanceByVersion.set(version, { label: provenanceLabel, isLive });

  const verdictInfo = VERDICT_META[report.veredicto] || { state: "unknown", label: report.veredicto };
  resetCardBands(card, verdictInfo.state, verdictInfo.label, report.justificacion, provenanceLabel, isLive);

  if (report.siguiente_paso) {
    const nextStep = card.querySelector(".next-step");
    nextStep.textContent = `Siguiente paso recomendado: ${report.siguiente_paso}`;
    nextStep.hidden = false;
  }

  renderDeterministicProof(card, report);
  renderStages(card.querySelector(".stages"), report.etapas_devsecops, version);
  renderAgentInvestigation(card, report);
  renderGovernance(card, version, report.ejecucion?.id, report.accion_propuesta, false);
  renderDownloads(card, report);
  updateTransitCorridor();

  if (!stageInspector.hidden && inspectedStage) {
    openStageInspector(inspectedStage, inspectedVersion);
  }

  const qaState = report.investigacion?.estado;
  return (report.diagnosticos && report.diagnosticos.length > 0)
    || !["COMPLETADA", "SOLO_EVIDENCIA"].includes(qaState);
}

function syncVisibleCardGrid() {
  const visible = [...cards.values()].filter((c) => !c.hidden).length;
  results.dataset.visibleCount = String(Math.max(visible, 1));
}

form.elements.modo.addEventListener("change", () => {
  document.querySelector("#mode-help").textContent = form.elements.modo.value === "agente"
    ? "Ejecuta en paralelo los agentes de QA y Seguridad/Operación sobre Azure AI Foundry; el dictamen lo decide siempre la política determinista."
    : "Evalúa la evidencia local y cloud aplicando únicamente la política determinista sin consumir tokens de IA.";
});

filterDiffBtn.addEventListener("click", () => {
  filterDiffOnly = !filterDiffOnly;
  filterDiffBtn.setAttribute("aria-pressed", String(filterDiffOnly));
  for (const [ver, rep] of reportsByVersion.entries()) {
    const card = cards.get(ver);
    if (card) renderStages(card.querySelector(".stages"), rep.etapas_devsecops, ver);
  }
  setStatus(
    filterDiffOnly
      ? "Filtro activo: mostrando únicamente etapas con fallos o atención requerida."
      : "Mostrando las 8 etapas completas del ciclo DevSecOps.",
    "info"
  );
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
  results.setAttribute("aria-busy", "true");

  for (const [version, card] of cards) {
    if (!preserveVisible) {
      card.hidden = !selectedVersions.includes(version);
    } else if (selectedVersions.includes(version)) {
      card.hidden = false;
    }
    if (selectedVersions.includes(version)) {
      resetCardBands(
        card,
        "idle",
        "En cola",
        "Preparando entorno aislado de compilación y recolección de artefactos…",
        "Ejecución en preparación…",
        false
      );
    }
  }
  syncVisibleCardGrid();

  let issues = 0;
  let aborted = false;

  try {
    for (const [index, version] of selectedVersions.entries()) {
      if (activeController.signal.aborted) {
        aborted = true;
        break;
      }
      const card = cards.get(version);
      setStatus(`Evaluando ${version} (${index + 1} de ${selectedVersions.length}) · ${mode === "agente" ? "Agentes MAF" : "Solo evidencia"}…`, "busy");
      const runningReason = mode === "agente"
        ? "Ejecutando pruebas xUnit y consultando en paralelo a los agentes de QA y SecOps…"
        : "Ejecutando pruebas xUnit y verificando integridad de fuentes con SHA-256…";
      resetCardBands(card, "busy", "Evaluando", runningReason, "Ejecutando ahora…", true);

      try {
        const response = await fetch("/api/evaluar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version, modo: mode }),
          signal: activeController.signal,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `La evaluación de ${version} no pudo completarse.`);
        cachedLatest[version] = { ...data, registrado_ms: Date.now() };
        loadLatestBtn.hidden = false;
        if (showReport(card, version, data, { isLive: true, timestampMs: Date.now() })) issues++;
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
        resetCardBands(card, "error", "Error de ejecución", error.message, "Fallo de ejecución", false);
        const alertEl = card.querySelector(".card-alert");
        const retryBtn = element("button", `Reintentar ${version}`, "btn-inline-action");
        retryBtn.type = "button";
        retryBtn.addEventListener("click", () => executeAssessment([version], mode, { preserveVisible: true }));
        alertEl.append(
          element("span", `${error.message} Si falló el proveedor IA, prueba con «Solo evidencia determinista».`),
          retryBtn
        );
        alertEl.hidden = false;
      }
    }

    if (aborted) {
      setStatus("Evaluación detenida por el usuario. Las entregas previas se conservaron.", "warn");
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
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const mode = form.elements.modo.value;
  const chosen = form.elements.version.value === "todas" ? versions : [form.elements.version.value];
  await executeAssessment(chosen, mode, { preserveVisible: false });
});

function restoreCachedRuns() {
  let count = 0;
  for (const ver of versions) {
    const card = cards.get(ver);
    card.hidden = false;
    if (cachedLatest[ver]) {
      showReport(card, ver, cachedLatest[ver], { isLive: false, timestampMs: cachedLatest[ver].registrado_ms });
      count++;
    }
  }
  syncVisibleCardGrid();
  if (count) {
    setStatus(`Mostrando ${count} corridas previas en caché (0 tokens). Pulsa «Ejecutar evaluación» para auditar en vivo.`, "info");
  } else {
    setStatus("No hay corridas previas almacenadas.", "idle");
  }
}

loadLatestBtn.addEventListener("click", restoreCachedRuns);

// Global Keyboard Accelerators
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (activeController) {
      event.preventDefault();
      activeController.abort();
      return;
    }
    if (!stageInspector.hidden) {
      event.preventDefault();
      closeStageInspector();
      return;
    }
    if (!helpDrawer.hidden) {
      event.preventDefault();
      setHelpOpen(false);
      helpToggleBtn.focus({ preventScroll: true });
      return;
    }
  }

  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || event.metaKey || event.ctrlKey || event.altKey) {
    return;
  }

  if (event.key === "?") {
    event.preventDefault();
    setHelpOpen(helpDrawer.hidden);
  } else if ((event.key === "r" || event.key === "R") && !activeController) {
    event.preventDefault();
    runBtn.click();
  } else if (event.key === "d" || event.key === "D") {
    event.preventDefault();
    filterDiffBtn.click();
  } else if (event.key >= "1" && event.key <= "8") {
    event.preventDefault();
    openStageInspector(Number(event.key), inspectedVersion);
  }
});

async function initEcosystem() {
  initTransitCorridor();
  try {
    const res = await fetch("/api/ecosistema");
    if (!res.ok) {
      updateSandboxBanner(null);
      return;
    }
    const data = await res.json();
    const eco = data.ecosistema || {};
    cachedLatest = data.ultimos || {};

    const navMap = [
      ["#nav-boards", eco.boards_url],
      ["#nav-pr", eco.github_pr_url],
      ["#nav-sec", eco.github_security_url],
    ];
    for (const [sel, url] of navMap) {
      const link = document.querySelector(sel);
      if (!link) continue;
      if (url) {
        link.href = url;
        link.hidden = false;
      }
    }

    updateSandboxBanner(eco.sandbox);

    if (Object.keys(cachedLatest).length > 0) {
      loadLatestBtn.hidden = false;
    }

    const params = new URLSearchParams(window.location.search);
    const autoVer = params.get("autoevaluar");
    if (versions.includes(autoVer)) {
      form.elements.version.value = autoVer;
      await executeAssessment([autoVer], form.elements.modo.value, { preserveVisible: false });
    } else if (Object.keys(cachedLatest).length > 0) {
      restoreCachedRuns();
    }
  } catch {
    updateSandboxBanner(null);
  }
}

initEcosystem();
