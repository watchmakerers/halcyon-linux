import QtQuick

// Vista's pale-blue selection, for hovered rows in the white column.
// Plain hex colours, so Window Color (wintheme.py) can recolour a copy of this file.
Rectangle {
    anchors.fill: parent
    anchors.margins: 1
    radius: 3
    border.color: "#84b9ea"
    gradient: Gradient {
        GradientStop { position: 0; color: "#f4faff" }
        GradientStop { position: 1; color: "#d3e9fc" }
    }
}
