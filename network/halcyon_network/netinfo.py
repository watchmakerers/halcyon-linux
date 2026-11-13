"""Network state for the Network and Sharing Center, read from nmcli and
/sys. No Qt here, so it can be tested on its own.

    python3 -m halcyon_network.netinfo --selftest
    python3 -m halcyon_network.netinfo            # print what the app would show
"""
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

# Devices that are plumbing, not "your network": containers, bridges, loopback.
USER_TYPES = ("wifi", "ethernet", "gsm", "cdma", "wwan", "bt", "vpn", "wireguard", "infiniband", "team", "bond")
TYPE_NAMES = {"wifi": "Wireless", "ethernet": "Wired", "gsm": "Mobile broadband", "cdma": "Mobile broadband",
              "wwan": "Mobile broadband", "bt": "Bluetooth", "vpn": "VPN", "wireguard": "VPN"}
CHECK_URL = "http://networkcheck.kde.org/"


def run(*cmd, timeout=4):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def split_terse(line):
    """Split one line of `nmcli -t` output: fields are ':'-separated, and
    ':' and '\\' inside a value are escaped with a backslash."""
    out, cur, esc = [], [], False
    for ch in line:
        if esc:
            cur.append(ch)
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def parse_rows(text, n):
    rows = []
    for line in text.splitlines():
        if line.strip():
            f = split_terse(line)
            rows.append((f + [""] * n)[:n])
    return rows


def parse_show(text):
    """`nmcli -t device show DEV` -> {key: value or [values]} (IP4.DNS[1], [2]... become a list)."""
    d = {}
    for line in text.splitlines():
        key, sep, val = line.partition(":")
        if not sep:
            continue
        if "[" in key and key.endswith("]"):
            d.setdefault(key[:key.index("[")], []).append(val)
        else:
            d[key] = val
    return d


def parse_connectivity(word):
    """nmcli's connectivity -> (Vista 'Access' wording, map state)."""
    return {"full": ("Local and Internet", "internet"),
            "limited": ("Local only", "local"),
            "portal": ("Local only (sign-in page)", "portal"),
            "none": ("No network access", "none")}.get(word, ("Unknown", "unknown"))


def signal_bars(pct):
    """0-100% -> 0-5 bars, the way Vista drew Wi-Fi strength."""
    if pct is None:
        return 0
    return max(0, min(5, (int(pct) + 19) // 20))


def pick_primary(devices):
    """The connection people mean by 'my network': the first connected
    user-facing device, Wi-Fi/Ethernet before VPNs."""
    usable = [d for d in devices if d["state"] == "connected" and d["type"] in USER_TYPES]
    usable.sort(key=lambda d: (d["type"] in ("vpn", "wireguard"), USER_TYPES.index(d["type"])))
    return usable[0] if usable else None


def hostname():
    try:
        with open("/etc/hostname") as f:
            name = f.read().strip()
            if name:
                return name
    except OSError:
        pass
    return socket.gethostname() or "This computer"


def devices():
    return [{"device": d, "type": t, "state": s, "connection": c}
            for d, t, s, c in parse_rows(run("nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"), 4)]


def wifi_active():
    """(ssid, signal %, rate, security) of the Wi-Fi network in use, or None."""
    for use, ssid, sig, rate, sec in parse_rows(
            run("nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,RATE,SECURITY", "device", "wifi", "list", "--rescan", "no"), 5):
        if use.strip() == "*":
            return ssid, int(sig) if sig.isdigit() else None, rate, sec
    return None


def counters(dev):
    base = f"/sys/class/net/{dev}/statistics/"
    try:
        with open(base + "rx_bytes") as r, open(base + "tx_bytes") as t:
            return int(r.read()), int(t.read())
    except (OSError, ValueError):
        return None


def link_speed(dev):
    try:
        with open(f"/sys/class/net/{dev}/speed") as f:
            v = int(f.read())
            return f"{v} Mbps" if v > 0 else ""
    except (OSError, ValueError):
        return ""


def human_bytes(n):
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.0f} {unit}" if unit == "bytes" else f"{n:,.1f} {unit}"
        n /= 1024


def snapshot():
    """Everything the main window shows, gathered in one go (call it off the UI thread)."""
    gen = parse_rows(run("nmcli", "-t", "-f", "STATE,CONNECTIVITY,WIFI,NETWORKING", "general"), 4)
    state, conn, wifi_on, net_on = gen[0] if gen else ("unknown", "unknown", "", "")
    devs = devices()
    prim = pick_primary(devs)
    snap = {"host": hostname(), "networking": net_on == "enabled", "wifi_enabled": wifi_on == "enabled",
            "connectivity": conn, "devices": devs, "primary": prim, "wifi": None, "details": {}}
    snap["access"], snap["map"] = parse_connectivity(conn if prim else "none")
    if prim:
        snap["details"] = parse_show(run("nmcli", "-t", "device", "show", prim["device"]))
        if prim["type"] == "wifi":
            snap["wifi"] = wifi_active()
    snap["sharing"] = sharing()
    return snap


# ---------------------------------------------------------------- sharing ---
def service_active(name):
    return run("systemctl", "is-active", name).strip() == "active"


def ufw_enabled(conf="/etc/ufw/ufw.conf"):
    """ufw's own switch (readable without root, unlike `ufw status`)."""
    try:
        with open(conf) as f:
            return any(line.strip().lower() == "enabled=yes" for line in f)
    except OSError:
        return False


def sharing():
    """Sharing and Discovery rows: name -> (state text, on?, how to change it or None)."""
    rows = {}
    if shutil.which("avahi-daemon"):
        on = service_active("avahi-daemon.service")
        rows["Network discovery"] = ("On" if on else "Off", on,
                                     ["pkexec", "systemctl", "disable" if on else "enable", "--now",
                                      "avahi-daemon.service"])
    else:
        rows["Network discovery"] = ("Not installed", False, None)
    if shutil.which("smbd"):
        on = service_active("smb.service")
        rows["File sharing"] = ("On" if on else "Off", on,
                                ["pkexec", "systemctl", "disable" if on else "enable", "--now", "smb.service"])
    else:
        rows["File sharing"] = ("Not installed", False, None)
    if shutil.which("ufw"):
        on = ufw_enabled()
        # ufw.service must be enabled too, or the rules aren't loaded at the next boot.
        cmd = "ufw disable && systemctl disable ufw.service" if on else "ufw enable && systemctl enable ufw.service"
        rows["Firewall"] = ("On" if on else "Off", on, ["pkexec", "sh", "-c", cmd])
    elif shutil.which("firewall-cmd"):
        on = service_active("firewalld.service")
        rows["Firewall"] = ("On" if on else "Off", on,
                            ["pkexec", "systemctl", "disable" if on else "enable", "--now", "firewalld.service"])
    else:
        rows["Firewall"] = ("Not installed", False, None)
    return rows


# --------------------------------------------------------------- diagnose ---
def _ping(host):
    if not host or not shutil.which("ping"):
        return None
    return subprocess.run(["ping", "-c", "2", "-W", "2", host], capture_output=True).returncode == 0


def diagnose_steps():
    """[(title, check)] where check() -> (ok, plain-language result, suggested fix or '')."""
    ctx = {}

    def link():
        ctx["devs"] = devices()
        prim = pick_primary(ctx["devs"])
        ctx["prim"] = prim
        if prim:
            return True, f"Connected to “{prim['connection']}” through {prim['device']}.", ""
        has_wifi = any(d["type"] == "wifi" for d in ctx["devs"])
        cable = any(d["type"] == "ethernet" and d["state"] == "unavailable" for d in ctx["devs"])
        fix = "Connect to a wireless network" if has_wifi else ""
        if cable:
            fix = (fix + ", or plug" if fix else "Plug") + " in a network cable"
        return False, "This computer isn't connected to a network.", fix + "."

    def address():
        prim = ctx.get("prim")
        if not prim:
            return False, "Skipped: no network connection.", ""
        ctx["show"] = d = parse_show(run("nmcli", "-t", "device", "show", prim["device"]))
        addrs = d.get("IP4.ADDRESS", []) + [a for a in d.get("IP6.ADDRESS", []) if not a.startswith("fe80")]
        if addrs:
            return True, f"This computer's address is {addrs[0].split('/')[0]}.", ""
        return False, "The network didn't give this computer an address.", \
            "Reset the network adapter, or restart your router."

    def gateway():
        d = ctx.get("show") or {}
        gw = d.get("IP4.GATEWAY") or d.get("IP6.GATEWAY") or ""
        if not gw or gw == "--":
            return False, "No router (default gateway) was found.", "Restart your router or reset the adapter."
        ok = _ping(gw)
        if ok is None:
            return True, f"Router at {gw} (couldn't test it: ping is missing).", ""
        return (True, f"Your router ({gw}) is responding.", "") if ok else \
            (False, f"Your router ({gw}) isn't responding.", "Check that the router is on, then reset the adapter.")

    def dns():
        try:
            socket.setdefaulttimeout(4)
            socket.getaddrinfo("kde.org", 80)
            return True, "Website names can be looked up (DNS is working).", ""
        except OSError:
            return False, "Website names can't be looked up (DNS isn't responding).", \
                "Reset the adapter; if that doesn't help, your Internet provider may be having problems."
        finally:
            socket.setdefaulttimeout(None)

    def internet():
        try:
            with urllib.request.urlopen(CHECK_URL, timeout=6) as r:
                body = r.read(200).decode("utf-8", "replace")
                if r.status == 200 and "OK" in body:
                    return True, "This computer can reach the Internet.", ""
                return False, "A sign-in page is in the way (hotel, airport or café network).", \
                    "Open a web browser and sign in to the network."
        except OSError:
            return False, "The Internet can't be reached.", "Restart your router or modem, then try again."

    return [("Checking the network connection", link), ("Checking this computer's address", address),
            ("Contacting your router", gateway), ("Looking up a website name", dns),
            ("Connecting to the Internet", internet)]


# ---------------------------------------------------------------- selftest ---
def _selftest():
    assert split_terse(r"*:My\:Net:75:WPA2") == ["*", "My:Net", "75", "WPA2"]
    assert split_terse(r"a\\b:c") == ["a\\b", "c"]
    assert split_terse("x::y") == ["x", "", "y"]
    rows = parse_rows("wlo1:wifi:connected:SHAZAM!!!\nlo:loopback:connected (externally):lo\n\n", 4)
    assert rows == [["wlo1", "wifi", "connected", "SHAZAM!!!"], ["lo", "loopback", "connected (externally)", "lo"]]
    assert parse_rows("only", 3) == [["only", "", ""]]
    show = parse_show("GENERAL.DEVICE:wlo1\nIP4.ADDRESS[1]:192.168.1.5/24\nIP4.DNS[1]:1.1.1.1\nIP4.DNS[2]:8.8.8.8\n"
                      "IP4.GATEWAY:192.168.1.1\nIP6.ADDRESS[1]:fe80::1/64\nGENERAL.HWADDR:04:EC:D8:65:49:47\n")
    assert show["IP4.DNS"] == ["1.1.1.1", "8.8.8.8"] and show["IP4.GATEWAY"] == "192.168.1.1"
    assert show["GENERAL.HWADDR"] == "04:EC:D8:65:49:47", show["GENERAL.HWADDR"]   # only the first ':' splits
    devs = [{"device": "docker0", "type": "bridge", "state": "connected", "connection": "docker0"},
            {"device": "tun0", "type": "vpn", "state": "connected", "connection": "Work"},
            {"device": "enp4s0", "type": "ethernet", "state": "unavailable", "connection": ""},
            {"device": "wlo1", "type": "wifi", "state": "connected", "connection": "Home"}]
    assert pick_primary(devs)["device"] == "wlo1"
    assert pick_primary(devs[:3])["device"] == "tun0"
    assert pick_primary(devs[:1]) is None
    assert [signal_bars(v) for v in (None, 0, 1, 20, 21, 55, 80, 81, 100)] == [0, 0, 1, 1, 2, 3, 4, 5, 5]
    assert parse_connectivity("full") == ("Local and Internet", "internet")
    assert parse_connectivity("limited")[1] == "local" and parse_connectivity("weird")[1] == "unknown"
    assert human_bytes(512) == "512 bytes" and human_bytes(1536) == "1.5 KB" and human_bytes(5 * 1024 ** 3) == "5.0 GB"
    assert [t for t, _ in diagnose_steps()][0] == "Checking the network connection"
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as f:
        f.write("# comment\nENABLED=yes\nLOGLEVEL=low\n")
    assert ufw_enabled(f.name) and not ufw_enabled("/nonexistent")
    os.unlink(f.name)
    print("netinfo selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        t = time.time()
        s = snapshot()
        print({k: v for k, v in s.items() if k != "details"}, f"\n({time.time() - t:.2f}s)")
