import QtQuick
import Quickshell
import "Backend" as Backend
Item {
    property int stage: 0
    property string savedLayer: ""
    property string otherLayer: ""
    Backend.Service { id: service }
    Timer {
        interval: 30; repeat: true; running: true
        onTriggered: {
            try {
                if (stage===0 && service.revision) {
                    const c=JSON.parse(JSON.stringify(service.editConfig))
                    c.layers["2"].bindings.key00.gestures={double:{label:"Backspace",action:{kind:"key",key:"KC_BSPC"}}}
                    service.change(c);stage=1
                } else if (stage===1 && service.busy) {
                    const c=JSON.parse(JSON.stringify(service.editConfig))
                    c.layers["2"].bindings.key00.gestures.tap_hold={label:"Space",action:{kind:"key",key:"KC_SPC"}}
                    c.layers["3"].bindings.key01={label:"Tab",action:{kind:"key",key:"KC_TAB"}}
                    service.change(c);stage=2
                } else if (stage===2 && !service.saving) {
                    if (service.saveError) throw new Error(service.saveError)
                    const c=service.mappings
                    if (c.layers["2"].bindings.key00.action.key!=="KC_ENT" || c.layers["2"].bindings.key00.gestures.double.action.key!=="KC_BSPC" || c.layers["2"].bindings.key00.gestures.tap_hold.action.key!=="KC_SPC" || c.layers["3"].bindings.key01.action.key!=="KC_TAB") throw new Error("Queued save lost or crossed a mapping")
                    savedLayer=JSON.stringify(c.layers["2"])
                    otherLayer=JSON.stringify(c.layers["3"])
                    service.clearLayer("2")
                    if (!service.canRevertLayer("2")) throw new Error("Unsaved clear cannot revert")
                    service.revertLayer("2")
                    if (JSON.stringify(service.editConfig.layers["2"])!==savedLayer) throw new Error("Unsaved revert lost mappings")
                    service.clearLayer("2");stage=3
                } else if (stage===3 && !service.saving) {
                    if (service.saveError) throw new Error(service.saveError)
                    if (Object.values(service.mappings.layers["2"].bindings).some(b => b.action.kind!=="noop" || b.gestures)) throw new Error("Clear left an action or gesture")
                    if (JSON.stringify(service.mappings.layers["3"])!==otherLayer) throw new Error("Clear changed other layer")
                    if (!service.canRevertLayer("2")) throw new Error("Saved clear cannot revert")
                    service.revertLayer("2");stage=4
                } else if (stage===4 && !service.saving) {
                    if (service.saveError) throw new Error(service.saveError)
                    if (JSON.stringify(service.mappings.layers["2"])!==savedLayer) throw new Error("Saved revert lost mappings")
                    if (JSON.stringify(service.mappings.layers["3"])!==otherLayer) throw new Error("Revert changed other layer")
                    console.log("MICRO TEST PASS");Qt.quit();stage=5
                }
            } catch(e) { console.error("MICRO TEST FAIL: "+e);Qt.quit();stage=5 }
        }
    }
    Timer { interval: 10000; running: true; onTriggered: {console.error("MICRO TEST FAIL: autosave timeout");Qt.quit()} }
}
