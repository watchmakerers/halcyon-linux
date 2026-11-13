import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCMUtils
import "timefmt.js" as Fmt

// Halcyon Clock: Vista's taskbar clock. The time (and the date when the
// taskbar is tall enough) sits in the panel; clicking opens a flyout with a
// calendar, an analog clock and up to two more time zones.
PlasmoidItem {
    id: root

    readonly property var cfg: Plasmoid.configuration
    readonly property var zoneIds: [cfg.clock1Enabled ? cfg.clock1Zone : "", cfg.clock2Enabled ? cfg.clock2Zone : ""]
                                   .filter(z => z !== "")
    readonly property real localOffset: (time.data["Local"] || {})["Offset"] || -new Date().getTimezoneOffset() * 60
    readonly property var zones: {
        const out = []
        if (cfg.clock1Enabled && time.data[cfg.clock1Zone])
            out.push({ label: cfg.clock1Label || cfg.clock1Zone, offset: time.data[cfg.clock1Zone]["Offset"] })
        if (cfg.clock2Enabled && time.data[cfg.clock2Zone])
            out.push({ label: cfg.clock2Label || cfg.clock2Zone, offset: time.data[cfg.clock2Zone]["Offset"] })
        return out
    }
    property date now: new Date()
    readonly property var here: Fmt.inZone(now, localOffset)

    preferredRepresentation: compactRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    toolTipMainText: Fmt.longDate(here)
    toolTipSubText: zones.map(z => z.label + ": " + Fmt.time(Fmt.inZone(now, z.offset), cfg.use24Hour, false)).join("\n")

    // Offsets for local time and the extra zones (they change with daylight saving).
    P5Support.DataSource {
        id: time
        engine: "time"
        connectedSources: ["Local"].concat(root.zoneIds)
        interval: 60000
    }
    Timer {                                   // once a second is plenty for the panel
        interval: 1000
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: root.now = new Date()
    }

    compactRepresentation: MouseArea {
        id: compact
        readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
        readonly property bool twoLines: root.cfg.showDate && !vertical && height >= Kirigami.Units.gridUnit * 1.9
        property bool wasExpanded: false
        hoverEnabled: true
        Layout.minimumWidth: vertical ? -1 : Math.max(timeText.implicitWidth, dateText.visible ? dateText.implicitWidth : 0)
                                             + Kirigami.Units.largeSpacing * 2
        Layout.minimumHeight: vertical ? timeText.implicitHeight * (twoLines ? 2 : 1) + Kirigami.Units.smallSpacing : -1
        onPressed: wasExpanded = root.expanded
        onClicked: root.expanded = !wasExpanded

        Rectangle {                           // a soft glass highlight on hover, like Vista's tray
            anchors.fill: parent
            anchors.margins: 2
            radius: 3
            visible: compact.containsMouse || root.expanded
            color: Qt.rgba(1, 1, 1, root.expanded ? 0.22 : 0.12)
            border.color: Qt.rgba(1, 1, 1, 0.35)
        }
        Column {
            anchors.centerIn: parent
            PlasmaComponents3.Label {
                id: timeText
                anchors.horizontalCenter: parent.horizontalCenter
                text: Fmt.time(root.here, root.cfg.use24Hour, root.cfg.showSeconds)
                style: Text.Raised
                styleColor: Qt.rgba(0, 0, 0, 0.35)
            }
            PlasmaComponents3.Label {
                id: dateText
                anchors.horizontalCenter: parent.horizontalCenter
                visible: compact.twoLines
                text: Fmt.shortDate(root.here)
                style: Text.Raised
                styleColor: Qt.rgba(0, 0, 0, 0.35)
            }
        }
    }

    fullRepresentation: Flyout {
        Layout.minimumWidth: implicitWidth
        Layout.minimumHeight: implicitHeight
        Layout.maximumWidth: implicitWidth
        Layout.maximumHeight: implicitHeight
        localOffset: root.localOffset
        zones: root.zones
        use24: root.cfg.use24Hour
        showSeconds: true
        running: root.expanded
        onSettingsRequested: {
            root.expanded = false
            KCMUtils.KCMLauncher.openSystemSettings("kcm_clock")
        }
    }

    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            text: "Adjust Date/Time…"
            icon.name: "preferences-system-time"
            onTriggered: KCMUtils.KCMLauncher.openSystemSettings("kcm_clock")
        },
        PlasmaCore.Action {
            text: "Copy date to clipboard"
            icon.name: "edit-copy"
            onTriggered: clip.copyText(Fmt.longDate(root.here))
        }
    ]
    TextEdit {                                // a hidden field is the simplest way to reach the clipboard from QML
        id: clip
        visible: false
        function copyText(t) { text = t; selectAll(); copy() }
    }
}
