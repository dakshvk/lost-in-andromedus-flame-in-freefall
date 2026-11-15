// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// The investigation ranking (experiments.json) and the detail view for the
// investigations that have notes in investigations.json (matched on psi_id).

import { el, add, clear, link } from "./dom.js";
import { dialogShell } from "./materials.js";

export function renderRanking({ noteEl, filtersEl, listEl }, experimentsFile, investigations, onOpen) {
  const list = [...experimentsFile.experiments].sort((a, b) => a.rank - b.rank);
  noteEl.textContent = experimentsFile.note;
  const fuels = [...new Set(list.map((e) => e.fuel_type))];
  let active = "all";
  let expanded = false;
  const TOP = 5;

  const draw = () => {
    clear(listEl);
    const rows = list.filter((x) => active === "all" || x.fuel_type === active);
    for (const e of expanded ? rows : rows.slice(0, TOP)) {
      const inv = investigations.find((i) => i.psi_id === e.psi_id);
      listEl.append(el("li", { class: "rank-item panel" },
        el("div", { class: "rank-num", "aria-label": `Rank ${e.rank}` }, String(e.rank)),
        el("div", { class: "rank-main" },
          el("h3", {}, e.title),
          el("p", { class: "rank-meta" },
            el("span", { class: "tag" }, e.psi_id),
            el("span", { class: `tag fuel-${e.fuel_type}` }, `${e.fuel_type} fuel`),
            el("span", { class: "muted" }, e.sub_research_area),
            e.test_count !== null && e.test_count !== undefined
              ? el("span", { class: "muted", title: e.test_count_source || null }, `${e.test_count} tests`)
              : null),
          el("p", { class: "rank-summary" }, e.summary),
          el("ul", { class: "reasons", "aria-label": "Why it scored this" }, e.score_breakdown.map((r) =>
            el("li", { class: `reason${r.points > 0 ? "" : " is-zero"}` }, el("b", {}, `+${r.points}`), ` ${r.reason}`))),
          el("p", { class: "rank-actions" },
            inv && el("button", { type: "button", class: "btn btn-small", onclick: () => onOpen(inv, e) }, "Open details"),
            link(e.url, `${e.psi_id} on NASA PSI`))),
        el("div", { class: "rank-score", "aria-label": `Score ${e.score}` }, el("b", {}, String(e.score)), el("span", {}, "score"))));
    }
    if (rows.length > TOP) {
      listEl.append(el("li", { class: "rank-more" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => { expanded = !expanded; draw(); } },
          expanded ? `Show the top ${TOP}` : `Show all ${rows.length}`)));
    }
  };

  clear(filtersEl);
  const chip = (value, label) => el("button", {
    type: "button", class: "chip", "data-v": value, "aria-pressed": String(value === active),
    onclick: () => {
      active = value;
      expanded = false;
      filtersEl.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === value)));
      draw();
    },
  }, label);
  add(filtersEl, chip("all", `All (${list.length})`),
    fuels.map((f) => chip(f, `${f[0].toUpperCase()}${f.slice(1)} (${list.filter((e) => e.fuel_type === f).length})`)));
  draw();
}

export function openInvestigation(dialog, inv, experiment) {
  const row = (label, value) => (value ? [el("dt", {}, label), el("dd", {}, value)] : null);
  const body = el("div", { class: "detail-body" },
    el("dl", { class: "facts" },
      row("Objective", inv.objective),
      row("Fuels", inv.fuels),
      row("Conditions", inv.conditions),
      row("Sensors", inv.sensors),
      row("How it differs", inv.how_it_differs),
      row("Hardware", inv.hardware)),
    experiment && el("ul", { class: "reasons" }, experiment.score_breakdown.map((r) =>
      el("li", { class: `reason${r.points > 0 ? "" : " is-zero"}` }, el("b", {}, `+${r.points}`), ` ${r.reason}`))),
    el("p", { class: "sources" }, link(inv.source_url, `${inv.psi_id} on NASA PSI`)),
    inv.source_notes && el("p", { class: "muted small" }, inv.source_notes),
    inv.hardware_source && el("p", { class: "muted small" }, "Hardware: ", inv.hardware_source));
  dialogShell(dialog, inv.investigation, [
    el("span", { class: "tag" }, inv.psi_id),
    el("span", { class: "tag" }, inv.id),
    experiment && el("span", { class: "tag" }, `Rank ${experiment.rank}, score ${experiment.score}`),
  ], body);
}
