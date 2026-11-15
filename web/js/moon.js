// Written with SI assistance (Claude Code), reviewed by Daksh Kumar
// The hero Moon. A Three.js sphere the visitor can drag and spin, with the
// material markers riding just above the surface in a low ring and one
// marker on the surface for the Moon base target.
//
// Texture: web/assets/moon.jpg (NASA SVS CGI Moon Kit) graded toward a cool
// blue-silver, with moon_displacement.jpg as relief. `procedural` draws the
// texture with code instead, and is also the fallback if the image fails.
// Marker labels are real HTML buttons placed over the canvas each frame, so
// they work with a mouse, touch and the keyboard.

const MOON_TEXTURE = "assets/moon.jpg";
const MOON_RELIEF = "assets/moon_displacement.jpg";
const RING_RADIUS = 1.13;
const CAMERA_Z = 5.05;

// Why the 3D Moon did not start (shown on the page and in the console).
let failure = null;
export const moonFailure = () => failure;

export function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch (_) {
    return false;
  }
}

// ---- textures ------------------------------------------------------------

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Push a grey Moon map toward blue-silver with stronger contrast.
function gradePixels(data) {
  for (let i = 0; i < data.length; i += 4) {
    const l = (0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]) / 255;
    // Moderate contrast and a darker range so highlands stay textured
    // instead of clipping to white (Daksh, 2026-11-15: "too white").
    let v = (l - 0.40) * 1.9 + 0.45;
    v = Math.min(1, Math.max(0, v));
    v = Math.pow(v, 1.1);                      // deepen the maria
    data[i] = Math.min(255, 255 * (0.05 + v * 0.60));
    data[i + 1] = Math.min(255, 255 * (0.07 + v * 0.66));
    data[i + 2] = Math.min(255, 255 * (0.12 + v * 0.74));
  }
}

function gradedCanvas(image) {
  const c = document.createElement("canvas");
  c.width = image.width;
  c.height = image.height;
  const ctx = c.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(image, 0, 0);
  const img = ctx.getImageData(0, 0, c.width, c.height);
  gradePixels(img.data);
  ctx.putImageData(img, 0, 0);
  return c;
}

// A Moon drawn by code: 3D value noise for highlands and maria (sampled on
// the sphere so there is no seam), then craters and a few ray craters.
function proceduralCanvas() {
  const rand = mulberry32(20261114);
  const perm = new Uint8Array(512);
  const vals = new Float32Array(256);
  for (let i = 0; i < 256; i++) { perm[i] = i; vals[i] = rand(); }
  for (let i = 255; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; }
  for (let i = 0; i < 256; i++) perm[i + 256] = perm[i];
  const lattice = (x, y, z) => vals[perm[perm[perm[x & 255] + (y & 255)] + (z & 255)]];
  const fade = (t) => t * t * (3 - 2 * t);
  const noise = (x, y, z) => {
    const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
    const u = fade(x - xi), v = fade(y - yi), w = fade(z - zi);
    const mix = (a, b, t) => a + (b - a) * t;
    return mix(
      mix(mix(lattice(xi, yi, zi), lattice(xi + 1, yi, zi), u), mix(lattice(xi, yi + 1, zi), lattice(xi + 1, yi + 1, zi), u), v),
      mix(mix(lattice(xi, yi, zi + 1), lattice(xi + 1, yi, zi + 1), u), mix(lattice(xi, yi + 1, zi + 1), lattice(xi + 1, yi + 1, zi + 1), u), v),
      w);
  };
  const fbm = (x, y, z, oct) => {
    let s = 0, a = 0.5, f = 1, n = 0;
    for (let o = 0; o < oct; o++) { s += a * noise(x * f + 31, y * f + 17, z * f + 5); n += a; a *= 0.5; f *= 2.03; }
    return s / n;
  };

  const w = 768, h = 384;
  const small = document.createElement("canvas");
  small.width = w; small.height = h;
  const sctx = small.getContext("2d");
  const img = sctx.createImageData(w, h);
  for (let py = 0; py < h; py++) {
    const lat = (0.5 - (py + 0.5) / h) * Math.PI;
    const cl = Math.cos(lat), sl = Math.sin(lat);
    for (let px = 0; px < w; px++) {
      const lon = ((px + 0.5) / w - 0.5) * 2 * Math.PI;
      const x = cl * Math.sin(lon), y = sl, z = cl * Math.cos(lon);
      const mare = fbm(x * 1.5, y * 1.5, z * 1.5, 4) + 0.10 * z;       // more maria on the near side
      const m = Math.min(1, Math.max(0, (mare - 0.53) / 0.07));
      const detail = fbm(x * 9, y * 9, z * 9, 5);
      const v = (0.62 + 0.3 * detail) * (1 - m) + (0.2 + 0.16 * detail) * m;
      const i = (py * w + px) * 4;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = 255 * v;
      img.data[i + 3] = 255;
    }
  }
  gradePixels(img.data);
  sctx.putImageData(img, 0, 0);

  const W = 2048, H = 1024;
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const ctx = c.getContext("2d");
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(small, 0, 0, W, H);

  // Draw something at (cx, cy) with the right stretch for its latitude, and
  // again across the left/right seam when it sits near the edge.
  const stamp = (cx, cy, reach, draw) => {
    const stretch = 1 / Math.max(0.25, Math.cos((0.5 - cy / H) * Math.PI));
    for (const dx of [0, -W, W]) {
      if (cx + dx < -reach * stretch || cx + dx > W + reach * stretch) continue;
      ctx.save();
      ctx.translate(cx + dx, cy);
      ctx.scale(stretch, 1);
      draw();
      ctx.restore();
    }
  };

  for (let n = 0; n < 900; n++) {
    const cx = rand() * W;
    const cy = (Math.acos(1 - 2 * rand()) / Math.PI) * H;
    const r = 1.5 + Math.pow(rand(), 3.2) * 34;
    stamp(cx, cy, r * 1.3, () => {
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, r * 1.25);
      g.addColorStop(0, "rgba(14,22,44,0.42)");
      g.addColorStop(0.72, "rgba(14,22,44,0.30)");
      g.addColorStop(0.86, "rgba(226,238,255,0.50)");
      g.addColorStop(1, "rgba(226,238,255,0)");
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(0, 0, r * 1.25, 0, Math.PI * 2); ctx.fill();
    });
  }

  ctx.globalCompositeOperation = "lighter";
  const rays = [[0.47, 0.74, 150], [0.36, 0.38, 95], [0.62, 0.3, 70], [0.86, 0.6, 110], [0.12, 0.55, 90]];
  for (const [u, v, len] of rays) {
    stamp(u * W, v * H, len, () => {
      for (let k = 0; k < 70; k++) {
        const a = rand() * Math.PI * 2;
        const l = len * (0.25 + rand() * 0.75);
        const g = ctx.createLinearGradient(0, 0, Math.cos(a) * l, Math.sin(a) * l);
        g.addColorStop(0, "rgba(215,232,255,0.38)");
        g.addColorStop(1, "rgba(215,232,255,0)");
        ctx.strokeStyle = g;
        ctx.lineWidth = 0.8 + rand() * 2.4;
        ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(a) * l, Math.sin(a) * l); ctx.stroke();
      }
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, len * 0.16);
      g.addColorStop(0, "rgba(240,247,255,0.85)");
      g.addColorStop(1, "rgba(240,247,255,0)");
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(0, 0, len * 0.16, 0, Math.PI * 2); ctx.fill();
    });
  }
  ctx.globalCompositeOperation = "source-over";
  return c;
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Could not load ${src}`));
    img.src = src;
  });
}

function glowTexture(THREE, stops) {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  for (const [at, color] of stops) g.addColorStop(at, color);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// ---- scene ---------------------------------------------------------------

// markers: [{ button, color, weight }], base: { button }. Returns a small
// controller, or null when the 3D Moon could not start (the caller then
// shows the flat Moon).
export async function initMoon({ stage, markers, base, variant, reduced }) {
  if (!webglAvailable()) { failure = "webgl"; console.warn("Moon: WebGL is off or unsupported in this browser."); return null; }
  let THREE;
  try {
    THREE = await import("three");
  } catch (_) {
    // The first download source (cdn.jsdelivr.net) failed or is blocked: try
    // the same pinned version from a second source before giving up.
    try {
      THREE = await import("https://unpkg.com/three@0.160.0/build/three.module.js");
    } catch (err) {
      failure = "download";
      console.warn("Moon: the Three.js library could not be downloaded from jsdelivr or unpkg.", err);
      return null;
    }
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  } catch (err) {
    failure = "renderer";
    console.warn("Moon: WebGL could not start.", err);
    return null;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  const canvas = renderer.domElement;
  canvas.className = "moon-canvas";
  canvas.setAttribute("aria-hidden", "true");
  stage.prepend(canvas);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 50);
  camera.position.set(0, 0, CAMERA_Z);

  scene.add(new THREE.AmbientLight(0x9db8ff, 0.42));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(-1.9, 1.0, 2.2); // lower, more side light: crater rims cast shading
  scene.add(sun);

  const tilt = new THREE.Group();   // pitch from dragging
  const spin = new THREE.Group();   // yaw: the Moon and everything on it
  tilt.add(spin);
  scene.add(tilt);

  // Texture: the NASA map by default, the code-drawn one on request or if
  // the image does not load.
  let mapCanvas = null;
  let relief = null;
  if (variant !== "procedural") {
    try {
      const [color, height] = await Promise.all([loadImage(MOON_TEXTURE), loadImage(MOON_RELIEF).catch(() => null)]);
      mapCanvas = gradedCanvas(color);
      if (height) {
        relief = new THREE.Texture(height);
        relief.needsUpdate = true;
      }
    } catch (_) {
      mapCanvas = null;
    }
  }
  if (!mapCanvas) mapCanvas = proceduralCanvas();
  const map = new THREE.CanvasTexture(mapCanvas);
  map.colorSpace = THREE.SRGBColorSpace;
  map.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  // Crater relief: the surface image carries the crater rims and rays at full
  // resolution, so use it for the bump map (the elevation map is coarse).
  relief = new THREE.CanvasTexture(mapCanvas);

  const moon = new THREE.Mesh(
    new THREE.SphereGeometry(1, 96, 64),
    new THREE.MeshStandardMaterial({ map, bumpMap: relief, bumpScale: 3.4, roughness: 1, metalness: 0 }));
  moon.rotation.y = -Math.PI / 2; // put the map's centre (the near side) toward the camera
  spin.add(moon);

  // Blue limb glow: a rim on the disc and a soft halo behind it.
  const rim = new THREE.Mesh(
    new THREE.SphereGeometry(1.012, 64, 48),
    new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { tint: { value: new THREE.Color(0x5aa6ff) } },
      vertexShader: "varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }",
      fragmentShader: "uniform vec3 tint; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(1.0 - max(dot(normalize(vN), normalize(vV)), 0.0), 3.2); gl_FragColor = vec4(tint * f * 0.75, f * 0.7); }",
    }));
  scene.add(rim);

  const haloSize = 1.42; // half width in Moon radii; must fade out inside the view
  const edge = 1 / haloSize;
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTexture(THREE, [
      [0, "rgba(110,175,255,0)"], [edge * 0.9, "rgba(110,175,255,0)"], [edge * 0.985, "rgba(120,175,255,0.45)"],
      [edge * 1.06, "rgba(80,140,250,0.28)"], [edge * 1.2, "rgba(60,110,240,0.13)"], [0.98, "rgba(40,80,220,0)"], [1, "rgba(40,80,220,0)"],
    ]),
    transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending,
  }));
  halo.scale.setScalar(haloSize * 2);
  halo.renderOrder = -1;
  scene.add(halo);

  // Low ring of material markers, tilted a little off the equator.
  const ring = new THREE.Group();
  ring.rotation.set(0.16, 0, 0.2);
  spin.add(ring);
  const ringPts = [];
  for (let i = 0; i <= 160; i++) {
    const a = (i / 160) * Math.PI * 2;
    ringPts.push(new THREE.Vector3(Math.sin(a) * RING_RADIUS, 0, Math.cos(a) * RING_RADIUS));
  }
  ring.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(ringPts),
    new THREE.LineBasicMaterial({ color: 0x9cc4ff, transparent: true, opacity: 0.3 })));

  const dotGlow = glowTexture(THREE, [[0, "rgba(255,255,255,1)"], [0.25, "rgba(255,255,255,0.55)"], [1, "rgba(255,255,255,0)"]]);
  const items = markers.map((m, i) => {
    const a = (i / markers.length) * Math.PI * 2 + 0.35;
    const g = new THREE.Group();
    g.position.set(Math.sin(a) * RING_RADIUS, 0, Math.cos(a) * RING_RADIUS);
    const size = 0.03 + 0.012 * Math.log10(1 + (m.weight || 1));
    g.add(new THREE.Mesh(new THREE.SphereGeometry(size, 20, 16), new THREE.MeshBasicMaterial({ color: m.color })));
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotGlow, color: m.color, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    glow.scale.setScalar(size * 6.5);
    g.add(glow);
    ring.add(g);
    return { node: g, button: m.button };
  });

  // The Moon base target sits on the surface itself.
  const baseNode = new THREE.Group();
  const lat = 0.42, lon = -0.45;
  baseNode.position.set(Math.cos(lat) * Math.sin(lon), Math.sin(lat), Math.cos(lat) * Math.cos(lon)).multiplyScalar(1.006);
  baseNode.lookAt(baseNode.position.clone().multiplyScalar(2));
  const baseMat = () => new THREE.MeshBasicMaterial({ color: 0xff8fab, transparent: true, side: THREE.DoubleSide, depthWrite: false });
  const baseRing = new THREE.Mesh(new THREE.RingGeometry(0.04, 0.052, 40), baseMat());
  const basePulse = new THREE.Mesh(new THREE.RingGeometry(0.052, 0.06, 40), baseMat());
  const baseDot = new THREE.Mesh(new THREE.CircleGeometry(0.016, 20), baseMat());
  baseNode.add(baseRing, basePulse, baseDot);
  spin.add(baseNode);
  items.push({ node: baseNode, button: base.button });

  // ---- interaction ----
  const state = {
    yaw: 0.25, pitch: 0.12, vyaw: 0, auto: !reduced, reduced,
    dragging: false, lastX: 0, lastY: 0, target: null, idleAt: 0, vpitch: 0,
  };
  const touch = () => { state.auto = false; state.idleAt = performance.now(); };

  // Listen on the whole stage, so the Moon can be grabbed anywhere on it, not
  // only where the canvas happens to be uncovered. Markers keep their clicks.
  stage.addEventListener("pointerdown", (e) => {
    if (e.button > 0 || e.target.closest?.(".marker, button, a")) return;
    state.dragging = true; state.lastX = e.clientX; state.lastY = e.clientY; state.vyaw = 0; state.vpitch = 0; state.target = null;
    touch();
    stage.setPointerCapture?.(e.pointerId);
    stage.classList.add("is-dragging");
  });
  stage.addEventListener("pointermove", (e) => {
    if (!state.dragging) return;
    const dx = e.clientX - state.lastX, dy = e.clientY - state.lastY;
    state.lastX = e.clientX; state.lastY = e.clientY;
    const k = 3.2 / Math.max(200, stage.clientWidth);
    state.yaw += dx * k;
    state.vyaw = dx * k;
    state.pitch = Math.min(0.9, Math.max(-0.9, state.pitch + dy * k));
    state.vpitch = dy * k;
    touch();
  });
  const endDrag = () => { state.dragging = false; stage.classList.remove("is-dragging"); };
  stage.addEventListener("pointerup", endDrag);
  stage.addEventListener("pointercancel", endDrag);
  stage.addEventListener("lostpointercapture", endDrag);

  stage.addEventListener("keydown", (e) => {
    if (e.target !== stage) return;
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      state.target = null;
      state.yaw += e.key === "ArrowLeft" ? -0.2 : 0.2;
      touch();
      e.preventDefault();
    }
  });

  const v = new THREE.Vector3();
  const camPos = camera.position;
  function place() {
    const w = stage.clientWidth, h = stage.clientHeight;
    for (const it of items) {
      it.node.getWorldPosition(v);
      // Hidden when the Moon is between the camera and the marker.
      const dx = v.x - camPos.x, dy = v.y - camPos.y, dz = v.z - camPos.z;
      const t = -(camPos.x * dx + camPos.y * dy + camPos.z * dz) / (dx * dx + dy * dy + dz * dz);
      let hidden = false;
      if (t > 0 && t < 1) {
        const cx = camPos.x + dx * t, cy = camPos.y + dy * t, cz = camPos.z + dz * t;
        hidden = cx * cx + cy * cy + cz * cz < 0.985;
      }
      v.project(camera);
      const x = (v.x * 0.5 + 0.5) * w, y = (-v.y * 0.5 + 0.5) * h;
      // Wide: the label sits outside the marker. Narrow: it faces inward, so it
      // never reaches the edge of the screen.
      const flip = w < 520 && x > w * 0.5;
      it.button.classList.toggle("is-left", flip);
      it.button.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)${flip ? " translateX(-100%)" : ""}`;
      it.button.classList.toggle("is-behind", hidden);
    }
  }

  let running = false, raf = 0, prev = 0, sized = 0;
  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    sized = w;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - prev) / 1000 || 0);
    prev = now;
    if (state.target !== null) {
      const d = state.target - state.yaw;
      if (state.reduced || Math.abs(d) < 0.002) { state.yaw = state.target; state.target = null; }
      else state.yaw += d * Math.min(1, dt * 5);
      state.pitch += (0.12 - state.pitch) * Math.min(1, dt * 5);
    } else if (!state.dragging) {
      if (state.auto) state.yaw += dt * 0.07;
      else if (!state.reduced && (Math.abs(state.vyaw) > 0.0002 || Math.abs(state.vpitch) > 0.0002)) {
        state.yaw += state.vyaw; state.vyaw *= 0.93;
        state.pitch = Math.min(0.9, Math.max(-0.9, state.pitch + state.vpitch)); state.vpitch *= 0.9;
      }
      if (!state.auto && !state.reduced && now - state.idleAt > 14000 && !stage.matches(":focus-within, :hover")) state.auto = true;
    }
    spin.rotation.y = state.yaw;
    tilt.rotation.x = state.pitch;
    if (!state.reduced) {
      const p = (now / 1600) % 1;
      basePulse.scale.setScalar(1 + p * 1.6);
      basePulse.material.opacity = 1 - p;
    }
    renderer.render(scene, camera);
    place();
  }
  function start() { if (!running) { running = true; prev = performance.now(); raf = requestAnimationFrame(frame); } }
  function stop() { running = false; cancelAnimationFrame(raf); }

  new ResizeObserver(() => { if (stage.clientWidth !== sized) resize(); }).observe(stage);
  let onScreen = true;
  new IntersectionObserver((entries) => {
    onScreen = entries[0].isIntersecting;
    if (onScreen && !document.hidden) start(); else stop();
  }).observe(stage);
  document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); else if (onScreen) start(); });
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); stop(); stage.classList.remove("is-3d"); stage.classList.add("is-flat"); });

  resize();
  start();
  stage.classList.add("is-3d");

  return {
    // Turn the Moon so a marker faces the visitor (used on keyboard focus).
    faceMarker(index) {
      const it = items[index];
      if (!it) return;
      touch();
      spin.updateMatrixWorld(true);
      it.node.getWorldPosition(v);
      tilt.worldToLocal(v);                 // position in the frame that only yaw moves
      const now = Math.atan2(v.x, v.z);     // where it points now, 0 = toward the camera
      let d = -now;
      while (d > Math.PI) d -= Math.PI * 2;
      while (d < -Math.PI) d += Math.PI * 2;
      state.target = state.yaw + d;
    },
    pause: touch,
    setReducedMotion(on) { state.reduced = on; if (on) { state.auto = false; state.vyaw = 0; } },
  };
}
