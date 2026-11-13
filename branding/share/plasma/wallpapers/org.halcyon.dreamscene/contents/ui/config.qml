import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Dialogs
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: root
    twinFormLayouts: parentLayout

    property string cfg_Scene
    property string cfg_VideoFile
    property alias cfg_Speed: speed.value
    property alias cfg_PauseOnBattery: battery.checked
    property alias formLayout: root

    readonly property var scenes: [
        { id: "aurora", name: "Aurora: northern lights over the hills" },
        { id: "aqua", name: "Aqua: sunbeams and bubbles under water" },
        { id: "bokeh", name: "Bokeh: drifting lights on blue" },
        { id: "fields", name: "Fields: bands of light across blue and green" },
        { id: "video", name: "My own video" }
    ]

    QQC2.ComboBox {
        Kirigami.FormData.label: "Scene:"
        model: root.scenes
        textRole: "name"
        valueRole: "id"
        currentIndex: Math.max(0, root.scenes.findIndex(s => s.id === root.cfg_Scene))
        onActivated: root.cfg_Scene = currentValue
    }

    RowLayout {
        Kirigami.FormData.label: "Video:"
        visible: root.cfg_Scene === "video"
        QQC2.TextField {
            Layout.preferredWidth: Kirigami.Units.gridUnit * 16
            readOnly: true
            placeholderText: "No video chosen"
            text: root.cfg_VideoFile ? decodeURIComponent(root.cfg_VideoFile.toString().replace("file://", "")) : ""
        }
        QQC2.Button {
            icon.name: "document-open"
            text: "Choose…"
            onClicked: picker.open()
        }
    }
    QQC2.Label {
        visible: root.cfg_Scene === "video"
        text: "The video plays silently on a loop. Short, smooth clips work best."
        opacity: 0.7
    }

    QQC2.Slider {
        id: speed
        Kirigami.FormData.label: "Speed:"
        visible: root.cfg_Scene !== "video"
        from: 25; to: 200; stepSize: 25
        Layout.preferredWidth: Kirigami.Units.gridUnit * 12
    }

    QQC2.CheckBox {
        id: battery
        Kirigami.FormData.label: "Battery:"
        text: "Pause the animation when running on battery"
    }

    FileDialog {
        id: picker
        title: "Choose a video"
        nameFilters: ["Videos (*.mp4 *.webm *.mkv *.mov *.avi *.m4v)", "All files (*)"]
        onAccepted: root.cfg_VideoFile = selectedFile.toString()
    }
}
