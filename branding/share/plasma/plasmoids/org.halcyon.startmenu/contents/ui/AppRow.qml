import QtQuick
import org.kde.kirigami as Kirigami

// One program in the white left pane: icon, title and an optional grey second line.
MouseArea {
    id: row
    property var icon
    property string title
    property string subtitle
    property bool big: false     // pinned rows: larger icon, bold title, subtitle
    property bool current: false // keyboard selection
    property real indent: 0
    signal activated()
    signal contextRequested(real x, real y)

    readonly property real gu: Kirigami.Units.gridUnit
    width: parent ? parent.width : 0
    height: Math.round(big ? gu * 2.3 : gu * 1.85)
    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    onClicked: (m) => m.button === Qt.RightButton ? contextRequested(m.x, m.y) : activated()

    Highlight { visible: row.containsMouse || row.current }

    Kirigami.Icon {
        id: ic
        anchors { left: parent.left; leftMargin: Math.round(row.gu * 0.3 + row.indent); verticalCenter: parent.verticalCenter }
        width: Math.round(row.big ? row.gu * 1.8 : row.gu * 1.45); height: width
        source: row.icon
        animated: false
    }
    Column {
        anchors { left: ic.right; leftMargin: Math.round(row.gu * 0.35); right: parent.right; rightMargin: 4
                  verticalCenter: parent.verticalCenter }
        Text {
            width: parent.width
            text: row.title
            elide: Text.ElideRight
            color: "#000000"
            font.family: Kirigami.Theme.defaultFont.family
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
            font.bold: row.big
        }
        Text {
            width: parent.width
            visible: row.big && text.length > 0
            text: row.subtitle
            elide: Text.ElideRight
            color: "#6d6d6d"
            font.family: Kirigami.Theme.defaultFont.family
            font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.92
        }
    }
}
