import QtQuick
import QtQuick.Window

// One fullscreen window per monitor for the Bubbles saver. Any key, click or
// real mouse movement on any of them ends it. Monitors plugged in or removed
// while it runs get a window added or taken away.
Instantiator {
    model: Qt.application.screens

    delegate: Window {
        id: win
        required property var modelData
        screen: modelData
        x: modelData.virtualX
        y: modelData.virtualY
        width: modelData.width
        height: modelData.height
        visible: true
        visibility: Window.FullScreen
        color: "black"
        title: "Halcyon Screensaver"
        property point start: Qt.point(-1, -1)

        Bubbles { anchors.fill: parent }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.BlankCursor
            onPositionChanged: (m) => {
                if (win.start.x < 0) { win.start = Qt.point(m.x, m.y); return }
                if (Math.abs(m.x - win.start.x) + Math.abs(m.y - win.start.y) > 12) Qt.quit()
            }
            onPressed: Qt.quit()
            onWheel: Qt.quit()
        }
        Item { anchors.fill: parent; focus: true; Keys.onPressed: Qt.quit() }
    }
}
