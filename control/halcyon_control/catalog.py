"""What Control Panel shows: Vista's categories, the tasks under each, and
what each task opens (a System Settings page or a Halcyon tool). Tasks whose
target isn't installed are left out, so every link works.

    python3 -m halcyon_control.catalog --selftest
"""
import os
import shutil
import sys

KCM_ROOT = "/usr/lib/qt6/plugins/plasma/kcms"

# A task: (title, target, keywords). target is "kcm:<name>" (a System Settings
# page) or "app:<command line>" (its first word must be on PATH).
# A category: (id, title, icon, blurb links shown on the home page, groups),
# groups being (green heading, [tasks]).
CATEGORIES = [
    ("system", "System and Maintenance", "computer", [
        "Get started with Halcyon", "Check this computer's performance rating", "Back up your computer"], [
        ("Welcome Center", [
            ("Get started with Halcyon", "app:halcyon-welcome", "welcome tour"),
        ]),
        ("System", [
            ("View basic information about your computer", "kcm:kcm_about-distro", "about version cpu memory"),
            ("View detailed hardware information", "app:kinfocenter", "device manager hardware info"),
            ("Check this computer's performance rating", "app:halcyon-experience", "experience index score benchmark"),
        ]),
        ("Backup and Restore Center", [
            ("Back up your computer", "app:halcyon-backup", "backup restore snapshot"),
            ("Restore files from a backup", "app:halcyon-backup", "backup restore"),
        ]),
        ("Halcyon Update", [
            ("Check for updates", "app:halcyon-update", "update upgrade patches"),
        ]),
        ("Power Options", [
            ("Change power-saving settings", "kcm:kcm_powerdevilprofilesconfig", "power battery sleep suspend"),
        ]),
        ("Startup and Services", [
            ("Choose programs that start with the computer", "kcm:kcm_autostart", "startup autostart"),
            ("Manage background services", "kcm:kcm_kded", "services daemons"),
            ("Change how files are indexed for search", "kcm:kcm_baloofile", "indexing search files"),
        ]),
    ]),
    ("security", "Security", "security-high", [
        "Check for updates", "Turn the firewall on or off", "Lock the computer when it's idle"], [
        ("Halcyon Update", [
            ("Check for updates", "app:halcyon-update", "update security patches"),
        ]),
        ("Firewall", [
            ("Turn the firewall on or off", "kcm:kcm_firewall", "firewall ports"),
        ]),
        ("Lock Screen", [
            ("Lock the computer when it's idle", "kcm:kcm_screenlocker", "lock password idle"),
        ]),
        ("Privacy", [
            ("Choose what usage information is shared", "kcm:kcm_feedback", "privacy telemetry feedback"),
            ("Clear recent files history", "kcm:kcm_recentFiles", "privacy history recent"),
        ]),
    ]),
    ("network", "Network and Internet", "network-workgroup", [
        "View network status and tasks", "Connect to a network", "Set up Bluetooth devices"], [
        ("Network and Sharing Center", [
            ("View network status and tasks", "app:halcyon-network", "network status internet map"),
            ("Connect to a network", "kcm:kcm_networkmanagement", "wifi wireless connect vpn"),
            ("Manage network connections", "kcm:kcm_networkmanagement", "adapter ethernet wifi"),
        ]),
        ("Internet Options", [
            ("Change proxy settings", "kcm:kcm_proxy", "proxy internet"),
            ("Change web search shortcuts", "kcm:kcm_webshortcuts", "search keywords"),
            ("Set your default web browser", "kcm:kcm_componentchooser", "browser default"),
        ]),
        ("Bluetooth Devices", [
            ("Set up Bluetooth devices", "kcm:kcm_bluetooth", "bluetooth pair"),
        ]),
    ]),
    ("hardware", "Hardware and Sound", "audio-card", [
        "Change system sounds", "Mouse", "Adjust screen resolution"], [
        ("Sound", [
            ("Adjust system volume and devices", "kcm:kcm_pulseaudio", "audio volume speakers microphone"),
            ("Change system sounds", "kcm:kcm_soundtheme", "sounds events"),
        ]),
        ("Mouse and Keyboard", [
            ("Mouse", "kcm:kcm_mouse", "mouse pointer buttons speed"),
            ("Touchpad", "kcm:kcm_touchpad", "touchpad trackpad tap"),
            ("Keyboard", "kcm:kcm_keyboard", "keyboard repeat layout"),
            ("Game controllers", "kcm:kcm_gamecontroller", "joystick gamepad controller"),
            ("Pen and tablet", "kcm:kcm_tablet", "tablet pen stylus"),
        ]),
        ("Display", [
            ("Adjust screen resolution", "kcm:kcm_kscreen", "display monitor resolution scale"),
            ("Reduce blue light at night", "kcm:kcm_nightlight", "night light color"),
        ]),
        ("AutoPlay", [
            ("Change what happens when you insert a disc or device", "kcm:kcm_solid_actions", "autoplay media"),
            ("Change how removable drives are mounted", "kcm:kcm_device_automounter", "usb mount drive"),
        ]),
        ("Printers", [
            ("Add or manage printers", "kcm:kcm_printer_manager", "printer print"),
        ]),
        ("Power Options", [
            ("Change power-saving settings", "kcm:kcm_powerdevilprofilesconfig", "power battery"),
        ]),
    ]),
    ("programs", "Programs", "applications-other", [
        "Get new programs", "Set your default programs", "Set up games"], [
        ("Programs and Features", [
            ("Get new programs", "app:plasma-discover", "install uninstall software store"),
            ("Install programs from the AUR", "app:konsole --hide-menubar -e halcyon-aur", "aur packages"),
            ("Set up games", "app:halcyon-gaming", "steam wine proton games"),
        ]),
        ("Default Programs", [
            ("Set your default programs", "kcm:kcm_componentchooser", "default browser email"),
            ("Always open a file type with a certain program", "kcm:kcm_filetypes", "file associations types"),
        ]),
        ("Startup Programs", [
            ("Choose programs that start with the computer", "kcm:kcm_autostart", "startup autostart"),
        ]),
        ("Desktop Gadgets", [
            ("Add gadgets to the desktop", "app:halcyon-gadgets", "gadgets sidebar"),
        ]),
    ]),
    ("users", "User Accounts", "system-users", [
        "Change your account picture", "Add or remove user accounts", "Change the login screen"], [
        ("User Accounts", [
            ("Change your account picture", "kcm:kcm_users", "picture avatar photo"),
            ("Change your password", "kcm:kcm_users", "password"),
            ("Add or remove user accounts", "kcm:kcm_users", "users accounts add remove"),
        ]),
        ("Online Accounts", [
            ("Add online accounts", "kcm:kcm_kaccounts", "online google nextcloud"),
        ]),
        ("Login Screen", [
            ("Change the login screen", "kcm:kcm_sddm", "login sddm greeter"),
        ]),
    ]),
    ("appearance", "Appearance and Personalization", "preferences-desktop-theme", [
        "Change desktop background", "Change the color of windows", "Change screen saver"], [
        ("Personalization", [
            ("Change the color of windows", "app:halcyon-colors", "color colour window tint aero"),
            ("Change desktop background", "kcm:kcm_wallpaper", "wallpaper background"),
            ("Change screen saver", "app:halcyon-screensaver --settings", "screensaver"),
            ("Use a Windows desktop theme", "app:halcyon-wintheme", "theme plus xp"),
            ("Change the mouse pointers", "kcm:kcm_cursortheme", "cursor pointer"),
            ("Change the global theme", "kcm:kcm_lookandfeel", "theme look feel"),
        ]),
        ("Fonts and Icons", [
            ("Change fonts", "kcm:kcm_fonts", "font text size"),
            ("Install or remove fonts", "kcm:kcm_fontinst", "font install"),
            ("Change icons", "kcm:kcm_icons", "icons"),
        ]),
        ("Desktop and Windows", [
            ("Switch between classic and tiling desktop", "app:halcyon-mode toggle", "tiling classic mode"),
            ("Turn desktop effects on or off", "kcm:kcm_kwin_effects", "effects animations blur"),
            ("Change window borders", "kcm:kcm_kwindecoration", "title bar decoration"),
            ("Change the startup splash screen", "kcm:kcm_splashscreen", "splash boot"),
        ]),
        ("Desktop Gadgets", [
            ("Add gadgets to the desktop", "app:halcyon-gadgets", "gadgets sidebar"),
        ]),
    ]),
    ("clock", "Clock, Language, and Region", "preferences-system-time", [
        "Change the date and time", "Change display language", "Change keyboard layouts"], [
        ("Date and Time", [
            ("Change the date and time", "kcm:kcm_clock", "date time clock timezone"),
        ]),
        ("Regional and Language Options", [
            ("Change display language", "kcm:kcm_regionandlang", "language locale"),
            ("Change number, date and currency formats", "kcm:kcm_regionandlang", "formats region currency"),
            ("Change keyboard layouts", "kcm:kcm_keyboard", "keyboard layout input"),
            ("Change spell checking", "kcm:kcm_spellchecking", "spelling dictionary"),
        ]),
    ]),
    ("access", "Ease of Access", "preferences-desktop-accessibility", [
        "Use the on-screen keyboard", "Optimize visual display", "Learn keyboard shortcuts"], [
        ("Ease of Access Center", [
            ("Optimize visual display", "kcm:kcm_access", "accessibility zoom contrast sticky keys"),
            ("Use the on-screen keyboard", "app:halcyon-osk toggle", "osk keyboard touch"),
            ("Set up a virtual keyboard", "kcm:kcm_virtualkeyboard", "virtual keyboard"),
            ("Slow down or turn off animations", "kcm:kcm_animations", "animation speed motion"),
        ]),
        ("Keyboard Shortcuts", [
            ("Learn keyboard shortcuts", "app:halcyon-keys", "shortcuts cheat sheet"),
            ("Change keyboard shortcuts", "kcm:kcm_keys", "shortcuts hotkeys"),
        ]),
    ]),
    ("more", "Additional Options", "preferences-other", [
        "Change notification settings", "Change window behavior", "Open all settings"], [
        ("Notifications", [
            ("Change notification settings", "kcm:kcm_notifications", "notifications popups"),
        ]),
        ("Windows and Desktops", [
            ("Change window behavior", "kcm:kcm_kwinoptions", "focus window behaviour"),
            ("Change window rules", "kcm:kcm_kwinrules", "rules"),
            ("Change the task switcher", "kcm:kcm_kwintabbox", "alt tab switcher"),
            ("Change screen edges and corners", "kcm:kcm_kwinscreenedges", "corners edges"),
            ("Add or remove virtual desktops", "kcm:kcm_kwin_virtualdesktops", "workspaces desktops"),
            ("Manage activities", "kcm:kcm_activities", "activities"),
        ]),
        ("Search and Session", [
            ("Change search settings", "kcm:kcm_plasmasearch", "krunner search"),
            ("Change what happens at log out", "kcm:kcm_smserver", "session logout"),
        ]),
        ("All Settings", [
            ("Open all settings", "app:systemsettings", "system settings everything"),
        ]),
    ]),
]


def installed_kcms(root=KCM_ROOT):
    """Names of the System Settings pages on this computer."""
    found = set()
    for base, _, files in os.walk(root):
        for f in files:
            if f.endswith(".so"):
                found.add(f[:-3])
    return found


def available(target, kcms, which=shutil.which):
    kind, _, what = target.partition(":")
    if kind == "kcm":
        return what in kcms
    return kind == "app" and bool(what) and which(what.split()[0]) is not None


def command(target):
    """The command line that opens a task."""
    kind, _, what = target.partition(":")
    if kind == "kcm":
        if shutil.which("kcmshell6"):
            return ["kcmshell6", what]
        return ["systemsettings", what]
    return what.split()


def build(kcms=None, which=shutil.which):
    """The catalog with only the tasks that work here; empty groups and categories drop out."""
    kcms = installed_kcms() if kcms is None else kcms
    cats = []
    for cid, title, icon, blurbs, groups in CATEGORIES:
        kept = []
        for heading, tasks in groups:
            ok = [t for t in tasks if available(t[1], kcms, which)]
            if ok:
                kept.append((heading, ok))
        if kept:
            titles = {t[0] for _, ts in kept for t in ts}
            shown = [b for b in blurbs if b in titles]
            cats.append((cid, title, icon, shown, kept))
    return cats


def all_tasks(cats):
    """Every distinct task once, alphabetical (the Classic View)."""
    seen = {}
    for cid, _, icon, _, groups in cats:
        for _, tasks in groups:
            for t in tasks:
                seen.setdefault(t[0], (t, cid, icon))
    return [seen[k] for k in sorted(seen, key=str.lower)]


def search(cats, text):
    words = text.lower().split()
    if not words:
        return []
    return [(t, cid, icon) for t, cid, icon in all_tasks(cats)
            if all(w in f"{t[0]} {t[2]}".lower() for w in words)]


def _selftest():
    import tempfile
    ids = [c[0] for c in CATEGORIES]
    assert len(ids) == len(set(ids)), "duplicate category ids"
    for cid, title, icon, blurbs, groups in CATEGORIES:
        assert title and icon and groups, cid
        titles = {t[0] for _, ts in groups for t in ts}
        for b in blurbs:
            assert b in titles, f"{cid}: home link {b!r} is not one of its tasks"
        for heading, tasks in groups:
            assert heading and tasks, (cid, heading)
            for t in tasks:
                assert len(t) == 3 and t[0] and t[2], t
                kind, _, what = t[1].partition(":")
                assert kind in ("kcm", "app") and what, t
                if kind == "kcm":
                    assert what.startswith("kcm") or what == "kinfocenter", t
    # Discovery walks subfolders and only counts plugins.
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "systemsettings"))
        for p in ("kcm_mouse.so", "systemsettings/kcm_users.so", "systemsettings/readme.txt"):
            open(os.path.join(d, p), "w").close()
        assert installed_kcms(d) == {"kcm_mouse", "kcm_users"}
    # Filtering: only what exists survives, and empty categories vanish.
    cats = build({"kcm_mouse", "kcm_users"}, which=lambda c: "/usr/bin/" + c if c == "halcyon-colors" else None)
    assert [c[0] for c in cats] == ["hardware", "users", "appearance"], [c[0] for c in cats]
    hw = dict((c[0], c) for c in cats)["hardware"]
    assert hw[3] == ["Mouse"] and hw[4] == [("Mouse and Keyboard", [hw[4][0][1][0]])]
    assert command("app:halcyon-mode toggle") == ["halcyon-mode", "toggle"]
    assert [t[0][0] for t in search(cats, "WINDOW color")] == ["Change the color of windows"]
    assert len(all_tasks(cats)) == len({t[0][0] for t in all_tasks(cats)})
    print("catalog selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        for cid, title, _, _, groups in build():
            print(title)
            for heading, tasks in groups:
                print("   ", heading, "-", ", ".join(t[0] for t in tasks))
