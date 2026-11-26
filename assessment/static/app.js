"use strict";

const form = document.querySelector("#controls");
const results = document.querySelector("#results");
const status = document.querySelector("#status");
const loadLatestBtn = document.querySelector("#load-latest");
const stopSandboxBtn = document.querySelector("#stop-sandbox");
const sandboxPill = document.querySelector("#sandbox-pill");
const sandboxText = document.querySelector("#sandbox-text");
const stageDialog = document.querySelector("#stage-dialog");
const stageDialogKicker = document.querySelector("#stage-dialog-kicker");
const stageDialogTitle = document.querySelector("#stage-dialog-title");
const stageDialogBody = document.querySelector("#stage-dialog-body");

const versions = ["v1", "v2", "v3"];
const versionRoles = {
  v1: "Código excluye cancelados · Prueba REN-001 presente",
  v2: "Defecto deliberado en cancelados · Prueba detecta fallo",
  v3: "Código excluye cancelados · Falta prueba REN-001",
};

const STAGE_CATALOG = [
  {
    numero: 1, bloque: "DevSec", etapa: "Planificar", herramienta: "Azure Boards",
    pregunta: "¿Qué debía resolver esta versión y cómo se aceptaría?",
    descripcion: "Audita la historia de usuario en Azure Boards (AB#1) y sus criterios formales de aceptación para REN-001.",
  },
  {
    numero: 2, bloque: "DevSec", etapa: "Crear código", herramienta: "GitHub PR",
    pregunta: "¿Qué cambio implementó la historia y quién lo integró?",
    descripcion: "Conecta el commit evaluado con el Pull Request en GitHub y comprueba la trazabilidad bidireccional mediante AB#1.",
  },
  {
    numero: 3, bloque: "DevSec", etapa: "Asegurar desde el origen", herramienta: "CodeQL + Dependabot",
    pregunta: "¿Qué controles SAST y de dependencias se ejecutaron sobre el cambio?",
    descripcion: "Consulta alertas de análisis estático (CodeQL) y estado de vigilancia de paquetes (Dependabot) sobre el código fuente.",
  },
  {
    numero: 4, bloque: "DevSec", etapa: "Integrar y probar", herramienta: "GitHub Actions + xUnit TRX",
    pregunta: "¿Qué pruebas pasaron y cuáles respaldan explícitamente el criterio?",
    descripcion: "Cruza el XML del TRX por testId y executionId contra la sintaxis de la prueba xUnit y aplica la política determinista REN-001.v2.",
  },
  {
    numero: 5, bloque: "CloudOps", etapa: "Desplegar", herramienta: "Azure Container Apps",
    pregunta: "¿Qué artefacto inmutable y revisión están activos en el ambiente cloud?",
    descripcion: "Verifica en Azure Resource Manager la revisión activa del Container App, imagen publicada, commit_sha y configuración de red.",
  },
  {
    numero: 6, bloque: "CloudOps", etapa: "Operar", herramienta: "Microsoft Defender for Cloud",
    pregunta: "¿Existen brechas de postura cloud que afecten al recurso?",
    descripcion: "Consulta Microsoft.Security/assessments en Azure Resource Graph, forzamiento HTTPS y estado de Managed Identity.",
  },
  {
    numero: 7, bloque: "CloudOps", etapa: "Observar y aprender", herramienta: "Application Insights",
    pregunta: "¿Cambió la tasa de errores 5xx o la latencia tras el despliegue?",
    descripcion: "Ejecuta una consulta KQL sobre AppRequests en Log Analytics para medir volumen, fallos de servidor y tiempo de respuesta.",
  },
  {
    numero: 8, bloque: "CloudOps", etapa: "Optimizar con IA", herramienta: "Azure AI Foundry + Boards",
    pregunta: "¿Qué acción proponemos y cómo evitamos duplicar tareas en el backlog?",
    descripcion: "Persiste un checkpoint para revisión humana y sincroniza la tarea en Azure Boards con huella idempotente WIQL (devsecops-fp-...).",
  },
];

const STATE_ICONS = {
  verificado: "✓",
  incumplido: "✕",
  atencion: "!",
  pendiente: "!",
  informativo: "i",
};

const verdicts = {
  VERIFICADO: ["pass", "✓ Verificado"],
  INCUMPLIDO: ["fail", "✕ Incumplido"],
  EVIDENCIA_INSUFICIENTE: ["unknown", "! Evidencia insuficiente"],
};

const outcomes = {
  Passed: ["aprobada", "aprobadas"],
  Failed: ["fallida", "fallidas"],
  NotExecuted: ["omitida", "omitidas"],
};

const tools = {
  listar_resultados: "QA · Listó ejecuciones individuales del TRX",
  buscar_pruebas_vinculadas: "QA · Buscó pruebas marcadas con Trait REN-001",
  inspeccionar_prueba: "QA · Inspeccionó el código C# y aserción de la prueba",
  obtener_historia_boards: "QA · Consultó historia y criterios en Azure Boards",
  consultar_cambio_github: "QA · Consultó Pull Request y pipeline en GitHub",
  consultar_seguridad_origen: "SecOps · Consultó alertas CodeQL y Dependabot",
  consultar_despliegue_y_defender: "SecOps · Consultó Container App y Defender CSPM",
  consultar_telemetria_appinsights: "SecOps · Consultó métricas KQL en Application Insights",
};

const cards = new Map();
const reportsByVersion = new Map();
let cachedLatest = {};
let ecosystemState = {};

// Safari fallback for <dialog closedby="any"> (per modern-web-guidance)
if (!("closedBy" in HTMLDialogElement.prototype)) {
  const outside = (e, dialog) => {
    const r = dialog.getBoundingClientRect();
    return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
  };
  for (const dialog of document.querySelectorAll('dialog[closedby="any"]')) {
    let pressedOutside = false;
    dialog.addEventListener("pointerdown", (e) => { pressedOutside = outside(e, dialog); });
    dialog.addEventListener("pointerup", (e) => { if (pressedOutside && outside(e, dialog)) dialog.close(); });
  }
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

for (const version of versions) {
  const card = document.querySelector("#version-card").content.firstElementChild.cloneNode(true);
  card.dataset.version = version;
  card.querySelector("h3").textContent = `Versión ${version.slice(1)}`;
  card.querySelector(".version-role").textContent = versionRoles[version];
  renderCardInterop(card, version, null);
  cards.set(version, card);
  results.append(card);
}

function renderTopLoop() {
  const devsecBox = document.querySelector("#loop-devsec");
  const cloudBox = document.querySelector("#loop-cloudops");
  devsecBox.replaceChildren();
  cloudBox.replaceChildren();

  for (const meta of STAGE_CATALOG) {
    let aggState = "informativo";
    const observedStates = [];
    for (const ver of versions) {
      const rep = reportsByVersion.get(ver);
      const st = rep?.etapas_devsecops?.find((x) => x.numero === meta.numero)?.estado;
      if (st) observedStates.push(st);
    }
    if (observedStates.includes("incumplido")) aggState = "incumplido";
    else if (observedStates.includes("atencion") || observedStates.includes("pendiente")) aggState = "atencion";
    else if (observedStates.includes("verificado")) aggState = "verificado";

    const btn = element("button", null, "stage-pill");
    btn.type = "button";
    btn.dataset.state = aggState;
    const top = element("span", null, "stage-pill-top");
    top.append(
      element("span", `${meta.numero}. ${meta.etapa}`),
      element("span", STATE_ICONS[aggState] || "•", "stage-dot")
    );
    btn.append(top, element("span", meta.herramienta, "stage-pill-sub"));
    btn.addEventListener("click", () => openStageInspector(meta.numero, null));
    (meta.bloque === "DevSec" ? devsecBox : cloudBox).append(btn);
  }
}

function openStageInspector(stageNumber, focusVersion) {
  const baseMeta = STAGE_CATALOG.find((s) => s.numero === stageNumber) || STAGE_CATALOG[0];
  const preferredReport = (focusVersion && reportsByVersion.get(focusVersion))
    || reportsByVersion.get("v1")
    || reportsByVersion.get("v2")
    || reportsByVersion.get("v3");
  const liveStage = preferredReport?.etapas_devsecops?.find((s) => s.numero === stageNumber) || {};
  const merged = { ...baseMeta, ...liveStage };

  stageDialogKicker.textContent = `Etapa ${merged.numero} de 8 · ${merged.bloque} · ${merged.herramienta}`;
  stageDialogTitle.textContent = `${merged.numero}. ${merged.etapa}`;
  stageDialogBody.replaceChildren();

  const qBox = element("div", null, "modal-question");
  qBox.append(
    element("strong", "Pregunta clave que resuelve el agente"),
    element("p", merged.pregunta || baseMeta.pregunta)
  );
  stageDialogBody.append(qBox, element("p", merged.descripcion || baseMeta.descripcion));

  if (merged.datos && Object.keys(merged.datos).length) {
    const dl = element("dl", null, "modal-kv");
    for (const [k, v] of Object.entries(merged.datos)) {
      const wrap = element("div", null, "kv-box");
      wrap.append(element("dt", k), element("dd", String(v)));
      dl.append(wrap);
    }
    stageDialogBody.append(dl);
  }

  if (reportsByVersion.size > 0) {
    const compTitle = element("h2", "Estado comparado por versión evaluada");
    compTitle.style.fontSize = "0.96rem";
    const grid = element("div", null, "modal-compare");
    for (const ver of versions) {
      const col = element("div", null, "compare-col");
      const rep = reportsByVersion.get(ver);
      const st = rep?.etapas_devsecops?.find((s) => s.numero === stageNumber);
      col.append(element("strong", `Versión ${ver.slice(1)}`));
      if (st) {
        col.append(
          element("span", `${STATE_ICONS[st.estado] || "•"} ${st.estado.toUpperCase()}`, "chip-meta"),
          element("p", st.resumen)
        );
      } else {
        col.append(element("p", "Aún no evaluada en esta sesión."));
      }
      grid.append(col);
    }
    stageDialogBody.append(compTitle, grid);
  }

  const actions = element("div", null, "modal-actions");
  if (merged.url) {
    const ext = element("a", `${merged.etiqueta_url || "Abrir evidencia en herramienta origen"} ↗`, "btn-ghost");
    ext.href = merged.url;
    ext.target = "_blank";
    ext.rel = "noopener";
    ext.style.display = "inline-flex";
    ext.style.alignItems = "center";
    ext.style.textDecoration = "none";
    actions.append(ext);
  }
  const launchVer = focusVersion || "v1";
  const sandboxBtn = element("button", `Abrir AppContratos (${launchVer}) en vivo ↗`, "btn-secondary");
  sandboxBtn.type = "button";
  sandboxBtn.addEventListener("click", () => {
    stageDialog.close();
    launchSandbox(launchVer);
  });
  actions.append(sandboxBtn);
  stageDialogBody.append(actions);

  stageDialog.showModal();
}

function updateSandboxBanner(sandbox) {
  if (sandbox && sandbox.activo) {
    sandboxPill.dataset.active = "true";
    sandboxText.textContent = `App viva (${sandbox.version}) · :5080`;
    stopSandboxBtn.hidden = false;
  } else {
    sandboxPill.dataset.active = "false";
    sandboxText.textContent = "App local :5080 detenida";
    stopSandboxBtn.hidden = true;
  }
}

async function launchSandbox(version) {
  status.textContent = `Iniciando instancia viva de AppContratos (${version}) en 127.0.0.1:5080…`;
  try {
    const res = await fetch("/api/sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accion: "iniciar", version }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "No se pudo iniciar AppContratos.");
    updateSandboxBanner(data.sandbox);
    status.textContent = `AppContratos (${version}) activa en ${data.sandbox.url}`;
    window.open(data.sandbox.url_interoperable || data.sandbox.url, "_blank", "noopener");
  } catch (err) {
    status.textContent = err.message;
  }
}

stopSandboxBtn.addEventListener("click", async () => {
  stopSandboxBtn.disabled = true;
  try {
    const res = await fetch("/api/sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accion: "detener" }),
    });
    const data = await res.json();
    updateSandboxBanner(data.sandbox);
    status.textContent = "Instancia local en 127.0.0.1:5080 detenida.";
  } finally {
    stopSandboxBtn.disabled = false;
  }
});

for (const btn of document.querySelectorAll("[data-launch]")) {
  btn.addEventListener("click", () => launchSandbox(btn.dataset.launch));
}

function renderCardInterop(card, version, commitSha) {
  const box = card.querySelector(".card-interop");
  box.replaceChildren();
  const btn = element("button", `Interactuar en App ${version} ↗`, "btn-ghost");
  btn.type = "button";
  btn.addEventListener("click", () => launchSandbox(version));
  box.append(btn);
  if (commitSha) {
    box.append(element("span", `commit ${commitSha.slice(0, 8)}`, "chip-meta"));
  }
}

function setCard(card, state, label, reason) {
  card.dataset.verdict = state;
  const badge = card.querySelector(".badge");
  badge.dataset.state = state;
  badge.textContent = label;
  card.querySelector(".reason").textContent = reason;
  card.querySelector(".stages").replaceChildren();
  card.querySelector(".evidence").replaceChildren();
  card.querySelector(".governance").replaceChildren();
  card.querySelector(".downloads").replaceChildren();
}

function renderStages(container, stages, version) {
  container.replaceChildren();
  if (!stages || !stages.length) return;
  const list = element("ol", null, "stage-list");
  for (const s of stages) {
    const li = element("li", null, "stage-item");
    li.dataset.state = s.estado;
    const trigger = element("button", null, "stage-trigger");
    trigger.type = "button";
    const head = element("div", null, "stage-head");
    head.append(
      element("span", `${STATE_ICONS[s.estado] || "•"} ${s.numero}. ${s.etapa}`),
      element("span", s.herramienta, "stage-tool")
    );
    trigger.append(head, element("span", s.resumen, "stage-desc"));
    trigger.addEventListener("click", () => openStageInspector(s.numero, version));
    li.append(trigger);
    list.append(li);
  }
  const details = element("details", null, "stages-box");
  details.open = true;
  details.append(element("summary", "Recorrido DevSecOps (8 etapas · clic para inspeccionar)"), list);
  container.append(details);
}

function renderGovernance(card, version, runId, action) {
  const box = card.querySelector(".governance");
  box.replaceChildren();
  if (!action) return;

  const panel = element("div", null, "gov-panel");
  panel.dataset.state = action.estado;
  const header = element("div", null, "gov-head");
  header.append(
    element("strong", "🏛️ Gobernanza · Azure Boards"),
    element("span", action.tag_idempotencia, "gov-fp")
  );
  panel.append(header, element("p", action.titulo, "gov-title"));

  if (action.estado === "APROBADA" && action.boards_resultado) {
    const br = action.boards_resultado;
    const msg = element("p", `✓ Tarea ${br.operacion} sin duplicados: `, "gov-result");
    const link = element("a", `${br.referencia} ↗`);
    link.href = br.url;
    link.target = "_blank";
    link.rel = "noopener";
    msg.append(link);
    panel.append(msg);
  } else if (action.estado === "DESCARTADA") {
    panel.append(element("p", `Recomendación descartada: ${action.nota_humana || ""}`, "gov-result"));
  } else {
    const noteInput = document.createElement("input");
    noteInput.type = "text";
    noteInput.className = "gov-input";
    noteInput.setAttribute("aria-label", `Nota de aprobación o descarte para ${version}`);
    noteInput.placeholder = "Nota de revisión para Azure Boards o motivo de descarte…";

    const actionsRow = element("div", null, "gov-buttons");
    const approveBtn = element("button", "Aprobar en Azure Boards", "btn-approve");
    approveBtn.type = "button";
    const dismissBtn = element("button", "Descartar", "btn-dismiss");
    dismissBtn.type = "button";

    const submitDecision = async (decision) => {
      approveBtn.disabled = true;
      dismissBtn.disabled = true;
      noteInput.disabled = true;
      status.textContent = decision === "aprobar" ? "Sincronizando Work Item en Azure Boards…" : "Registrando descarte…";
      try {
        const res = await fetch("/api/acciones", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ejecucion: runId, decision, nota: noteInput.value }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "No se pudo actualizar la acción.");
        const currentReport = reportsByVersion.get(version);
        if (currentReport) {
          currentReport.accion_propuesta = data.accion_propuesta;
          if (data.etapas_devsecops?.length) currentReport.etapas_devsecops = data.etapas_devsecops;
        }
        renderGovernance(card, version, runId, data.accion_propuesta);
        if (data.etapas_devsecops?.length) {
          renderStages(card.querySelector(".stages"), data.etapas_devsecops, version);
          renderTopLoop();
        }
        status.textContent = decision === "aprobar"
          ? `Tarea sincronizada en Azure Boards (${data.accion_propuesta?.boards_resultado?.referencia || "OK"})`
          : "Recomendación descartada con trazabilidad en el checkpoint.";
      } catch (err) {
        approveBtn.disabled = false;
        dismissBtn.disabled = false;
        noteInput.disabled = false;
        status.textContent = err.message;
      }
    };

    approveBtn.addEventListener("click", () => submitDecision("aprobar"));
    dismissBtn.addEventListener("click", () => submitDecision("descartar"));
    actionsRow.append(approveBtn, dismissBtn);
    panel.append(noteInput, actionsRow);
  }
  box.append(panel);
}

function showReport(card, version, report) {
  reportsByVersion.set(version, report);
  setCard(card, ...verdicts[report.veredicto], report.justificacion);
  renderCardInterop(card, version, report.ejecucion?.commit);
  renderStages(card.querySelector(".stages"), report.etapas_devsecops, version);
  renderTopLoop();

  const evidence = card.querySelector(".evidence");
  const counts = new Map();
  for (const row of report.resultados_trx) {
    const name = row.outcome === "Skipped" ? "NotExecuted" : row.outcome;
    counts.set(name, (counts.get(name) || 0) + 1);
  }
  if (counts.size) {
    const countLabels = [...counts].map(([name, count]) => {
      const label = outcomes[name]?.[count === 1 ? 0 : 1] || name;
      return `${count} ${label}`;
    });
    evidence.append(element("p", `Suite xUnit · ${countLabels.join(" · ")}`, "chip-meta"));
  }
  if (report.siguiente_paso) evidence.append(element("p", `Siguiente paso: ${report.siguiente_paso}`));

  const qa = report.investigacion;
  if (qa.detalle) evidence.prepend(element("p", qa.detalle));
  const qaNotes = [
    ...report.referencias.map((ref) => ` Vínculo verificado · ${ref.id} (${ref.metodo})`),
    ...report.diagnosticos.map((diagnostic) => diagnostic.detalle),
    qa.explicacion,
    ...qa.llamadas.map((call) => `↳ ${tools[call.herramienta] || call.herramienta}`),
  ].filter(Boolean);

  if (qaNotes.length) {
    const detail = element("details");
    const content = element("div", null, "detail-content");
    content.append(...qaNotes.map((note) => element("p", note)));
    detail.append(element("summary", qa.proveedor ? "Investigación Agente QA y Trazabilidad" : "Detalle de pruebas y fuente"), content);
    evidence.append(detail);
  }

  const secops = report.investigacion_secops;
  if (secops && secops.estado && secops.estado !== "NO_SOLICITADA") {
    const detail = element("details");
    const content = element("div", null, "detail-content");
    if (secops.detalle) content.append(element("p", secops.detalle));
    if (secops.resumen) content.append(element("p", secops.resumen));
    for (const h of secops.hallazgos || []) {
      const box = element("div", null, "finding-row");
      const tags = element("div", null, "scope-tags");
      tags.append(
        element("span", `Alcance: ${h.alcance}`, "scope-badge"),
        element("span", `Severidad: ${h.severidad}`, "scope-badge")
      );
      box.append(tags, element("strong", h.titulo), element("p", h.evidencia));
      content.append(box);
    }
    for (const call of secops.llamadas || []) {
      content.append(element("p", `↳ ${tools[call.herramienta] || call.herramienta}`));
    }
    if (content.childElementCount) {
      detail.append(element("summary", "Postura y Telemetría · Agente SecOps"), content);
      evidence.append(detail);
    }
  }

  renderGovernance(card, version, report.ejecucion.id, report.accion_propuesta);

  const files = [["informe.md", "Informe MD"], ["informe.json", "Evidencia JSON"]];
  if (report.ejecucion.trx) files.push(["resultados.trx", "TRX XML"]);
  if (report.ejecucion.log) files.push(["dotnet-test.log", "Log Build"]);
  if (report.accion_propuesta) files.push(["checkpoint_aprobacion.json", "Checkpoint"]);
  for (const [file, label] of files) {
    const link = element("a", label);
    link.href = `/informes/${report.ejecucion.id}/${file}`;
    link.target = "_blank";
    link.rel = "noopener";
    card.querySelector(".downloads").append(link);
  }
  return report.diagnosticos.length > 0 || !["COMPLETADA", "SOLO_EVIDENCIA"].includes(qa.estado);
}

form.elements.modo.addEventListener("change", () => {
  document.querySelector("#mode-help").textContent = form.elements.modo.value === "agente"
    ? "Ejecuta en paralelo los agentes de QA y Seguridad/Operación sobre Azure AI Foundry; el veredicto siempre es determinista."
    : "Revisa la evidencia local y de nube aplicando la política determinista sin consumir tokens.";
});

async function executeAssessment(selectedVersions, mode) {
  const inputs = [...form.elements];
  inputs.forEach((input) => { input.disabled = true; });
  results.setAttribute("aria-busy", "true");
  for (const [version, card] of cards) {
    card.hidden = !selectedVersions.includes(version);
    if (selectedVersions.includes(version)) {
      setCard(card, "idle", "• En cola", "Preparando entorno aislado de compilación y recolección…");
    }
  }
  let issues = 0;
  try {
    for (const [index, version] of selectedVersions.entries()) {
      const card = cards.get(version);
      status.textContent = `Evaluando ${version} · ${index + 1} de ${selectedVersions.length}`;
      const reason = mode === "agente"
        ? "Ejecutando xUnit y consultando en paralelo Agente QA + Agente SecOps…"
        : "Ejecutando xUnit y verificando fuentes…";
      setCard(card, "idle", "↻ Evaluando", reason);
      try {
        const response = await fetch("/api/evaluar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version, modo: mode }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "La evaluación no pudo completarse.");
        if (showReport(card, version, data)) issues++;
      } catch (error) {
        issues++;
        setCard(card, "error", "✕ Error", error.message);
      }
    }
    status.textContent = issues
      ? `Evaluación finalizada · ${issues} ${issues === 1 ? "entrega con diagnóstico" : "entregas con diagnóstico"}`
      : `${selectedVersions.length} ${selectedVersions.length === 1 ? "versión auditada" : "versiones auditadas"}`;
  } finally {
    results.setAttribute("aria-busy", "false");
    inputs.forEach((input) => { input.disabled = false; });
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const mode = form.elements.modo.value;
  const chosen = form.elements.version.value === "todas" ? versions : [form.elements.version.value];
  await executeAssessment(chosen, mode);
});

loadLatestBtn.addEventListener("click", () => {
  let count = 0;
  for (const ver of versions) {
    const card = cards.get(ver);
    card.hidden = false;
    if (cachedLatest[ver]) {
      showReport(card, ver, cachedLatest[ver]);
      count++;
    }
  }
  status.textContent = count ? `Restauradas ${count} corridas previas sin consumo de tokens.` : "No hay corridas previas.";
});

async function initEcosystem() {
  renderTopLoop();
  try {
    const res = await fetch("/api/ecosistema");
    if (!res.ok) return;
    const data = await res.json();
    ecosystemState = data.ecosistema || {};
    cachedLatest = data.ultimos || {};

    if (ecosystemState.boards_url) document.querySelector("#nav-boards").href = ecosystemState.boards_url;
    if (ecosystemState.github_pr_url) document.querySelector("#nav-pr").href = ecosystemState.github_pr_url;
    if (ecosystemState.github_security_url) document.querySelector("#nav-sec").href = ecosystemState.github_security_url;
    updateSandboxBanner(ecosystemState.sandbox);

    if (Object.keys(cachedLatest).length > 0) {
      loadLatestBtn.hidden = false;
    }

    const params = new URLSearchParams(window.location.search);
    const autoVer = params.get("autoevaluar");
    if (versions.includes(autoVer)) {
      form.elements.version.value = autoVer;
      await executeAssessment([autoVer], form.elements.modo.value);
    } else if (Object.keys(cachedLatest).length > 0) {
      loadLatestBtn.click();
    }
  } catch {
    updateSandboxBanner(null);
  }
}

initEcosystem();
