const metaUrl = "/api/v1/meta/review";
const analyzeUrl = "/api/v1/analyze";

const elements = {
  modePill: document.getElementById("mode-pill"),
  pipelineSteps: document.getElementById("pipeline-steps"),
  noteInput: document.getElementById("note-input"),
  analyzeButton: document.getElementById("analyze-button"),
  entitiesOutput: document.getElementById("entities-output"),
  codesOutput: document.getElementById("codes-output"),
  diagnosisOutput: document.getElementById("diagnosis-output"),
  reportOutput: document.getElementById("report-output"),
};

async function loadMeta() {
  try {
    const response = await fetch(metaUrl);
    const meta = await response.json();
    elements.modePill.textContent = `Mode: ${meta.configured_mode}`;
    elements.pipelineSteps.innerHTML = meta.pipeline_steps
      .map((step, i) => `<li><span class="step-num">${i + 1}</span>${step}</li>`)
      .join("");
  } catch (_) {
    elements.modePill.textContent = "Status unknown";
  }
}

async function analyzeNote() {
  const noteText = elements.noteInput.value.trim();
  if (!noteText) return;

  elements.analyzeButton.disabled = true;
  elements.analyzeButton.textContent = "Analyzing...";
  elements.entitiesOutput.textContent = "Running...";
  elements.codesOutput.textContent = "Running...";
  elements.diagnosisOutput.textContent = "Running...";
  elements.reportOutput.textContent = "Running...";

  try {
    const response = await fetch(analyzeUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note_text: noteText, include_report: true }),
    });
    const data = await response.json();

    elements.modePill.textContent = `Mode: ${data.mode}`;
    elements.modePill.style.background = data.mode === "full" ? "rgba(12,138,129,0.18)" : "rgba(200,80,40,0.15)";

    elements.entitiesOutput.textContent = JSON.stringify(data.entities, null, 2);
    elements.codesOutput.textContent = JSON.stringify(data.icd_codes, null, 2);
    elements.diagnosisOutput.textContent = JSON.stringify(
      { diagnosis: data.diagnosis, risks: data.risks, validation_notes: data.validation_notes },
      null, 2,
    );
    elements.reportOutput.textContent = data.report || "(no report)";
  } catch (error) {
    elements.reportOutput.textContent = `Error: ${error}`;
  } finally {
    elements.analyzeButton.disabled = false;
    elements.analyzeButton.textContent = "Analyze Note";
  }
}

elements.analyzeButton.addEventListener("click", analyzeNote);
loadMeta();

loadMeta().catch((error) => {
  elements.modelName.textContent = "Meta load failed";
  elements.modelRuntime.textContent = String(error);
});
