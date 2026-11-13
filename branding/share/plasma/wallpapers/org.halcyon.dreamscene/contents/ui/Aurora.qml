import QtQuick
import QtQuick.Shapes

// Northern lights: slow green and violet ribbons over a starry night and dark hills.
Item {
    id: scene
    property bool running: true
    property real speed: 1.0
    readonly property color accent: "#3fd68a"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#01040c" }
            GradientStop { position: 0.55; color: "#06162b" }
            GradientStop { position: 1; color: "#0d2a3a" }
        }
    }
    Repeater {                                   // stars, placed by a fixed pseudo-random sequence
        model: 140
        Rectangle {
            readonly property real r1: ((index * 7919) % 1000) / 1000
            readonly property real r2: ((index * 104729) % 997) / 997
            x: r1 * scene.width
            y: r2 * scene.height * 0.7
            width: index % 9 === 0 ? 2.4 : 1.4
            height: width
            radius: width / 2
            color: "white"
            opacity: 0.35 + 0.5 * ((index * 31) % 10) / 10
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                paused: !scene.running
                NumberAnimation { to: 0.15; duration: (2200 + (index * 137) % 3000) / scene.speed; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0.9; duration: (2200 + (index * 211) % 3000) / scene.speed; easing.type: Easing.InOutSine }
            }
        }
    }
    Ribbon {
        width: parent.width; height: parent.height * 0.5; y: parent.height * 0.05
        rotation: -7; color: "#2fe08a"; amplitude: 70; thickness: 120; period: 1100
        seconds: 55 / scene.speed; running: scene.running; opacity: 0.75
    }
    Ribbon {
        width: parent.width; height: parent.height * 0.5; y: parent.height * 0.14
        rotation: -4; color: "#22c4c8"; amplitude: 50; thickness: 80; period: 800
        seconds: 38 / scene.speed; running: scene.running; opacity: 0.55
    }
    Ribbon {
        width: parent.width; height: parent.height * 0.4; y: parent.height * 0.0
        rotation: -10; color: "#9a5cf0"; amplitude: 40; thickness: 60; period: 1300
        seconds: 70 / scene.speed; running: scene.running; opacity: 0.4
    }
    Shape {                                      // the hills
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: -1
            fillColor: "#02070d"
            PathSvg {
                path: {
                    const w = scene.width, h = scene.height
                    return `M 0 ${h * 0.82} C ${w * 0.18} ${h * 0.72} ${w * 0.3} ${h * 0.8} ${w * 0.46} ${h * 0.78}`
                         + ` C ${w * 0.62} ${h * 0.76} ${w * 0.78} ${h * 0.68} ${w} ${h * 0.76} L ${w} ${h} L 0 ${h} Z`
                }
            }
        }
    }
}
