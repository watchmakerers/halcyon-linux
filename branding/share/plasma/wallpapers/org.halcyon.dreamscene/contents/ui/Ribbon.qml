import QtQuick
import QtQuick.Shapes
import QtQuick.Effects

// A band of light that flows sideways forever. The wave repeats every
// `period` pixels and the band is drawn wider than the screen by whole
// periods, so sliding it left by one period loops without a seam. It's
// blurred once (layer) and then only moved, so nothing is re-blurred while
// it animates.
Item {
    id: ribbon
    property color color: "#7fffb0"
    property real amplitude: 60
    property real thickness: 140
    property real period: 900
    property real seconds: 40                 // time for one period to pass
    property bool running: true
    property real blur: 1.0

    readonly property int waves: Math.ceil(width / period) + 2

    Item {
        id: band
        width: ribbon.period * ribbon.waves
        height: ribbon.thickness + ribbon.amplitude * 2 + 160
        y: (ribbon.height - height) / 2
        layer.enabled: ribbon.blur > 0
        layer.effect: MultiEffect {
            blurEnabled: true
            blur: ribbon.blur
            blurMax: 64
            autoPaddingEnabled: true
        }

        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeWidth: -1
                fillGradient: LinearGradient {
                    x1: 0; y1: 80; x2: 0; y2: band.height - 80
                    GradientStop { position: 0; color: "transparent" }
                    GradientStop { position: 0.4; color: ribbon.color }
                    GradientStop { position: 0.52; color: Qt.lighter(ribbon.color, 1.35) }
                    GradientStop { position: 1; color: "transparent" }
                }
                // A Repeater can't add path elements, so the outline is built as SVG path text.
                PathSvg { path: ribbon.outline(band.height) }
            }
        }

        NumberAnimation on x {
            from: 0; to: -ribbon.period
            duration: ribbon.seconds * 1000
            loops: Animation.Infinite
            paused: !ribbon.running
        }
    }

    function outline(h) {
        const p = period, a = amplitude, mid = h / 2, t = thickness / 2
        let d = `M 0 ${mid - t}`
        for (let i = 0; i < waves; i++) {          // top edge: a hump and a dip per period
            const x = i * p
            d += ` C ${x + p * 0.25} ${mid - t - a} ${x + p * 0.25} ${mid - t - a} ${x + p * 0.5} ${mid - t}`
            d += ` C ${x + p * 0.75} ${mid - t + a} ${x + p * 0.75} ${mid - t + a} ${x + p} ${mid - t}`
        }
        d += ` L ${waves * p} ${mid + t}`
        for (let i = waves - 1; i >= 0; i--) {     // bottom edge back, swinging less, so the band breathes
            const x = (i + 1) * p
            d += ` C ${x - p * 0.25} ${mid + t + a * 0.6} ${x - p * 0.25} ${mid + t + a * 0.6} ${x - p * 0.5} ${mid + t}`
            d += ` C ${x - p * 0.75} ${mid + t - a * 0.6} ${x - p * 0.75} ${mid + t - a * 0.6} ${x - p} ${mid + t}`
        }
        return d + " Z"
    }
}
