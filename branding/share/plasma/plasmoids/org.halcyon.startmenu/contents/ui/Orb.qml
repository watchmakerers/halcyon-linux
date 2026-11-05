import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

// The Start button. A floating panel's window is taller than the bar you see
// (the floating gap is part of it), so the orb is drawn bigger than the panel
// and rises into that gap, like Vista's orb rising out of the taskbar. It stays
// inside the panel's own window: KWin keeps separate windows out of the panel
// area. On a non-floating or vertical panel, or with the option off, it just
// fills the panel.
MouseArea {
    id: orb

    readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
    readonly property int edge: Plasmoid.location
    readonly property bool topEdge: edge === PlasmaCore.Types.TopEdge
    readonly property real thick: vertical ? width : height
    readonly property var panelWin: Window.window
    readonly property real panelThick: panelWin && panelWin.thickness > 0 ? panelWin.thickness : thick
    readonly property bool rising: Plasmoid.configuration.floatingOrb && !vertical
        && (edge === PlasmaCore.Types.BottomEdge || topEdge)

    // Room between our slot and the inner edge of the panel window (the edge
    // facing the middle of the screen). Updated by measure().
    property real room: 0
    function measure() {
        let v = 0
        if (panelWin && rising) {
            const p = orb.mapToItem(null, 0, 0)
            v = Math.max(0, Math.floor(topEdge ? panelWin.height - (p.y + orb.height) : p.y))
        }
        if (v !== room) room = v
    }
    // The panel slides as it floats / unfloats (e.g. when a window is maximised),
    // which moves us without changing our own geometry, so keep checking.
    Timer {
        interval: 100
        repeat: true
        running: orb.rising
        onTriggered: orb.measure()
    }
    onHeightChanged: measure()
    onYChanged: measure()
    onRisingChanged: measure()
    Connections {
        target: orb.panelWin
        ignoreUnknownSignals: true
        function onHeightChanged() { orb.measure() }
        function onThicknessChanged() { orb.measure() }
    }
    Component.onCompleted: {
        Qt.callLater(measure)
        // Let the orb spill past the applet's box into the panel window's gap.
        for (let p = parent; p; p = p.parent) p.clip = false
    }

    // Orb diameter: the slot, plus half the panel's margin on the screen-edge
    // side, plus the room between the slot and the window's inner edge (less
    // 1px), at most ~1.4x the panel. So the orb's inner edge never passes the
    // window's edge, where it would be cut off.
    readonly property real pad: Math.max(0, (panelThick - thick) / 2)
    readonly property real d: rising
        ? Math.round(Math.min(panelThick * 1.4, thick + pad * 0.5 + Math.max(0, room - 1)))
        : Math.round(Math.min(width, height) * 0.96)

    // Fixed slot width (room for the largest orb) so the taskbar doesn't shuffle as the panel floats.
    Layout.minimumWidth: vertical ? -1 : Math.round(rising ? panelThick * 1.42 : thick * 1.12)
    Layout.maximumWidth: Layout.minimumWidth
    Layout.minimumHeight: vertical ? Math.round(thick * 1.12) : -1
    Layout.maximumHeight: Layout.minimumHeight

    property bool wasExpanded: false
    hoverEnabled: true
    // Pressing outside the popup closes it first, so remember the state at press time.
    onPressed: wasExpanded = kicker.expanded
    onClicked: kicker.expanded = !wasExpanded

    // Tell the menu where the orb is on screen so it can draw it over its own
    // corner: the popup opens over the part of the orb that pokes out.
    function publish() {
        const g = art.mapToGlobal(0, 0)
        const r = kicker.orbRect
        if (r.x !== g.x || r.y !== g.y || r.width !== art.width)
            kicker.orbRect = Qt.rect(g.x, g.y, art.width, art.height)
    }
    Connections {
        target: kicker
        function onExpandedChanged() { if (kicker.expanded) orb.publish() }
    }

    OrbArt {
        id: art
        width: orb.d; height: orb.d
        x: Math.round((orb.width - orb.d) / 2)
        // Rising: sit on the panel's screen-edge side and grow inwards.
        y: !orb.rising ? Math.round((orb.height - orb.d) / 2)
           : orb.topEdge ? Math.round(-orb.pad * 0.5)
           : Math.round(orb.height + orb.pad * 0.5 - orb.d)
        lit: orb.containsMouse || kicker.expanded
    }
}
