import QtQuick
import Quickshell
import "Backend" as Backend
Item {
    property int stage: 0
    Backend.Service { id: service; statusMaxAgeMs: 120 }
    function check(value, message) { if (!value) throw new Error(message) }
    Timer {
        interval: 20; repeat: true; running: true
        onTriggered: {
            try {
                if (stage === 0 && service.revision && service.state.connected) {
                    // Block further fixture polls while exercising the actual service.
                    service.pending = service.mappings
                    service.acceptStatus({status: "connected", connected: true, battery: 98})
                    service.acceptStatus({status: "busy", connected: null})
                    check(service.state.connected && service.state.battery === 98, "Busy discarded last status")
                    stage = 1
                } else if (stage === 1 && service.state.status === "unavailable") {
                    check(service.connectionLabel === "Status unavailable", "Stale status mislabeled")
                    service.acceptStatus({status: "busy", connected: null})
                    check(service.state.status === "unavailable", "Busy revived stale state")
                    service.acceptStatus({status: "connected", connected: true, battery: 97})
                    check(service.state.connected && service.state.battery === 97, "Recovery failed")
                    service.acceptStatus({status: "disconnected", connected: false})
                    check(service.connectionLabel === "Disconnected", "Removal hidden")
                    service.acceptStatus({status: "busy", connected: null})
                    check(service.connectionLabel === "Disconnected", "Busy revived disconnected state")
                    service.acceptStatus({status: "unresponsive", connected: null})
                    check(service.connectionLabel === "Not responding", "Timeout mislabeled")
                    service.acceptStatus({error: "bad response"})
                    check(service.connectionLabel === "Status unavailable", "Malformed status mislabeled")
                    service.state = {status: "checking", connected: null}
                    service.acceptStatus({status: "busy", connected: null})
                    service.expireStatus()
                    check(service.connectionLabel === "Status unavailable", "Initial busy never expires")
                    console.log("MICRO TEST PASS"); Qt.quit(); stage = 2
                }
            } catch(e) { console.error("MICRO TEST FAIL: " + e); Qt.quit(); stage = 2 }
        }
    }
    Timer { interval: 2000; running: true; onTriggered: { console.error("MICRO TEST FAIL: status timeout"); Qt.quit() } }
}
