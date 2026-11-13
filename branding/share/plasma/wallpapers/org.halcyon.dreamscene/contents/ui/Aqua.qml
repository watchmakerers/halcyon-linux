import QtQuick
import QtQuick.Particles

// Underwater: sunbeams from the surface, drifting light and bubbles rising.
Item {
    id: scene
    property bool running: true
    property real speed: 1.0
    readonly property color accent: "#2fa8e8"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#3ab8ee" }
            GradientStop { position: 0.35; color: "#0c6fb8" }
            GradientStop { position: 1; color: "#021a3c" }
        }
    }
    Repeater {                                   // sunbeams, swaying a little
        model: 6
        Rectangle {
            x: scene.width * (0.08 + index * 0.17)
            y: -scene.height * 0.1
            width: scene.width * (0.05 + (index % 3) * 0.025)
            height: scene.height * 1.2
            transformOrigin: Item.Top
            rotation: 14 + index * 2
            gradient: Gradient {
                GradientStop { position: 0; color: Qt.rgba(1, 1, 1, 0.22) }
                GradientStop { position: 1; color: "transparent" }
            }
            SequentialAnimation on rotation {
                loops: Animation.Infinite
                paused: !scene.running
                NumberAnimation { to: 18 + index * 2; duration: (7000 + index * 900) / scene.speed; easing.type: Easing.InOutSine }
                NumberAnimation { to: 12 + index * 2; duration: (7000 + index * 700) / scene.speed; easing.type: Easing.InOutSine }
            }
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                paused: !scene.running
                NumberAnimation { to: 0.4; duration: (5000 + index * 600) / scene.speed; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: (5000 + index * 800) / scene.speed; easing.type: Easing.InOutSine }
            }
        }
    }
    Repeater {                                   // caustic light patches near the surface
        model: 7
        Glow {
            size: scene.width * (0.18 + (index % 3) * 0.06)
            color: Qt.rgba(0.75, 0.95, 1, 0.22)
            x: scene.width * ((index * 0.17) % 1) - size / 2
            y: scene.height * (0.02 + (index % 4) * 0.07)
            transform: Translate { id: drift }
            SequentialAnimation {
                running: true
                loops: Animation.Infinite
                paused: !scene.running
                NumberAnimation { target: drift; property: "x"; from: 0; to: scene.width * 0.06; duration: (9000 + index * 1100) / scene.speed; easing.type: Easing.InOutSine }
                NumberAnimation { target: drift; property: "x"; from: scene.width * 0.06; to: 0; duration: (9000 + index * 1300) / scene.speed; easing.type: Easing.InOutSine }
            }
        }
    }
    ParticleSystem { id: sys; running: scene.running }
    Emitter {
        system: sys
        anchors.bottom: parent.bottom
        width: parent.width; height: 10
        emitRate: 5 * scene.speed
        lifeSpan: 14000 / scene.speed
        size: 22; sizeVariation: 16
        velocity: PointDirection { y: -scene.height / 13 * scene.speed; yVariation: 15; xVariation: 6 }
    }
    Wander { system: sys; anchors.fill: parent; xVariance: 30; pace: 40 }
    ItemParticle {
        system: sys
        fade: false
        delegate: Rectangle {                      // a bubble: clear middle, bright rim, a highlight
            width: 14 + Math.random() * 18
            height: width
            radius: width / 2
            color: Qt.rgba(1, 1, 1, 0.06)
            border.color: Qt.rgba(1, 1, 1, 0.55)
            border.width: 1.2
            Rectangle {
                x: parent.width * 0.22; y: parent.height * 0.18
                width: parent.width * 0.3; height: width; radius: width / 2
                color: Qt.rgba(1, 1, 1, 0.7)
            }
        }
    }
}
