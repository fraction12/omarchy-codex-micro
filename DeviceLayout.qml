import QtQuick
import qs.Commons
import "DisplayLabels.js" as Labels

Rectangle {
    id: device
    property var bindings: ({})
    property string selectedControl: ""
    property string selectedGesture: "single"
    signal choose(string control)
    function binding(control) {
        const base = bindings[control] || {label: "Unassigned", action: {kind: "noop"}}
        return control === selectedControl && selectedGesture !== "single"
            ? (base.gestures || {})[selectedGesture] || {label: "Unassigned", action: {kind: "noop"}}
            : base
    }
    function icon(control) { return Labels.keyIcon(binding(control)) }
    function label(control) { return Labels.keyLabel(binding(control).label) }
    implicitHeight: width + 12
    radius: 28
    color: Qt.alpha(Color.foreground, 0.07)
    border.color: Qt.alpha(Color.foreground, 0.25)
    border.width: 2
    readonly property real unit: (width - 48) / 4

    Rectangle {
        anchors.fill: parent; anchors.margins: 12
        radius: 19; color: "transparent"
        border.color: Qt.alpha(Color.foreground, 0.15)
    }
    Repeater {
        model: [0, 1, 2, 3]
        Rectangle {
            required property int modelData
            x: modelData % 2 === 0 ? 19 : device.width - 27
            y: modelData < 2 ? 19 : device.height - 27
            width: 8; height: 8; radius: 4
            color: Qt.alpha(Color.foreground, 0.35)
        }
    }
    MicroText {
        anchors.top: parent.top; anchors.topMargin: 9; anchors.horizontalCenter: parent.horizontalCenter
        text: "↑"; color: Color.foreground; opacity: 0.5
    }
    // Actual cap positions: dial, two agent keys, joystick; four keys;
    // four command keys; touch sensor, a two-switch microphone cap, voice key.
    Repeater {
        model: [
            {control:"key00", col:1, row:0}, {control:"key01", col:2, row:0},
            {control:"key02", col:0, row:1}, {control:"key03", col:1, row:1},
            {control:"key04", col:2, row:1}, {control:"key05", col:3, row:1},
            {control:"key06", col:0, row:2}, {control:"key07", col:1, row:2},
            {control:"key08", col:2, row:2}, {control:"key09", col:3, row:2},
            {control:"key10", col:1, row:3, wide:true},
            {control:"key12", col:3, row:3}
        ]
        Rectangle {
            required property var modelData
            x: 24 + modelData.col * device.unit
            y: 30 + modelData.row * device.unit
            width: device.unit * (modelData.wide ? 2 : 1) - 6
            height: device.unit - 8
            radius: 13
            color: Qt.alpha(Color.foreground, modelData.row < 2 ? 0.08 : 0.16)
            border.color: device.selectedControl === modelData.control ? Color.accent : Qt.alpha(Color.foreground, 0.24)
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: device.choose(parent.modelData.control) }
            MicroText {
                anchors.top: parent.top; anchors.topMargin: 8
                anchors.horizontalCenter: parent.horizontalCenter
                readonly property var mappedIcon: device.icon(parent.modelData.control)
                text: mappedIcon.text
                font.family: mappedIcon.font || Style.font.family
                font.pixelSize: 17
                color: device.selectedControl === parent.modelData.control ? Color.accent : Color.foreground
            }
            MicroText {
                anchors.left: parent.left; anchors.right: parent.right
                anchors.top: parent.top; anchors.bottom: parent.bottom
                anchors.leftMargin: 8; anchors.rightMargin: 8; anchors.topMargin: 27; anchors.bottomMargin: 7
                text: device.label(parent.modelData.control)
                color: Color.foreground; font.pixelSize: Style.font.caption
                horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
                clip: true
            }
        }
    }
    Rectangle {
        x: 24; y: 30; width: device.unit - 8; height: width; radius: width / 2
        color: Qt.alpha(Color.foreground, 0.18)
        border.color: device.selectedControl.indexOf("dial_") === 0 ? Color.accent : Qt.alpha(Color.foreground, 0.4)
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: device.choose("dial_press") }
        Rectangle {
            width: 3; height: 13; radius: 1; color: Color.accent
            anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: 5
        }
        MicroText {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 17
            readonly property var mappedIcon: device.icon("dial_press")
            text: mappedIcon.text
            font.family: mappedIcon.font || Style.font.family
            font.pixelSize: 15
        }
        MicroText {
            anchors.fill: parent; anchors.margins: 11; anchors.topMargin: 35
            text: device.label("dial_press")
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            color: Color.foreground; font.pixelSize: Style.font.caption
            wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight; clip: true
        }
    }
    Rectangle {
        x: 24 + 3 * device.unit; y: 30; width: device.unit - 8; height: width; radius: 12
        color: Qt.alpha(Color.foreground, 0.06)
        border.color: device.selectedControl.indexOf("stick_") === 0 ? Color.accent : "transparent"
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: device.choose("stick_up") }
        Rectangle {
            anchors.centerIn: parent; width: parent.width * 0.77; height: width; radius: width / 2
            color: Qt.alpha(Color.foreground, 0.2)
            MicroText { anchors.centerIn: parent; text: "↑\n← ● →\n↓"; color: Color.foreground; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
        }
    }
    Column {
        x: 24; y: 30 + 3 * device.unit; width: device.unit - 8; spacing: 5
        Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 28; height: 28; radius: 18; color: Qt.alpha(Color.foreground, 0.3); border.color: Color.accent }
        MicroText { width: parent.width; text: "Layer"; color: Color.foreground; opacity: 0.65; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 10 }
    }
    MicroText {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 12; anchors.horizontalCenter: parent.horizontalCenter
        text: "CODEX MICRO"; color: Color.foreground; opacity: 0.4; font.pixelSize: Style.font.caption; font.letterSpacing: 3
    }
}
