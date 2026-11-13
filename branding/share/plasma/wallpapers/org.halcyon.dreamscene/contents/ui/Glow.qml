import QtQuick
import QtQuick.Shapes

// A soft round light: a radial gradient fading to nothing. Cheap to draw and to move.
Shape {
    id: glow
    property color color: "white"
    property real size: 100
    width: size
    height: size
    preferredRendererType: Shape.CurveRenderer
    ShapePath {
        strokeWidth: -1
        fillGradient: RadialGradient {
            centerX: glow.size / 2; centerY: glow.size / 2
            centerRadius: glow.size / 2
            focalX: centerX; focalY: centerY
            GradientStop { position: 0; color: glow.color }
            GradientStop { position: 0.45; color: Qt.rgba(glow.color.r, glow.color.g, glow.color.b, glow.color.a * 0.45) }
            GradientStop { position: 1; color: "transparent" }
        }
        PathAngleArc { centerX: glow.size / 2; centerY: glow.size / 2; radiusX: glow.size / 2; radiusY: glow.size / 2; sweepAngle: 360 }
    }
}
