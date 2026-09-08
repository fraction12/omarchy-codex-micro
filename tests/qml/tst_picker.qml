import QtQuick
import QtQuick.Window
import Quickshell
import "Micro" as Micro

Window {
    width: 500; height: 600; visible: true
    property string gesture: "single"
    property var mappings: ({single:"enter",double:"backspace",hold:"space"})
    Micro.ShortcutPicker {
        id: picker
        width: 360
        value: mappings[gesture]
        options: [{value:"enter",label:"Enter"},{value:"backspace",label:"Backspace"},{value:"space",label:"Space"}]
        onChanged: function(value) {
            const next=Object.assign({},mappings)
            next[gesture]=value
            mappings=next
        }
    }
    function check(actual, expected, message) {
        if (actual !== expected) throw new Error(message+": expected "+expected+", got "+actual)
    }
    function findList(item,seen) {
        if (!item || seen.indexOf(item)>=0) return null
        seen.push(item)
        if (typeof item.selectCurrent === "function") return item
        const children=[...(item.children || []),...(item.data || []), item.contentItem]
        for (let child of children) { const found=findList(child,seen); if (found) return found }
        return null
    }
    function findSearch(item,seen) {
        if (!item || seen.indexOf(item)>=0) return null
        seen.push(item)
        if (typeof item.selectAll === "function" && item.placeholderText !== undefined) return item
        for (let child of [...(item.children || []),...(item.data || []),item.contentItem]) {
            const found=findSearch(child,seen)
            if (found) return found
        }
        return null
    }
    Timer {
        interval: 100; running: true
        onTriggered: {
            try {
                gesture="double"
                check(picker.value,"backspace","Double value")
                picker.open()
                const search=findSearch(picker,[])
                if (!search) throw new Error("Cannot find search field")
                search.text="AgjÉ"
                if (search.height-search.topPadding-search.bottomPadding < search.contentHeight)
                    throw new Error("Search glyphs clipped: available="+(search.height-search.topPadding-search.bottomPadding)+", text="+search.contentHeight)
                search.text=""
                const list=findList(picker,[])
                if (!list) throw new Error("Cannot find real dropdown list")
                list.currentIndex=2
                list.selectCurrent()
                check(mappings.double,"space","Selection saved to double")
                gesture="single"
                check(picker.value,"enter","Single must retain its own selection")
                gesture="hold"
                check(picker.value,"space","Hold selection")
                console.log("MICRO TEST PASS")
            } catch(e) { console.error("MICRO TEST FAIL: "+e) }
            Qt.quit()
        }
    }
}
