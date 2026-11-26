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
  listar_resultados: "Listó los resultados del TRX",
  buscar_pruebas_vinculadas: "Buscó pruebas vinculadas a REN-001",
  inspeccionar_prueba: "Inspeccionó el código de la prueba",
};

function element(tag, text) {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}

function setCard(card, state, label, reason) {
  const badge = card.querySelector(".badge");
  badge.dataset.state = state;
  badge.textContent = label;
  card.querySelector(".reason").textContent = reason;
  card.querySelector(".evidence").replaceChildren();
  card.querySelector(".downloads").replaceChildren();
}

function showReport(card, report) {
  setCard(card, ...verdicts[report.veredicto], report.justificacion);
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
    const content = element("div", "");
    content.className = "detail-content";
    content.append(...notes.map((note) => element("p", note)));
    detail.append(element("summary", qa.proveedor ? "Evidencia y traza de QA" : "Evidencia"), content);
    evidence.append(detail);
  }

  const files = [["informe.md", "Informe"], ["informe.json", "JSON"]];
  if (report.ejecucion.trx) files.push(["resultados.trx", "TRX"]);
  if (report.ejecucion.log) files.push(["dotnet-test.log", "Log"]);
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
    ? "El agente consulta la evidencia con el modelo configurado. El veredicto se calcula localmente."
    : "Revisa la evidencia local sin llamar al modelo.";
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
      const reason = mode === "agente" ? "Ejecutando xUnit y preparando la revisión del agente." : "Ejecutando xUnit y revisando la evidencia.";
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
