import QtQuick
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.private.kicker as Kicker

// Halcyon Start menu: a Vista-style two-column launcher.
// The glass orb sits in the panel; the menu is the popup.
PlasmoidItem {
    id: kicker  // the kicker models look the applet up by this interface

    preferredRepresentation: compactRepresentation
    compactRepresentation: Orb {}
    fullRepresentation: MenuPanel {}

    Plasmoid.icon: Plasmoid.configuration.icon
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    activationTogglesExpanded: true
    hideOnWindowDeactivate: true
    toolTipMainText: "Start"
    toolTipSubText: ""

    // Screen rectangle of the orb artwork (set by Orb.qml when the menu opens).
    property rect orbRect: Qt.rect(0, 0, 0, 0)

    // ---------------------------------------------------------- models ---
    // Category tree for "All Programs"; also owns the pinned (favorites) model.
    Kicker.RootModel {
        id: rootModel
        autoPopulate: false
        appletInterface: kicker
        flat: false
        sorted: true
        showSeparators: false
        showTopLevelItems: true
        showAllApps: false
        showAllAppsCategorized: false
        showRecentApps: false
        showRecentDocs: false
        showPowerSession: false
        showFavoritesPlaceholder: false

        Component.onCompleted: {
            favoritesModel.initForClient("org.halcyon.startmenu.favorites.instance-" + Plasmoid.id)
            if (!Plasmoid.configuration.favoritesPortedToKAstats) {
                if (favoritesModel.count < 1)
                    favoritesModel.portOldFavorites(Plasmoid.configuration.favoriteApps)
                Plasmoid.configuration.favoritesPortedToKAstats = true
            }
        }
    }
    readonly property alias rootModel: rootModel
    readonly property var favoritesModel: rootModel.favoritesModel

    Kicker.RunnerModel {
        id: runnerModel
        appletInterface: kicker
        favoritesModel: rootModel.favoritesModel
        mergeResults: true
    }
    readonly property alias runnerModel: runnerModel

    // Most-used programs, under the pinned ones.
    Kicker.RecentUsageModel {
        id: popularApps
        shownItems: Kicker.RecentUsageModel.OnlyApps
        ordering: Kicker.RecentUsageModel.Popular
    }
    readonly property alias popularApps: popularApps

    // Until there's usage history, show a starter set like Vista did.
    Kicker.SimpleFavoritesModel {
        id: starterApps
        favorites: Plasmoid.configuration.starterApps
    }
    readonly property alias starterApps: starterApps

    Kicker.RecentUsageModel {
        id: recentDocs
        shownItems: Kicker.RecentUsageModel.OnlyDocs
        ordering: Kicker.RecentUsageModel.Recent
    }
    readonly property alias recentDocs: recentDocs

    Kicker.SystemModel { id: systemModel }
    readonly property alias systemModel: systemModel

    // SystemModel row lookup by id ("shutdown", "lock-screen", ...).
    Instantiator {
        id: systemEntries
        model: systemModel
        delegate: QtObject {
            required property int index
            required property var model
            readonly property string fid: model.favoriteId || ""
        }
    }
    function system(id, fallback) {
        for (let i = 0; i < systemEntries.count; ++i) {
            const e = systemEntries.objectAt(i)
            if (e && e.fid === id) {
                systemModel.trigger(e.index, "", null)
                kicker.expanded = false
                return
            }
        }
        run(fallback)
    }

    // --------------------------------------------------------- actions ---
    P5Support.DataSource {
        id: executable
        engine: "executable"
        onNewData: (source) => disconnectSource(source)
    }
    // Start a program detached from plasmashell, then close the menu.
    function run(cmd) {
        executable.connectSource("setsid -f " + cmd + " >/dev/null 2>&1")
        kicker.expanded = false
    }
    function open(url) {
        Qt.openUrlExternally(url)
        kicker.expanded = false
    }
    function launch(model, row) {
        model.trigger(row, "", null)
        kicker.expanded = false
    }

    Component.onCompleted: rootModel.refresh()
}
