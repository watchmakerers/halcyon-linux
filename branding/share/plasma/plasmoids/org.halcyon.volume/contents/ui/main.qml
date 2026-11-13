import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.private.volume
import org.kde.kcmutils as KCMUtils
import "volume.js" as Volume

// Halcyon Volume: Vista's tray volume control. Click the speaker for one
// slider and a mute button; "Mixer" widens the flyout into a column per
// program that's playing sound, next to the speakers.
PlasmoidItem {
    id: root

    readonly property var sink: PreferredDevice.sink
    readonly property int percent: sink ? Math.round(sink.volume / PulseAudio.NormalVolume * 100) : 0
    readonly property bool muted: sink ? sink.muted : true
    property bool mixer: false

    function setPercent(v) {
        if (!sink)
            return
        sink.volume = Math.round(Math.max(0, Math.min(100, v)) / 100 * PulseAudio.NormalVolume)
        if (sink.muted && v > 0)
            sink.muted = false
    }

    Plasmoid.icon: Volume.iconFor(percent, muted)
    Plasmoid.status: PlasmaCore.Types.ActiveStatus
    toolTipMainText: Volume.deviceName(sink) + (sink ? (muted ? ": Muted" : ": " + percent + "%") : "")
    toolTipSubText: sink ? (sink.description || "") : ""
    switchWidth: Kirigami.Units.gridUnit * 4
    switchHeight: Kirigami.Units.gridUnit * 4
    onExpandedChanged: if (!expanded) mixer = false     // reopen as the small slider, like Vista

    SinkInputModel { id: streams }

    compactRepresentation: MouseArea {
        id: compact
        property bool wasExpanded: false
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
        hoverEnabled: true
        onPressed: (mouse) => { if (mouse.button === Qt.LeftButton) wasExpanded = root.expanded }
        onClicked: (mouse) => {
            if (mouse.button === Qt.MiddleButton) {
                if (root.sink) root.sink.muted = !root.sink.muted
            } else {
                root.expanded = !wasExpanded
            }
        }
        onWheel: (wheel) => {
            const steps = wheel.angleDelta.y / 120
            root.setPercent(root.percent + Math.round(steps * 5))
        }
        Kirigami.Icon {
            anchors.fill: parent
            source: Plasmoid.icon
            active: compact.containsMouse
        }
    }

    fullRepresentation: Item {
        id: flyout
        Layout.minimumWidth: root.mixer ? mixerRow.implicitWidth + Kirigami.Units.largeSpacing * 2
                                        : Kirigami.Units.gridUnit * 6
        Layout.minimumHeight: Kirigami.Units.gridUnit * 17
        Layout.maximumWidth: Layout.minimumWidth
        Layout.preferredWidth: Layout.minimumWidth
        Layout.preferredHeight: Layout.minimumHeight

        // ------------------------------------------------ the small flyout ---
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            visible: !root.mixer
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents3.Label {
                Layout.alignment: Qt.AlignHCenter
                text: root.sink ? (root.muted ? "Muted" : root.percent + "%") : "No device"
                opacity: 0.8
            }
            VistaSlider {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillHeight: true
                value: root.percent
                dimmed: root.muted
                enabled: root.sink !== null
                onMoved: (v) => root.setPercent(v)
            }
            MuteButton {
                Layout.alignment: Qt.AlignHCenter
                muted: root.muted
                percent: root.percent
                onClicked: if (root.sink) root.sink.muted = !root.sink.muted
            }
            PlasmaComponents3.Label {
                Layout.alignment: Qt.AlignHCenter
                text: "<a href='mixer'>Mixer</a>"
                textFormat: Text.StyledText
                linkColor: Kirigami.Theme.linkColor
                onLinkActivated: root.mixer = true
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }
        }

        // ----------------------------------------------------- the mixer ---
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            visible: root.mixer
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                id: mixerRow
                Layout.fillHeight: true
                spacing: Kirigami.Units.largeSpacing

                ColumnLayout {
                    Layout.fillHeight: true
                    PlasmaComponents3.Label { text: "Device"; font.bold: true }
                    MixerColumn {
                        target: root.sink
                        label: Volume.deviceName(root.sink)
                        iconName: Volume.deviceIcon(root.sink)
                    }
                }

                Rectangle {                      // the divider between device and programs
                    Layout.fillHeight: true
                    Layout.topMargin: Kirigami.Units.gridUnit
                    Layout.preferredWidth: 1
                    color: Kirigami.Theme.textColor
                    opacity: 0.2
                }

                ColumnLayout {
                    Layout.fillHeight: true
                    PlasmaComponents3.Label { text: "Applications"; font.bold: true }
                    RowLayout {
                        Layout.fillHeight: true
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: streams
                            delegate: MixerColumn {
                                required property var model
                                visible: !model.VirtualStream
                                target: model.PulseObject
                                label: Volume.appName(model.PulseObject)
                                iconName: Volume.appIcon(model.PulseObject, model.IconName)
                            }
                        }
                        PlasmaComponents3.Label {
                            visible: streams.count === 0
                            Layout.preferredWidth: Kirigami.Units.gridUnit * 7
                            Layout.alignment: Qt.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            opacity: 0.7
                            text: "No programs are playing sound right now."
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                PlasmaComponents3.Label {
                    text: "<a href='back'>‹ Back</a>"
                    textFormat: Text.StyledText
                    linkColor: Kirigami.Theme.linkColor
                    onLinkActivated: root.mixer = false
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
                Item { Layout.fillWidth: true }
                PlasmaComponents3.Label {
                    text: "<a href='settings'>Sound settings</a>"
                    textFormat: Text.StyledText
                    linkColor: Kirigami.Theme.linkColor
                    onLinkActivated: KCMUtils.KCMLauncher.openSystemSettings("kcm_pulseaudio")
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
        }
    }

    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            text: "Open Volume Mixer"
            icon.name: "view-media-equalizer"
            onTriggered: { root.mixer = true; root.expanded = true }
        },
        PlasmaCore.Action {
            text: root.muted ? "Unmute" : "Mute"
            icon.name: "audio-volume-muted"
            onTriggered: if (root.sink) root.sink.muted = !root.sink.muted
        },
        PlasmaCore.Action {
            text: "Sound Settings…"
            icon.name: "configure"
            onTriggered: KCMUtils.KCMLauncher.openSystemSettings("kcm_pulseaudio")
        }
    ]
}
