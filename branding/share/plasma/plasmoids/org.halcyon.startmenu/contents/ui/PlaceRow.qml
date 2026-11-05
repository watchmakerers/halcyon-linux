import QtQuick
import org.kde.kirigami as Kirigami

// One link in the dark glass right column. Hovering it shows its icon in the
// picture frame at the top, like Vista.
MouseArea {
    id: row
    property string text
    property string icon
    property bool arrow: false
    property bool bold: false
    signal activated()

    readonly property real gu: Kirigami.Units.gridUnit
    width: parent ? parent.width : 0
    height: Math.round(gu * 1.72)
    hoverEnabled: true
    onClicked: activated()
    onContainsMouseChanged: menu.hoverIcon = containsMouse ? icon : (menu.hoverIcon === icon ? "" : menu.hoverIcon)

    Rectangle {
        anchors.fill: parent
        radius: 3
        visible: row.containsMouse
        border.color: Qt.rgba(1, 1, 1, 0.55)
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.85, 0.93, 1, 0.42) }
            GradientStop { position: 0.5; color: Qt.rgba(0.62, 0.76, 0.88, 0.32) }
            GradientStop { position: 1.0; color: Qt.rgba(0.55, 0.70, 0.84, 0.42) }
        }
        Rectangle {  // inner shine
            anchors.fill: parent; anchors.margins: 1; radius: 2
            color: "transparent"; border.color: Qt.rgba(1, 1, 1, 0.25)
        }
    }
    Text {
        anchors { left: parent.left; leftMargin: Math.round(row.gu * 0.45); right: tri.left; rightMargin: 4
                  verticalCenter: parent.verticalCenter }
        text: row.text
        elide: Text.ElideRight
        color: "#ffffff"
        style: Text.Raised
        styleColor: Qt.rgba(0, 0, 0, 0.35)
        font.family: Kirigami.Theme.defaultFont.family
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
        font.bold: row.bold
    }
    Triangle {
        id: tri
        visible: row.arrow
        color: "#ffffff"
        anchors { right: parent.right; rightMargin: Math.round(row.gu * 0.45); verticalCenter: parent.verticalCenter }
        width: row.arrow ? 4 : 0; height: 7
    }
}
