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
line(108, 98, 25, 108, 107, 25, 2, 1);
line(108, 107, 25, 97, 107, 25, 2, 1);
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
let autoMotion = !reduced.matches,
  clock = 0;
function motionLabel() {
  motionButton.textContent = autoMotion ? "Pause motion" : "Play motion";
  motionButton.setAttribute("aria-pressed", String(!autoMotion));
}
motionLabel();
let width = 0,
  height = 0,
  ratio = 1,
  dragging = false,
  lastX = 0,
  lastY = 0,
  yaw = -0.28,
  pitch = 0.4,
  targetYaw = yaw,
  targetPitch = pitch,
  frame = 0,
  visible = true,
  lastTime = 0;
function resize() {
  const r = canvas.getBoundingClientRect();
  width = r.width;
  height = r.height;
  ratio = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  draw();
}
function project(p) {
  const viewYaw = yaw + (autoMotion ? Math.sin(clock / 4200) * 0.12 : 0),
    viewPitch = pitch + (autoMotion ? Math.cos(clock / 5100) * 0.06 : 0);
  const cy = Math.cos(viewYaw),
    sy = Math.sin(viewYaw),
    cx = Math.cos(viewPitch),
    sx = Math.sin(viewPitch);
  const x = p.x * cy + p.z * sy,
    z = -p.x * sy + p.z * cy,
    y = p.y * cx - z * sx,
    zz = p.y * sx + z * cx;
  const scale =
    (Math.min(width / (width < 760 ? 420 : 560), height / 465, 1.8) * 720) /
    (720 + zz);
  return {
    x: width / 2 + x * scale,
    y: height * 0.48 + y * scale,
    z: zz,
    scale,
  };
}
function draw() {
  if (!width) return;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.fillStyle = "#0e1018";
  context.fillRect(0, 0, width, height);
  for (const s of stars) {
    const x = (s.x * width + yaw * 12 * s.z + width) % width,
      y = (s.y * height + pitch * 12 * s.z + height) % height;
    context.fillStyle = `rgba(132,164,216,${0.14 + s.z * 0.4})`;
    context.fillRect(x, y, s.size, s.size);
  }
  const sorted = points
    .map((p) => ({ ...project(p), light: p.light, size: p.size }))
    .sort((a, b) => b.z - a.z);
  for (const p of sorted) {
    const alpha = Math.min(0.96, Math.max(0.08, p.light * (0.95 - p.z / 650)));
    context.fillStyle = `rgba(${p.light > 1 ? 234 : 172},${p.light > 1 ? 244 : 208},255,${alpha})`;
    const size = Math.max(1, p.size * p.scale * 0.8);
    if (p.light > 0.18) {
      context.font = `700 ${Math.max(6, 5.4 * p.scale)}px monospace`;
      context.fillText(
        p.size > 1 ? "#" : p.light > 1 ? "+" : p.light > 0.6 ? "*" : ".",
        p.x,
        p.y,
      );
    } else {
      context.fillRect(p.x, p.y, size, size);
    }
  }
}
function animate(time) {
  frame = 0;
  if (!visible || document.hidden) return;
  if (time - lastTime > 30) {
    yaw += (targetYaw - yaw) * 0.13;
    pitch += (targetPitch - pitch) * 0.13;
    clock = time;
    draw();
    lastTime = time;
  }
  if (
    autoMotion ||
    Math.abs(targetYaw - yaw) + Math.abs(targetPitch - pitch) > 0.001
  )
    frame = requestAnimationFrame(animate);
}
function update() {
  if (reduced.matches) {
    yaw = targetYaw;
    pitch = targetPitch;
    draw();
  } else if (!frame) frame = requestAnimationFrame(animate);
}
canvas.addEventListener("pointerdown", (event) => {
  dragging = true;
  autoMotion = false;
  motionLabel();
  lastX = event.clientX;
  lastY = event.clientY;
  canvas.setPointerCapture(event.pointerId);
  canvas.classList.add("dragging");
});
canvas.addEventListener("pointermove", (event) => {
  if (!dragging) return;
  targetYaw += (event.clientX - lastX) * 0.008;
  targetPitch = Math.max(
    -1.1,
    Math.min(1.1, targetPitch + (event.clientY - lastY) * 0.006),
  );
  lastX = event.clientX;
  lastY = event.clientY;
  update();
});
function release() {
  dragging = false;
  canvas.classList.remove("dragging");
}
canvas.addEventListener("pointerup", release);
canvas.addEventListener("pointercancel", release);
canvas.addEventListener("keydown", (event) => {
  if (
    !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home"].includes(
      event.key,
    )
  )
    return;
  event.preventDefault();
  autoMotion = false;
  motionLabel();
  if (event.key === "Home") {
    targetYaw = -0.28;
    targetPitch = 0.4;
  } else if (event.key === "ArrowLeft") targetYaw -= 0.2;
  else if (event.key === "ArrowRight") targetYaw += 0.2;
  else
    targetPitch = Math.max(
      -1.1,
      Math.min(1.1, targetPitch + (event.key === "ArrowUp" ? -0.2 : 0.2)),
    );
  update();
});
document.querySelector("#reset-view").addEventListener("click", () => {
  targetYaw = -0.28;
  targetPitch = 0.4;
  update();
});
motionButton.addEventListener("click", () => {
  autoMotion = !autoMotion;
  motionLabel();
  if (autoMotion && !frame) frame = requestAnimationFrame(animate);
  else draw();
});
reduced.addEventListener("change", () => {
  if (reduced.matches) {
    autoMotion = false;
    motionLabel();
    draw();
  }
});
new ResizeObserver(resize).observe(canvas);
new IntersectionObserver(([entry]) => {
  visible = entry.isIntersecting;
  if (visible) {
    update();
    if (autoMotion && !frame) frame = requestAnimationFrame(animate);
  } else {
    cancelAnimationFrame(frame);
    frame = 0;
  }
}).observe(canvas);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    cancelAnimationFrame(frame);
    frame = 0;
  } else {
    update();
    if (autoMotion && !frame) frame = requestAnimationFrame(animate);
  }
});
