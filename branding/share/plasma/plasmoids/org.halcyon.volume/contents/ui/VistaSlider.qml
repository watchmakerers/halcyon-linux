import QtQuick

// A vertical volume slider the Vista way: a thin inset track that fills with
// blue from the bottom and a glossy pill thumb. value is 0-100.
Item {
    id: slider
    property real value: 0
    property bool dimmed: false          // muted: the fill goes grey
    signal moved(real value)

    implicitWidth: 34
    implicitHeight: 160

    readonly property real pad: 7        // half the thumb's height, so it never leaves the box
    readonly property real span: height - pad * 2
    readonly property real thumbY: pad + span * (1 - value / 100)

    function setFromY(y) {
        const v = Math.max(0, Math.min(100, Math.round((1 - (y - pad) / span) * 100)))
        if (v !== value)
            moved(v)
    }

    // tick marks either side, every 10%
    Repeater {
        model: 11
        Item {
            y: slider.pad + slider.span * index / 10
            width: slider.width; height: 1
            Rectangle { x: 2; width: index % 5 === 0 ? 6 : 4; height: 1; color: "#7a8ea6"; opacity: 0.7 }
            Rectangle { x: slider.width - width - 2; width: index % 5 === 0 ? 6 : 4; height: 1; color: "#7a8ea6"; opacity: 0.7 }
        }
    }

    Rectangle {                          // the inset track
        id: track
        anchors.horizontalCenter: parent.horizontalCenter
        y: slider.pad - 2
        width: 6
        height: slider.span + 4
        radius: 3
        border.color: "#46566a"
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "#1c2632" }
            GradientStop { position: 1; color: "#3a4a5e" }
        }
        Rectangle {                      // the filled part
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 1 }
            height: Math.max(0, slider.span * slider.value / 100 + 2)
            radius: 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: slider.dimmed ? "#8a96a4" : "#2f9bf0" }
                GradientStop { position: 0.5; color: slider.dimmed ? "#c4ccd6" : "#9fe0ff" }
                GradientStop { position: 1; color: slider.dimmed ? "#7a8694" : "#1a74c8" }
            }
        }
    }

    Rectangle {                          // the thumb
        id: thumb
        anchors.horizontalCenter: parent.horizontalCenter
        y: slider.thumbY - height / 2
        width: 22
        height: 12
        radius: 6
        border.color: area.pressed ? "#0d4a8a" : "#2a5a8c"
        gradient: Gradient {
            GradientStop { position: 0; color: area.containsMouse || area.pressed ? "#ffffff" : "#f2f8ff" }
            GradientStop { position: 0.5; color: area.containsMouse || area.pressed ? "#cbe9ff" : "#c9dcf0" }
            GradientStop { position: 0.51; color: area.containsMouse || area.pressed ? "#8fd0ff" : "#a6bfdc" }
            GradientStop { position: 1; color: area.containsMouse || area.pressed ? "#c8ecff" : "#dbe7f4" }
        }
        Rectangle {                      // gloss line
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 2 }
            height: 1
            color: "white"
            opacity: 0.8
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true
        onPressed: (mouse) => slider.setFromY(mouse.y)
        onPositionChanged: (mouse) => { if (pressed) slider.setFromY(mouse.y) }
        onWheel: (wheel) => {
            const step = wheel.angleDelta.y > 0 ? 2 : -2
            slider.moved(Math.max(0, Math.min(100, Math.round(slider.value) + step)))
        }
    }

    Accessible.role: Accessible.Slider
    Accessible.name: "Volume"
    focus: true
    Keys.onUpPressed: moved(Math.min(100, Math.round(value) + 2))
    Keys.onDownPressed: moved(Math.max(0, Math.round(value) - 2))
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_PageUp) { moved(Math.min(100, Math.round(value) + 10)); event.accepted = true }
        else if (event.key === Qt.Key_PageDown) { moved(Math.max(0, Math.round(value) - 10)); event.accepted = true }
    }
}
