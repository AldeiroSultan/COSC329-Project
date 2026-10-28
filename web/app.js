// Dashboard logic (branch MF-00007). Plain JS, no build step.

const USE_MOCK = true; // flip to false once /api/plan works on staging (MF-00004 merged)
const CONCEPTS = ["C1", "C2", "C3"];

async function fetchPlan(payload) {
  if (USE_MOCK) {
    const res = await fetch("mock/plan.json");
    return res.json();
  }
  const res = await fetch("/api/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

function renderConceptInputs() {
  // TODO(MF-00007): for each concept, a difficulty select (easy/medium/hard)
  // and a quiz select (unknown/low/high)
}

function readForm(form) {
  // TODO(MF-00007): build {difficulty, quiz, sleep, exam_date} matching api.PlanRequest
  return {};
}

function renderPosteriors(plan) {
  // TODO(MF-00007): bar chart of P(Mastery=high) per concept, P(Stress=high), P(pass)
}

function renderExpectedUtility(plan) {
  // TODO(MF-00007): bar chart of plan.expected_utility, highlight plan.best_action
}

function renderCalendar(plan) {
  // TODO(MF-00007): simple 7-day grid showing plan.events
}

document.addEventListener("DOMContentLoaded", () => {
  renderConceptInputs();
  document.getElementById("plan-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const plan = await fetchPlan(readForm(e.target));
    renderPosteriors(plan);
    renderExpectedUtility(plan);
    renderCalendar(plan);
  });
});
