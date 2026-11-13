// Halcyon Aero default layout: one glass taskbar along the bottom.
var panel = new Panel;
panel.location = "bottom";
panel.height = Math.round(gridUnit * 2.1);
panel.floating = false;  // docked: fills the whole bottom edge
panel.lengthMode = "fill";

var start = panel.addWidget("org.halcyon.startmenu");  // Vista-style Start orb + menu
start.currentConfigGroup = ["General"];
start.writeConfig("icon", "/usr/share/pixmaps/halcyon-logo.png");

panel.addWidget("org.halcyon.workspaces");  // numbered round workspace orbs
var tasks = panel.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "applications:firefox.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:halcyon-games.desktop",
    "applications:systemsettings.desktop"
]);
panel.addWidget("org.kde.plasma.marginsseparator");
var tray = panel.addWidget("org.kde.plasma.systemtray");
// Halcyon's Vista-style volume flyout instead of Plasma's; the stock one is
// listed as known so the tray doesn't add it back by itself.
var trayItems = ["org.kde.kscreen", "org.kde.plasma.battery", "org.kde.plasma.bluetooth",
                 "org.kde.plasma.brightness", "org.kde.plasma.cameraindicator", "org.kde.plasma.clipboard",
                 "org.kde.plasma.devicenotifier", "org.kde.plasma.keyboardlayout",
                 "org.kde.plasma.manage-inputmethod", "org.kde.plasma.mediacontroller",
                 "org.kde.plasma.networkmanagement", "org.kde.plasma.notifications", "org.halcyon.volume"];
tray.currentConfigGroup = ["General"];
tray.writeConfig("extraItems", trayItems);
tray.writeConfig("knownItems", trayItems.concat(["org.kde.plasma.volume"]));
panel.addWidget("org.halcyon.clock");                  // Vista-style clock with the calendar flyout
panel.addWidget("org.kde.plasma.showdesktop");

var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    var d = desktopsArray[j];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file:///usr/share/wallpapers/Halcyon/");
}
