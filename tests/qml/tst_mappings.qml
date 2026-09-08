import QtQuick
import QtQuick.Window
import Quickshell
import "Micro" as Micro

Window {
    width: 600; height: 800; visible: false
    QtObject {
        id: service
        property var state: ({connected:true,battery:80})
        property var editConfig: ({version:1,profile:0,layers:{"2":{name:"PC",bindings:{key00:{label:"Enter",action:{kind:"key",key:"KC_ENT"}},key01:{label:"Space",action:{kind:"key",key:"KC_SPC"}}}},"3":{name:"Work",bindings:{key00:{label:"Tab",action:{kind:"key",key:"KC_TAB"}}}}}})
        property var options: [
            {value:"key:KC_ENT",description:"Enter",label:"Enter",action:{kind:"key",key:"KC_ENT"}},
            {value:"key:KC_BSPC",description:"Backspace",label:"Backspace",action:{kind:"key",key:"KC_BSPC"}},
            {value:"key:KC_SPC",description:"Space",label:"Space",action:{kind:"key",key:"KC_SPC"}},
            {value:"key:KC_TAB",description:"Tab",label:"Tab",action:{kind:"key",key:"KC_TAB"}}]
        property bool busy: false
        function canRevertLayer(number) { return false }
        property bool saving: false
        property string saveError: ""
        property string lastError: ""
        function change(next) { editConfig=next }
        function refresh() {}
        function loadEditor() {}
    }
    QtObject { id: shellMock; function serviceFor(id) { return service } }
    QtObject {
        id: barMock
        property var shell: shellMock
        property bool vertical: false
        property string position: "top"
        property int barSize: 24
        property string fontFamily: "monospace"
        property color barForeground: "white"
        property color urgent: "red"
        property bool foregroundAnimationEnabled: false
        function showTooltip(item,text) {}
        function hideTooltip(item) {}
    }
    Micro.BarWidget { id: widget; bar: barMock }
    function check(actual,expected,message) { if (actual!==expected) throw new Error(message+": expected "+expected+", got "+actual) }
    Timer {
        interval: 100; running: true
        onTriggered: {
            try {
                widget.setQuickMicro(true)
                check(service.editConfig.quick_micro,true,"Quick Micro saves globally")
                widget.selectedControl="dial_press"
                widget.selectedGesture="double"
                check(widget.quickMicroReserved,true,"Dial double reserved")
                const beforeQuickChoice=JSON.stringify(service.editConfig)
                widget.selectBinding("key:KC_BSPC")
                check(JSON.stringify(service.editConfig),beforeQuickChoice,"Reserved double cannot be overwritten")
                widget.selectedLayer="3"
                check(widget.quickMicroReserved,true,"Reserved on other layer")
                widget.setQuickMicro(false)
                check(widget.quickMicroReserved,false,"Disable restores editing")
                widget.selectedLayer="2"
                widget.selectedControl="key00"
                const untouched = JSON.stringify(service.editConfig.layers["2"])
                widget.selectedLayer="3"
                widget.assignApp("t3code")
                check(service.editConfig.layers["3"].app,"t3code","App assigned")
                check(JSON.stringify(service.editConfig.layers["2"]),untouched,"App selection preserved other layer")
                widget.assignApp("")
                check(service.editConfig.layers["3"].app,undefined,"Any app clears target")
                widget.selectedLayer="2"
                check(widget.selectedBinding.action.key,"KC_ENT","Initial single")
                widget.selectedGesture="double"
                widget.selectBinding("key:KC_BSPC")
                check(widget.selectedBinding.action.key,"KC_BSPC","Double changed")
                widget.selectedGesture="single"
                check(widget.selectedBinding.action.key,"KC_ENT","Single remains Enter")
                widget.selectedGesture="tap_hold"
                widget.selectBinding("key:KC_SPC")
                widget.selectedGesture="double"
                check(widget.selectedBinding.action.key,"KC_BSPC","Double remains Backspace")
                widget.selectedLayer="3"
                check(widget.selectedBinding.action.kind,"noop","Other layer double unassigned")
                widget.selectedGesture="single"
                check(widget.selectedBinding.action.key,"KC_TAB","Other layer single")
                widget.selectedLayer="2"
                widget.selectedControl="key01"
                check(widget.selectedBinding.action.key,"KC_SPC","Other key single")
                widget.selectedControl="key00"
                widget.selectedGesture="tap_hold"
                widget.selectBinding("key:KC_TAB")
                check(widget.selectedBinding.action.key,"KC_TAB","Click hold assignment")
                widget.selectedGesture="tap_hold"
                check(widget.selectedBinding.action.key,"KC_TAB","Click hold updated")
                widget.selectedGesture="tap_hold"
                check(widget.selectedBinding.action.key,"KC_TAB","Click hold survives switching")
                widget.selectedGesture="double"
                widget.selectBinding("")
                check(widget.selectedBinding.action.kind,"noop","Clear only double")
                widget.selectedGesture="tap_hold"
                check(widget.selectedBinding.action.key,"KC_TAB","Click hold survives clearing double")
                widget.selectedGesture="single"
                check(widget.selectedBinding.action.key,"KC_ENT","Single survives clearing double")
                widget.selectedControl="dial_press"
                check(widget.controlOptions().length,5,"Dial has one set of five options")
                widget.selectControlOption("dial_left:single")
                check(widget.selectedControl,"dial_left","Dial left selected")
                check(widget.controlOptions().length,5,"Dial row stays stable for rotation")
                widget.selectControlOption("dial_press:tap_hold")
                check(widget.selectedControl,"dial_press","Dial press selected")
                check(widget.selectedGesture,"tap_hold","Dial click hold selected")
                widget.selectedControl="stick_up"
                check(widget.controlOptions().length,4,"Joystick has one direction row")
                widget.selectControlOption("stick_right:single")
                check(widget.selectedControl,"stick_right","Joystick right selected")
                console.log("MICRO TEST PASS")
            } catch(e) { console.error("MICRO TEST FAIL: "+e) }
            Qt.quit()
        }
    }
}
