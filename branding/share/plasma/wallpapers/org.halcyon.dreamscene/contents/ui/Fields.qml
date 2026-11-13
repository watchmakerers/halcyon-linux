import QtQuick

// Bright swooping bands of light across blue and green, in the spirit of
// the Vista-era desktop.
Item {
    id: scene
    property bool running: true
    property real speed: 1.0
    readonly property color accent: "#2a9fd6"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#0a3f74" }
            GradientStop { position: 0.5; color: "#1a86c8" }
            GradientStop { position: 0.85; color: "#2bb39a" }
            GradientStop { position: 1; color: "#1f8a4a" }
        }
    }
    Glow {
        size: scene.width * 0.7
        color: Qt.rgba(0.85, 1, 0.95, 0.35)
        x: scene.width * 0.45; y: scene.height * 0.25
        SequentialAnimation on opacity {
            loops: Animation.Infinite
            paused: !scene.running
            NumberAnimation { to: 0.55; duration: 9000 / scene.speed; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0; duration: 9000 / scene.speed; easing.type: Easing.InOutSine }
        }
    }
    Ribbon {
        width: parent.width * 1.2; height: parent.height * 0.6; x: -parent.width * 0.1; y: parent.height * 0.35
        rotation: -12; color: "#c8fff0"; amplitude: 90; thickness: 70; period: 1400
        seconds: 60 / scene.speed; running: scene.running; opacity: 0.55; blur: 0.7
    }
    Ribbon {
        width: parent.width * 1.2; height: parent.height * 0.6; x: -parent.width * 0.1; y: parent.height * 0.42
        rotation: -9; color: "#7ff0ff"; amplitude: 70; thickness: 40; period: 1000
        seconds: 42 / scene.speed; running: scene.running; opacity: 0.6; blur: 0.5
    }
    Ribbon {
        width: parent.width * 1.2; height: parent.height * 0.6; x: -parent.width * 0.1; y: parent.height * 0.5
        rotation: -14; color: "#b6ff7a"; amplitude: 110; thickness: 110; period: 1700
        seconds: 75 / scene.speed; running: scene.running; opacity: 0.35; blur: 1.0
    }
    Ribbon {
        width: parent.width * 1.2; height: parent.height * 0.5; x: -parent.width * 0.1; y: parent.height * 0.3
        rotation: -6; color: "#ffffff"; amplitude: 40; thickness: 14; period: 900
        seconds: 30 / scene.speed; running: scene.running; opacity: 0.7; blur: 0.25
    }
}
