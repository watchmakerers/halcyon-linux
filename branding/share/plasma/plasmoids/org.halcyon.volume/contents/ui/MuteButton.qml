import QtQuick
import org.kde.kirigami as Kirigami
import "volume.js" as Volume

// The small glass speaker button under each slider; a red "no" sign when muted.
Item {
    id: btn
    property bool muted: false
    property real percent: 50
    signal clicked()

    implicitWidth: Kirigami.Units.gridUnit * 2
    implicitHeight: Kirigami.Units.gridUnit * 1.6

    Rectangle {
        anchors.fill: parent
        radius: 4
        visible: area.containsMouse || area.pressed
        border.color: "#8fb8e6"
        gradient: Gradient {
            GradientStop { position: 0; color: area.pressed ? "#c2dcf6" : "#f2f8ff" }
            GradientStop { position: 0.5; color: area.pressed ? "#a9cdf0" : "#dceaf9" }
            GradientStop { position: 0.51; color: area.pressed ? "#93c0ec" : "#c6ddf5" }
            GradientStop { position: 1; color: area.pressed ? "#b8d6f4" : "#e2eefb" }
        }
    }

    Kirigami.Icon {
        anchors.centerIn: parent
        width: Kirigami.Units.iconSizes.smallMedium
        height: width
        source: Volume.iconFor(btn.percent, btn.muted)
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: btn.clicked()
    }

    Accessible.role: Accessible.Button
    Accessible.name: muted ? "Unmute" : "Mute"
}
