import QtQuick
import QtQuick.Layouts
import QtCore
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami
import org.kde.coreaddons as KCoreAddons

// The Start menu popup, laid out like Windows Vista's:
//   left   white pane: pinned programs, most-used programs, All Programs; Start Search below
//   right  dark glass: user picture, places, settings links; power / lock / more below
Item {
    id: menu

    readonly property real gu: Kirigami.Units.gridUnit
    readonly property real leftW: Math.round(gu * 15.5)
    readonly property real rightW: Math.round(gu * 8.8)
    readonly property real gap: Math.round(gu * 0.45)
    readonly property real fieldH: Math.round(gu * 1.6)
    readonly property real menuW: leftW + gap + rightW
    readonly property real menuH: Math.round(gu * 30)

    Layout.minimumWidth: menuW
    Layout.maximumWidth: menuW
    Layout.preferredWidth: menuW
    Layout.minimumHeight: menuH
    Layout.maximumHeight: menuH
    Layout.preferredHeight: menuH

    // home | all | recent | search
    property string mode: "home"
    // icon shown in the picture frame while a right-column link is hovered
    property string hoverIcon: ""

    function reset() {
        search.text = ""
        mode = "home"
        hoverIcon = ""
        rebuildFrequent()
        search.forceActiveFocus()
    }
    Connections {
        target: kicker
        function onExpandedChanged() { if (kicker.expanded) menu.reset() }
    }
    Component.onCompleted: {
        reset()
        // The orb copy below reaches past our edges into the popup frame;
        // stop Plasma's containers from clipping it there.
        for (let p = parent; p; p = p.parent) p.clip = false
    }

    function shellQuote(s) { return "'" + s.replace(/'/g, "'\\''") + "'" }

    // ------------------------------------------------ most-used programs ---
    component Entry: QtObject {
        required property int index
        required property var model
        readonly property string fid: (model.favoriteId || "").replace(/^applications:/, "")
        readonly property string title: model.display || ""
        readonly property var icon: model.decoration
        readonly property string desc: model.description || ""
        readonly property var actions: model.actionList
    }
    Instantiator {
        id: pinned
        model: kicker.favoritesModel
        delegate: Entry {}
        onObjectAdded: Qt.callLater(menu.rebuildFrequent)
        onObjectRemoved: Qt.callLater(menu.rebuildFrequent)
    }
    Instantiator {
        id: popular
        model: kicker.popularApps
        delegate: Entry {}
        onObjectAdded: Qt.callLater(menu.rebuildFrequent)
        onObjectRemoved: Qt.callLater(menu.rebuildFrequent)
    }
    Instantiator {
        id: starters
        model: kicker.starterApps
        delegate: Entry {}
        onObjectAdded: Qt.callLater(menu.rebuildFrequent)
        onObjectRemoved: Qt.callLater(menu.rebuildFrequent)
    }

    // As many as fit between the pinned programs and "All Programs".
    readonly property int maxFrequent: Math.max(0, Math.floor(
        (pane.height - pinnedCol.height - footer.height - gu * 0.9) / Math.round(gu * 1.85)))
    onMaxFrequentChanged: Qt.callLater(rebuildFrequent)

    property var frequent: []
    function rebuildFrequent() {
        const out = [], seen = {}
        const mark = (o) => { seen["id:" + o.fid] = true; seen["t:" + o.title.toLowerCase()] = true }
        const has = (o) => seen["id:" + o.fid] || seen["t:" + o.title.toLowerCase()]
        for (let i = 0; i < pinned.count; ++i) { const o = pinned.objectAt(i); if (o) mark(o) }
        const take = (inst, model) => {
            for (let i = 0; i < inst.count && out.length < maxFrequent; ++i) {
                const o = inst.objectAt(i)
                if (!o || !o.title || has(o)) continue
                mark(o)
                out.push({ model: model, row: o.index, title: o.title, icon: o.icon, actions: o.actions })
            }
        }
        take(popular, kicker.popularApps)
        take(starters, kicker.starterApps)
        frequent = out
    }

    // Vista's two big pinned entries get role names, with the program underneath.
    function pinnedTitle(o) {
        if (o.fid === "preferred://browser") return "Internet"
        if (o.fid === "preferred://mail") return "E-mail"
        return o.title
    }
    function pinnedSubtitle(o) {
        return o.fid.indexOf("preferred://") === 0 ? o.title : o.desc
    }

    // --------------------------------------------------- context menus ---
    property var actionModel: null
    property int actionRow: -1
    property var actionItems: []
    function showActions(model, row, actions, item, x, y) {
        const list = (actions || []).filter(a => a && a.type !== "separator" && a.type !== "title"
                                             && a.text && !a.subActions)
        if (!list.length) return
        actionModel = model; actionRow = row; actionItems = list
        actionMenu.popup(item, x, y)
    }
    PlasmaComponents3.Menu {
        id: actionMenu
        Instantiator {
            model: menu.actionItems
            delegate: PlasmaComponents3.MenuItem {
                required property var modelData
                text: modelData.text
                icon.name: typeof modelData.icon === "string" ? modelData.icon : ""
                onClicked: {
                    if (menu.actionModel.trigger(menu.actionRow, modelData.actionId, modelData.actionArgument))
                        kicker.expanded = false
                    Qt.callLater(menu.rebuildFrequent)
                }
            }
            onObjectAdded: (i, o) => actionMenu.insertItem(i, o)
            onObjectRemoved: (i, o) => actionMenu.removeItem(o)
        }
    }

    PlasmaComponents3.Menu {
        id: powerMenu
        Instantiator {
            model: kicker.systemModel
            delegate: PlasmaComponents3.MenuItem {
                required property int index
                required property var model
                text: model.display
                onClicked: {
                    kicker.systemModel.trigger(index, "", null)
                    kicker.expanded = false
                }
            }
            onObjectAdded: (i, o) => powerMenu.insertItem(i, o)
            onObjectRemoved: (i, o) => powerMenu.removeItem(o)
        }
    }

    // ======================================================= left side ===
    Rectangle {
        id: pane
        x: 0; y: 0
        width: menu.leftW
        height: menu.menuH - menu.fieldH - menu.gap
        radius: 3
        color: "#ffffff"
        border.color: "#6f8aa6"
        clip: true

        Item {
            id: body
            anchors { left: parent.left; right: parent.right; top: parent.top; bottom: footer.top
                      margins: 3 }

            // Home: pinned, separator, most used
            Column {
                anchors.fill: parent
                visible: menu.mode === "home"
                Column {
                    id: pinnedCol
                    width: parent.width
                    Repeater {
                        model: kicker.favoritesModel
                        delegate: AppRow {
                            id: pin
                            required property int index
                            required property var model
                            readonly property var o: ({ fid: (model.favoriteId || "").replace(/^applications:/, ""),
                                                        title: model.display || "", desc: model.description || "" })
                            big: true
                            title: menu.pinnedTitle(o)
                            subtitle: menu.pinnedSubtitle(o)
                            icon: model.decoration
                            onActivated: kicker.launch(kicker.favoritesModel, index)
                            onContextRequested: (x, y) => menu.showActions(kicker.favoritesModel, index, model.actionList, pin, x, y)
                        }
                    }
                    Separator { visible: menu.frequent.length > 0 && kicker.favoritesModel.count > 0; inset: 6 }
                }
                Repeater {
                    model: menu.frequent
                    delegate: AppRow {
                        id: freq
                        required property var modelData
                        title: modelData.title
                        icon: modelData.icon
                        onActivated: kicker.launch(modelData.model, modelData.row)
                        onContextRequested: (x, y) => menu.showActions(modelData.model, modelData.row, modelData.actions, freq, x, y)
                    }
                }
            }

            // All Programs
            PlasmaComponents3.ScrollView {
                anchors.fill: parent
                visible: menu.mode === "all"
                PlasmaComponents3.ScrollBar.horizontal.policy: PlasmaComponents3.ScrollBar.AlwaysOff
                contentWidth: availableWidth
                AppTree {
                    width: parent ? parent.width : 0
                    srcModel: menu.mode === "all" ? kicker.rootModel : null
                }
            }

            // Recent Items
            ListView {
                id: recentList
                anchors.fill: parent
                visible: menu.mode === "recent"
                clip: true
                model: menu.mode === "recent" ? kicker.recentDocs : null
                boundsBehavior: Flickable.StopAtBounds
                delegate: AppRow {
                    id: doc
                    required property int index
                    required property var model
                    width: ListView.view.width
                    title: model.display || ""
                    icon: model.decoration
                    onActivated: kicker.launch(kicker.recentDocs, index)
                    onContextRequested: (x, y) => menu.showActions(kicker.recentDocs, index, model.actionList, doc, x, y)
                }
                Text {
                    anchors.centerIn: parent
                    visible: recentList.count === 0
                    text: "No recent items"
                    color: "#6d6d6d"
                    font.italic: true
                }
            }

            // Search results
            ListView {
                id: results
                anchors.fill: parent
                visible: menu.mode === "search"
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: kicker.runnerModel.count > 0 ? kicker.runnerModel.modelForRow(0) : null
                onModelChanged: currentIndex = 0
                onCountChanged: currentIndex = 0
                delegate: AppRow {
                    id: hit
                    required property int index
                    required property var model
                    width: ListView.view.width
                    title: model.display || ""
                    icon: model.decoration
                    current: ListView.isCurrentItem
                    onActivated: kicker.launch(results.model, index)
                    onContextRequested: (x, y) => menu.showActions(results.model, index, model.actionList, hit, x, y)
                }
                Text {
                    anchors.centerIn: parent
                    visible: results.count === 0 && !kicker.runnerModel.querying
                    text: "No items match your search."
                    color: "#6d6d6d"
                    font.italic: true
                }
            }
        }

        // "All Programs" / "Back" / "See all results"
        Column {
            id: footer
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 3 }
            Separator { inset: 6 }
            MouseArea {
                id: footRow
                width: parent.width
                height: Math.round(menu.gu * 1.6)
                hoverEnabled: true
                onClicked: {
                    if (menu.mode === "home") menu.mode = "all"
                    else if (menu.mode === "search") kicker.run("halcyon-search " + menu.shellQuote(search.text))
                    else menu.mode = "home"
                }
                Rectangle {
                    anchors.fill: parent; anchors.margins: 1; radius: 3
                    visible: footRow.containsMouse
                    border.color: "#84b9ea"
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#f4faff" }
                        GradientStop { position: 1; color: "#d3e9fc" }
                    }
                }
                Triangle {
                    id: footTri
                    visible: menu.mode !== "search"
                    flip: menu.mode !== "home"
                    anchors { left: parent.left; leftMargin: Math.round(menu.gu * 0.6); verticalCenter: parent.verticalCenter }
                }
                Text {
                    anchors { left: footTri.right; leftMargin: Math.round(menu.gu * 0.9); verticalCenter: parent.verticalCenter }
                    text: menu.mode === "home" ? "All Programs" : menu.mode === "search" ? "See all results" : "Back"
                    color: "#000000"
                    font.family: Kirigami.Theme.defaultFont.family
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    font.bold: true
                }
            }
        }
    }

    // Start Search
    Rectangle {
        id: field
        x: 0
        y: menu.menuH - menu.fieldH
        width: menu.leftW
        height: menu.fieldH
        radius: 2
        color: "#ffffff"
        border.color: search.activeFocus ? "#3c7fb1" : "#6f8aa6"

        TextInput {
            id: search
            anchors { left: parent.left; right: glass.left; leftMargin: 6; rightMargin: 4; verticalCenter: parent.verticalCenter }
            clip: true
            color: "#000000"
            selectByMouse: true
            selectionColor: "#3399ff"
            font.family: Kirigami.Theme.defaultFont.family
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
            onTextChanged: {
                kicker.runnerModel.query = text
                if (text.length) menu.mode = "search"
                else if (menu.mode === "search") menu.mode = "home"
            }
            Keys.onEscapePressed: {
                if (text.length) text = ""
                else if (menu.mode !== "home") menu.mode = "home"
                else kicker.expanded = false
            }
            Keys.onDownPressed: if (menu.mode === "search") results.incrementCurrentIndex()
            Keys.onUpPressed: if (menu.mode === "search") results.decrementCurrentIndex()
            Keys.onReturnPressed: activateFirst()
            Keys.onEnterPressed: activateFirst()
            function activateFirst() {
                if (menu.mode === "search" && results.count > 0)
                    kicker.launch(results.model, Math.max(0, results.currentIndex))
            }
        }
        Text {
            anchors { left: search.left; verticalCenter: parent.verticalCenter }
            visible: search.text.length === 0
            text: "Start Search"
            color: "#6d6d6d"
            font.italic: true
            font.family: Kirigami.Theme.defaultFont.family
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
        }
        Kirigami.Icon {
            id: glass
            anchors { right: parent.right; rightMargin: 4; verticalCenter: parent.verticalCenter }
            width: Math.round(menu.fieldH * 0.7); height: width
            source: "edit-find"
        }
        MouseArea {  // clicking the frame focuses the field
            anchors.fill: parent
            acceptedButtons: Qt.NoButton
            cursorShape: Qt.IBeamCursor
        }
    }

    // ====================================================== right side ===
    KCoreAddons.KUser { id: kuser }

    Item {
        id: right
        x: menu.leftW + menu.gap
        y: 0
        width: menu.rightW
        height: menu.menuH

        // Picture frame: the user's face, or the hovered link's icon.
        Rectangle {
            id: frame
            anchors { top: parent.top; horizontalCenter: parent.horizontalCenter }
            width: Math.round(menu.gu * 4); height: width
            radius: 6
            border.color: Qt.rgba(0, 0.06, 0.12, 0.8)
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#f4fbff" }
                GradientStop { position: 0.48; color: "#c9e2f2" }
                GradientStop { position: 0.52; color: "#9cc2dc" }
                GradientStop { position: 1.0; color: "#d7ecf8" }
            }
            Rectangle {
                id: pic
                anchors.fill: parent
                anchors.margins: Math.round(menu.gu * 0.3)
                radius: 2
                color: "#0d2a44"
                border.color: Qt.rgba(0, 0, 0, 0.5)
                clip: true
                Image {
                    id: face
                    anchors.fill: parent
                    anchors.margins: 1
                    source: kuser.faceIconUrl
                    fillMode: Image.PreserveAspectCrop
                    sourceSize: Qt.size(width * 2, height * 2)
                    opacity: menu.hoverIcon === "" && status === Image.Ready ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 120 } }
                }
                Kirigami.Icon {
                    anchors.fill: parent
                    anchors.margins: Math.round(menu.gu * 0.35)
                    source: menu.hoverIcon || "user-identity"
                    opacity: face.opacity < 1 ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 120 } }
                }
            }
        }

        Column {
            anchors { top: frame.bottom; topMargin: Math.round(menu.gu * 0.5); left: parent.left; right: parent.right }
            readonly property color rule: Qt.rgba(1, 1, 1, 0.16)

            PlaceRow { text: kuser.fullName || kuser.loginName; icon: "user-home"
                       onActivated: kicker.open(StandardPaths.writableLocation(StandardPaths.HomeLocation)) }
            PlaceRow { text: "Documents"; icon: "folder-documents"
                       onActivated: kicker.open(StandardPaths.writableLocation(StandardPaths.DocumentsLocation)) }
            PlaceRow { text: "Pictures"; icon: "folder-image"
                       onActivated: kicker.open(StandardPaths.writableLocation(StandardPaths.PicturesLocation)) }
            PlaceRow { text: "Music"; icon: "folder-sound"
                       onActivated: kicker.open(StandardPaths.writableLocation(StandardPaths.MusicLocation)) }
            PlaceRow { text: "Games"; icon: "applications-games"; onActivated: kicker.run("halcyon-games") }
            Separator { color: parent.rule }
            PlaceRow { text: "Search"; icon: "system-search"; onActivated: kicker.run("halcyon-search") }
            PlaceRow { text: "Recent Items"; icon: "document-open-recent"; arrow: true
                       onActivated: { search.text = ""; menu.mode = "recent"; search.forceActiveFocus() } }
            PlaceRow { text: "Computer"; icon: "computer"; onActivated: kicker.open("file:///") }
            PlaceRow { text: "Network"; icon: "network-workgroup"; onActivated: kicker.run("dolphin remote:/") }
            PlaceRow { text: "Connect To"; icon: "network-connect"
                       onActivated: kicker.run("systemsettings kcm_networkmanagement") }
            Separator { color: parent.rule }
            PlaceRow { text: "Control Panel"; icon: "preferences-system"; onActivated: kicker.run("systemsettings") }
            PlaceRow { text: "Default Programs"; icon: "preferences-desktop-default-applications"
                       onActivated: kicker.run("systemsettings kcm_componentchooser") }
            PlaceRow { text: "Help and Support"; icon: "help-browser"
                       onActivated: kicker.run("sh -c 'command -v khelpcenter >/dev/null && exec khelpcenter || exec halcyon-welcome'") }
        }

        // Power (red), lock, and the arrow with the rest of the session actions.
        Row {
            anchors { bottom: parent.bottom; left: parent.left; leftMargin: Math.round(menu.gu * 0.3) }
            height: menu.fieldH
            GlossButton {
                width: Math.round(menu.gu * 2.4); height: parent.height
                tint: "#b0231a"; glyph: "power"; tip: "Shut down"
                onClicked: kicker.system("shutdown",
                    "dbus-send --session --type=method_call --dest=org.kde.LogoutPrompt /LogoutPrompt org.kde.LogoutPrompt.promptShutDown")
            }
            GlossButton {
                width: Math.round(menu.gu * 2.4); height: parent.height
                tint: "#36424e"; glyph: "lock"; tip: "Lock this computer"
                onClicked: kicker.system("lock-screen", "loginctl lock-session")
            }
        }
        GlossButton {
            id: more
            anchors { bottom: parent.bottom; right: parent.right; rightMargin: Math.round(menu.gu * 0.3) }
            width: Math.round(menu.gu * 1.4); height: menu.fieldH
            tint: "#36424e"; glyph: "arrow"; tip: "More options"
            onClicked: powerMenu.popup(more, 0, -powerMenu.implicitHeight)
        }
    }

    // ============================================= orb over the menu ===
    // The popup opens over the bit of orb that pokes out of the panel. Draw the
    // orb here too at the same screen spot, so it sits on top of the menu like
    // Vista's. Only the part overlapping the popup shows; the rest is the real one.
    property point origin: Qt.point(0, 0)
    function track() {
        const o = menu.mapToGlobal(0, 0)
        if (o.x !== origin.x || o.y !== origin.y) origin = Qt.point(o.x, o.y)
    }
    Timer {
        interval: 16
        repeat: true
        running: kicker.expanded
        triggeredOnStart: true
        onTriggered: menu.track()
    }
    MouseArea {
        visible: kicker.orbRect.width > 0
        x: kicker.orbRect.x - menu.origin.x
        y: kicker.orbRect.y - menu.origin.y
        width: kicker.orbRect.width
        height: kicker.orbRect.height
        z: 100
        onClicked: kicker.expanded = false
        OrbArt { anchors.fill: parent; lit: true }
    }
}
