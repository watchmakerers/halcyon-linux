.pragma library

// Speaker icon for a volume level, from the icon theme's full-colour set
// (Oxygen draws these the way Vista's tray did).
function iconFor(percent, muted) {
    if (muted || percent <= 0)
        return "audio-volume-muted"
    if (percent < 34)
        return "audio-volume-low"
    if (percent < 67)
        return "audio-volume-medium"
    return "audio-volume-high"
}

// A program's name and icon from its stream's properties.
function appName(stream) {
    if (!stream)
        return ""
    const p = stream.properties || {}
    return p["application.name"] || (stream.client ? stream.client.name : "") || stream.name || "Program"
}

function appIcon(stream, roleIcon) {
    const p = (stream && stream.properties) || {}
    const name = (p["application.name"] || "").toLowerCase()
    return p["application.icon_name"] || roleIcon || p["application.process.binary"] || name || "audio-card"
}

// What to call an output device: its active port ("Headphones", "Speakers")
// rather than the sound card's long name, like Vista.
function deviceName(sink) {
    if (!sink)
        return "No device"
    const ports = sink.ports || []
    const port = ports[sink.activePortIndex]
    if (port && port.description)
        return port.description
    return sink.description || "Speakers"
}

function deviceIcon(sink) {
    if (!sink)
        return "audio-card"
    const name = deviceName(sink).toLowerCase()
    if (sink.formFactor === "headphone" || sink.formFactor === "headset" || name.indexOf("headphone") >= 0)
        return "audio-headphones"
    return "audio-speakers"
}
