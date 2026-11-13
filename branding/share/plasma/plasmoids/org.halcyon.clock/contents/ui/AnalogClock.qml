import QtQuick

// A glossy analog clock face. The face is painted once; the hands are plain
// rotated rectangles, so moving them costs nothing. Set h/m/s (s may be
// fractional for a smooth sweep).
Item {
    id: clock
    property real h: 10
    property real m: 10
    property real s: 0
    property bool seconds: true
    property string label: ""
    readonly property real d: Math.min(width, height)

    Canvas {
        id: face
        anchors.centerIn: parent
        width: clock.d; height: clock.d
        onWidthChanged: requestPaint()
        onPaint: {
            const c = getContext("2d"), r = width / 2
            c.reset()
            // chrome rim
            let g = c.createLinearGradient(0, 0, 0, width)
            g.addColorStop(0, "#f8fbff"); g.addColorStop(0.5, "#9fb3c8"); g.addColorStop(1, "#5d7086")
            c.fillStyle = g
            c.beginPath(); c.arc(r, r, r - 0.5, 0, Math.PI * 2); c.fill()
            c.strokeStyle = "#3d4d60"; c.lineWidth = 1; c.stroke()
            // dial
            g = c.createRadialGradient(r, r * 0.8, r * 0.1, r, r, r * 0.9)
            g.addColorStop(0, "#ffffff"); g.addColorStop(0.7, "#eef4fa"); g.addColorStop(1, "#c9d8e8")
            c.fillStyle = g
            c.beginPath(); c.arc(r, r, r * 0.88, 0, Math.PI * 2); c.fill()
            c.strokeStyle = "rgba(60, 80, 110, 0.5)"; c.stroke()
            // ticks
            for (let i = 0; i < 60; i++) {
                const a = i / 60 * Math.PI * 2, big = i % 5 === 0
                const r1 = r * (big ? 0.68 : 0.76), r2 = r * 0.82
                c.beginPath()
                c.moveTo(r + Math.sin(a) * r1, r - Math.cos(a) * r1)
                c.lineTo(r + Math.sin(a) * r2, r - Math.cos(a) * r2)
                c.strokeStyle = big ? "#2c3a4c" : "#8a9bb0"
                c.lineWidth = big ? Math.max(1.5, r * 0.035) : 1
                c.stroke()
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: clock.height / 2 + clock.d * 0.18
        visible: clock.label !== ""
        text: clock.label
        color: "#3d4d60"
        font.pixelSize: Math.max(8, clock.d * 0.075)
    }

    Rectangle {                          // hour hand
        antialiasing: true
        width: Math.max(3, clock.d * 0.05); height: clock.d * 0.26
        radius: width / 2
        color: "#1f2b3a"
        x: clock.width / 2 - width / 2; y: clock.height / 2 - height
        transformOrigin: Item.Bottom
        rotation: ((clock.h % 12) + clock.m / 60) * 30
    }
    Rectangle {                          // minute hand
        antialiasing: true
        width: Math.max(2, clock.d * 0.035); height: clock.d * 0.37
        radius: width / 2
        color: "#1f2b3a"
        x: clock.width / 2 - width / 2; y: clock.height / 2 - height
        transformOrigin: Item.Bottom
        rotation: (clock.m + clock.s / 60) * 6
    }
    Rectangle {                          // second hand, with a short tail
        id: secondHand
        visible: clock.seconds
        antialiasing: true
        width: Math.max(1, clock.d * 0.012); height: clock.d * 0.48
        color: "#d0281e"
        x: clock.width / 2 - width / 2; y: clock.height / 2 - clock.d * 0.40
        transform: Rotation {                     // pivot at the clock's centre, not the hand's
            origin.x: secondHand.width / 2; origin.y: clock.d * 0.40
            angle: clock.s * 6
        }
    }
    Rectangle {                          // centre cap
        width: clock.d * 0.07; height: width; radius: width / 2
        anchors.centerIn: parent
        color: "#d0281e"
        border.color: "#7a140e"
    }
    Rectangle {                          // glass gloss over the top half
        anchors.horizontalCenter: parent.horizontalCenter
        y: clock.height / 2 - clock.d * 0.42
        width: clock.d * 0.7; height: clock.d * 0.36
        radius: height / 2
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.rgba(1, 1, 1, 0.55) }
            GradientStop { position: 1; color: Qt.rgba(1, 1, 1, 0.0) }
        }
    }
}
