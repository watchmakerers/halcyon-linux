import QtQuick
import QtQuick.Layouts
import "timefmt.js" as Fmt

// The flyout: the date as a heading, the month calendar, an analog clock
// for local time and one or two more for other time zones, and a link to
// the date and time settings.
Item {
    id: fly
    property real localOffset: 0          // seconds from UTC
    property var zones: []                // [{label, offset}]
    property bool use24: false
    property bool showSeconds: true
    property bool running: true           // tick only while shown
    signal settingsRequested()

    property date now: new Date()
    readonly property var here: Fmt.inZone(now, localOffset)
    readonly property real clockSize: zones.length ? 112 : 150

    implicitWidth: layout.implicitWidth + 28
    implicitHeight: layout.implicitHeight + 24

    Timer {                               // 20 fps for a smooth second hand, only while open
        interval: 50
        repeat: true
        running: fly.running
        triggeredOnStart: true
        onTriggered: fly.now = new Date()
    }

    Rectangle {                           // light inner panel, so the text reads on any glass colour
        anchors.fill: parent
        anchors.margins: 2
        radius: 5
        border.color: "#b9cbe0"
        gradient: Gradient {
            GradientStop { position: 0; color: "#ffffff" }
            GradientStop { position: 1; color: "#eaf1f9" }
        }
    }

    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        Text {                            // Friday, November 13, 2026 (click: back to this month)
            text: Fmt.longDate(fly.here)
            color: dateArea.containsMouse ? "#3399ff" : "#0066cc"
            font.pixelSize: 15
            font.underline: dateArea.containsMouse
            MouseArea {
                id: dateArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: cal.goToday()
            }
        }

        RowLayout {
            spacing: 18
            MonthCalendar {
                id: cal
                Layout.preferredWidth: 7 * 30
                Layout.preferredHeight: implicitHeight
                Layout.alignment: Qt.AlignTop
                todayDay: fly.here.day
                todayMonth: fly.here.month
                todayYear: fly.here.year
            }
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                color: "#c9d6e6"
            }
            Repeater {
                model: [{ label: "", offset: fly.localOffset, local: true }].concat(fly.zones)
                ColumnLayout {
                    required property var modelData
                    readonly property var t: Fmt.inZone(fly.now, modelData.offset)
                    Layout.alignment: Qt.AlignTop
                    spacing: 4
                    AnalogClock {
                        Layout.preferredWidth: fly.clockSize
                        Layout.preferredHeight: fly.clockSize
                        Layout.alignment: Qt.AlignHCenter
                        h: parent.t.h
                        m: parent.t.m
                        s: parent.t.s + parent.t.ms / 1000
                        seconds: fly.showSeconds
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: Fmt.time(parent.t, fly.use24, fly.showSeconds)
                        color: "#1e1e1e"
                        font.pixelSize: 13
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.maximumWidth: fly.clockSize + 20
                        elide: Text.ElideRight
                        text: parent.modelData.local ? "Local time"
                              : parent.modelData.label + ", " + Fmt.dayWord(parent.t, fly.here)
                        color: "#5a6a7e"
                        font.pixelSize: 11
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#c9d6e6"
        }
        Text {
            text: "Change date and time settings…"
            color: setArea.containsMouse ? "#3399ff" : "#0066cc"
            font.underline: setArea.containsMouse
            MouseArea {
                id: setArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: fly.settingsRequested()
            }
        }
    }
}
