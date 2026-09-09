// A small, dependency-free point-cloud illustration of the Micro's control layout.
// No device access: this canvas is an interactive illustration only.
const canvas = document.querySelector("#micro-scene");
const context = canvas.getContext("2d", { alpha: false });
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const points = [];
let seed = 517;
function random() {
  seed = (seed * 16807) % 2147483647;
  return (seed - 1) / 2147483646;
}
function dot(x, y, z, light = 1) {
  points.push({ x, y, z, light, size: random() > 0.97 ? 2 : 1 });
}
function line(ax, ay, az, bx, by, bz, spacing = 3, light = 1) {
  const count = Math.ceil(Math.hypot(bx - ax, by - ay, bz - az) / spacing);
  if (count === 0) {
    dot(ax, ay, az, light);
    return;
  }
  for (let i = 0; i <= count; i++) {
    const t = i / count;
    dot(ax + (bx - ax) * t, ay + (by - ay) * t, az + (bz - az) * t, light);
  }
}
function ring(cx, cy, r, z, light = 1) {
  for (let a = 0; a < Math.PI * 2; a += 2.5 / r)
    dot(cx + Math.cos(a) * r, cy + Math.sin(a) * r, z, light);
}
function rounded(cx, cy, w, h, r, z, light = 1) {
  line(cx - w / 2 + r, cy - h / 2, z, cx + w / 2 - r, cy - h / 2, z, 3, light);
  line(cx - w / 2 + r, cy + h / 2, z, cx + w / 2 - r, cy + h / 2, z, 3, light);
  line(cx - w / 2, cy - h / 2 + r, z, cx - w / 2, cy + h / 2 - r, z, 3, light);
  line(cx + w / 2, cy - h / 2 + r, z, cx + w / 2, cy + h / 2 - r, z, 3, light);
  for (let q = 0; q < 4; q++) {
    const x = cx + (q === 0 || q === 3 ? 1 : -1) * (w / 2 - r),
      y = cy + (q < 2 ? 1 : -1) * (h / 2 - r);
    for (let a = (q * Math.PI) / 2; a < ((q + 1) * Math.PI) / 2; a += 0.12)
      dot(x + Math.cos(a) * r, y + Math.sin(a) * r, z, light);
  }
}
// Layered enclosure and keycaps provide depth when visitors rotate the view.
rounded(0, 0, 300, 330, 30, -14, 0.45);
rounded(0, 0, 300, 330, 30, 8, 0.9);
rounded(0, 0, 288, 318, 26, 11, 0.5);
for (const x of [-120, 120])
  for (const y of [-135, 135]) {
    ring(x, y, 3, 12, 0.8);
  }
for (let y = -132; y <= 132; y += 7) {
  dot(-150, y, -5, 0.3);
  dot(150, y, -5, 0.3);
}
for (let x = -120; x <= 120; x += 6) {
  dot(x, -165, -5, 0.3);
  dot(x, 165, -5, 0.3);
}
function key(x, y, w = 55, h = 55) {
  rounded(x, y, w, h, 11, 13, 0.45);
  rounded(x, y, w, h, 11, 18, 0.38);
  rounded(x, y, w, h, 11, 24, 1);
  for (let px = -w / 2 + 9; px < w / 2 - 8; px += 7)
    for (let py = -h / 2 + 9; py < h / 2 - 8; py += 7)
      dot(x + px, y + py, 24, 0.2 + random() * 0.2);
  for (let a = -w / 2 + 8; a < w / 2 - 8; a += 8) {
    dot(x + a, y + h / 2, 18, 0.3);
  }
}
for (const x of [-34, 34]) key(x, -102);
for (const y of [-34, 34]) for (const x of [-102, -34, 34, 102]) key(x, y);
ring(-102, -102, 27, 13, 0.5);
ring(-102, -102, 27, 19, 0.6);
ring(-102, -102, 27, 25, 0.6);
ring(-102, -102, 27, 30, 1);
ring(-102, -102, 22, 30, 0.4);
line(-102, -124, 31, -102, -112, 31, 2, 1.6);
ring(102, -102, 27, 19, 0.8);
ring(102, -102, 11, 32, 1);
for (let a = 0; a < Math.PI * 2; a += Math.PI / 2) {
  const x = 102 + Math.cos(a) * 20,
    y = -102 + Math.sin(a) * 20;
  dot(x, y, 28, 1.8);
}
ring(-102, 104, 15, 20, 0.8);
key(-1, 104, 124, 55);
key(102, 104);
// Flip the control layout before adding upright key legends.
for (const point of points) point.x *= -1;
// Small key legends, indicated as luminous marks rather than fake UI text.
for (const y of [-102, -34, 34])
  for (const x of [-102, -34, 34, 102]) {
    if (y === -102 && (x === -102 || x === 102)) continue;
    line(x - 6, y - 5, 25, x + 6, y - 5, 25, 2, 0.9);
    line(x - 6, y - 5, 25, x - 6, y + 5, 25, 2, 0.9);
    line(x - 6, y + 5, 25, x + 3, y + 5, 25, 2, 0.9);
  }
for (let x = -36; x <= 36; x += 6)
  line(
    x,
    104 - Math.abs(Math.sin(x * 0.16)) * 10,
    26,
    x,
    104 + Math.abs(Math.sin(x * 0.16)) * 10,
    26,
    2,
    1.3,
  );
line(-96, 98, 25, -96, 107, 25, 2, 1);
line(-96, 107, 25, -107, 107, 25, 2, 1);
for (let i = 0; i < 350; i++) {
  const x = (random() - 0.5) * 275,
    y = (random() - 0.5) * 300;
  dot(x, y, 9, 0.12);
}
const stars = Array.from({ length: 1000 }, () => ({
  x: random(),
  y: random(),
  z: random(),
  size: random() > 0.96 ? 2 : 1,
}));
const motionButton = document.querySelector("#pause-motion");
let autoMotion = !reduced.matches;
let width = 0,
  height = 0,
  ratio = 1,
  pointer = null,
  lastX = 0,
  lastY = 0,
  yaw = -0.28,
  pitch = 0.4,
  orbitTime = 0,
  frame = 0,
  visible = true,
  lastTime = null;

// Rasterize the small ASCII alphabet once, at the display's pixel density.
// Drawing cached glyphs avoids thousands of fractional font rasterizations per frame.
const glyphs = document.createElement("canvas");
const background = document.createElement("canvas");
const cell = 20;
const alphabet = [".", "*", "+", "#"];
const order = points.map((_, index) => index);
const projectedX = new Float32Array(points.length);
const projectedY = new Float32Array(points.length);
const depth = new Float32Array(points.length);
const scales = new Float32Array(points.length);
const glyphColumns = points.map(
  (p) =>
    (p.size > 1 ? 3 : p.light > 1 ? 2 : p.light > 0.6 ? 1 : 0) +
    (p.light > 1 ? 4 : 0),
);
function cacheArtwork() {
  glyphs.width = cell * 8 * ratio;
  glyphs.height = cell * 11 * ratio;
  const ink = glyphs.getContext("2d");
  ink.setTransform(ratio, 0, 0, ratio, 0, 0);
  for (let size = 6; size <= 16; size++) {
    ink.font = `700 ${size}px monospace`;
    for (let column = 0; column < 8; column++) {
      ink.fillStyle = column < 4 ? "#acd0ff" : "#eaf4ff";
      ink.fillText(
        alphabet[column % 4],
        column * cell + 2,
        (size - 6) * cell + 16,
      );
    }
  }
  background.width = canvas.width;
  background.height = canvas.height;
  const sky = background.getContext("2d", { alpha: false });
  sky.setTransform(ratio, 0, 0, ratio, 0, 0);
  sky.fillStyle = "#0e1018";
  sky.fillRect(0, 0, width, height);
  for (const star of stars) {
    sky.fillStyle = `rgba(132,164,216,${0.14 + star.z * 0.4})`;
    sky.fillRect(star.x * width, star.y * height, star.size, star.size);
  }
}
function motionLabel() {
  motionButton.textContent = autoMotion ? "Pause motion" : "Play motion";
  motionButton.setAttribute("aria-pressed", String(!autoMotion));
}
function clampPitch(value) {
  return Math.max(-1.1, Math.min(1.1, value));
}
function stopMotion() {
  if (autoMotion) {
    // Keep the pose already on screen when a visitor grabs or pauses it.
    yaw += Math.sin(orbitTime / 4200) * 0.12;
    pitch = clampPitch(pitch + (Math.cos(orbitTime / 5100) - 1) * 0.06);
    autoMotion = false;
  }
  orbitTime = 0;
  lastTime = null;
  motionLabel();
}
function resize() {
  const bounds = canvas.getBoundingClientRect();
  const nextRatio = Math.min(devicePixelRatio || 1, 2);
  if (width === bounds.width && height === bounds.height && ratio === nextRatio)
    return;
  width = bounds.width;
  height = bounds.height;
  ratio = nextRatio;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  cacheArtwork();
  update();
}
function draw() {
  if (!width || !height) return;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.globalAlpha = 1;
  context.drawImage(background, 0, 0, width, height);
  const viewYaw = yaw + (autoMotion ? Math.sin(orbitTime / 4200) * 0.12 : 0);
  const viewPitch = clampPitch(
    pitch + (autoMotion ? (Math.cos(orbitTime / 5100) - 1) * 0.06 : 0),
  );
  const cy = Math.cos(viewYaw),
    sy = Math.sin(viewYaw);
  const cx = Math.cos(viewPitch),
    sx = Math.sin(viewPitch);
  const perspective =
    Math.min(width / (width < 760 ? 420 : 560), height / 465, 1.8) * 720;
  for (let index = 0; index < points.length; index++) {
    const p = points[index];
    const x = p.x * cy + p.z * sy;
    const z = -p.x * sy + p.z * cy;
    const y = p.y * cx - z * sx;
    depth[index] = p.y * sx + z * cx;
    const scale = perspective / (720 + depth[index]);
    projectedX[index] = width / 2 + x * scale;
    projectedY[index] = height * 0.48 + y * scale;
    scales[index] = scale;
  }
  order.sort((a, b) => depth[b] - depth[a] || a - b);
  context.fillStyle = "#acd0ff";
  for (const index of order) {
    const p = points[index];
    const scale = scales[index];
    context.globalAlpha = Math.min(
      0.96,
      Math.max(0.08, p.light * (0.95 - depth[index] / 650)),
    );
    const x = Math.round(projectedX[index] * ratio) / ratio;
    const y = Math.round(projectedY[index] * ratio) / ratio;
    if (p.light > 0.18) {
      const fontSize = Math.min(16, Math.max(6, Math.round(5.4 * scale)));
      const glyphWidth = Math.ceil(fontSize * 0.7) + 2;
      const glyphHeight = fontSize + 2;
      context.drawImage(
        glyphs,
        (glyphColumns[index] * cell + 1) * ratio,
        ((fontSize - 6) * cell + 16 - fontSize) * ratio,
        glyphWidth * ratio,
        glyphHeight * ratio,
        x - 1,
        y - fontSize,
        glyphWidth,
        glyphHeight,
      );
    } else {
      const size = Math.max(1, p.size * scale * 0.8);
      context.fillRect(x, y, size, size);
    }
  }
  context.globalAlpha = 1;
}
function animate(time) {
  frame = 0;
  if (!visible || document.hidden) return;
  if (autoMotion) {
    if (lastTime !== null) orbitTime += Math.min(time - lastTime, 50);
    lastTime = time;
  }
  draw();
  if (autoMotion) update();
}
function update() {
  if (visible && !document.hidden && !frame)
    frame = requestAnimationFrame(animate);
}
canvas.addEventListener("pointerdown", (event) => {
  if (!event.isPrimary || event.button !== 0 || pointer !== null) return;
  pointer = event.pointerId;
  stopMotion();
  lastX = event.clientX;
  lastY = event.clientY;
  canvas.setPointerCapture(pointer);
  canvas.classList.add("dragging");
});
canvas.addEventListener("pointermove", (event) => {
  if (event.pointerId !== pointer) return;
  // Direct input, painted once on the next display frame. No easing or frame cap.
  yaw += (event.clientX - lastX) * 0.008;
  pitch = clampPitch(pitch + (event.clientY - lastY) * 0.006);
  lastX = event.clientX;
  lastY = event.clientY;
  update();
});
function release(event) {
  if (event.pointerId !== pointer) return;
  pointer = null;
  canvas.classList.remove("dragging");
  if (canvas.hasPointerCapture(event.pointerId))
    canvas.releasePointerCapture(event.pointerId);
}
canvas.addEventListener("pointerup", release);
canvas.addEventListener("pointercancel", release);
canvas.addEventListener("lostpointercapture", release);
function reset() {
  yaw = -0.28;
  pitch = 0.4;
  orbitTime = 0;
  lastTime = null;
  update();
}
canvas.addEventListener("keydown", (event) => {
  if (
    !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home"].includes(
      event.key,
    )
  )
    return;
  event.preventDefault();
  stopMotion();
  if (event.key === "Home") reset();
  else {
    if (event.key === "ArrowLeft") yaw -= 0.2;
    else if (event.key === "ArrowRight") yaw += 0.2;
    else pitch = clampPitch(pitch + (event.key === "ArrowUp" ? -0.2 : 0.2));
    update();
  }
});
document.querySelector("#reset-view").addEventListener("click", reset);
motionButton.addEventListener("click", () => {
  if (autoMotion) stopMotion();
  else {
    autoMotion = true;
    lastTime = null;
    motionLabel();
  }
  update();
});
reduced.addEventListener("change", () => {
  if (reduced.matches) {
    stopMotion();
    update();
  }
});
function visibilityChanged() {
  lastTime = null;
  if (!visible || document.hidden) {
    cancelAnimationFrame(frame);
    frame = 0;
  } else update();
}
motionLabel();
new ResizeObserver(resize).observe(canvas);
new IntersectionObserver(([entry]) => {
  visible = entry.isIntersecting;
  visibilityChanged();
}).observe(canvas);
document.addEventListener("visibilitychange", visibilityChanged);
