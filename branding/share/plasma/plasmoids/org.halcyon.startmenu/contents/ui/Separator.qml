import QtQuick

// Thin rule that fades out at both ends.
Item {
    id: sep
    property color color: "#d5dfe5"
    property real inset: 0
    width: parent ? parent.width : 0
    height: 9
    Rectangle {
        anchors { left: parent.left; right: parent.right; leftMargin: sep.inset; rightMargin: sep.inset
                  verticalCenter: parent.verticalCenter }
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.2; color: sep.color }
            GradientStop { position: 0.8; color: sep.color }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }
}
