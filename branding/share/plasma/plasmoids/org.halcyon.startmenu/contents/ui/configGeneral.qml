import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_floatingOrb: floating.checked

    Kirigami.FormLayout {
        QQC2.CheckBox {
            id: floating
            Kirigami.FormData.label: "Start orb:"
            text: "Rise above the taskbar"
        }
        QQC2.Label {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            wrapMode: Text.Wrap
            font: Kirigami.Theme.smallFont
            opacity: 0.7
            text: "The orb grows into the gap of a floating horizontal panel. On a panel that isn't floating it just fills the panel."
        }
    }
}
