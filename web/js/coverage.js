// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// The main evidence chart: one row per material on a shared oxygen axis.
// It answers one question at a glance: how far does the tested oxygen reach,
// and does anything reach a Moon cabin (30%+)? Each tick is one real test at
// its starting oxygen; the bar spans the material's tested range. No jitter,
// no invented values. Link et al. 2018 rows are left out, as on the cards.

import { el, clear, pct, MOON_O2, MAP_AXIS_MIN_RIGHT, OUTCOME_LABEL, OUTCOMES as OUTCOME_ORDER } from "./dom.js";
import { entryPoints } from "./materials.js";

const tooltip = () => document.getElementById("tooltip");

export function createCoverage(host, entries, tests, { onOpen } = {}) {
  const rows = entries
    .map((entry) => ({
      entry,
      // Standard rows never include the low-pressure Saffire V tests: those
      // sit in their own row, as on the cards (team decision).
      pts: entryPoints(entry, tests).filter((p) => !p.is_link2018 && p.o2_start !== null
        && (entry.kind === "standard" ? !p.low_pressure : true)),
    }))
    .filter((r) => r.pts.length)
    .sort((a, b) => (a.entry.kind === b.entry.kind ? b.pts.length - a.pts.length : a.entry.kind === "standard" ? -1 : 1));

  const allO2 = rows.flatMap((r) => r.pts.map((p) => p.o2_start));
  const xMin = Math.floor((Math.min(...allO2) - 0.5) / 2) * 2;
  const xMax = Math.max(MAP_AXIS_MIN_RIGHT, Math.ceil(Math.max(...allO2) + 2));

  clear(host);
  host.classList.add("chart");
  const frame = el("div", { class: "chart-frame" });
  const present = [...new Set(rows.flatMap((r) => r.pts.map((p) => p.outcome)))];
  const key = el("div", { class: "legend" }, OUTCOME_ORDER.filter((o) => present.includes(o)).map((o) =>
    el("span", { class: "legend-item" }, el("span", { class: `cov-key bg-${o}`, "aria-hidden": "true" }), OUTCOME_LABEL[o])));
  const legend = el("p", { class: "chart-status" },
    "Each tick is one test at its starting oxygen, colored by its outcome. The bar spans the tested range. ",
    "Outcomes are read from crew notes and paper text, not measured by an instrument. ",
    "Select a row for that material's full detail.");
  host.append(frame, key, legend);

  function draw() {
    const W = Math.max(300, Math.round(frame.clientWidth || 720));
    const small = W < 560;
    const labelW = small ? 104 : 190;
    const rowH = small ? 40 : 44;
    const m = { l: labelW, r: 16, t: 34, b: 38 };
    const H = m.t + rows.length * rowH + m.b;
    const pw = W - m.l - m.r;
    const x = (v) => m.l + ((v - xMin) / (xMax - xMin)) * pw;

    const svg = el("svg", {
      viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
      "aria-label": "Tested oxygen range per material. " + rows.map((r) => {
        const o = r.pts.map((p) => p.o2_start);
        return `${r.entry.name}: ${r.pts.length} tests, ${pct(Math.min(...o))} to ${pct(Math.max(...o))}`;
      }).join(". ") + `. No material reaches ${MOON_O2}%.`,
    });

    // Moon cabin band, drawn first so rows sit on top.
    const bandTop = m.t - 8;
    svg.append(
      el("rect", { x: x(MOON_O2), y: bandTop, width: x(xMax) - x(MOON_O2), height: H - m.b - bandTop, class: "moon-band" }),
      el("line", { x1: x(MOON_O2), y1: bandTop, x2: x(MOON_O2), y2: H - m.b, class: "moon-line" }),
      el("text", { x: x(MOON_O2) - 6, y: m.t - 16, class: "moon-label", "text-anchor": "end" }, `Moon cabin ${MOON_O2}%+ O₂`),
    );

    // Axis.
    const step = small ? 4 : 2;
    for (let v = Math.ceil(xMin / step) * step; v <= xMax; v += step) {
      svg.append(
        el("line", { x1: x(v), y1: m.t - 8, x2: x(v), y2: H - m.b, class: "grid" }),
        el("text", { x: x(v), y: H - m.b + 16, class: "tick", "text-anchor": "middle" }, `${v}`),
      );
    }
    svg.append(el("text", { x: m.l + pw / 2, y: H - 6, class: "axis-label", "text-anchor": "middle" },
      "Oxygen at the start of the test (% by volume)"));

    rows.forEach((r, i) => {
      const cy = m.t + i * rowH + rowH / 2;
      const o = r.pts.map((p) => p.o2_start);
      const lo = Math.min(...o);
      const hi = Math.max(...o);
      const g = el("g", { class: "cov-row", tabindex: "0", role: "button",
        "aria-label": `${r.entry.name}, ${r.pts.length} test${r.pts.length === 1 ? "" : "s"}, ${pct(lo)} to ${pct(hi)}. Open detail.` });
      g.append(
        el("rect", { x: 0, y: cy - rowH / 2, width: W, height: rowH, class: "cov-hit" }),
        el("text", { x: 0, y: cy - 2, class: "cov-name" }, small && r.entry.kind !== "standard" ? "Low pressure" : r.entry.name),
        el("text", { x: 0, y: cy + 13, class: "cov-count" }, `${r.pts.length} test${r.pts.length === 1 ? "" : "s"}`),
        el("rect", { x: x(lo) - 3, y: cy - 7, width: Math.max(6, x(hi) - x(lo) + 6), height: 14, rx: 2, class: "cov-bar" }),
      );
      for (const p of r.pts) {
        g.append(el("line", {
          x1: x(p.o2_start), y1: cy - 6, x2: x(p.o2_start), y2: cy + 6,
          class: `cov-tick oc-${p.outcome}`, "data-id": p.id,
        }));
      }
      g.append(el("text", { x: x(hi) + 8, y: cy + 4, class: "cov-max" }, pct(hi)));
      const open = () => onOpen?.(r.entry);
      g.addEventListener("click", open);
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
      g.addEventListener("pointermove", (e) => showTip(e, r, lo, hi));
      g.addEventListener("pointerleave", () => { tooltip().hidden = true; });
      svg.append(g);
    });

    svg.append(el("text", {
      x: x(MOON_O2) + (x(xMax) - x(MOON_O2)) / 2, y: m.t + (rows.length * rowH) / 2,
      class: "moon-empty", "text-anchor": "middle",
      transform: `rotate(-90 ${x(MOON_O2) + (x(xMax) - x(MOON_O2)) / 2} ${m.t + (rows.length * rowH) / 2})`,
    }, "No tests"));

    clear(frame).append(svg);
  }

  function showTip(evt, r, lo, hi) {
    const counts = {};
    for (const p of r.pts) counts[p.outcome] = (counts[p.outcome] || 0) + 1;
    const tip = tooltip();
    clear(tip).append(
      el("p", { class: "tip-title" }, r.entry.name),
      el("dl", { class: "tip-grid" },
        el("dt", {}, "Tests"), el("dd", {}, String(r.pts.length)),
        el("dt", {}, "Oxygen"), el("dd", {}, `${pct(lo)} to ${pct(hi)}`),
        ...Object.entries(counts).flatMap(([k, n]) => [el("dt", {}, OUTCOME_LABEL[k] || k), el("dd", {}, String(n))])),
    );
    tip.hidden = false;
    const left = Math.min(evt.clientX + 14, window.innerWidth - tip.offsetWidth - 12);
    const top = Math.min(evt.clientY + 14, window.innerHeight - tip.offsetHeight - 12);
    tip.style.left = `${Math.max(12, left)}px`;
    tip.style.top = `${Math.max(12, top)}px`;
  }

  let last = 0;
  new ResizeObserver(() => {
    const w = Math.round(frame.clientWidth);
    if (w && w !== last) { last = w; draw(); }
  }).observe(frame);
  draw();
  last = Math.round(frame.clientWidth);
}
