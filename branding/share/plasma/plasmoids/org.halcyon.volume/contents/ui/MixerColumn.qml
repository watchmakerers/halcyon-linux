import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.private.volume

// One column of the mixer: icon, name, vertical slider, mute button.
// target is a PulseAudioQt sink (the speakers) or sink input (a program).
ColumnLayout {
    id: col
    property var target: null
    property string label: ""
    property string iconName: "audio-card"

    readonly property real percent: target ? Math.round(target.volume / PulseAudio.NormalVolume * 100) : 0
    readonly property bool muted: target ? target.muted : false

    spacing: Kirigami.Units.smallSpacing
    Layout.preferredWidth: Kirigami.Units.gridUnit * 5.2
    Layout.fillHeight: true

    function setPercent(v) {
        if (!target)
            return
        target.volume = Math.round(v / 100 * PulseAudio.NormalVolume)
        if (target.muted && v > 0)
            target.muted = false          // moving the slider up unmutes, like Windows
    }

    Kirigami.Icon {
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: Kirigami.Units.iconSizes.medium
        Layout.preferredHeight: Kirigami.Units.iconSizes.medium
        source: col.iconName
        fallback: "audio-card"
    }

    PlasmaComponents3.Label {
        Layout.fillWidth: true
        Layout.preferredHeight: Kirigami.Units.gridUnit * 2.2
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignTop
        wrapMode: Text.Wrap
        maximumLineCount: 2
        elide: Text.ElideRight
        text: col.label
    }

    VistaSlider {
        Layout.alignment: Qt.AlignHCenter
        Layout.fillHeight: true
        Layout.minimumHeight: Kirigami.Units.gridUnit * 7
        value: col.percent
        dimmed: col.muted
        onMoved: (v) => col.setPercent(v)
    }

    PlasmaComponents3.Label {
        Layout.alignment: Qt.AlignHCenter
        text: col.muted ? "Muted" : col.percent + "%"
        opacity: 0.75
        font: Kirigami.Theme.smallFont
    }

    MuteButton {
        Layout.alignment: Qt.AlignHCenter
        muted: col.muted
        percent: col.percent
        onClicked: if (col.target) col.target.muted = !col.target.muted
    }
}
