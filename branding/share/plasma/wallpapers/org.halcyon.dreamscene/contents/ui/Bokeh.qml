import QtQuick

// Out-of-focus lights drifting on deep blue.
Item {
    id: scene
    property bool running: true
    property real speed: 1.0
    readonly property color accent: "#3c9ae8"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: "#06214d" }
            GradientStop { position: 0.6; color: "#0f4f9a" }
            GradientStop { position: 1; color: "#3aa8e8" }
        }
    }
    Repeater {
        model: 30
        Glow {
            id: g
            readonly property real r1: ((index * 7919) % 1000) / 1000
            readonly property real r2: ((index * 6151) % 991) / 991
            size: scene.height * (0.08 + 0.22 * ((index * 37) % 10) / 10)
            color: [Qt.rgba(0.6, 0.85, 1, 0.5), Qt.rgba(1, 1, 1, 0.4), Qt.rgba(0.4, 1, 0.95, 0.35),
                    Qt.rgba(0.55, 0.6, 1, 0.4)][index % 4]
            x: r1 * scene.width - size / 2
            y: r2 * scene.height - size / 2
            readonly property real dx: scene.width * (0.03 + r2 * 0.05)
            readonly property real dy: scene.height * 0.04
            transform: Translate { id: drift }
            SequentialAnimation {
                running: true
                loops: Animation.Infinite
                paused: !scene.running
                NumberAnimation { target: drift; property: "x"; from: 0; to: g.dx; duration: (14000 + index * 900) / scene.speed; easing.type: Easing.InOutSine }
                NumberAnimation { target: drift; property: "x"; from: g.dx; to: 0; duration: (14000 + index * 700) / scene.speed; easing.type: Easing.InOutSine }
            }
            SequentialAnimation {
                running: true
                loops: Animation.Infinite
                paused: !scene.running
                NumberAnimation { target: drift; property: "y"; from: 0; to: -g.dy; duration: (11000 + index * 500) / scene.speed; easing.type: Easing.InOutSine }
                NumberAnimation { target: drift; property: "y"; from: -g.dy; to: 0; duration: (11000 + index * 800) / scene.speed; easing.type: Easing.InOutSine }
            }
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                paused: !scene.running
                NumberAnimation { to: 0.35; duration: (6000 + index * 400) / scene.speed; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: (6000 + index * 300) / scene.speed; easing.type: Easing.InOutSine }
            }
        }
    }
}
