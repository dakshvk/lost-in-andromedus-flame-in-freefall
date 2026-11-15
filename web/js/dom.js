// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// Small DOM helpers and the page's shared labels and colours.
// Nothing here holds test data: numbers on the page come from data.js.

// The one condition the whole project asks about: a Moon cabin at 30% oxygen
// or more (the challenge premise; the answers' own text uses the same figure).
export const MOON_O2 = 30;
// Layout only: where the shared oxygen bars and the map's x axis end.
export const BAR_AXIS_MAX = 40;
export const MAP_AXIS_MIN_RIGHT = 32;

export const OUTCOMES = ["burning", "quenched", "blow_off", "no_ignition", "ignited_only", "unknown"];
export const OUTCOME_LABEL = {
  burning: "Burning",
  quenched: "Quenched",
  blow_off: "Blow off",
  no_ignition: "No ignition",
  ignited_only: "Ignited only",
  unknown: "Unknown",
};

export const MATERIAL_COLORS = ["#7fb2ff", "#ffb86b", "#8fe3c0", "#ffd84d", "#e79cff"];
export const LOW_PRESSURE_COLOR = "#7de3ff";

const SVG_NS = "http://www.w3.org/2000/svg";
const SVG_TAGS = new Set(["svg", "g", "path", "line", "rect", "circle", "text", "title", "tspan"]);

// el("div", {class: "x", onclick: fn}, child, "text", [more])
export function el(tag, attrs, ...children) {
  const node = SVG_TAGS.has(tag) ? document.createElementNS(SVG_NS, tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (k === "class") node.setAttribute("class", v);
    else if (k === "text") node.textContent = v;
    else if (k === "style" && typeof v === "object") {
      for (const [prop, val] of Object.entries(v)) {
        if (prop.startsWith("--")) node.style.setProperty(prop, val); else node.style[prop] = val;
      }
    }
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  append(node, children);
  return node;
}

// Like node.append, but takes arrays and skips null/false.
export function add(node, ...children) {
  append(node, children);
  return node;
}

function append(node, children) {
  for (const c of children) {
    if (c === null || c === undefined || c === false) continue;
    if (Array.isArray(c)) append(node, c);
    else node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

export function link(href, text, cls) {
  return el("a", { href, target: "_blank", rel: "noopener noreferrer", class: cls }, text);
}

// Display only: one decimal for oxygen, flows as recorded.
export const pct = (n) => (n === null || n === undefined ? "not recorded" : `${Number(n).toFixed(1)}%`);
export const num = (n) => (n === null || n === undefined ? "not recorded" : String(Number(n)));

export function range(pair, unit, fmt = num) {
  if (!pair || pair.length < 2 || pair[0] === null) return "not recorded";
  const [a, b] = pair;
  return a === b ? `${fmt(a)}${unit}` : `${fmt(a)} to ${fmt(b)}${unit}`;
}

// "20 → 5" when the flow changed during the test, else just the start flow.
export function flowText(start, end) {
  if (start === null || start === undefined) return "not recorded";
  if (end === null || end === undefined || end === start) return num(start);
  return `${num(start)} → ${num(end)}`;
}

export function trim(text, max) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
}

export const baseMaterial = (name) => name.split(" (")[0];

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function scrollToEl(node) {
  node.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
}
