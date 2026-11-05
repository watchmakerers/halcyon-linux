import QtQuick
import org.kde.kirigami as Kirigami

// "All Programs": the category tree, expanding in place like Vista's.
Column {
    id: tree
    property var srcModel
    property int depth: 0
    readonly property real gu: Kirigami.Units.gridUnit
    width: parent ? parent.width : 0

    Repeater {
        model: tree.srcModel
        delegate: Column {
            id: node
            required property int index
            required property var model
            readonly property bool folder: !!model.hasChildren
            property bool open: false
            width: tree.width

            AppRow {
                id: leaf
                title: node.model.display || ""
                icon: node.folder ? (node.open ? "folder-open" : "folder") : node.model.decoration
                indent: tree.depth * tree.gu * 0.9
                height: Math.round(tree.gu * 1.55)
                onActivated: node.folder ? node.open = !node.open : kicker.launch(tree.srcModel, node.index)
                onContextRequested: (x, y) => {
                    if (!node.folder) menu.showActions(tree.srcModel, node.index, node.model.actionList, leaf, x, y)
                }
            }
            Loader {
                width: tree.width
                // A Loader keeps its last height after unloading, which left a gap
                // under a collapsed folder; tie the height to the loaded tree.
                height: active && item ? item.implicitHeight : 0
                active: node.open
                source: "AppTree.qml"
                onLoaded: {
                    item.depth = tree.depth + 1
                    item.srcModel = tree.srcModel.modelForRow(node.index)
                }
            }
        }
    }
}
