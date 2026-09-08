.pragma library

function shortLabel(value) {
    const label = String(value || "Unassigned")
    if (/push-to-talk/i.test(label)) return "Push to talk"
    return label
}

function keyLabel(value) {
    return shortLabel(value)
        .replace("Microphone mute", "Mic mute")
        .replace("Previous workspace", "Prev space")
        .replace("Next workspace", "Next space")
        .replace("Scratchpad", "Scratch")
        .replace("Toggle dictation", "Dictation")
        .replace("Audio mute", "Mute")
}

function keyIcon(binding) {
    const action = binding && binding.action ? binding.action : {kind: "noop"}
    if (action.kind === "noop") return {text: "—", font: ""}
    if (action.kind === "keybind") return {text: "\ue900", font: "omarchy"}
    if (action.kind === "key") {
        const keys = {
            KC_ENT: "↵", KC_PENT: "↵", KC_BSPC: "⌫", KC_DEL: "⌦", KC_TAB: "⇥",
            KC_ESC: "⎋", KC_SPC: "␣", KC_UP: "↑", KC_DOWN: "↓", KC_LEFT: "←", KC_RGHT: "→",
            KC_HOME: "⇱", KC_END: "⇲", KC_PGUP: "⇞", KC_PGDN: "⇟", KC_CAPS: "⇪",
            KC_VOLU: "", KC_VOLD: "", KC_MUTE: "", KC_BRIU: "󰃠", KC_BRID: "󰃞",
            KC_MPLY: "󰐊", KC_MNXT: "󰒭", KC_MPRV: "󰒮", KC_MSTP: "󰓛",
            KC_MINS: "−", KC_EQL: "=", KC_LBRC: "[", KC_RBRC: "]", KC_BSLS: "\\",
            KC_SCLN: ";", KC_QUOT: "'", KC_GRV: "`", KC_COMM: ",", KC_DOT: ".", KC_SLSH: "/"
        }
        const key = action.key || ""
        if (keys[key]) return {text: keys[key], font: ""}
        if (/^KC_[A-Z0-9]$/.test(key) || /^KC_F\d+$/.test(key)) return {text: key.slice(3), font: ""}
        if (/^KC_P\d$/.test(key)) return {text: key.slice(4), font: ""}
        return {text: "󰌌", font: ""}
    }
    if (action.kind === "volume") return {text: action.delta > 0 ? "" : "", font: ""}
    if (action.kind === "focus") return {text: {l:"←",r:"→",u:"↑",d:"↓"}[action.direction] || "󰌌", font: ""}
    if (action.kind === "workspace" || action.kind === "herdr_workspace") return {text: "󰕰", font: ""}
    if (/voice|dictation|talk/i.test(binding.label || "")) return {text: "󰍬", font: ""}
    return {text: "", font: ""}
}
