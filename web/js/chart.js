// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// The evidence map: oxygen % (x) against airflow cm/s (y), one mark per test.
// Used for the main map and for each material's own graph. Plain SVG, no
// library. Positions are never jittered: a mark sits where the test was run.

import { mapPoints } from "./data.js";
import {
  el, add, clear, pct, num, flowText, trim, baseMaterial,
  MOON_O2, MAP_AXIS_MIN_RIGHT, OUTCOMES, OUTCOME_LABEL,
} from "./dom.js";

const tooltip = () => document.getElementById("tooltip");

// Marker shape per outcome, drawn around (0,0). Shape and colour both carry
// the outcome so the map still reads without colour.
function markPath(outcome, r) {
  switch (outcome) {
    case "quenched": return `M0 ${r} L${r} ${-r * 0.8} L${-r} ${-r * 0.8} Z`;
    case "blow_off": return `M0 ${-r * 1.15} L${r * 1.15} 0 L0 ${r * 1.15} L${-r * 1.15} 0 Z`;
    case "no_ignition": return `M${-r} ${-r} L${r} ${r} M${-r} ${r} L${r} ${-r}`;
    case "ignited_only": return `M${-r} ${-r} H${r} V${r} H${-r} Z`;
    default: return `M${r} 0 A${r} ${r} 0 1 1 ${-r} 0 A${r} ${r} 0 1 1 ${r} 0 Z`;
  }
}

export function legendMark(outcome) {
  return el("svg", { viewBox: "-8 -8 16 16", width: 14, height: 14, "aria-hidden": "true" },
    el("path", { d: markPath(outcome, 5), class: `mark oc-${outcome}` }));
}

function niceCeil(v, step) { return Math.ceil(v / step) * step; }

// points: rows from tests.json. opts.filters: show material filter chips.
export function createChart(host, points, opts = {}) {
  const all = mapPoints(points);
  const hasLink = all.some((p) => p.is_link2018);
  const state = { showLink: false, material: "all" };

  const flows = all.flatMap((p) => [p.flow_start, p.flow_end]).filter((v) => v !== null);
  const o2 = all.map((p) => p.o2_start);
  const yMax = niceCeil(Math.max(10, ...flows) * 1.05, 10);
  const xMin = Math.floor((Math.min(MOON_O2, ...o2) - 0.5) / 2) * 2;
  const xMax = Math.max(MAP_AXIS_MIN_RIGHT, niceCeil(Math.max(...o2) + 1, 2));
  const moonCount = all.filter((p) => p.o2_start >= MOON_O2).length;
  const noFlow = all.some((p) => p.flow_start === null);

  clear(host);
  host.classList.add("chart");
  const controls = el("div", { class: "chart-controls" });
  const frame = el("div", { class: "chart-frame" });
  const legend = el("div", { class: "legend" });
  const status = el("p", { class: "chart-status", "aria-live": "polite" });
  host.append(controls, frame, legend, status);

  // Material filter chips (main map only).
  if (opts.filters) {
    const names = [...new Set(all.map((p) => (p.low_pressure ? "Low pressure (Saffire V)" : baseMaterial(p.material))))];
    const group = el("div", { class: "chips", role: "group", "aria-label": "Filter by material" });
    const make = (value, label) => el("button", {
      type: "button", class: "chip", "aria-pressed": String(state.material === value),
      onclick: () => {
        state.material = value;
        group.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === value)));
        draw();
      },
      "data-v": value,
    }, label);
    add(group, make("all", "All materials"), names.map((n) => make(n, n)));
    controls.append(group);
  }
  if (hasLink) {
    const id = `link-${Math.random().toString(36).slice(2, 8)}`;
    const count = all.filter((p) => p.is_link2018).length;
    controls.append(el("label", { class: "switch", for: id },
      el("input", {
        type: "checkbox", id,
        onchange: (e) => { state.showLink = e.target.checked; draw(); },
      }),
      el("span", { class: "switch-track", "aria-hidden": "true" }),
      el("span", {}, `Show ${count} Link et al. 2018 rows (paper rod data, not outcome evidence)`)));
  }

  // Legend.
  const present = OUTCOMES.filter((o) => all.some((p) => p.outcome === o));
  add(legend,
    present.map((o) => el("span", { class: "legend-item" }, legendMark(o), OUTCOME_LABEL[o])),
    all.some((p) => p.flow_end !== null && p.flow_end !== p.flow_start) &&
      el("span", { class: "legend-item" },
        el("svg", { viewBox: "0 0 16 16", width: 14, height: 14, "aria-hidden": "true" },
          el("line", { x1: 8, y1: 1, x2: 8, y2: 15, class: "span-line" })),
        "Flow changed during the test (start to end)"),
    all.some((p) => p.low_flow_uncertain) &&
      el("span", { class: "legend-item" }, el("span", { class: "legend-faded", "aria-hidden": "true" }), "Faded: low flow, uncertain reading"),
    all.some((p) => p.low_pressure) &&
      el("span", { class: "legend-item" }, el("span", { class: "legend-ring", "aria-hidden": "true" }), "Ringed: low-pressure Saffire V test"),
  );

  function visible() {
    return all.filter((p) => {
      if (p.is_link2018 && !state.showLink) return false;
      if (state.material === "all") return true;
      const name = p.low_pressure ? "Low pressure (Saffire V)" : baseMaterial(p.material);
      return name === state.material;
    });
  }

  function draw() {
    const W = Math.max(280, Math.round(frame.clientWidth || 640));
    const small = W < 520;
    const H = Math.round(Math.min(520, Math.max(300, W * (opts.compact ? 0.62 : 0.5))));
    const m = { l: small ? 40 : 54, r: small ? 10 : 18, t: 30, b: (noFlow ? 30 : 0) + 46 };
    const pw = W - m.l - m.r;
    const ph = H - m.t - m.b;
    const x = (v) => m.l + ((v - xMin) / (xMax - xMin)) * pw;
    const y = (v) => m.t + ph - (v / yMax) * ph;
    const r = small ? 4 : 5;
    const pts = visible();

    const svg = el("svg", {
      viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
      "aria-label": `${opts.label || "Evidence map"}: ${pts.length} tests by oxygen percent and airflow. ` +
        `${moonCount} tests at ${MOON_O2}% oxygen or more.`,
    });

    // Moon band: everything from the Moon cabin oxygen level up.
    svg.append(
      el("rect", { x: x(MOON_O2), y: m.t, width: x(xMax) - x(MOON_O2), height: ph, class: "moon-band" }),
      el("line", { x1: x(MOON_O2), y1: m.t - 6, x2: x(MOON_O2), y2: m.t + ph, class: "moon-line" }),
    );

    // Grid and axes.
    const xStep = small ? 4 : 2;
    for (let v = Math.ceil(xMin / xStep) * xStep; v <= xMax; v += xStep) {
      svg.append(
        el("line", { x1: x(v), y1: m.t, x2: x(v), y2: m.t + ph, class: "grid" }),
        el("text", { x: x(v), y: m.t + ph + 16, class: "tick", "text-anchor": "middle" }, `${v}`),
      );
    }
    const yStep = yMax > 40 ? 10 : 5;
    for (let v = 0; v <= yMax; v += yStep) {
      svg.append(
        el("line", { x1: m.l, y1: y(v), x2: m.l + pw, y2: y(v), class: "grid" }),
        el("text", { x: m.l - 8, y: y(v) + 4, class: "tick", "text-anchor": "end" }, `${v}`),
      );
    }
    svg.append(
      el("text", { x: m.l + pw / 2, y: H - 6, class: "axis-label", "text-anchor": "middle" }, "Oxygen at the start of the test (%)"),
      el("text", { x: 12, y: m.t + ph / 2, class: "axis-label", "text-anchor": "middle", transform: `rotate(-90 12 ${m.t + ph / 2})` }, "Airflow (cm/s)"),
      el("text", { x: m.l + pw, y: m.t - 10, class: "moon-label", "text-anchor": "end" }, `Moon cabin (${MOON_O2}%+ O2)`),
      el("text", { x: x(MOON_O2) + (x(xMax) - x(MOON_O2)) / 2, y: m.t + ph / 2, class: "moon-empty", "text-anchor": "middle", transform: small || x(xMax) - x(MOON_O2) < 120 ? `rotate(-90 ${x(MOON_O2) + (x(xMax) - x(MOON_O2)) / 2} ${m.t + ph / 2})` : null },
        moonCount === 0 ? "No tests here" : `${moonCount} tests here`),
    );

    // Tests with oxygen but no recorded flow sit on a strip under the plot.
    const stripY = m.t + ph + 34;
    if (noFlow) {
      svg.append(
        el("line", { x1: m.l, y1: stripY, x2: m.l + pw, y2: stripY, class: "strip" }),
        el("text", { x: m.l + pw, y: stripY - 6, class: "tick", "text-anchor": "end" }, "Flow not recorded"),
      );
    }

    // Marks. Group tests that sit on the same spot so the tooltip lists all.
    const spots = new Map();
    for (const p of pts) {
      const fy = p.flow_start === null ? null : (p.flow_end ?? p.flow_start);
      const key = `${p.o2_start}|${fy}`;
      if (!spots.has(key)) spots.set(key, []);
      spots.get(key).push(p);
    }
    // Low-pressure labels alternate sides so neighbours do not overlap.
    const lpSide = new Map(pts.filter((p) => p.low_pressure).sort((p, q) => p.o2_start - q.o2_start).map((p, i) => [p.id, i % 2 ? 1 : -1]));
    const marks = el("g", {});
    const lines = el("g", {});
    for (const p of pts) {
      const fy = p.flow_start === null ? null : (p.flow_end ?? p.flow_start);
      const cx = x(p.o2_start);
      const cy = fy === null ? stripY : y(fy);
      const cls = [
        "mark", `oc-${p.outcome}`,
        p.low_flow_uncertain ? "is-faded" : "",
        p.is_link2018 ? "is-link" : "",
      ].join(" ");
      if (fy !== null && p.flow_end !== null && p.flow_end !== p.flow_start) {
        lines.append(
          el("line", { x1: cx, y1: y(p.flow_start), x2: cx, y2: cy, class: `span-line oc-${p.outcome} ${p.low_flow_uncertain ? "is-faded" : ""}` }),
          el("circle", { cx, cy: y(p.flow_start), r: 1.8, class: `span-start oc-${p.outcome}` }),
        );
      }
      const g = el("g", { transform: `translate(${cx} ${cy})`, class: "mark-g", "data-key": `${p.o2_start}|${fy}` });
      if (p.low_pressure) {
        g.append(el("circle", { r: r + 5, class: "lp-ring" }));
        if (p.pressure_kPa !== null) {
          const side = lpSide.get(p.id) || -1;
          g.append(el("text", { x: side * (r + 9), y: 4, class: "lp-label", "text-anchor": side < 0 ? "end" : "start" }, `${num(p.pressure_kPa)} kPa`));
        }
      }
      g.append(
        el("path", { d: markPath(p.outcome, p.is_link2018 ? r * 0.75 : r), class: cls }),
        el("circle", { r: r + 6, class: "hit" }),
      );
      marks.append(g);
    }
    svg.append(lines, marks);

    // Tooltip: hover with a mouse, tap on touch.
    const show = (g, evt) => {
      const list = spots.get(g.dataset.key) || [];
      if (!list.length) return;
      const tip = tooltip();
      add(clear(tip), tipContent(list));
      tip.hidden = false;
      const pad = 12;
      const tw = tip.offsetWidth;
      const th = tip.offsetHeight;
      let left = evt.clientX + 14;
      let top = evt.clientY + 14;
      if (left + tw > window.innerWidth - pad) left = Math.max(pad, evt.clientX - tw - 14);
      if (top + th > window.innerHeight - pad) top = Math.max(pad, evt.clientY - th - 14);
      tip.style.left = `${left}px`;
      tip.style.top = `${top}px`;
    };
    const hide = () => { tooltip().hidden = true; };
    svg.addEventListener("pointermove", (e) => {
      const g = e.target.closest?.(".mark-g");
      if (g) show(g, e); else if (e.pointerType === "mouse") hide();
    });
    svg.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") hide(); });
    svg.addEventListener("click", (e) => {
      const g = e.target.closest?.(".mark-g");
      if (g) show(g, e); else hide();
    });

    clear(frame).append(svg);
    const hiddenLink = hasLink && !state.showLink ? all.filter((p) => p.is_link2018).length : 0;
    status.textContent = `Showing ${pts.length} of ${all.length} tests with an oxygen value.` +
      (hiddenLink ? ` ${hiddenLink} Link et al. 2018 rows are hidden.` : "");
  }

  let last = 0;
  const ro = new ResizeObserver(() => {
    const w = Math.round(frame.clientWidth);
    if (w && w !== last) { last = w; draw(); }
  });
  ro.observe(frame);
  draw();
  last = Math.round(frame.clientWidth);
  return { redraw: draw };
}

function tipContent(list) {
  const p = list[0];
  const rows = [
    ["Material", p.material],
    ["Shape", p.shape],
    ["Oxygen", pct(p.o2_start)],
    ["Airflow", `${flowText(p.flow_start, p.flow_end)}${p.flow_start === null ? "" : " cm/s"}`],
    p.pressure_kPa !== null && ["Pressure", `${num(p.pressure_kPa)} kPa`],
    ["Outcome", OUTCOME_LABEL[p.outcome] || p.outcome],
  ].filter(Boolean);
  return [
    el("p", { class: "tip-title" }, `Test ${p.test_id}`,
      p.is_link2018 && el("span", { class: "tag" }, "Link 2018"),
      p.low_flow_uncertain && el("span", { class: "tag" }, "Low flow, uncertain")),
    el("dl", { class: "tip-grid" }, rows.map(([k, v]) => [el("dt", {}, k), el("dd", {}, v)])),
    p.outcome_note && el("p", { class: "tip-note" }, trim(p.outcome_note, 150)),
    p.flow_note && el("p", { class: "tip-note" }, trim(p.flow_note, 150)),
    el("p", { class: "tip-cite" }, trim(p.citation, 170)),
    list.length > 1 && el("p", { class: "tip-more" },
      `${list.length - 1} more at this spot: `,
      list.slice(1, 7).map((q) => `${q.test_id} (${(OUTCOME_LABEL[q.outcome] || q.outcome).toLowerCase()})`).join(", "),
      list.length > 7 ? ` and ${list.length - 7} more` : ""),
  ];
}
