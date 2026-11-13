import QtQuick
import org.kde.plasma.plasmoid
import org.kde.kirigami as Kirigami

// The Start orb artwork: dark glass sphere, logo, gloss cap and (when lit) a cyan glow.
Item {
    id: art
    property bool lit: false
    readonly property real d: Math.min(width, height)
    // Plain hex colours, so Window Color (wintheme.py) can recolour a copy of this file.
    readonly property color glow: "#8ce6ff"
    readonly property color rim: "#000a17"

    onLitChanged: { body.requestPaint(); gloss.requestPaint() }
    onDChanged: { body.requestPaint(); gloss.requestPaint() }

    Canvas {
        id: body
        anchors.centerIn: parent
        width: art.d; height: art.d
        onPaint: {
            const c = getContext("2d"), r = width / 2
            c.reset()
            if (art.lit) {
                const g = c.createRadialGradient(r, r, r * 0.6, r, r, r)
                g.addColorStop(0, Qt.rgba(art.glow.r, art.glow.g, art.glow.b, 0.75))
                g.addColorStop(1, Qt.rgba(art.glow.r, art.glow.g, art.glow.b, 0))
                c.fillStyle = g
                c.beginPath(); c.arc(r, r, r, 0, Math.PI * 2); c.fill()
            }
            const R = r * 0.86
            // Light comes from below, so the core glows low in the ball.
            const s = c.createRadialGradient(r, r * 1.38, R * 0.1, r, r * 1.05, R * 1.05)
            s.addColorStop(0, art.lit ? "#9cf0ff" : "#4cc4ee")
            s.addColorStop(0.45, art.lit ? "#1d8fd4" : "#11679f")
            s.addColorStop(0.85, "#062a4a")
            s.addColorStop(1, "#020e1c")
            c.fillStyle = s
            c.beginPath(); c.arc(r, r, R, 0, Math.PI * 2); c.fill()
            c.lineWidth = Math.max(1, R * 0.06)
            c.strokeStyle = Qt.rgba(art.rim.r, art.rim.g, art.rim.b, 0.9)
            c.stroke()
            c.lineWidth = 1
            c.strokeStyle = Qt.rgba(1, 1, 1, 0.35)
            c.beginPath(); c.arc(r, r, R - 1.5, 0, Math.PI * 2); c.stroke()
        }
    }

    Kirigami.Icon {
        anchors.centerIn: parent
        width: Math.round(art.d * 0.56); height: width
        source: Plasmoid.icon
        active: art.lit
    }

    Canvas {
        id: gloss
        anchors.centerIn: parent
        width: art.d; height: art.d
        onPaint: {
            const c = getContext("2d"), r = width / 2, R = r * 0.86
            c.reset()
            const g = c.createLinearGradient(0, r - R, 0, r)
            g.addColorStop(0, Qt.rgba(1, 1, 1, art.lit ? 0.6 : 0.45))
            g.addColorStop(1, Qt.rgba(1, 1, 1, 0.04))
            c.fillStyle = g
            c.beginPath()
            c.ellipse(r - R * 0.78, r - R * 0.94, R * 1.56, R * 1.0)
            c.fill()
        }
    }
}
