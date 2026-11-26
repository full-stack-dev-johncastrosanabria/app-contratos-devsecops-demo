"use strict";

const form = document.querySelector("#controls");
const results = document.querySelector("#results");
const status = document.querySelector("#status");
const versions = ["v1", "v2", "v3"];
const cards = new Map();

for (const version of versions) {
  const card = document.querySelector("#version-card").content.firstElementChild.cloneNode(true);
  card.dataset.version = version;
  card.querySelector("h3").textContent = `Versión ${version.slice(1)}`;
  cards.set(version, card);
  results.append(card);
}

const verdicts = {
  VERIFICADO: ["pass", "Verificado"],
  INCUMPLIDO: ["fail", "Incumplido"],
  EVIDENCIA_INSUFICIENTE: ["unknown", "Evidencia insuficiente"],
};
const outcomes = {
  Passed: ["aprobada", "aprobadas"],
  Failed: ["fallida", "fallidas"],
  NotExecuted: ["omitida", "omitidas"],
};
const tools = {
  listar_resultados: "QA · Listó los resultados del TRX",
  buscar_pruebas_vinculadas: "QA · Buscó pruebas vinculadas a REN-001",
  inspeccionar_prueba: "QA · Inspeccionó el código de la prueba",
  obtener_historia_boards: "QA · Consultó la historia y criterios en Azure Boards",
  consultar_cambio_github: "QA · Consultó PR y corrida CI en GitHub",
  consultar_seguridad_origen: "SecOps · Consultó CodeQL y Dependabot en GitHub",
  consultar_despliegue_y_defender: "SecOps · Consultó Container App y Defender for Cloud",
  consultar_telemetria_appinsights: "SecOps · Consultó métricas en Application Insights",
};

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function setCard(card, state, label, reason) {
  const badge = card.querySelector(".badge");
  badge.dataset.state = state;
  badge.textContent = label;
  card.querySelector(".reason").textContent = reason;
  card.querySelector(".stages").replaceChildren();
  card.querySelector(".evidence").replaceChildren();
  card.querySelector(".governance").replaceChildren();
  card.querySelector(".downloads").replaceChildren();
}

function renderStages(container, stages) {
  container.replaceChildren();
  if (!stages || !stages.length) return;
  const list = element("ol", null, "stage-list");
  for (const s of stages) {
    const li = element("li", null, "stage-item");
    li.dataset.state = s.estado;
    const head = element("div", null, "stage-head");
    head.append(element("span", `${s.numero}. ${s.etapa}`, "stage-name"), element("span", s.herramienta, "stage-tool"));
    li.append(head);
    if (s.url) {
      const a = element("a", s.resumen, "stage-link");
      a.href = s.url;
      a.target = "_blank";
      a.rel = "noopener";
      li.append(a);
    } else {
      li.append(element("p", s.resumen, "stage-desc"));
    }
    list.append(li);
  }
  const details = element("details", null, "stages-box");
  details.open = true;
  details.append(element("summary", "Recorrido DevSecOps (8 etapas)"), list);
  container.append(details);
}

function renderGovernance(card, runId, action) {
  const box = card.querySelector(".governance");
  box.replaceChildren();
  if (!action) return;

  const panel = element("div", null, "gov-panel");
  panel.dataset.state = action.estado;
  const header = element("div", null, "gov-head");
  header.append(
    element("strong", "Gobernanza · Azure Boards"),
    element("span", action.tag_idempotencia, "gov-fp")
  );
  panel.append(header, element("p", action.titulo, "gov-title"));

  if (action.estado === "APROBADA" && action.boards_resultado) {
    const br = action.boards_resultado;
    const msg = element("p", `Tarea ${br.operacion} sin duplicados: `, "gov-result");
    const link = element("a", br.referencia);
    link.href = br.url;
    link.target = "_blank";
    link.rel = "noopener";
    msg.append(link);
    panel.append(msg);
  } else if (action.estado === "DESCARTADA") {
    panel.append(element("p", `Descartada: ${action.nota_humana || ""}`, "gov-result"));
  } else {
    const noteInput = document.createElement("input");
    noteInput.type = "text";
    noteInput.className = "gov-input";
    noteInput.placeholder = "Comentario opcional para Boards o motivo de descarte…";

    const actionsRow = element("div", null, "gov-buttons");
    const approveBtn = element("button", "Aprobar en Azure Boards", "btn-approve");
    approveBtn.type = "button";
    const dismissBtn = element("button", "Descartar", "btn-dismiss");
    dismissBtn.type = "button";

    const submitDecision = async (decision) => {
      approveBtn.disabled = true;
      dismissBtn.disabled = true;
      noteInput.disabled = true;
      status.textContent = decision === "aprobar" ? "Registrando tarea en Azure Boards…" : "Registrando descarte…";
      try {
        const res = await fetch("/api/acciones", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ejecucion: runId, decision, nota: noteInput.value }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "No se pudo actualizar la acción.");
        renderGovernance(card, runId, data.accion_propuesta);
        if (data.etapas_devsecops?.length) {
          renderStages(card.querySelector(".stages"), data.etapas_devsecops);
        }
        status.textContent = decision === "aprobar"
          ? `Tarea sincronizada en Azure Boards (${data.accion_propuesta?.boards_resultado?.referencia || "OK"})`
          : "Recomendación descartada con registro de auditoría.";
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

function showReport(card, report) {
  setCard(card, ...verdicts[report.veredicto], report.justificacion);
  renderStages(card.querySelector(".stages"), report.etapas_devsecops);

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
    evidence.append(element("p", `Pruebas xUnit · ${countLabels.join(" · ")}`));
  }
  if (report.siguiente_paso) evidence.append(element("p", report.siguiente_paso));

  const qa = report.investigacion;
  if (qa.detalle) evidence.prepend(element("p", qa.detalle));
  const notes = [
    ...report.referencias.map((ref) => `Fuente · ${ref.id}`),
    ...report.diagnosticos.map((diagnostic) => diagnostic.detalle),
    qa.explicacion,
    ...qa.llamadas.map((call) => tools[call.herramienta] || call.herramienta),
  ].filter(Boolean);
  if (notes.length) {
    const detail = element("details", "");
    const content = element("div", "", "detail-content");
    content.append(...notes.map((note) => element("p", note)));
    detail.append(element("summary", qa.proveedor ? "Evidencia y traza Agente QA" : "Evidencia"), content);
    evidence.append(detail);
  }

  const secops = report.investigacion_secops;
  if (secops && secops.estado && secops.estado !== "NO_SOLICITADA") {
    const secNotes = [
      secops.detalle,
      secops.resumen,
      ...(secops.hallazgos || []).map((h) => `[${h.alcance} · ${h.severidad}] ${h.titulo}: ${h.evidencia}`),
      ...(secops.llamadas || []).map((call) => tools[call.herramienta] || call.herramienta),
    ].filter(Boolean);
    if (secNotes.length) {
      const detail = element("details", "");
      const content = element("div", "", "detail-content");
      content.append(...secNotes.map((note) => element("p", note)));
      detail.append(element("summary", "Postura y traza Agente SecOps"), content);
      evidence.append(detail);
    }
  }

  renderGovernance(card, report.ejecucion.id, report.accion_propuesta);

  const files = [["informe.md", "Informe"], ["informe.json", "JSON"]];
  if (report.ejecucion.trx) files.push(["resultados.trx", "TRX"]);
  if (report.ejecucion.log) files.push(["dotnet-test.log", "Log"]);
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
    ? "Ejecuta en paralelo los agentes de QA y Seguridad/Operación sobre Azure AI Foundry; el veredicto es determinista."
    : "Revisa la evidencia local y de nube sin llamar al modelo.";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const mode = form.elements.modo.value;
  const chosen = form.elements.version.value === "todas" ? versions : [form.elements.version.value];
  const inputs = [...form.elements];
  inputs.forEach((input) => { input.disabled = true; });
  results.setAttribute("aria-busy", "true");
  for (const [version, card] of cards) {
    card.hidden = !chosen.includes(version);
    setCard(card, "idle", "En espera", "La versión está en la cola de evaluación.");
  }
  let issues = 0;
  try {
    for (const [index, version] of chosen.entries()) {
      const card = cards.get(version);
      status.textContent = `Evaluando ${version} · ${index + 1} de ${chosen.length}`;
      const reason = mode === "agente"
        ? "Ejecutando xUnit y consultando en paralelo Agente QA + Agente SecOps…"
        : "Ejecutando xUnit y recopilando evidencia…";
      setCard(card, "idle", "En curso", reason);
      try {
        const response = await fetch("/api/evaluar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version, modo: mode }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "La evaluación no pudo completarse.");
        if (showReport(card, data)) issues++;
      } catch (error) {
        issues++;
        setCard(card, "error", "Error de ejecución", error.message);
      }
    }
    status.textContent = issues
      ? `Evaluación finalizada · ${issues} ${issues === 1 ? "versión con diagnóstico" : "versiones con diagnóstico"}`
      : `${chosen.length} ${chosen.length === 1 ? "versión evaluada" : "versiones evaluadas"}`;
  } finally {
    results.setAttribute("aria-busy", "false");
    inputs.forEach((input) => { input.disabled = false; });
  }
});
