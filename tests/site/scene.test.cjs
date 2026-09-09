const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const { createHash } = require("node:crypto");
const source = fs.readFileSync(
  path.join(__dirname, "../../site/scene.js"),
  "utf8",
);

function scene({ reducedMotion = false } = {}) {
  const callbacks = new Map();
  let nextFrame = 0;
  let now = 0;
  let draws = 0;
  let pixels = [];
  function element(main = false) {
    const events = new Map();
    const captures = new Set();
    const classes = new Set();
    const context = {
      setTransform() {
        if (main) {
          draws++;
          pixels = [];
        }
      },
      clearRect() {},
      fillRect(...args) {
        if (main) pixels.push(["rect", ...args]);
      },
      fillText(...args) {
        if (main) pixels.push(["text", ...args]);
      },
      drawImage(_image, ...args) {
        if (main) pixels.push(["image", ...args]);
      },
    };
    return {
      hidden: false,
      textContent: "",
      classList: {
        add: (x) => classes.add(x),
        remove: (x) => classes.delete(x),
        contains: (x) => classes.has(x),
      },
      getContext: () => context,
      getBoundingClientRect: () => ({ width: 1440, height: 820 }),
      setAttribute() {},
      setPointerCapture: (id) => captures.add(id),
      hasPointerCapture: (id) => captures.has(id),
      releasePointerCapture: (id) => captures.delete(id),
      addEventListener: (type, callback) => events.set(type, callback),
      emit: (type, event = {}) =>
        events.get(type)?.({
          pointerId: 1,
          button: 0,
          isPrimary: true,
          clientX: 0,
          clientY: 0,
          preventDefault() {},
          ...event,
        }),
    };
  }
  const canvas = element(true),
    pause = element(),
    reset = element(),
    document = element();
  const media = element();
  media.matches = reducedMotion;
  document.createElement = () => element();
  document.querySelector = (selector) =>
    ({ "#micro-scene": canvas, "#pause-motion": pause, "#reset-view": reset })[
      selector
    ];
  let resize, intersection;
  vm.runInNewContext(source, {
    document,
    matchMedia: () => media,
    devicePixelRatio: 2,
    performance: { now: () => now },
    requestAnimationFrame: (callback) => {
      callbacks.set(++nextFrame, callback);
      return nextFrame;
    },
    cancelAnimationFrame: (id) => callbacks.delete(id),
    ResizeObserver: class {
      constructor(callback) {
        resize = callback;
      }
      observe() {}
    },
    IntersectionObserver: class {
      constructor(callback) {
        intersection = callback;
      }
      observe() {}
    },
  });
  const tick = (time) => {
    now = time;
    const batch = [...callbacks.values()];
    callbacks.clear();
    for (const callback of batch) callback(time);
  };
  resize();
  intersection([{ isIntersecting: true }]);
  tick(40);
  return {
    canvas,
    pause,
    reset,
    document,
    media,
    tick,
    intersect: (visible) => intersection([{ isIntersecting: visible }]),
    get draws() {
      return draws;
    },
    get finite() {
      return pixels.every((operation) =>
        operation
          .slice(1)
          .every(
            (value) => typeof value !== "number" || Number.isFinite(value),
          ),
      );
    },
    get pixels() {
      return createHash("sha256").update(JSON.stringify(pixels)).digest("hex");
    },
    get pending() {
      return callbacks.size;
    },
  };
}

function paused() {
  const s = scene();
  s.pause.emit("click");
  s.tick(80);
  return s;
}

test("drag paints on the next 60 Hz frame and stops without a trailing animation", () => {
  const s = paused();
  const before = s.pixels;
  const count = s.draws;
  s.canvas.emit("pointerdown");
  s.canvas.emit("pointermove", { clientX: 80, clientY: 20 });
  s.canvas.emit("pointerup", { clientX: 80, clientY: 20 });
  s.tick(96.67);
  assert.equal(
    s.draws,
    count + 1,
    "the next display frame must paint the full drag",
  );
  assert.notEqual(s.pixels, before);
  assert.equal(
    s.pending,
    0,
    "released input must not keep easing toward the pointer",
  );
  const final = s.pixels;
  s.tick(1000);
  assert.equal(s.pixels, final);
});

test("pausing or grabbing the illustration preserves its displayed pose", () => {
  for (const grab of [false, true]) {
    const s = scene();
    s.tick(2040);
    const before = s.pixels;
    if (grab) s.canvas.emit("pointerdown");
    else s.pause.emit("click");
    s.tick(2056.67);
    assert.equal(
      s.pixels,
      before,
      "stopping automatic motion must not snap the view",
    );
  }
});

test("pointer capture loss ends dragging and other pointers cannot move it", () => {
  const s = paused();
  s.canvas.emit("pointerdown");
  s.canvas.emit("pointermove", { pointerId: 2, clientX: 200 });
  s.tick(120);
  assert.equal(s.pending, 0);
  const before = s.pixels;
  s.canvas.emit("lostpointercapture");
  s.canvas.emit("pointermove", { clientX: 100 });
  s.tick(160);
  assert.equal(s.pixels, before);
  assert.equal(s.canvas.classList.contains("dragging"), false);
});

test("right mouse button does not rotate the illustration", () => {
  const s = paused();
  const before = s.pixels;
  s.canvas.emit("pointerdown", { button: 2 });
  s.canvas.emit("pointermove", { clientX: 100 });
  s.tick(120);
  assert.equal(s.pixels, before);
});

test("reduced motion starts still, while arrow keys and reset remain usable", () => {
  const s = scene({ reducedMotion: true });
  const before = s.pixels;
  assert.equal(s.pending, 0);
  s.canvas.emit("keydown", { key: "ArrowRight" });
  s.tick(80);
  assert.notEqual(s.pixels, before);
  assert.equal(s.pending, 0);
  s.reset.emit("click");
  s.tick(120);
  assert.equal(s.pixels, before);
});

test("offscreen and hidden scenes stop scheduling work", () => {
  const s = scene();
  assert.equal(s.pending, 1);
  s.intersect(false);
  assert.equal(s.pending, 0);
  s.intersect(true);
  s.tick(80);
  assert.equal(s.pending, 1);
  s.document.hidden = true;
  s.document.emit("visibilitychange");
  assert.equal(s.pending, 0);
  const count = s.draws;
  s.reset.emit("click");
  s.tick(120);
  assert.equal(s.draws, count);
  s.document.hidden = false;
  s.document.emit("visibilitychange");
  s.tick(160);
  assert.equal(s.pending, 1);
});

test("all submitted drawing coordinates are finite across rotations", () => {
  const s = paused();
  for (let turn = 0; turn < 12; turn++) {
    s.canvas.emit("keydown", { key: "ArrowRight" });
    s.tick(120 + turn * 16.67);
    assert.ok(
      s.finite,
      "invalid geometry must not reach the depth sort or canvas",
    );
  }
});

test("grabbing at the vertical rotation limit does not jump", () => {
  const s = paused();
  for (let press = 0; press < 8; press++)
    s.canvas.emit("keydown", { key: "ArrowUp" });
  s.tick(120);
  s.pause.emit("click");
  for (let frame = 0; frame < 100; frame++) s.tick(140 + frame * 16.67);
  const before = s.pixels;
  s.canvas.emit("pointerdown");
  s.canvas.emit("pointermove");
  s.tick(1840);
  assert.equal(s.pixels, before);
});
