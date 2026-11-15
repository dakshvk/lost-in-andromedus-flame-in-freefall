// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// The limits drawer and the footer. Every value and rule is read from
// limits.json; source links are collected from the data files.

import { el, add, clear, link, num } from "./dom.js";

export const MOON_CREDIT = {
  text: "Moon texture and elevation: NASA's Scientific Visualization Studio, CGI Moon Kit (LRO data).",
  url: "https://svs.gsfc.nasa.gov/4720",
};

// Plain-language names for the threshold keys in limits.json.
const VALUE_LABELS = {
  near_margin_oxygen_points: ["NEAR margin, oxygen", "points of oxygen"],
  near_margin_flow_fraction: ["NEAR margin, airflow", "of the material's flow range (as a fraction)"],
  low_flow_cutoff_cm_s: ["Low flow cutoff", "cm/s"],
  standard_pressure_min_kPa: ["Standard pressure starts at", "kPa"],
  duct_airflow_max_cm_s: ["Duct airflow maximum", "cm/s"],
  duct_airflow_near_max_cm_s: ["Duct airflow, near maximum", "cm/s"],
  rag_score_cutoff: ["Match score cutoff for text questions", ""],
};

export function renderLimits(dialog, limits) {
  const values = Object.entries(limits).filter(([, v]) => typeof v === "number");
  clear(dialog).append(
    el("div", { class: "modal-head" },
      el("h2", { id: "limits-title" }, "Limits and rules"),
      el("button", { type: "button", class: "icon-btn", "aria-label": "Close", onclick: () => dialog.close() }, "×")),
    el("div", { class: "detail-body" },
      el("p", { class: "gravity" }, el("span", {}, limits.gravity_note)),
      el("h3", {}, "Thresholds"),
      el("dl", { class: "facts" }, values.map(([k, v]) => {
        const [label, unit] = VALUE_LABELS[k] || [k.replaceAll("_", " "), ""];
        return [el("dt", {}, label), el("dd", {}, el("b", {}, num(v)), unit ? ` ${unit}` : "")];
      })),
      el("h3", {}, "Rules"),
      el("ul", { class: "rules" }, (limits.rules || []).map((r) => el("li", {}, r))),
      limits.ranking_note && [el("h3", {}, "Ranking"), el("p", {}, limits.ranking_note)],
      el("h3", {}, "Acknowledgment and license"),
      el("p", {}, limits.si_acknowledgment),
      el("p", {}, limits.license),
      el("p", {}, link(MOON_CREDIT.url, MOON_CREDIT.text))));
}

// Footer sources: PSI pages and papers named in the data, plus the reports
// the test rows cite.
export function renderFooter({ listEl, siEl, licenseEl }, { cardsFile, experimentsFile, tests, limits }) {
  const items = [];
  const addSource = (name, url) => { if (!items.some((i) => i.name === name)) items.push({ name, url }); };

  for (const c of [...cardsFile.cards, ...cardsFile.low_pressure_group.cards]) {
    for (const s of c.sources) addSource(s.name, s.url);
  }
  // Reports and papers cited by the test rows (text taken from the citations).
  const cites = tests.map((t) => t.citation || "");
  const firstMatch = (re) => { for (const c of cites) { const m = c.match(re); if (m) return m; } return null; };
  const bass = firstMatch(/BASS-II report (NASA\/TM-\d+)/);
  if (bass) addSource(`BASS-II summary report, ${bass[1]}`, null);
  const zhao = firstMatch(/Zhao et al\. 2015, NASA (\d+)/);
  if (zhao) addSource(`Zhao et al. 2015, NASA ${zhao[1]}`, `https://ntrs.nasa.gov/citations/${zhao[1]}`);
  const linkPaper = firstMatch(/Link et al\., Scientific Reports 2018 \(DOI ([^)]+)\)/);
  if (linkPaper) addSource("Link et al. 2018, Scientific Reports", `https://doi.org/${linkPaper[1]}`);

  add(clear(listEl),
    items.map((i) => el("li", {}, i.url ? link(i.url, i.name) : i.name)),
    el("li", {}, el("details", {},
      el("summary", {}, `All ${experimentsFile.experiments.length} ranked NASA PSI investigations`),
      el("ul", { class: "source-sub" }, experimentsFile.experiments.map((e) => el("li", {}, link(e.url, `${e.psi_id}: ${e.title}`)))))),
    el("li", {}, link(MOON_CREDIT.url, MOON_CREDIT.text)));
  siEl.textContent = limits.si_acknowledgment;
  licenseEl.textContent = limits.license;
}
