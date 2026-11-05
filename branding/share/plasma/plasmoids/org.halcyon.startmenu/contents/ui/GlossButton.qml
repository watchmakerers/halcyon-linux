import QtQuick
import QtQuick.Controls as QQC2

// Glossy pill button for the power row. glyph: "power" | "lock" | "arrow".
MouseArea {
    id: b
    property color tint: "#39434d"
    property string glyph: "power"
    property string tip: ""
    hoverEnabled: true
    QQC2.ToolTip.visible: containsMouse && tip.length > 0
    QQC2.ToolTip.text: tip
    QQC2.ToolTip.delay: 600

    Rectangle {
        anchors.fill: parent
        radius: 3
        border.color: Qt.darker(b.tint, 2.4)
        gradient: Gradient {
            GradientStop { position: 0.00; color: Qt.lighter(b.tint, b.containsMouse ? 2.1 : 1.75) }
            GradientStop { position: 0.47; color: Qt.lighter(b.tint, b.containsMouse ? 1.45 : 1.2) }
            GradientStop { position: 0.50; color: b.pressed ? Qt.darker(b.tint, 1.2) : b.tint }
            GradientStop { position: 1.00; color: Qt.lighter(b.tint, b.containsMouse ? 1.6 : 1.3) }
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: 1; radius: 2
            color: "transparent"; border.color: Qt.rgba(1, 1, 1, 0.32)
        }
    }

    Canvas {
        id: g
        anchors.centerIn: parent
        width: Math.round(b.height * 0.62); height: width
        Connections { target: b; function onGlyphChanged() { g.requestPaint() } }
        onPaint: {
            const c = getContext("2d"), s = width
            c.reset()
            c.strokeStyle = "#ffffff"; c.fillStyle = "#ffffff"
            c.lineCap = "round"; c.lineWidth = Math.max(1.5, s * 0.13)
            c.shadowColor = Qt.rgba(0, 0, 0, 0.5); c.shadowBlur = 2; c.shadowOffsetY = 1
            if (b.glyph === "power") {
                c.beginPath()
                c.arc(s / 2, s * 0.55, s * 0.36, -Math.PI / 2 + 0.75, -Math.PI / 2 - 0.75 + Math.PI * 2)
                c.stroke()
                c.beginPath(); c.moveTo(s / 2, s * 0.08); c.lineTo(s / 2, s * 0.5); c.stroke()
            } else if (b.glyph === "lock") {
                c.lineWidth = Math.max(1.5, s * 0.11)
                c.beginPath()
                c.arc(s / 2, s * 0.38, s * 0.2, Math.PI, 0)
                c.lineTo(s * 0.7, s * 0.5); c.moveTo(s * 0.3, s * 0.38); c.lineTo(s * 0.3, s * 0.5)
                c.stroke()
                c.fillRect(s * 0.2, s * 0.48, s * 0.6, s * 0.42)
            } else {
                c.beginPath()
                c.moveTo(s * 0.38, s * 0.25); c.lineTo(s * 0.66, s * 0.5); c.lineTo(s * 0.38, s * 0.75)
                c.closePath(); c.fill()
            }
        }
    }
}
