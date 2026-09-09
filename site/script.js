const status = document.getElementById("copy-status");
for (const button of document.querySelectorAll("[data-copy]")) {
  if (!navigator.clipboard?.writeText) continue;
  button.hidden = false;
  button.addEventListener("click", async () => {
    const code = document.getElementById(button.dataset.copy);
    try {
      await navigator.clipboard.writeText(code.textContent);
      button.textContent = "Copied";
      status.textContent = "Commands copied. Review them before running.";
      setTimeout(() => {
        button.textContent = "Copy";
      }, 2000);
    } catch {
      status.textContent =
        "Clipboard unavailable. Select and copy the commands directly.";
    }
  });
}

const examples = {
  single: {
    key: "ENTER",
    caption: "Single click → Enter",
    mapping: { label: "Enter", action: { kind: "key", key: "KC_ENT" } },
  },
  double: {
    key: "BACKSPACE",
    caption: "Double click → Backspace",
    mapping: {
      gestures: {
        double: { label: "Backspace", action: { kind: "key", key: "KC_BSPC" } },
      },
    },
  },
  hold: {
    key: "F9 / VOICE",
    caption: "Click + hold → Voice input",
    mapping: {
      gestures: {
        tap_hold: {
          label: "Voice input",
          action: { kind: "key", key: "KC_F9" },
        },
      },
    },
  },
};
for (const button of document.querySelectorAll("[data-gesture]")) {
  button.addEventListener("click", () => {
    const example = examples[button.dataset.gesture];
    for (const item of document.querySelectorAll("[data-gesture]"))
      item.setAttribute("aria-pressed", String(item === button));
    const left = Math.floor((20 - example.key.length) / 2);
    const label =
      " ".repeat(left) +
      example.key +
      " ".repeat(20 - left - example.key.length);
    document.querySelector(".key-example pre").textContent =
      "+--------------------+\n|                    |\n|" +
      label +
      "|\n|                    |\n+--------------------+";
    document.querySelector("#example-caption").textContent = example.caption;
    document.querySelector("#example-json").textContent = JSON.stringify(
      example.mapping,
      null,
      2,
    );
  });
}
