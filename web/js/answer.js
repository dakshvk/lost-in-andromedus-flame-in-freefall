// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// The answer panel. It shows what ask() returned and never rewrites it:
// the sentence, the evidence rows and every note are printed as given.

import { el, clear, link, pct, num, flowText, OUTCOME_LABEL } from "./dom.js";

const VERDICTS = {
  INSIDE: { cls: "v-inside", words: "Inside the tested range" },
  NEAR: { cls: "v-near", words: "Near the tested range" },
  BEYOND: { cls: "v-beyond", words: "Beyond what was tested" },
  NEED_OXYGEN: { cls: "v-neutral", words: "Needs an oxygen level", label: "MORE INFO" },
  INVALID: { cls: "v-neutral", words: "Not a possible condition" },
};

const isUrl = (s) => typeof s === "string" && /^https?:\/\//.test(s);

function evidenceTable(rows) {
  const hasPressure = rows.some((r) => r.pressure_kPa !== null && r.pressure_kPa !== undefined);
  return el("div", { class: "table-wrap", tabindex: "0", role: "region", "aria-label": "Evidence rows" },
    el("table", {},
      el("thead", {}, el("tr", {},
        ["Test", "Material", "Oxygen", "Flow, cm/s", hasPressure && "Pressure, kPa", "Outcome", "Source"]
          .filter(Boolean).map((h) => el("th", { scope: "col" }, h)))),
      el("tbody", {}, rows.map((r) => el("tr", {},
        el("th", { scope: "row" }, r.test_id),
        el("td", {}, r.material, r.material_form && r.material_form !== "unknown" ? el("span", { class: "muted" }, ` ${r.material_form}`) : null),
        el("td", {}, pct(r.oxygen_pct)),
        el("td", {}, flowText(r.airflow_cm_s, r.airflow_end_cm_s)),
        hasPressure && el("td", {}, r.pressure_kPa === null || r.pressure_kPa === undefined ? "" : num(r.pressure_kPa)),
        el("td", {}, el("span", { class: `pill oc-text-${r.outcome}` }, OUTCOME_LABEL[r.outcome] || r.outcome)),
        el("td", {}, isUrl(r.source_url) ? link(r.source_url, r.source) : r.source))))));
}

// One code answer (verdict, sentence, evidence and notes).
function codeAnswer(a, heading) {
  // A highest/lowest answer is a fact from the table, not a verdict about a
  // condition, so it gets a neutral label instead of "Inside the tested range".
  const fact = a.kind === "extreme" || a.kind === "range";
  const v = fact
    ? { cls: "v-neutral", words: "From the test table" }
    : VERDICTS[a.verdict] || { cls: "v-neutral", words: a.verdict || "Answer" };
  const label = fact ? "RESULT" : (v.label || a.verdict || "");
  const check = a.number_check;
  return el("div", { class: "answer-block" },
    heading && el("p", { class: "eyebrow" }, heading),
    el("div", { class: "badges" },
      el("span", { class: `verdict ${v.cls}` }, el("span", { class: "verdict-dot", "aria-hidden": "true" }),
        el("b", {}, label), el("span", {}, v.words)),
      check && check.ok && a.verdict !== "NEED_OXYGEN" && el("span", { class: "badge badge-ok" },
        el("svg", { viewBox: "0 0 16 16", width: 13, height: 13, "aria-hidden": "true" },
          el("path", { d: "M3 8.5l3.2 3L13 4.5", fill: "none", stroke: "currentColor", "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round" })),
        "Every number checked against the data"),
      check && !check.ok && el("span", { class: "badge badge-warn" },
        `Number check failed${check.unverified && check.unverified.length ? `: ${check.unverified.join(", ")}` : ""}`)),
    el("p", { class: "sentence" }, a.sentence),
    a.note && el("p", { class: "note" }, a.note),
    a.evidence && a.evidence.length
      ? [el("h3", {}, "Evidence"), evidenceTable(a.evidence)]
      : null,
    a.nearest_evidence && el("div", { class: "nearest" },
      el("h3", {}, "Nearest evidence"),
      el("p", {}, a.nearest_evidence.text),
      a.nearest_evidence.source && el("p", { class: "muted small" }, "Source: ", a.nearest_evidence.source)),
    a.unknown && a.unknown.length
      ? el("div", { class: "unknown" }, el("h3", {}, "Not known"), el("ul", {}, a.unknown.map((u) => el("li", {}, u))))
      : null,
    a.gravity_note && el("p", { class: "gravity" },
      el("svg", { viewBox: "0 0 20 20", width: 16, height: 16, "aria-hidden": "true" },
        el("circle", { cx: 10, cy: 10, r: 8, fill: "none", stroke: "currentColor", "stroke-width": 1.6 }),
        el("path", { d: "M10 9v5M10 6.2v.2", fill: "none", stroke: "currentColor", "stroke-width": 1.8, "stroke-linecap": "round" })),
      el("span", {}, a.gravity_note)),
    a.sources && a.sources.length
      ? el("p", { class: "sources" }, el("span", { class: "muted" }, "Sources: "),
          a.sources.map((s, i) => [i ? ", " : "", isUrl(s) ? link(s, s.replace(/^https?:\/\//, "")) : s]))
      : null);
}

// Retrieval answer: the matched entries, printed as stored, with their source.
function ragAnswer(retrieval, ctx) {
  if (!retrieval || !retrieval.match || !retrieval.results.length) {
    return el("div", { class: "answer-block" },
      el("div", { class: "badges" }, el("span", { class: "verdict v-neutral" },
        el("span", { class: "verdict-dot", "aria-hidden": "true" }), el("b", {}, "No match in our data"))),
      el("p", { class: "sentence" }, "Nothing in the test data or the investigation notes matches this question, so there is no answer to show."));
  }
  return el("div", { class: "answer-block" },
    el("div", { class: "badges" }, el("span", { class: "verdict v-neutral" },
      el("span", { class: "verdict-dot", "aria-hidden": "true" }), el("b", {}, "Closest matches in our data"))),
    el("ol", { class: "matches" }, retrieval.results.map((r) => {
      const e = r.entry;
      const inv = e.psi_id && ctx.investigations.find((i) => i.psi_id === e.psi_id);
      return el("li", { class: "match" },
        el("p", { class: "match-kind" }, e.kind === "investigation" ? "Investigation" : "Material note", e.psi_id ? ` · ${e.psi_id}` : ""),
        el("p", { class: "match-text" }, e.text),
        el("p", { class: "match-links" },
          isUrl(e.source) ? link(e.source, e.psi_id ? `${e.psi_id} on NASA PSI` : "Source") : e.source,
          inv && el("button", { type: "button", class: "btn btn-small btn-ghost", onclick: () => ctx.onInvestigation(inv) }, "Open details")));
    })));
}

export function renderAnswer(host, question, result, ctx) {
  clear(host);
  host.hidden = false;
  const main = el("div", { class: "panel answer" },
    el("p", { class: "eyebrow" }, "You asked"),
    el("h2", { class: "question" }, question));

  if (result.offline) {
    main.append(el("p", { class: "note note-offline" },
      result.error ? result.error : "Offline answer: the answer service could not be reached, so this is a saved answer."));
  }

  if (result.error) {
    if (!result.offline) main.append(el("p", { class: "note" }, result.error));
    if (result.examples && result.examples.length) {
      main.append(el("div", { class: "chips" }, result.examples.map((q) =>
        el("button", { type: "button", class: "chip", onclick: () => ctx.onAsk(q, true) }, q))));
    }
  } else if (result.path === "rag") {
    main.append(ragAnswer(result.retrieval, ctx));
  } else if (result.answer && result.answer.verdict) {
    main.append(codeAnswer(result.answer));
  } else if (result.answer) {
    // A saved comparison holds one answer per material.
    const parts = Object.entries(result.answer).filter(([, v]) => v && typeof v === "object" && v.verdict);
    if (parts.length) parts.forEach(([k, v]) => main.append(codeAnswer(v, k.toUpperCase())));
    else main.append(el("p", { class: "note" }, "This answer came back in a shape the page does not know how to show."));
  }
  if (result.reason) main.append(el("p", { class: "muted small answer-reason" }, "How this was answered: ", result.reason));

  const entry = result.material ? ctx.entryFor(result.material) : null;
  const layout = el("div", { class: `answer-layout${entry ? " has-aside" : ""}` }, main);
  host.append(layout);
  if (entry) {
    const aside = ctx.materialAside(entry);
    layout.append(aside.node);
    aside.mount();
  }
}

export function renderLoading(host, question) {
  clear(host);
  host.hidden = false;
  host.append(el("div", { class: "panel answer is-loading" },
    el("p", { class: "eyebrow" }, "You asked"),
    el("h2", { class: "question" }, question),
    el("p", { class: "muted" }, "Checking the test data…")));
}
