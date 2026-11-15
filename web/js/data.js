// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// Lane C data layer: the only file the page needs to talk to the data.
// No design here. Every view (moon, map, cards, ranking, answer panel)
// gets its data through these functions, so the design can change
// without touching where the numbers come from.
//
// Option A: the API (api/app.py) serves the data and answers questions.
// If the API is unreachable, data comes from the static web/data/*.json
// files and questions fall back to the saved demo answers.

// Same origin by default. Set window.FLAME_API_BASE before loading this
// module when the site and the API are hosted on different domains.
const API_BASE = (typeof window !== "undefined" && window.FLAME_API_BASE) || "";

async function getJSON(name) {
  try {
    const res = await fetch(`${API_BASE}/api/data/${name}`);
    if (res.ok) return await res.json();
  } catch (_) {
    // API down or not running: use the static copy below.
  }
  const res = await fetch(`data/${name}.json`);
  if (!res.ok) throw new Error(`Could not load ${name}.json (${res.status})`);
  return res.json();
}

export const loadTests = () => getJSON("tests");                 // map points
export const loadCards = () => getJSON("cards");                 // material cards
export const loadExperiments = () => getJSON("experiments");     // ranking
export const loadInvestigations = () => getJSON("investigations");
export const loadLimits = () => getJSON("limits");               // limits drawer
export const loadMeta = () => getJSON("meta");

// Ask a question. Returns Lane B's answer plus `material` (the material
// the question names, or null) and `offline` (true when the answer came
// from the saved demo answers because the API could not be reached).
export async function ask(question) {
  try {
    const res = await fetch(`${API_BASE}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (res.ok) return { ...(await res.json()), offline: false };
    if (res.status === 422) {
      return { offline: false, error: "Please type a question (300 characters at most)." };
    }
  } catch (_) {
    // fall through to the saved answers
  }
  const demo = await getJSON("demo_answers");
  const wanted = question.trim().toLowerCase();
  const hit = demo.answers.find((a) => a.question.trim().toLowerCase() === wanted);
  if (hit) return { path: "code", answer: hit, material: null, offline: true };
  return {
    offline: true,
    error: "The answer service is offline. Try one of the example questions.",
    examples: demo.answers.map((a) => a.question),
  };
}

// All cards in one list: the standard materials, then the low-pressure
// Saffire V group (each card has group: "standard" or "low_pressure").
export function allCards(cardsFile) {
  return [...cardsFile.cards, ...cardsFile.low_pressure_group.cards];
}

// The card for a material name from ask() ("PMMA", "Cotton", ...). A name
// that only exists at low pressure (Cotton) matches its Saffire V card.
export function cardForMaterial(cardsFile, material) {
  if (!material) return null;
  const cards = allCards(cardsFile);
  return (
    cards.find((c) => c.material === material) ||
    cards.find((c) => c.material.startsWith(`${material} (Saffire V`)) ||
    null
  );
}

// Map points for one material (for its own graph). Link et al. rows are
// kept but flagged (is_link2018) so the view can hide or style them.
export function pointsForMaterial(tests, material) {
  return tests.filter(
    (t) => t.material === material || t.material.startsWith(`${material} (Saffire V`)
  );
}

// Points that can sit on the oxygen x airflow map: they need an oxygen
// value. A test whose flow changed is drawn from flow_start to flow_end.
export function mapPoints(tests) {
  return tests.filter((t) => t.o2_start !== null && !t.context_only);
}
