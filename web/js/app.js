// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// Page start-up: load the data through data.js, then build each section.

import {
  loadTests, loadCards, loadExperiments, loadInvestigations, loadLimits, loadMeta, ask, mapPoints,
} from "./data.js";
import { el, add, clear, pct, scrollToEl, reducedMotion, MOON_O2 } from "./dom.js";
import { renderAnswer, renderLoading } from "./answer.js";
import { createChart } from "./chart.js";
import {
  buildEntries, entryForMaterial, renderCards, previewContent, openMaterialDetail, materialAside,
} from "./materials.js";
import { renderRanking, openInvestigation } from "./ranking.js";
import { renderLimits, renderFooter } from "./limits.js";
import { initMoon } from "./moon.js";

const $ = (id) => document.getElementById(id);

// ?moon=nasa (default) | procedural | photo | illustration
const VARIANTS = {
  nasa: { flat: false },
  procedural: { flat: false },
  photo: { flat: true, image: "assets/inspo_moon_photo.png", label: "Inspiration image, source to be credited" },
  illustration: { flat: true, image: "assets/inspo_moon_illustration.webp", label: "SI-generated image" },
};
const variantName = (() => {
  const v = new URLSearchParams(location.search).get("moon");
  return v && Object.hasOwn(VARIANTS, v) ? v : "nasa";
})();

// ---- starfield -----------------------------------------------------------

function drawStars() {
  const canvas = $("stars");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = window.innerWidth, h = window.innerHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  const g = ctx.createRadialGradient(w * 0.7, h * 0.3, 0, w * 0.7, h * 0.3, Math.max(w, h));
  g.addColorStop(0, "#0c1c4a"); g.addColorStop(0.45, "#071030"); g.addColorStop(1, "#03050d");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
  let seed = 7;
  const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const count = Math.round((w * h) / 1500);
  for (let i = 0; i < count; i++) {
    const r = rand() < 0.9 ? 0.3 + rand() * 0.6 : 0.9 + rand() * 0.7;
    ctx.fillStyle = `rgba(${200 + Math.round(rand() * 55)},${220 + Math.round(rand() * 35)},255,${0.25 + rand() * 0.65})`;
    ctx.beginPath(); ctx.arc(rand() * w, rand() * h, r, 0, Math.PI * 2); ctx.fill();
  }
  // A few sparkle stars.
  for (let i = 0; i < Math.max(5, Math.round(count / 90)); i++) {
    const x = rand() * w, y = rand() * h, len = 4 + rand() * 7;
    ctx.strokeStyle = "rgba(225,238,255,0.85)";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x - len, y); ctx.lineTo(x + len, y); ctx.moveTo(x, y - len); ctx.lineTo(x, y + len); ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.beginPath(); ctx.arc(x, y, 1.3, 0, Math.PI * 2); ctx.fill();
  }
}

// ---- marker preview ------------------------------------------------------

const preview = { el: null, key: null, timer: 0 };

function showPreview(key, anchor, content) {
  clearTimeout(preview.timer);
  const box = preview.el;
  add(clear(box), content);
  box.hidden = false;
  preview.key = key;
  const a = anchor.getBoundingClientRect();
  const bw = box.offsetWidth, bh = box.offsetHeight, pad = 10;
  let left = a.left + a.width / 2 - bw / 2;
  left = Math.min(window.innerWidth - bw - pad, Math.max(pad, left));
  let top = a.top - bh - 10;
  if (top < pad) top = Math.min(window.innerHeight - bh - pad, a.bottom + 10);
  box.style.left = `${left}px`;
  box.style.top = `${top}px`;
}
function hidePreview(delay = 0) {
  clearTimeout(preview.timer);
  preview.timer = setTimeout(() => { preview.el.hidden = true; preview.key = null; }, delay);
}

// A marker button: hover or focus shows the preview, click opens the detail.
// On touch the first tap shows the preview and the second opens the detail.
function markerButton({ key, label, color, cls, content, onOpen, onFocus }) {
  let pointer = "mouse";
  const btn = el("button", {
    type: "button", class: `marker ${cls || ""}`, style: { "--mat": color },
    onpointerdown: (e) => { pointer = e.pointerType; },
    onpointerenter: (e) => { if (e.pointerType === "mouse") showPreview(key, btn, content()); },
    onpointerleave: (e) => { if (e.pointerType === "mouse") hidePreview(160); },
    onfocus: () => { onFocus?.(); if (btn.matches(":focus-visible")) showPreview(key, btn, content()); },
    onblur: () => hidePreview(160),
    onclick: () => {
      if (pointer === "touch" && preview.key !== key) { showPreview(key, btn, content()); return; }
      hidePreview();
      onOpen();
    },
  }, el("span", { class: "marker-dot", "aria-hidden": "true" }), el("span", { class: "marker-label" }, label));
  return btn;
}

// Flat Moon (image variants, or no WebGL): markers sit around the disc.
function layoutFlat(stage, buttons, baseButton, variant) {
  stage.classList.add("is-flat");
  const flat = stage.querySelector(".moon-flat");
  if (variant.image) {
    flat.classList.add("has-image");
    flat.style.backgroundImage = `url("${variant.image}")`;
    stage.append(el("p", { class: "watermark" }, variant.label));
  }
  buttons.forEach((b, i) => {
    const a = (i / buttons.length) * Math.PI * 2 - Math.PI / 2 + 0.5;
    b.style.left = `${50 + Math.cos(a) * 41}%`;
    b.style.top = `${50 + Math.sin(a) * 41}%`;
    b.classList.toggle("is-left", Math.cos(a) < -0.2);
  });
  baseButton.style.left = "43%";
  baseButton.style.top = "40%";
}

// ---- start ---------------------------------------------------------------

async function main() {
  drawStars();
  let starTimer = 0;
  window.addEventListener("resize", () => { clearTimeout(starTimer); starTimer = setTimeout(drawStars, 150); });
  preview.el = $("preview");
  preview.el.addEventListener("pointerenter", () => clearTimeout(preview.timer));
  preview.el.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") hidePreview(160); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { hidePreview(); $("tooltip").hidden = true; } });
  document.addEventListener("pointerdown", (e) => {
    if (!e.target.closest(".marker, .preview")) hidePreview();
    if (!e.target.closest(".mark-g")) $("tooltip").hidden = true;
  });
  window.addEventListener("scroll", () => { $("tooltip").hidden = true; hidePreview(); }, { passive: true });

  let data;
  try {
    const [tests, cardsFile, experimentsFile, investigations, limits, meta, demo] = await Promise.all([
      loadTests(), loadCards(), loadExperiments(), loadInvestigations(), loadLimits(), loadMeta(),
      fetch("data/demo_answers.json").then((r) => (r.ok ? r.json() : { answers: [] })).catch(() => ({ answers: [] })),
    ]);
    data = { tests, cardsFile, experimentsFile, investigations, limits, meta, demo };
  } catch (err) {
    $("map-panel").append(el("p", { class: "note" }, "The test data could not be loaded. Run python3 web/export_data.py, then reload."));
    console.error(err);
    return;
  }
  const { tests, cardsFile, experimentsFile, investigations, limits, demo } = data;
  const entries = buildEntries(cardsFile);
  const detail = $("detail");
  const input = $("ask-input");

  // ---- asking ----
  let asking = 0;
  async function submit(question) {
    const q = question.trim();
    if (!q) return;
    const turn = ++asking;
    const host = $("answer");
    renderLoading(host, q);
    scrollToEl(host);
    const result = await ask(q);
    if (turn !== asking) return;
    renderAnswer(host, q, result, ctx);
  }
  function fillAsk(question, send = false) {
    input.value = question;
    if (send) { submit(question); return; }
    scrollToEl(document.querySelector(".hero"));
    input.focus({ preventScroll: true });
  }
  const openEntry = (entry) => openMaterialDetail(detail, entry, ctx);
  const ctx = {
    tests, limits, cardsFile, investigations,
    onAsk: fillAsk,
    onOpen: openEntry,
    onInvestigation: (inv) => openInvestigation(detail, inv, experimentsFile.experiments.find((e) => e.psi_id === inv.psi_id)),
    entryFor: (material) => entryForMaterial(entries, cardsFile, material),
    materialAside: (entry) => materialAside(entry, ctx),
  };

  $("ask-form").addEventListener("submit", (e) => { e.preventDefault(); submit(input.value); });
  const lowPressureName = cardsFile.low_pressure_group.cards.map((c) => c.material.split(" (")[0]).find((n) => !cardsFile.cards.some((c) => c.material === n));
  const examples = [
    `Will ${cardsFile.cards.find((c) => c.material === "PMMA") ? "PMMA" : cardsFile.cards[0].material} burn at ${MOON_O2}% oxygen?`,
    lowPressureName ? `Will ${lowPressureName.toLowerCase()} burn at 26% oxygen?` : null,
    "Which investigation studies smoke detection?",
    demo.answers.find((a) => /lowest oxygen/i.test(a.question))?.question,
  ].filter(Boolean);
  add($("ask-chips"), examples.map((q) => el("button", { type: "button", class: "chip", onclick: () => fillAsk(q, true) }, q)));

  // ---- map, cards, ranking, limits, footer ----
  const plotted = mapPoints(tests);
  const counted = plotted.filter((p) => !p.is_link2018);
  const top = Math.max(...counted.map((p) => p.o2_start));
  const atMoon = plotted.filter((p) => p.o2_start >= MOON_O2).length;
  $("map-sub").textContent =
    `${tests.length} tests in the data, ${plotted.length} with an oxygen value. The highest oxygen tested is ${pct(top)}. ` +
    `${atMoon === 0 ? "No test reaches" : `${atMoon} tests reach`} the ${MOON_O2}% a Moon cabin would run at.`;
  createChart($("map-panel"), tests, { filters: true, label: "Evidence map" });

  $("mat-sub").textContent = cardsFile.counting_rule;
  renderCards($("cards"), entries, { onAsk: fillAsk, onOpen: openEntry });

  renderRanking({ noteEl: $("rank-note"), filtersEl: $("rank-filters"), listEl: $("rank-list") },
    experimentsFile, investigations, ctx.onInvestigation ? (inv, e) => openInvestigation(detail, inv, e) : null);

  const limitsDialog = $("limits");
  renderLimits(limitsDialog, limits);
  $("limits-open").addEventListener("click", () => limitsDialog.showModal());
  for (const d of [detail, limitsDialog]) {
    d.addEventListener("click", (e) => { if (e.target === d) d.close(); }); // click on the backdrop
  }
  renderFooter({ listEl: $("source-list"), siEl: $("footer-si"), licenseEl: $("footer-license") },
    { cardsFile, experimentsFile, tests, limits });

  // ---- Moon ----
  const stage = $("moon-stage");
  const host = $("moon-markers");
  let moon = null;
  const buttons = entries.map((entry, i) => markerButton({
    key: entry.key, label: entry.label, color: entry.color,
    content: () => previewContent(entry, (en) => { hidePreview(); openEntry(en); }),
    onOpen: () => openEntry(entry),
    onFocus: () => moon?.faceMarker(i),
  }));
  const baseButton = markerButton({
    key: "moon-base", label: `Moon base: ${MOON_O2}%+ oxygen`, color: "#ff8fab", cls: "marker-base",
    content: () => [
      el("p", { class: "preview-title", style: { "--mat": "#ff8fab" } }, el("span", { class: "mat-dot", "aria-hidden": "true" }), "Moon base target"),
      el("p", { class: "preview-line" }, atMoon === 0 ? `No test reaches ${MOON_O2}% oxygen.` : `${atMoon} tests reach ${MOON_O2}% oxygen.`),
      el("p", { class: "preview-line" }, "Highest oxygen tested: ", el("b", {}, pct(top))),
      el("p", { class: "preview-line muted" }, limits.gravity_note_short),
      el("button", { type: "button", class: "btn btn-small", tabindex: "-1", onclick: () => { hidePreview(); scrollToEl($("map")); } }, "See the evidence map"),
    ],
    onOpen: () => scrollToEl($("map")),
    onFocus: () => moon?.faceMarker(entries.length),
  });
  add(host, buttons, baseButton);

  const variant = VARIANTS[variantName];
  if (variant.flat) {
    layoutFlat(stage, buttons, baseButton, variant);
    $("moon-hint").textContent = "Hover a marker for a preview, select it for every test.";
  } else {
    stage.tabIndex = 0;
    stage.setAttribute("aria-label", "The Moon with one marker per tested material. Left and right arrow keys spin it.");
    moon = await initMoon({
      stage, variant: variantName, reduced: reducedMotion(), base: { button: baseButton },
      markers: entries.map((entry, i) => ({ button: buttons[i], color: entry.color, weight: entry.summary.test_count })),
    });
    if (!moon) {
      stage.removeAttribute("tabindex");
      layoutFlat(stage, buttons, baseButton, {});
      $("moon-hint").textContent = "Hover a marker for a preview, select it for every test.";
    } else {
      window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", (e) => moon.setReducedMotion(e.matches));
    }
  }
}

main();
