import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Ui
import "DisplayLabels.js" as Labels

BarWidget {
    id: root
    moduleName: "fraction12.codex-micro"
    readonly property var micro: bar && bar.shell ? bar.shell.serviceFor(moduleName) : null
    readonly property var state: micro ? micro.state : ({})
    readonly property bool connected: state.connected === true
    property bool popupOpen: false
    readonly property bool opened: popupOpen
    function open() { popupOpen = true; if (micro) { micro.refresh(); micro.loadEditor() } }
    property string selectedLayer: "2"
    property string selectedControl: "key00"
    readonly property var config: micro ? micro.editConfig : ({})
    property string selectedGesture: "single"
    readonly property bool supportsGestures: selectedControl.indexOf("key") === 0 || selectedControl === "dial_press"
    onSelectedControlChanged: { selectedGesture = "single"; shortcutPicker.close() }
    onSelectedLayerChanged: { shortcutPicker.close(); appPicker.close() }
    onSelectedGestureChanged: shortcutPicker.close()
    readonly property var baseBinding: mappings[selectedControl] || ({label: "Unassigned", action: {kind: "noop"}})
    readonly property var selectedBinding: selectedGesture === "single" ? baseBinding : (baseBinding.gestures || {})[selectedGesture] || ({label: "Unassigned", action: {kind: "noop"}})
    readonly property bool quickMicroReserved: config.quick_micro === true && selectedControl === "dial_press" && selectedGesture === "double"
    function setQuickMicro(enabled) {
        if (!micro || !config.layers) return
        const next = JSON.parse(JSON.stringify(config))
        next.quick_micro = enabled
        micro.change(next)
        shortcutPicker.close()
    }
    function selectBinding(value) {
        if (quickMicroReserved) return
        if (!micro || !config.layers) return
        const next = JSON.parse(JSON.stringify(config))
        const option = micro.options.find(o => o.value === value)
        const binding = next.layers[selectedLayer].bindings[selectedControl] || {label: "Unassigned", action: {kind: "noop"}}
        const choice = option ? {label: option.description, action: option.action} : {label: "Unassigned", action: {kind: "noop"}}
        if (selectedGesture === "single") {
            binding.label = choice.label
            binding.action = choice.action
        } else {
            if (!binding.gestures) binding.gestures = {}
            if (option) binding.gestures[selectedGesture] = choice
            else delete binding.gestures[selectedGesture]
            if (Object.keys(binding.gestures).length === 0) delete binding.gestures
        }
        next.layers[selectedLayer].bindings[selectedControl] = binding
        micro.change(next)
    }
    readonly property bool layerNamesValid: !!config.layers && ["2", "3"].every(n => config.layers[n].name.trim().length > 0 && config.layers[n].name.length <= 40)
    function assignApp(app) {
        if (!micro || !config.layers) return
        const next = JSON.parse(JSON.stringify(config))
        if (app) next.layers[selectedLayer].app = app
        else delete next.layers[selectedLayer].app
        micro.change(next)
    }
    function renameLayer(name) {
        if (!micro || !config.layers || name === config.layers[selectedLayer].name) return
        const next = JSON.parse(JSON.stringify(config))
        next.layers[selectedLayer].name = name
        micro.change(next)
    }
    function controlOptions() {
        if (selectedControl.indexOf("stick_") === 0)
            return [{value:"stick_up:single",label:"Up"},{value:"stick_right:single",label:"Right"},{value:"stick_down:single",label:"Down"},{value:"stick_left:single",label:"Left"}]
        const dial = selectedControl.indexOf("dial_") === 0
        const control = dial ? "dial_press" : selectedControl
        const gestures = [{value:control+":single",label:dial ? "Press" : "Single"},{value:control+":double",label:"Double"},{value:control+":tap_hold",label:"Click + hold"}]
        return dial ? [{value:"dial_left:single",label:"Left",tooltip:"Turn left"},{value:"dial_right:single",label:"Right",tooltip:"Turn right"}].concat(gestures) : gestures
    }
    function selectControlOption(value) {
        const parts = value.split(":")
        selectedControl = parts[0]
        selectedGesture = parts[1]
    }
    function close() { popupOpen = false }
    readonly property var selectedMapping: config.layers ? config.layers[selectedLayer] : null
    readonly property var mappings: selectedMapping ? selectedMapping.bindings : ({})
    function label(control) { return mappings[control] ? mappings[control].label : "Unassigned" }
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰌌"
        active: root.connected
        tooltipText: root.connected ? "Codex Micro · " + (root.state.device && root.state.device.transport === "bluetooth" ? "Bluetooth · " : "USB · ") + root.state.battery + "% · click for mappings" : (root.micro && root.micro.lastError ? root.micro.lastError : "Codex Micro · " + (root.micro ? root.micro.connectionLabel : "Status unavailable"))
        onPressed: function(mouseButton) {
            if (mouseButton === Qt.LeftButton) { root.popupOpen = !root.popupOpen; if (root.micro) { root.micro.refresh(); root.micro.loadEditor() } }
        }
    }
    KeyboardPanel {
        id: popup
        focusTarget: contentColumn
        contentWidth: popup.fittedContentWidth(360)
        contentHeight: popup.fittedContentHeight(contentColumn.implicitHeight)
        anchorItem: root
        bar: root.bar
        owner: root
        open: root.popupOpen
        padding: Style.space(14)
        ColumnLayout {
            id: contentColumn
            focus: true
            Keys.priority: Keys.AfterItem
            Keys.onEscapePressed: function(event) { root.close(); event.accepted = true }
            width: parent.width
            spacing: Style.space(12)
            RowLayout {
                Layout.fillWidth: true
                MicroText {
                    Layout.fillWidth: true
                    text: "Codex Micro"
                    font.pixelSize: Style.font.subtitle
                    font.bold: true
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                    Layout.minimumWidth: 0
                }
                Button {
                    fontSize: Style.font.caption
                    horizontalPadding: Style.space(2)
                    verticalPadding: Style.space(2)
                    text: "Clear"
                    tooltipText: "Clear every mapping in this layer"
                    enabled: !!root.micro && !root.micro.busy && !!root.selectedMapping
                    onClicked: root.micro.clearLayer(root.selectedLayer)
                }
                Button {
                    fontSize: Style.font.caption
                    horizontalPadding: Style.space(2)
                    verticalPadding: Style.space(2)
                    text: "Revert"
                    tooltipText: "Restore this layer’s last saved key setup"
                    enabled: !!root.micro && root.micro.canRevertLayer(root.selectedLayer)
                    onClicked: root.micro.revertLayer(root.selectedLayer)
                }
                RowLayout {
                    spacing: Style.space(4)
                    Item {
                        implicitWidth: Style.space(14)
                        implicitHeight: Style.space(16)
                        MicroText {
                            anchors.centerIn: parent
                            visible: !root.micro || !root.micro.saving
                            text: root.micro && root.micro.saveError ? "!" : "✓"
                            color: root.micro && root.micro.saveError ? Color.urgent : Color.foreground
                        }
                        MicroText {
                            anchors.centerIn: parent
                            visible: root.micro && root.micro.saving
                            text: "◌"
                            RotationAnimator on rotation { from: 0; to: 360; duration: 900; loops: Animation.Infinite; running: root.micro && root.micro.saving }
                        }
                    }
                    MicroText {
                        text: root.micro && root.micro.saveError ? "Not saved" : root.micro && root.micro.saving ? "Saving…" : "Saved"
                        font.pixelSize: Style.font.bodySmall
                        opacity: 0.65
                    }
                }
                MicroText {
                    text: root.connected ? root.state.battery + "%" + (root.state.is_charging ? " charging" : "") : (root.micro ? root.micro.connectionLabel : "Status unavailable")
                    font.pixelSize: Style.font.bodySmall
                    opacity: 0.65
                }
            }
            MicroText {
                visible: root.state.status === "disconnected"
                Layout.fillWidth: true
                text: "Connect your Micro by USB or Bluetooth."
                opacity: 0.65
            }
            Toggle {
                Layout.fillWidth: true
                label: "Quick Micro"
                description: "Double-click the dial to toggle Micro on any layer."
                titleSize: Style.font.bodySmall
                checked: root.config.quick_micro === true
                enabled: !!root.micro && !root.micro.busy
                onClicked: root.setQuickMicro(!checked)
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Style.spacing.md
                Repeater {
                    model: ["2", "3"]
                    Button {
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: Style.spacing.controlHeight
                        text: ""
                        readonly property string layerName: root.config.layers && root.config.layers[modelData] ? root.config.layers[modelData].name : "Layer"
                        color: activeFocus ? Style.focusFillFor(foreground, accent)
                            : selected ? Style.selectedFillFor(foreground, accent) : background
                        borderSpec: Border.controlSpec(activeFocus ? "focus" : selected && Border.controlHasWidth("selected") ? "selected" : "normal", foreground, accent)
                        MicroText {
                            anchors.fill: parent
                            anchors.leftMargin: Style.spacing.controlPaddingX
                            anchors.rightMargin: Style.spacing.controlPaddingX
                            text: parent.modelData + " · " + parent.layerName
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.NoWrap
                            elide: Text.ElideRight
                        }
                        selected: root.selectedLayer === modelData
                        bordered: true
                        focusable: true
                        onClicked: root.selectedLayer = modelData
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Style.spacing.md
                TextField {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: root.selectedMapping ? root.selectedMapping.name : ""
                    placeholderText: "Name this layer"
                    maximumLength: 40
                    selectByMouse: true
                    enabled: root.micro && root.selectedMapping !== null
                    onTextEdited: root.renameLayer(text)
                }

            }
            ShortcutPicker {
                id: appPicker
                Layout.fillWidth: true
                label: "App focus"
                placeholderText: "Search running apps…"
                options: [{value:"",label:"Any app"}].concat(root.micro && root.micro.apps ? root.micro.apps : [])
                value: root.selectedMapping && root.selectedMapping.app ? root.selectedMapping.app : ""
                triggerLabel: value || "Any app"
                enabled: !!root.micro && !root.micro.busy
                onChanged: value => root.assignApp(value)
            }
            ButtonGroup {
                options: root.controlOptions()
                value: root.selectedControl + ":" + root.selectedGesture
                fontSize: Style.font.bodySmall
                onChanged: value => root.selectControlOption(value)
            }
            ShortcutPicker {
                id: shortcutPicker
                Layout.fillWidth: true
                label: root.quickMicroReserved ? "Quick Micro" : "Key or shortcut"
                placeholderText: "Search keys and shortcuts…"
                options: [{value:"", label:"Unassigned"}].concat(root.micro ? root.micro.options.map(o => Object.assign({}, o, {label: Labels.shortLabel(o.label)})) : [])
                value: root.selectedBinding.action.kind === "key" ? "key:" + (root.selectedBinding.action.modifiers && root.selectedBinding.action.modifiers.length ? root.selectedBinding.action.modifiers.join("+") + ":" : "") + root.selectedBinding.action.key : root.selectedBinding.action.kind === "keybind" ? root.selectedBinding.action.binding : root.selectedBinding.action.kind === "noop" ? "" : "__custom"
                triggerLabel: root.quickMicroReserved ? "Open Micro · all layers" : ["key", "keybind"].indexOf(root.selectedBinding.action.kind) >= 0 ? Labels.shortLabel(root.selectedBinding.label) : root.selectedBinding.action.kind === "noop" ? "Unassigned" : Labels.shortLabel(root.selectedBinding.label)
                enabled: !!root.micro && !root.quickMicroReserved
                onChanged: value => root.selectBinding(value)
            }
            DeviceLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: width + 12
                bindings: root.mappings
                selectedControl: root.selectedControl
                selectedGesture: root.selectedGesture
                enabled: !!root.micro
                onChoose: control => root.selectedControl = control
            }
            RowLayout {
                visible: root.micro && root.micro.saveError !== ""
                Layout.fillWidth: true
                spacing: Style.spacing.md
                MicroText {
                    Layout.fillWidth: true
                    text: root.micro ? root.micro.saveError : ""
                    opacity: 0.65
                }
                Button {
                    visible: root.micro && root.micro.saveError !== ""
                    text: "Retry"
                    onClicked: { root.micro.saveError = ""; root.micro.savePending() }
                }
            }
        }
    }
}
