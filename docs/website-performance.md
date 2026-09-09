# Website interaction checks

Run the scene regressions with Node 20 or newer:

```sh
node --test tests/site/scene.test.cjs
```

The Pages workflow runs these before deployment. They cover the next display
frame after dragging, stopping without trailing animation, pause/grab continuity,
pointer capture loss, secondary pointers, right clicks, keyboard/reset behavior,
reduced motion, hidden/offscreen scheduling, and finite drawing coordinates.
The canvas mock checks submitted drawing operations; it does not measure browser
paint time. Check the rendered page in a browser after changing the artwork.

## Renderer benchmark — 2026-09-09

With Chromium installed, run the separate software-rendering benchmark:

```sh
python tests/site/benchmark.py site/scene.js /tmp/micro-render.json
```

This uses an isolated headless Chromium process with GPU acceleration disabled,
a 1440 × 820 CSS-pixel canvas at DPR 2, and 6,956 points. Each of three runs
warms up for 20 draws and measures 90 rotating views. A pixel readback after
every draw forces rasterization to complete. No measured outliers are discarded.

On the development workstation, Chromium 152.0.7977.82:

| Renderer | Run medians (ms) | Run p95s (ms) |
| --- | --- | --- |
| Before (`cf9bc63`) | 207.5 / 236.3 / 99.5 | 382.5 / 340.0 / 405.1 |
| Cached glyphs and direct drag | 24.3 / 26.0 / 24.1 | 25.5 / 28.3 / 27.1 |

The median of the run medians fell from 207.5 to 24.3 ms (about 8.5×).
The baseline varied substantially; even its fastest run remained slower than
the candidate's slowest run. This is a comparison of software rendering cost,
not a claim about interactive FPS on hardware-accelerated browsers. Remeasure
when changing point density, glyph rendering, canvas size, or browser/runtime.

The change removes the 30 ms frame gate and pointer easing, caches glyphs and
the star field, reuses projection buffers, and calculates camera trigonometry
once per frame. A zero-length stroke now produces a finite point instead of NaN,
which also keeps the depth ordering deterministic. The model is mirrored as
requested, with upright key markings.
