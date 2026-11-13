import QtQuick
import QtQuick.Layouts
import "timefmt.js" as Fmt

// Vista's flyout calendar: a month grid with today boxed. Click the title
// for the year's months, pick one to go back to its days.
Item {
    id: cal
    property int todayDay: 1
    property int todayMonth: 0
    property int todayYear: 2026
    property int month: todayMonth
    property int year: todayYear
    property bool yearView: false
    property color textColor: "#1e1e1e"
    property color mutedColor: "#9aa6b4"
    property color accent: "#3c7fb1"

    implicitWidth: 7 * 30
    implicitHeight: 30 + 22 + 6 * 24

    function goToday() { month = todayMonth; year = todayYear; yearView = false }
    function step(d) {
        if (yearView) { year += d; return }
        month += d
        if (month < 0) { month = 11; year-- }
        if (month > 11) { month = 0; year++ }
    }

    // The 42 cells shown for this month: [day, month offset (-1/0/1)]
    readonly property var cells: {
        const first = new Date(Date.UTC(year, month, 1)).getUTCDay()     // 0 = Sunday
        const len = new Date(Date.UTC(year, month + 1, 0)).getUTCDate()
        const prevLen = new Date(Date.UTC(year, month, 0)).getUTCDate()
        const out = []
        for (let i = 0; i < 42; i++) {
            const n = i - first + 1
            if (n < 1) out.push([prevLen + n, -1])
            else if (n > len) out.push([n - len, 1])
            else out.push([n, 0])
        }
        return out
    }

    RowLayout {                                   // < November 2026 >
        id: head
        width: parent.width
        height: 28
        Arrow { pointsLeft: true; onClicked: cal.step(-1) }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: cal.yearView ? cal.year : Fmt.MONTHS[cal.month] + " " + cal.year
            color: titleArea.containsMouse ? cal.accent : cal.textColor
            font.bold: true
            MouseArea {
                id: titleArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: cal.yearView = !cal.yearView
            }
        }
        Arrow { pointsLeft: false; onClicked: cal.step(1) }
    }

    // ------------------------------------------------------------ month ---
    Item {
        visible: !cal.yearView
        anchors { top: head.bottom; left: parent.left; right: parent.right; bottom: parent.bottom; topMargin: 2 }
        Row {
            id: weekdays
            Repeater {
                model: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
                Text {
                    width: cal.width / 7; height: 20
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData
                    color: cal.mutedColor
                    font.pixelSize: 11
                }
            }
        }
        Rectangle {
            anchors.top: weekdays.bottom
            width: parent.width; height: 1
            color: cal.mutedColor; opacity: 0.4
        }
        Grid {
            anchors.top: weekdays.bottom
            anchors.topMargin: 3
            columns: 7
            Repeater {
                model: cal.cells
                Item {
                    width: cal.width / 7; height: 24
                    readonly property bool today: modelData[1] === 0 && modelData[0] === cal.todayDay
                                                  && cal.month === cal.todayMonth && cal.year === cal.todayYear
                    Rectangle {
                        anchors.fill: parent; anchors.margins: 1
                        radius: 2
                        visible: parent.today || dayArea.containsMouse
                        color: parent.today ? Qt.rgba(0.24, 0.5, 0.7, 0.12) : Qt.rgba(0.24, 0.5, 0.7, 0.08)
                        border.color: parent.today ? cal.accent : Qt.rgba(0.24, 0.5, 0.7, 0.4)
                    }
                    Text {
                        anchors.centerIn: parent
                        text: modelData[0]
                        color: modelData[1] === 0 ? cal.textColor : cal.mutedColor
                        font.bold: parent.today
                    }
                    MouseArea {
                        id: dayArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: if (modelData[1] !== 0) cal.step(modelData[1])
                    }
                }
            }
        }
    }

    // ------------------------------------------------------------- year ---
    Grid {
        visible: cal.yearView
        anchors { top: head.bottom; left: parent.left; right: parent.right; topMargin: 8 }
        columns: 4
        Repeater {
            model: 12
            Item {
                width: cal.width / 4; height: (cal.height - 40) / 3
                readonly property bool current: index === cal.todayMonth && cal.year === cal.todayYear
                Rectangle {
                    anchors.fill: parent; anchors.margins: 3
                    radius: 3
                    visible: parent.current || monthArea.containsMouse
                    color: Qt.rgba(0.24, 0.5, 0.7, parent.current ? 0.12 : 0.08)
                    border.color: parent.current ? cal.accent : Qt.rgba(0.24, 0.5, 0.7, 0.4)
                }
                Text {
                    anchors.centerIn: parent
                    text: Fmt.MONTHS[index].slice(0, 3)
                    color: cal.textColor
                }
                MouseArea {
                    id: monthArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { cal.month = index; cal.yearView = false }
                }
            }
        }
    }

    component Arrow: Item {
        id: arrow
        property bool pointsLeft: true
        signal clicked()
        Layout.preferredWidth: 24
        Layout.preferredHeight: 24
        Canvas {
            id: tri
            anchors.centerIn: parent
            width: 10; height: 12
            onPaint: {
                const c = getContext("2d")
                c.reset()
                c.fillStyle = area.containsMouse ? cal.accent : cal.textColor
                c.beginPath()
                if (arrow.pointsLeft) { c.moveTo(9, 1); c.lineTo(2, 6); c.lineTo(9, 11) }
                else { c.moveTo(1, 1); c.lineTo(8, 6); c.lineTo(1, 11) }
                c.closePath()
                c.fill()
            }
            Connections { target: area; function onContainsMouseChanged() { tri.requestPaint() } }
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: arrow.clicked()
        }
    }
}
