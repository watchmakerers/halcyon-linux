import QtQuick
import QtQuick.Shapes

// Small solid arrowhead; points right, or left with flip: true.
Shape {
    id: tri
    property color color: "black"
    property bool flip: false
    width: 5; height: 9
    preferredRendererType: Shape.CurveRenderer
    ShapePath {
        strokeWidth: 0
        strokeColor: "transparent"
        fillColor: tri.color
        startX: tri.flip ? tri.width : 0; startY: 0
        PathLine { x: tri.flip ? 0 : tri.width; y: tri.height / 2 }
        PathLine { x: tri.flip ? tri.width : 0; y: tri.height }
        PathLine { x: tri.flip ? tri.width : 0; y: 0 }
    }
}
