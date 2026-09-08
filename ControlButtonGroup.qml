import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

RowLayout {
    id: root
    property var options: []
    property string value: ""
    property real fontSize: Style.font.bodySmall
    property int focusedIndex: -1
    signal changed(string value)

    spacing: Style.spacing.md
    activeFocusOnTab: true
    onActiveFocusChanged: focusedIndex = activeFocus ? Math.max(0, options.findIndex(o => o.value === value)) : -1
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Left || event.key === Qt.Key_H) {
            focusedIndex = Math.max(0, focusedIndex - 1)
        } else if (event.key === Qt.Key_Right || event.key === Qt.Key_L) {
            focusedIndex = Math.min(options.length - 1, focusedIndex + 1)
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            if (focusedIndex >= 0 && focusedIndex < options.length) changed(options[focusedIndex].value)
        } else {
            return
        }
        event.accepted = true
    }

    Repeater {
        model: root.options
        Button {
            required property var modelData
            required property int index
            Layout.fillWidth: true
            text: modelData.label
            tooltipText: modelData.tooltip || ""
            selected: modelData.value === root.value
            bordered: true
            hasCursor: root.activeFocus && root.focusedIndex === index
            fontSize: root.fontSize
            onClicked: root.changed(modelData.value)
        }
    }
}
