import QtQuick
import QtMultimedia
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as P5Support

// DreamScene: animated wallpapers, after Vista Ultimate's. Built-in scenes
// are plain QML (no video files), or play a video of your own on a loop.
// Everything pauses on battery if you ask it to.
WallpaperItem {
    id: root

    readonly property string scene: root.configuration.Scene || "aurora"
    readonly property real speed: Math.max(25, Math.min(200, root.configuration.Speed || 100)) / 100
    readonly property bool onBattery: power.hasAdapter && !power.pluggedIn
    readonly property bool running: !(root.configuration.PauseOnBattery && onBattery)

    accentColor: loader.item && loader.item.accent ? loader.item.accent : "#2a9fd6"

    Rectangle {                      // shown under everything, and while a scene loads
        anchors.fill: parent
        color: "#0b3a66"
    }

    Loader {
        id: loader
        anchors.fill: parent
        active: root.scene !== "video"
        source: ({ aurora: "Aurora.qml", aqua: "Aqua.qml", bokeh: "Bokeh.qml", fields: "Fields.qml" })[root.scene]
                || "Aurora.qml"
        onLoaded: {
            item.running = Qt.binding(() => root.running)
            item.speed = Qt.binding(() => root.speed)
        }
    }

    // ----------------------------------------------------- your own video ---
    MediaPlayer {
        id: player
        source: root.scene === "video" ? root.configuration.VideoFile : ""
        loops: MediaPlayer.Infinite
        videoOutput: video
        // no audioOutput: wallpapers stay silent
        onSourceChanged: if (source.toString() !== "" && root.running) play()
        onErrorOccurred: (error, message) => console.warn("DreamScene video:", message)
    }
    VideoOutput {
        id: video
        anchors.fill: parent
        visible: root.scene === "video" && root.configuration.VideoFile !== ""
        fillMode: VideoOutput.PreserveAspectCrop
    }
    Text {
        anchors.centerIn: parent
        visible: root.scene === "video" && root.configuration.VideoFile === ""
        color: "white"
        font.pixelSize: 22
        text: "Choose a video in the wallpaper settings"
    }
    onRunningChanged: {
        if (root.scene !== "video")
            return
        if (running)
            player.play()
        else
            player.pause()
    }

    // ------------------------------------------------- on battery or not ---
    P5Support.DataSource {
        id: power
        engine: "powermanagement"
        connectedSources: ["AC Adapter"]
        readonly property var ac: data["AC Adapter"] || {}
        // desktops have no adapter: always "plugged in"
        readonly property bool hasAdapter: ac["Plugged in"] !== undefined
        readonly property bool pluggedIn: ac["Plugged in"] === true
    }
}
