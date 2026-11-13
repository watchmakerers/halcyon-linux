import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasma5support as P5Support

Kirigami.FormLayout {
    id: page

    property alias cfg_use24Hour: h24.checked
    property alias cfg_showSeconds: secs.checked
    property alias cfg_showDate: date.checked
    property alias cfg_clock1Enabled: c1.checked
    property alias cfg_clock1Label: c1label.text
    property string cfg_clock1Zone
    property alias cfg_clock2Enabled: c2.checked
    property alias cfg_clock2Label: c2label.text
    property string cfg_clock2Zone

    // Every time zone the system knows (the time engine lists them as sources).
    P5Support.DataSource { id: time; engine: "time" }
    readonly property var allZones: time.sources.filter(s => s.indexOf("/") > 0).sort()

    QQC2.CheckBox { id: h24; Kirigami.FormData.label: "Time:"; text: "Use 24-hour time" }
    QQC2.CheckBox { id: secs; text: "Show seconds on the taskbar" }
    QQC2.CheckBox { id: date; text: "Show the date when the taskbar is tall enough" }

    Item { Kirigami.FormData.isSection: true }

    QQC2.CheckBox { id: c1; Kirigami.FormData.label: "Additional clocks:"; text: "Show this clock" }
    QQC2.TextField {
        id: c1label
        Kirigami.FormData.label: "Display name:"
        enabled: c1.checked
        placeholderText: "e.g. London office"
    }
    QQC2.ComboBox {
        Kirigami.FormData.label: "Time zone:"
        enabled: c1.checked
        Layout.preferredWidth: Kirigami.Units.gridUnit * 16
        model: page.allZones
        currentIndex: page.allZones.indexOf(page.cfg_clock1Zone)
        onActivated: page.cfg_clock1Zone = currentText
    }

    Item { Kirigami.FormData.isSection: true }

    QQC2.CheckBox { id: c2; text: "Show this clock" }
    QQC2.TextField {
        id: c2label
        Kirigami.FormData.label: "Display name:"
        enabled: c2.checked
        placeholderText: "e.g. Family in Tokyo"
    }
    QQC2.ComboBox {
        Kirigami.FormData.label: "Time zone:"
        enabled: c2.checked
        Layout.preferredWidth: Kirigami.Units.gridUnit * 16
        model: page.allZones
        currentIndex: page.allZones.indexOf(page.cfg_clock2Zone)
        onActivated: page.cfg_clock2Zone = currentText
    }
}
