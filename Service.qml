import QtQuick
import Quickshell.Io

Item {
    id: root
    visible: false
    property var shell: null
    property var manifest: null
    readonly property string sourceDir: decodeURIComponent(Qt.resolvedUrl(".").toString().replace(/^file:\/\//, "")).replace(/\/$/, "")
    property var state: ({status: "checking", connected: null})
    readonly property string connectionLabel: state.status === "disconnected" ? "Disconnected"
        : state.status === "unresponsive" ? "Not responding"
        : state.status === "checking" ? "Checking…" : "Status unavailable"
    property int statusMaxAgeMs: 30000

    function acceptStatus(result) {
        if (result.status === "busy") return
        if (result.connected === true) {
            state = result
            lastError = ""
            statusExpiry.restart()
        } else {
            state = result.status ? result : {status: "unavailable", connected: null}
            lastError = result.error || ""
        }
    }
    function expireStatus() {
        if (state.connected === true || state.status === "checking") {
            state = {status: "unavailable", connected: null}
            lastError = ""
        }
    }
    property var mappings: ({})
    property var previousLayers: ({})
    property var pending: null
    readonly property var editConfig: pending || mappings
    property var options: []
    property var apps: []
    readonly property bool needsAppRouting: !!editConfig.layers && Object.values(editConfig.layers).some(layer => !!layer.app)
    property bool routingReady: false
    property string revision: ""
    property string lastError: ""
    property string saveError: ""
    readonly property bool busy: saveProcess.running
    readonly property bool saving: busy || pending !== null && saveError === ""
    property string submitted: ""

    function canRevertLayer(number) {
        if (busy || !mappings.layers) return false
        return JSON.stringify(editConfig.layers[number].bindings) !== JSON.stringify(mappings.layers[number].bindings)
            || Object.prototype.hasOwnProperty.call(previousLayers, number)
    }
    function clearLayer(number) {
        if (busy || !editConfig.layers) return
        const next = JSON.parse(JSON.stringify(editConfig))
        for (const control of Object.keys(next.layers[number].bindings))
            next.layers[number].bindings[control] = {label: "Unassigned", action: {kind: "noop"}}
        change(next)
    }
    function revertLayer(number) {
        if (!canRevertLayer(number)) return
        const next = JSON.parse(JSON.stringify(editConfig))
        const unsaved = JSON.stringify(next.layers[number].bindings) !== JSON.stringify(mappings.layers[number].bindings)
        next.layers[number].bindings = JSON.parse(JSON.stringify(unsaved ? mappings.layers[number].bindings : previousLayers[number]))
        change(next)
    }
    function change(config) {
        pending = config
        saveError = ""
        debounce.restart()
    }
    function refresh() {
        if (busy || pending !== null || statusProcess.running) return
        statusProcess.command = [sourceDir + "/scripts/micro", "status"]
        statusProcess.running = true
    }
    function loadEditor() {
        if (busy || pending !== null || editorProcess.running) return
        editorProcess.command = [sourceDir + "/scripts/micro", "editor-state"]
        editorProcess.running = true
    }
    function savePending() {
        if (pending === null || saveError !== "") return
        if (!["2", "3"].every(n => pending.layers[n].name.trim().length > 0)) {
            saveError = "Enter a layer name"
            return
        }
        if (busy || editorProcess.running || statusProcess.running) { debounce.restart(); return }
        submitted = JSON.stringify(pending)
        saveProcess.payload = JSON.stringify({config: pending, expected_sha256: revision})
        saveProcess.command = [sourceDir + "/scripts/micro", "save-config"]
        saveProcess.running = true
    }
    Process {
        id: appRouter
        command: [root.sourceDir + "/scripts/micro", "dispatch-server"]
        running: root.needsAppRouting
        stdout: SplitParser {
            onRead: function(data) {
                try { const result=JSON.parse(data); if (result.ready) root.routingReady=true; if (result.error) root.lastError=result.error }
                catch(e) { root.lastError="Cannot read app dispatcher status" }
            }
        }
        onExited: { root.routingReady=false; if (root.needsAppRouting) routerRestart.restart() }
    }
    Timer { id: routerRestart; interval: 2000; onTriggered: if (root.needsAppRouting) appRouter.running=true }
    Component.onCompleted: { refresh(); loadEditor() }
    Timer { id: statusExpiry; interval: root.statusMaxAgeMs; running: true; onTriggered: root.expireStatus() }
    Timer { id: debounce; interval: 600; onTriggered: root.savePending() }
    Timer { interval: 10000; running: !root.busy; repeat: true; onTriggered: root.refresh() }
    Process {
        id: statusProcess
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.acceptStatus(JSON.parse(text)) }
                catch (e) { root.acceptStatus({status: "unavailable", connected: null, error: "Cannot read Micro status"}) }
            }
        }
    }
    Process {
        id: editorProcess
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text)
                    if (result.error) { root.lastError = result.error; return }
                    root.previousLayers = result.previous_layers || ({})
                    root.mappings = result.config
                    root.options = result.options
                    root.apps = result.apps || []
                    root.revision = result.revision
                } catch (e) { root.lastError = "Cannot load mappings" }
            }
        }
    }
    Process {
        id: saveProcess
        property string payload: ""
        onExited: root.refresh()
        stdinEnabled: true
        onStarted: { write(payload + "\n"); payload = "" }
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text)
                    if (result.error) { root.saveError = result.error; return }
                    root.previousLayers = result.previous_layers || ({})
                    root.mappings = result.config
                    root.revision = result.revision
                    if (JSON.stringify(root.pending) === root.submitted) root.pending = null
                    root.submitted = ""
                    root.debounceNext()
                } catch (e) { root.saveError = "Could not save. Check the Micro connection." }
            }
        }
    }
    function debounceNext() { if (pending !== null) debounce.restart() }
}
