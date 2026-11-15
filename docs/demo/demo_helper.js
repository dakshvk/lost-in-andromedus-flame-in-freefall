() => {
  if (window.demo) return "already";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const cur = document.createElement("div");
  cur.innerHTML = '<svg width="28" height="28" viewBox="0 0 24 24"><path d="M4 2 L4 20 L9 15 L12.5 22 L15.5 20.6 L12 13.8 L19 13.8 Z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  Object.assign(cur.style, { position: "fixed", left: "0", top: "0", zIndex: 99999, pointerEvents: "none", transform: "translate(900px,640px)" });
  document.body.appendChild(cur);
  let cx = 900, cy = 640;
  const move = async (x, y, ms = 700) => {
    cur.style.transition = `transform ${ms}ms cubic-bezier(.4,0,.2,1)`;
    cur.style.transform = `translate(${x - 4}px,${y - 2}px)`;
    cx = x; cy = y;
    await sleep(ms + 60);
  };
  const ring = () => {
    const r = document.createElement("div");
    Object.assign(r.style, { position: "fixed", left: cx - 16 + "px", top: cy - 16 + "px", width: "32px", height: "32px", borderRadius: "50%", border: "3px solid #ffb547", zIndex: 99998, pointerEvents: "none", transition: "transform .5s ease-out, opacity .5s ease-out" });
    document.body.appendChild(r);
    requestAnimationFrame(() => { r.style.transform = "scale(2.2)"; r.style.opacity = "0"; });
    setTimeout(() => r.remove(), 650);
  };
  const center = (el) => { const b = el.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; };
  const hoverEl = async (el, ms = 700) => {
    const [x, y] = center(el);
    await move(x, y, ms);
    for (const t of ["pointerover", "pointerenter", "mouseover", "mouseenter", "pointermove", "mousemove"]) {
      el.dispatchEvent(new (t.startsWith("pointer") ? PointerEvent : MouseEvent)(t, { bubbles: !t.endsWith("enter"), clientX: x, clientY: y }));
    }
  };
  const clickEl = async (el, ms = 700) => { await hoverEl(el, ms); ring(); await sleep(180); el.click(); };
  const glide = async (y, ms = 1200) => {
    const s = window.scrollY, t0 = performance.now();
    await new Promise((res) => {
      const f = (n) => {
        const p = Math.min(1, (n - t0) / ms);
        const e = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
        window.scrollTo(0, s + (y - s) * e);
        p < 1 ? requestAnimationFrame(f) : res();
      };
      requestAnimationFrame(f);
    });
  };
  const glideTo = (el, offset = 70, ms = 1200) => glide(el.getBoundingClientRect().top + window.scrollY - offset, ms);
  const typeQ = async (text, speed = 55) => {
    const i = document.getElementById("ask-input");
    await clickEl(i, 600);
    i.focus(); i.value = "";
    i.dispatchEvent(new Event("input", { bubbles: true }));
    for (const ch of text) {
      i.value += ch;
      i.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(speed + Math.random() * 30);
    }
    await sleep(350);
    await clickEl(document.getElementById("ask-submit"), 450);
  };
  window.demo = { sleep, move, ring, hoverEl, clickEl, glide, glideTo, typeQ, $: (s) => document.querySelector(s), $$: (s) => [...document.querySelectorAll(s)] };
  return "installed";
}
