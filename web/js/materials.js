// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// Material views: the cards grid, the small marker preview, the full detail
// dialog (card, graph, test table) and the card shown next to an answer.
// All counts and ranges are read from cards.json; nothing is recomputed
// except adding up the three Saffire V cards for their shared marker.

import { cardForMaterial, pointsForMaterial } from "./data.js";
import { createChart } from "./chart.js";
import {
  el, clear, link, pct, num, range, flowText, trim, baseMaterial,
  MOON_O2, BAR_AXIS_MAX, OUTCOMES, OUTCOME_LABEL, MATERIAL_COLORS, LOW_PRESSURE_COLOR,
} from "./dom.js";

// One entry per Moon marker: each standard material, then the Saffire V group.
export function buildEntries(cardsFile) {
  const entries = cardsFile.cards.map((c, i) => ({
    key: c.id,
    name: c.material,
    label: c.material,
    color: MATERIAL_COLORS[i % MATERIAL_COLORS.length],
    kind: "standard",
    cards: [c],
    summary: c,
  }));
  const lp = cardsFile.low_pressure_group;
  if (lp && lp.cards.length) {
    entries.push({
      key: "low-pressure",
      name: lp.title,
      label: "Low pressure",
      color: LOW_PRESSURE_COLOR,
      kind: "low_pressure",
      note: lp.note,
      cards: lp.cards,
      summary: sumCards(lp.cards),
    });
  }
  return entries;
}

// Adds up the low-pressure cards so the group has one preview.
function sumCards(cards) {
  const outcomes = {};
  for (const o of OUTCOMES) outcomes[o] = cards.reduce((n, c) => n + (c.outcomes[o] || 0), 0);
  const span = (key) => {
    const vals = cards.flatMap((c) => c[key]).filter((v) => v !== null && v !== undefined);
    return vals.length ? [Math.min(...vals), Math.max(...vals)] : [null, null];
  };
  const sources = [];
  for (const s of cards.flatMap((c) => c.sources)) if (!sources.some((x) => x.url === s.url)) sources.push(s);
  return {
    test_count: cards.reduce((n, c) => n + c.test_count, 0),
    known_outcomes: cards.reduce((n, c) => n + c.known_outcomes, 0),
    outcomes,
    oxygen_range_pct: span("oxygen_range_pct"),
    airflow_range_cm_s: span("airflow_range_cm_s"),
    pressure_kPa: [...new Set(cards.flatMap((c) => c.pressure_kPa))].sort((a, b) => a - b),
    forms: [...new Set(cards.flatMap((c) => c.forms))],
    too_few: cards.every((c) => c.too_few),
    sources,
    test_ids: cards.flatMap((c) => c.test_ids),
    low_flow_uncertain_tests: cards.reduce((n, c) => n + (c.low_flow_uncertain_tests || 0), 0),
    link2018_rows: cards.reduce((n, c) => n + (c.link2018_rows || 0), 0),
  };
}

// The marker entry for a material name returned by ask().
export function entryForMaterial(entries, cardsFile, material) {
  const card = cardForMaterial(cardsFile, material);
  if (!card) return null;
  return entries.find((e) => e.cards.includes(card)) || null;
}

function entryPoints(entry, tests) {
  if (entry.kind === "standard") return pointsForMaterial(tests, entry.name);
  const seen = new Set();
  return entry.cards.flatMap((c) => pointsForMaterial(tests, c.material)).filter((p) => !seen.has(p.id) && seen.add(p.id));
}

// ---- small shared pieces -------------------------------------------------

// Oxygen range on the shared 0 to 40% axis with the Moon cabin line.
export function o2Bar(pair, { compact = false } = {}) {
  const [a, b] = pair || [null, null];
  const has = a !== null && a !== undefined;
  const left = has ? (a / BAR_AXIS_MAX) * 100 : 0;
  const width = has ? ((b - a) / BAR_AXIS_MAX) * 100 : 0;
  return el("div", { class: `o2bar${compact ? " is-compact" : ""}` },
    el("div", {
      class: "o2bar-track", role: "img",
      "aria-label": has
        ? `Oxygen tested: ${range(pair, "", pct)}. Moon cabin line at ${MOON_O2}%.`
        : "Oxygen not recorded.",
    },
      has && el("span", { class: "o2bar-fill", style: { left: `${left}%`, width: `max(${width}%, 4px)` } }),
      el("span", { class: "o2bar-moon", style: { left: `${(MOON_O2 / BAR_AXIS_MAX) * 100}%` } })),
    el("div", { class: "o2bar-axis", "aria-hidden": "true" },
      el("span", { style: { left: "0%" } }, "0%"),
      el("span", { class: "is-moon", style: { left: `${(MOON_O2 / BAR_AXIS_MAX) * 100}%` } }, compact ? `${MOON_O2}%` : `${MOON_O2}% Moon`),
      el("span", { style: { left: "100%" } }, `${BAR_AXIS_MAX}%`)));
}

// Stacked bar of outcome counts, with a counted legend unless compact.
export function outcomeBar(outcomes, { compact = false } = {}) {
  const shown = OUTCOMES.filter((o) => (outcomes[o] || 0) > 0);
  const text = shown.map((o) => `${outcomes[o]} ${OUTCOME_LABEL[o].toLowerCase()}`).join(", ");
  return el("div", { class: `ocbar${compact ? " is-compact" : ""}` },
    el("div", { class: "ocbar-track", role: "img", "aria-label": `Outcomes: ${text || "none recorded"}.` },
      shown.map((o) => el("span", { class: `ocbar-seg bg-${o}`, style: { flexGrow: String(outcomes[o]) } }))),
    !compact && el("ul", { class: "ocbar-legend" },
      shown.map((o) => el("li", {}, el("span", { class: `dot bg-${o}`, "aria-hidden": "true" }), `${OUTCOME_LABEL[o]} `, el("b", {}, String(outcomes[o]))))));
}

function sourceLinks(sources) {
  return el("p", { class: "sources" }, el("span", { class: "muted" }, "Sources: "),
    sources.map((s, i) => [i ? ", " : "", link(s.url, s.name)]));
}

function stat(label, value) {
  return el("div", { class: "stat" }, el("dt", {}, label), el("dd", {}, value));
}

function cardFacts(c) {
  return el("dl", { class: "stats" },
    stat("Tests", String(c.test_count)),
    stat("Known outcomes", String(c.known_outcomes)),
    stat("Airflow", range(c.airflow_range_cm_s, " cm/s")),
    c.pressure_kPa && c.pressure_kPa.length ? stat("Pressure, where recorded", `${c.pressure_kPa.map(num).join(", ")} kPa`) : null);
}

const askQuestion = (name) => `Will ${name === "PMMA" || name === "SIBAL" ? name : name.toLowerCase()} burn at ${MOON_O2}% oxygen?`;

// ---- cards grid ----------------------------------------------------------

export function renderCards(host, entries, handlers) {
  clear(host);
  for (const entry of entries) {
    host.append(entry.kind === "standard" ? standardCard(entry, handlers) : groupCard(entry, handlers));
  }
}

function standardCard(entry, { onAsk, onOpen }) {
  const c = entry.summary;
  return el("article", { class: "card", id: `card-${entry.key}`, style: { "--mat": entry.color } },
    el("header", { class: "card-head" },
      el("h3", {}, el("span", { class: "mat-dot", "aria-hidden": "true" }), c.material),
      c.too_few && el("span", { class: "tag tag-warn" }, "Too few to cover")),
    el("p", { class: "forms" }, "Tested as: ", c.forms.join(", ")),
    cardFacts(c),
    el("p", { class: "bar-title" }, "Oxygen tested: ", el("b", {}, range(c.oxygen_range_pct, "", pct))),
    o2Bar(c.oxygen_range_pct),
    el("p", { class: "bar-title" }, "Outcomes"),
    outcomeBar(c.outcomes),
    sourceLinks(c.sources),
    el("div", { class: "card-actions" },
      el("button", { type: "button", class: "btn", onclick: () => onAsk(askQuestion(c.material)) }, "Ask about this material"),
      el("button", { type: "button", class: "btn btn-ghost", onclick: () => onOpen(entry) }, "See the tests")));
}

function groupCard(entry, { onAsk, onOpen }) {
  const names = [...new Set(entry.cards.map((c) => baseMaterial(c.material)))];
  return el("article", { class: "card card-wide", id: `card-${entry.key}`, style: { "--mat": entry.color } },
    el("header", { class: "card-head" },
      el("h3", {}, el("span", { class: "mat-dot", "aria-hidden": "true" }), entry.name),
      entry.summary.too_few && el("span", { class: "tag tag-warn" }, "Too few to cover")),
    el("p", { class: "forms" }, entry.note),
    el("div", { class: "subcards" }, entry.cards.map((c) =>
      el("section", { class: "subcard" },
        el("h4", {}, c.material),
        el("p", { class: "forms" }, "Tested as: ", c.forms.join(", "), ". Test ", c.test_ids.join(", ")),
        cardFacts(c),
        el("p", { class: "bar-title" }, "Oxygen tested: ", el("b", {}, range(c.oxygen_range_pct, "", pct))),
        o2Bar(c.oxygen_range_pct),
        outcomeBar(c.outcomes)))),
    sourceLinks(entry.summary.sources),
    el("div", { class: "card-actions" },
      names.map((n) => el("button", { type: "button", class: "btn", onclick: () => onAsk(askQuestion(n)) }, `Ask about ${n === "PMMA" ? n : n.toLowerCase()}`)),
      el("button", { type: "button", class: "btn btn-ghost", onclick: () => onOpen(entry) }, "See the tests")));
}

// ---- marker preview ------------------------------------------------------

export function previewContent(entry, onOpen) {
  const c = entry.summary;
  return [
    el("p", { class: "preview-title", style: { "--mat": entry.color } }, el("span", { class: "mat-dot", "aria-hidden": "true" }), entry.name),
    el("p", { class: "preview-line" }, el("b", {}, String(c.test_count)), ` tests, ${c.known_outcomes} with a known outcome`),
    el("p", { class: "preview-line" }, "Oxygen ", el("b", {}, range(c.oxygen_range_pct, "", pct))),
    o2Bar(c.oxygen_range_pct, { compact: true }),
    el("p", { class: "preview-line" }, "Airflow ", el("b", {}, range(c.airflow_range_cm_s, " cm/s")),
      entry.kind === "low_pressure" && c.pressure_kPa.length ? [" at ", el("b", {}, `${range([c.pressure_kPa[0], c.pressure_kPa[c.pressure_kPa.length - 1]], " kPa")}`)] : null),
    outcomeBar(c.outcomes, { compact: true }),
    el("button", { type: "button", class: "btn btn-small", tabindex: "-1", onclick: () => onOpen(entry) }, "Open all tests"),
  ];
}

// ---- material detail (dialog) and answer-side card ------------------------

function describe(entry, limits) {
  const c = entry.summary;
  const parts = [
    `${c.test_count} tests are counted here, ${c.known_outcomes} with a known outcome, tested as ${c.forms.join(", ")}.`,
    `Oxygen ran ${range(c.oxygen_range_pct, "", pct)} and airflow ${range(c.airflow_range_cm_s, " cm/s")}` +
      (c.oxygen_range_pct[1] !== null && c.oxygen_range_pct[1] < MOON_O2 ? `, so the evidence stops short of the ${MOON_O2}% Moon cabin line.` : "."),
  ];
  if (c.low_flow_uncertain_tests) {
    parts.push(`${c.low_flow_uncertain_tests} of them ran under ${num(limits.low_flow_cutoff_cm_s)} cm/s, where flow readings are uncertain.`);
  }
  if (c.link2018_rows) {
    parts.push(`${c.link2018_rows} more rows from Link et al. 2018 are listed for context only and are not counted.`);
  }
  if (c.too_few) parts.push("That is too few tests to say a condition is covered.");
  return parts.join(" ");
}

function detailBody(entry, tests, limits, cardsFile) {
  const c = entry.summary;
  const pts = entryPoints(entry, tests);
  const chartHost = el("div", {});
  const hasPressure = pts.some((p) => p.pressure_kPa !== null);
  const body = el("div", { class: "detail-body" },
    entry.note && el("p", { class: "note" }, entry.note),
    el("p", { class: "detail-desc" }, describe(entry, limits)),
    el("div", { class: "detail-top" },
      el("div", { class: "detail-card", style: { "--mat": entry.color } },
        cardFacts(c),
        el("p", { class: "bar-title" }, "Oxygen tested: ", el("b", {}, range(c.oxygen_range_pct, "", pct))),
        o2Bar(c.oxygen_range_pct),
        el("p", { class: "bar-title" }, "Outcomes"),
        outcomeBar(c.outcomes),
        sourceLinks(c.sources),
        el("p", { class: "muted small" }, cardsFile.counting_rule)),
      el("div", { class: "detail-chart" }, chartHost)),
    el("h3", {}, `All ${pts.length} rows`),
    el("div", { class: "table-wrap", tabindex: "0", role: "region", "aria-label": `Test table for ${entry.name}` },
      el("table", {},
        el("thead", {}, el("tr", {},
          ["Test", "Material", "Shape", "Oxygen", "Flow, cm/s", hasPressure && "Pressure, kPa", "Outcome", "Notes", "Citation"]
            .filter(Boolean).map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, pts.map((p) => el("tr", { class: p.is_link2018 || p.context_only ? "is-context" : null },
          el("th", { scope: "row" }, p.test_id),
          el("td", {}, p.material,
            p.is_link2018 && el("span", { class: "tag" }, "Link 2018"),
            p.context_only && el("span", { class: "tag" }, "Context only"),
            p.low_flow_uncertain && el("span", { class: "tag" }, "Low flow")),
          el("td", {}, p.shape),
          el("td", {}, pct(p.o2_start)),
          el("td", {}, flowText(p.flow_start, p.flow_end)),
          hasPressure && el("td", {}, p.pressure_kPa === null ? "" : num(p.pressure_kPa)),
          el("td", {}, el("span", { class: `pill oc-text-${p.outcome}` }, OUTCOME_LABEL[p.outcome] || p.outcome)),
          el("td", { class: "cell-note" }, trim([p.outcome_note, p.flow_note].filter(Boolean).join(" "), 220)),
          el("td", { class: "cell-note" }, p.citation)))))));
  return { body, mount: () => createChart(chartHost, pts, { compact: true, label: `${entry.name} tests` }) };
}

export function dialogShell(dialog, title, tags, body) {
  clear(dialog).append(
    el("div", { class: "modal-head" },
      el("div", {}, el("h2", { id: `${dialog.id}-title` }, title), tags && el("p", { class: "modal-tags" }, tags)),
      el("button", { type: "button", class: "icon-btn", "aria-label": "Close", onclick: () => dialog.close() }, "×")),
    body);
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop = 0;
}

export function openMaterialDetail(dialog, entry, ctx) {
  const { body, mount } = detailBody(entry, ctx.tests, ctx.limits, ctx.cardsFile);
  const c = entry.summary;
  body.append(el("div", { class: "card-actions" },
    [...new Set(entry.cards.map((x) => baseMaterial(x.material)))].map((n) =>
      el("button", { type: "button", class: "btn", onclick: () => { dialog.close(); ctx.onAsk(askQuestion(n)); } },
        `Ask about ${n === "PMMA" || n === "SIBAL" ? n : n.toLowerCase()}`))));
  dialogShell(dialog, entry.name, [
    el("span", { class: "tag" }, `${c.test_count} tests`),
    c.too_few && el("span", { class: "tag tag-warn" }, "Too few to cover"),
    el("span", { class: "tag" }, "Run in orbit, in microgravity"),
  ], body);
  mount();
}

// The compact card and graph shown beside an answer that names a material.
export function materialAside(entry, ctx) {
  const c = entry.summary;
  const chartHost = el("div", {});
  const node = el("aside", { class: "panel aside", style: { "--mat": entry.color }, "aria-label": `${entry.name} card and graph` },
    el("header", { class: "card-head" },
      el("h3", {}, el("span", { class: "mat-dot", "aria-hidden": "true" }), entry.name),
      c.too_few && el("span", { class: "tag tag-warn" }, "Too few to cover")),
    entry.note && el("p", { class: "forms" }, entry.note),
    cardFacts(c),
    el("p", { class: "bar-title" }, "Oxygen tested: ", el("b", {}, range(c.oxygen_range_pct, "", pct))),
    o2Bar(c.oxygen_range_pct),
    outcomeBar(c.outcomes),
    chartHost,
    el("div", { class: "card-actions" },
      el("button", { type: "button", class: "btn btn-ghost", onclick: () => ctx.onOpen(entry) }, "See the tests")));
  return { node, mount: () => createChart(chartHost, entryPoints(entry, ctx.tests), { compact: true, label: `${entry.name} tests` }) };
}
