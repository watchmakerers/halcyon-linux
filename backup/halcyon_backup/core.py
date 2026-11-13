"""Backup and Restore Center logic: settings, what to back up, where backups
live, running rsync, the schedule, and system restore points. No Qt here.

A backup is a dated folder of plain files:
    <destination>/Halcyon Backup/<user>@<host>/2026-11-12 2347/Pictures/...
Each new one is made with rsync --link-dest against the previous, so every
backup is complete on its own yet unchanged files take no extra space. A
backup is written as ".partial-<date>" and renamed when it finishes, so an
interrupted one never counts.

    python3 -m halcyon_backup.core --selftest
"""
import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "halcyon" / "backup.json"
UNITS = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "systemd" / "user"
UNIT = "halcyon-backup"
ROOT_NAME = "Halcyon Backup"
STAMP = "%Y-%m-%d %H%M"
STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{4}$")

# id, label, how to find it. "home" is everything else in the home folder.
CATEGORIES = [
    ("pictures", "Pictures", "PICTURES"),
    ("music", "Music", "MUSIC"),
    ("videos", "Videos", "VIDEOS"),
    ("documents", "Documents", "DOCUMENTS"),
    ("desktop", "Desktop", "DESKTOP"),
    ("email", "E-mail", ".local/share/halcyon/mail"),
    ("home", "Everything else in your home folder", ""),
]
# Never worth backing up: caches, trash, and other backups.
EXCLUDES = [".cache/", ".local/share/Trash/", ".local/share/baloo/", "*.partial-*/", ROOT_NAME + "/",
            ".var/app/*/cache/", ".steam/", ".local/share/Steam/steamapps/"]

DEFAULTS = {"destination": "", "categories": ["pictures", "music", "videos", "documents", "desktop", "email"],
            "schedule": {"enabled": False, "how": "weekly", "day": 0, "time": "19:00"}, "keep": 30}


# ---------------------------------------------------------------- settings ---
def load(path=CONFIG):
    try:
        d = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        d = {}
    out = json.loads(json.dumps(DEFAULTS))
    out.update({k: v for k, v in d.items() if k in DEFAULTS})
    out["schedule"] = {**DEFAULTS["schedule"], **(d.get("schedule") or {})}
    return out


def save(cfg, path=CONFIG):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=1))


# ---------------------------------------------------------- what to back up ---
def user_dir(key, home=None, dirs_file=None):
    home = Path(home or HOME)
    """An XDG user folder (Pictures, Music...) from user-dirs.dirs, falling back to ~/<Name>."""
    dirs_file = dirs_file or Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "user-dirs.dirs"
    try:
        for line in Path(dirs_file).read_text().splitlines():
            m = re.match(rf'^XDG_{key}_DIR="(.*)"', line.strip())
            if m:
                return Path(m.group(1).replace("$HOME", str(home)))
    except OSError:
        pass
    return home / key.title()


def category_path(cid, home=None, dirs_file=None):
    home = Path(home or HOME)
    for c, _, where in CATEGORIES:
        if c == cid:
            if not where:
                return home
            if where.isupper():
                return user_dir(where, home, dirs_file)
            return home / where
    raise KeyError(cid)


def sources(cids, home=None, dirs_file=None):
    """Folders to back up, relative to home where possible (so a backup mirrors the home layout).
    Choosing "home" covers everything, so the rest are dropped."""
    home = Path(home or HOME)
    if "home" in cids:
        return ["."]
    out = []
    for cid in cids:
        p = category_path(cid, home, dirs_file)
        if p.exists() and p != home:
            try:
                out.append(str(p.relative_to(home)))
            except ValueError:
                out.append(str(p))
    return sorted(set(out))


def folder_size(path, limit_s=4.0):
    """Bytes in a folder (stops counting after limit_s seconds and returns what it has)."""
    import time
    total, t0 = 0, time.monotonic()
    for base, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in (".cache", "Trash") and not d.startswith(".partial-")]
        for f in files:
            try:
                total += os.lstat(os.path.join(base, f)).st_size
            except OSError:
                pass
        if time.monotonic() - t0 > limit_s:
            break
    return total


def human(n):
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024


# ------------------------------------------------------------ destinations ---
def mount_source(path, mountinfo="/proc/self/mountinfo"):
    """The device behind the mount holding path (st_dev is virtual on btrfs, so use the mount table)."""
    path = os.path.realpath(path)
    best, src = "", ""
    try:
        with open(mountinfo) as f:
            for line in f:
                left, _, right = line.partition(" - ")
                point = left.split()[4].replace("\\040", " ")
                if (path == point or path.startswith(point.rstrip("/") + "/")) and len(point) >= len(best):
                    best, src = point, right.split()[1]
    except (OSError, IndexError):
        pass
    return src


def drives(user=None):
    """Mounted drives you could back up to: removable media and /mnt, with free space."""
    user = user or os.environ.get("USER", "")
    out = []
    for base in (f"/run/media/{user}", "/media", "/mnt"):
        try:
            entries = sorted(os.scandir(base), key=lambda e: e.name)
        except OSError:
            continue
        for e in entries:
            if e.is_dir() and os.path.ismount(e.path):
                try:
                    du = shutil.disk_usage(e.path)
                    out.append((e.path, e.name, du.free, du.total))
                except OSError:
                    pass
    return out


def check_destination(dest, home=None, mountinfo="/proc/self/mountinfo"):
    """(ok, message). Backups on the same disk as the files don't protect against the disk failing."""
    home = Path(home or HOME)
    if not dest:
        return False, "Choose where to save the backup."
    d = Path(dest)
    if not d.is_dir():
        return False, "That location isn't available. Is the drive connected?"
    if not os.access(d, os.W_OK):
        return False, "You don't have permission to save files there."
    try:
        d.resolve().relative_to(Path(home).resolve())
        return False, "That folder is inside your home folder, which is what's being backed up."
    except ValueError:
        pass
    src_home, src_dest = mount_source(home, mountinfo), mount_source(d, mountinfo)
    if src_home and src_home == src_dest:
        return False, "That's the same disk your files are on. If the disk fails you'd lose both; choose another drive."
    return True, ""


def backup_root(dest, user=None, host=None):
    user = user or os.environ.get("USER") or Path(HOME).name
    host = host or socket.gethostname() or "computer"
    return Path(dest) / ROOT_NAME / f"{user}@{host}"


def list_backups(dest, **kw):
    """Finished backups, newest first: [(datetime, path)]."""
    root = backup_root(dest, **kw)
    out = []
    try:
        for e in os.scandir(root):
            if e.is_dir() and STAMP_RE.match(e.name):
                out.append((datetime.datetime.strptime(e.name, STAMP), Path(e.path)))
    except OSError:
        pass
    return sorted(out, reverse=True)


def to_prune(backups, keep):
    """Which backups to delete so `keep` remain: the oldest, but never the newest one."""
    keep = max(1, int(keep))
    return [p for _, p in sorted(backups, reverse=True)[keep:]]


# -------------------------------------------------------------- run rsync ---
def rsync_command(srcs, target, link_dest=None, home=None):
    home = Path(home or HOME)
    cmd = ["rsync", "-a", "--relative", "--info=progress2", "--no-inc-recursive", "--partial"]
    cmd += [f"--exclude={x}" for x in EXCLUDES]
    if link_dest:
        cmd.append(f"--link-dest={link_dest}")
    # "/./" marks where --relative starts, so files land as <target>/Pictures/...
    cmd += [f"{home}/./{s}" if not os.path.isabs(s) else s for s in srcs]
    cmd.append(str(target) + "/")
    return cmd


PROGRESS_RE = re.compile(r"^\s*([\d,]+)\s+(\d+)%\s+(\S+)\s+(\S+)")


def parse_progress(line):
    """rsync --info=progress2 line -> (bytes done, percent) or None."""
    m = PROGRESS_RE.match(line)
    if not m:
        return None
    return int(m.group(1).replace(",", "")), int(m.group(2))


def run_backup(cfg, progress=None, stop=None, now=None):
    """Make one backup. progress(percent, text) is called as it goes; stop() -> True cancels.
    Returns (ok, message)."""
    ok, msg = check_destination(cfg["destination"])
    if not ok:
        return False, msg
    srcs = sources(cfg["categories"])
    if not srcs:
        return False, "There's nothing to back up: none of the chosen folders exist."
    root = backup_root(cfg["destination"])
    root.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.datetime.now()).strftime(STAMP)
    final = root / stamp
    if final.exists():
        return True, "A backup was already made this minute."
    work = root / f".partial-{stamp}"
    previous = list_backups(cfg["destination"])
    link = previous[0][1] if previous else None
    cmd = rsync_command(srcs, work, link)
    if progress:
        progress(0, "Preparing…")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    buf = ""
    while True:
        ch = proc.stdout.read(1)
        if not ch:
            break
        if ch in "\r\n":
            p = parse_progress(buf)
            if p and progress:
                progress(p[1], f"{human(p[0])} copied")
            buf = ""
            if stop and stop():
                proc.terminate()
        else:
            buf += ch
    err = proc.stderr.read()
    code = proc.wait()
    if stop and stop():
        shutil.rmtree(work, ignore_errors=True)
        return False, "The backup was cancelled."
    # 23/24: some files vanished or couldn't be read (open files, permissions); the backup is still useful.
    if code not in (0, 23, 24):
        shutil.rmtree(work, ignore_errors=True)
        return False, "The backup didn't finish.\n\n" + err.strip()[-500:]
    work.rename(final)
    for old in to_prune(list_backups(cfg["destination"]), cfg.get("keep", 30)):
        shutil.rmtree(old, ignore_errors=True)
    note = "" if code == 0 else " Some files couldn't be read and were skipped."
    return True, f"Your files were backed up.{note}"


def restore(items, backup, target=None, overwrite=True, progress=None):
    """Copy items (paths inside a backup) back. target None = their original place in the home folder."""
    backup = Path(backup)
    rel = [str(Path(i).relative_to(backup)) for i in items]
    dest = Path(target) if target else Path(HOME)
    cmd = ["rsync", "-a", "--relative", "--info=progress2"]
    if not overwrite:
        cmd.append("--ignore-existing")
    cmd += [f"{backup}/./{r}" for r in rel] + [str(dest) + "/"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode not in (0, 23, 24):
        return False, proc.stderr.strip()[-500:]
    return True, f"Your files were restored to {dest}."


# ---------------------------------------------------------------- schedule ---
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def on_calendar(sched):
    """systemd OnCalendar for the schedule. day: weekday 0-6 (weekly) or day of month 1-28 (monthly)."""
    hh, mm = (int(x) for x in sched.get("time", "19:00").split(":"))
    t = f"{hh:02d}:{mm:02d}:00"
    how = sched.get("how", "weekly")
    if how == "daily":
        return f"*-*-* {t}"
    if how == "monthly":
        return f"*-*-{max(1, min(28, int(sched.get('day', 1)))):02d} {t}"
    return f"{DAYS[int(sched.get('day', 0)) % 7]} *-*-* {t}"


def describe_schedule(sched):
    if not sched.get("enabled"):
        return "Automatic backups are turned off"
    how, t = sched.get("how", "weekly"), sched.get("time", "19:00")
    if how == "daily":
        return f"Every day at {t}"
    if how == "monthly":
        return f"On day {sched.get('day', 1)} of every month at {t}"
    return f"Every {DAY_NAMES[int(sched.get('day', 0)) % 7]} at {t}"


def unit_files(sched, launcher="halcyon-backup"):
    exe = shutil.which(launcher) or launcher
    service = ("[Unit]\nDescription=Halcyon scheduled backup\n\n"
               f"[Service]\nType=oneshot\nNice=10\nIOSchedulingClass=idle\nExecStart={exe} --run\n")
    timer = ("[Unit]\nDescription=Halcyon scheduled backup\n\n"
             f"[Timer]\nOnCalendar={on_calendar(sched)}\nPersistent=true\nRandomizedDelaySec=120\n\n"
             "[Install]\nWantedBy=timers.target\n")
    return service, timer


def apply_schedule(sched, units=UNITS):
    """Write (or remove) the systemd user timer. Returns an error message or ''."""
    units = Path(units)
    svc, tmr = units / f"{UNIT}.service", units / f"{UNIT}.timer"
    run = lambda *a: subprocess.run(["systemctl", "--user", *a], capture_output=True, text=True)
    if sched.get("enabled"):
        units.mkdir(parents=True, exist_ok=True)
        s, t = unit_files(sched)
        svc.write_text(s)
        tmr.write_text(t)
        run("daemon-reload")
        r = run("enable", "--now", f"{UNIT}.timer")
        return r.stderr.strip() if r.returncode else ""
    run("disable", "--now", f"{UNIT}.timer")
    for f in (svc, tmr):
        try:
            f.unlink()
        except OSError:
            pass
    run("daemon-reload")
    return ""


def next_run():
    out = subprocess.run(["systemctl", "--user", "show", f"{UNIT}.timer", "-p", "NextElapseUSecRealtime", "--value"],
                         capture_output=True, text=True).stdout.strip()
    return out if out and out != "n/a" else ""


# ---------------------------------------------------------- restore points ---
def snapshot_tool():
    for t in ("snapper", "timeshift"):
        if shutil.which(t):
            return t
    return ""


def list_snapshots(tool):
    """[(date text, description)] newest first; may be empty if the tool needs root to list."""
    if tool == "snapper":
        out = subprocess.run(["snapper", "--csvout", "list", "--columns", "number,date,description"],
                             capture_output=True, text=True).stdout
        rows = [r.split(",", 2) for r in out.splitlines()[1:] if r.strip()]
        return [(d, desc or f"Snapshot {n}") for n, d, desc in reversed(rows) if n != "0"]
    return []


def create_snapshot_cmd(tool, description="Restore point made in Backup and Restore Center"):
    if tool == "snapper":
        return ["pkexec", "snapper", "create", "--description", description]
    if tool == "timeshift":
        return ["pkexec", "timeshift", "--create", "--comments", description]
    return []


# ---------------------------------------------------------------- selftest ---
def _selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        home = t / "home"
        (home / "Bilder").mkdir(parents=True)
        (home / "Documents").mkdir()
        (home / ".local/share/halcyon/mail").mkdir(parents=True)
        dirs = t / "user-dirs.dirs"
        dirs.write_text('# comment\nXDG_PICTURES_DIR="$HOME/Bilder"\nXDG_DOCUMENTS_DIR="$HOME/Documents"\n')
        assert category_path("pictures", home, dirs) == home / "Bilder"
        assert category_path("music", home, dirs) == home / "Music"           # not listed: default name
        assert category_path("email", home, dirs) == home / ".local/share/halcyon/mail"
        assert category_path("home", home, dirs) == home
        assert sources(["pictures", "music", "email"], home, dirs) == [".local/share/halcyon/mail", "Bilder"]
        assert sources(["pictures", "home"], home, dirs) == ["."]

        cfgp = t / "cfg.json"
        c = load(cfgp)
        assert c["keep"] == 30 and c["schedule"]["how"] == "weekly"
        c["destination"] = "/x"
        c["schedule"]["enabled"] = True
        save(c, cfgp)
        c2 = load(cfgp)
        assert c2["destination"] == "/x" and c2["schedule"]["enabled"] and c2["schedule"]["time"] == "19:00"

        # destinations: inside home, same disk, missing
        mi = t / "mountinfo"
        mi.write_text(f"1 0 0:1 / / rw - btrfs /dev/nvme0n1p3 rw\n"
                      f"2 1 0:2 / {t}/usb rw - vfat /dev/sdb1 rw\n")
        (t / "usb").mkdir()
        (t / "same").mkdir()
        assert not check_destination("", home, mi)[0]
        assert "inside your home" in check_destination(str(home / "Bilder"), home, mi)[1]
        assert "same disk" in check_destination(str(t / "same"), home, mi)[1]
        assert check_destination(str(t / "usb"), home, mi) == (True, "")
        assert "available" in check_destination(str(t / "gone"), home, mi)[1]

        # listing ignores partial and odd folders; pruning keeps the newest
        root = backup_root(t / "usb", user="u", host="h")
        for name in ("2026-01-01 1000", "2026-03-01 1000", "2026-02-01 1000", ".partial-2026-04-01 1000", "notes"):
            (root / name).mkdir(parents=True)
        b = list_backups(t / "usb", user="u", host="h")
        assert [p.name for _, p in b] == ["2026-03-01 1000", "2026-02-01 1000", "2026-01-01 1000"]
        assert [p.name for p in to_prune(b, 2)] == ["2026-01-01 1000"]
        assert to_prune(b, 0) == [b[1][1], b[2][1]]          # always keeps at least the newest
        assert to_prune(b, 10) == []

    cmd = rsync_command(["Pictures", "/srv/x"], "/mnt/b/.partial-1", "/mnt/b/prev", home=Path("/home/u"))
    assert cmd[-3:] == ["/home/u/./Pictures", "/srv/x", "/mnt/b/.partial-1/"] and "--link-dest=/mnt/b/prev" in cmd
    assert parse_progress("    1,234,567  42%   12.34MB/s    0:00:10 (xfr#3, to-chk=1/9)") == (1234567, 42)
    assert parse_progress("sending incremental file list") is None
    assert on_calendar({"how": "daily", "time": "7:05"}) == "*-*-* 07:05:00"
    assert on_calendar({"how": "weekly", "day": 6, "time": "19:00"}) == "Sun *-*-* 19:00:00"
    assert on_calendar({"how": "monthly", "day": 31, "time": "01:30"}) == "*-*-28 01:30:00"
    assert describe_schedule({"enabled": True, "how": "weekly", "day": 2, "time": "19:00"}) == "Every Wednesday at 19:00"
    s, tm = unit_files({"how": "daily", "time": "08:00"}, launcher="/nonexistent/halcyon-backup")
    assert "ExecStart=/nonexistent/halcyon-backup --run" in s and "OnCalendar=*-*-* 08:00:00" in tm
    assert human(1536) == "1.5 KB"
    print("backup core selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
