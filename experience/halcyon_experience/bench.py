"""Performance Rating benchmarks and scoring, after Vista's Windows Experience
Index: five components, each rated 1.0-5.9; the base score is the lowest.

Each benchmark returns a raw number (with its unit); a scorer maps it onto
1.0-5.9 through anchor points, interpolated on a log scale, so a 2008-era
laptop lands around 3 and a current desktop in the 5s.

    python3 -m halcyon_experience.bench --selftest
    python3 -m halcyon_experience.bench            # run everything, print raw numbers and scores
"""
import datetime
import hashlib
import json
import math
import mmap
import os
import random
import sys
import threading
import time
import zlib
from pathlib import Path

DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "halcyon" / "experience"
SCORE_FILE = DATA / "score.json"
# The disk test must hit the real disk: /tmp is often RAM (tmpfs), the cache folder isn't.
DISK_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "halcyon-experience"

COMPONENTS = [            # key, name, what is rated
    ("cpu", "Processor", "Calculations per second"),
    ("memory", "Memory (RAM)", "Memory operations per second"),
    ("graphics", "Graphics", "Desktop performance for the glass effects"),
    ("gaming", "Gaming graphics", "3D business and gaming graphics performance"),
    ("disk", "Primary hard disk", "Disk data transfer rate"),
]

# (raw value, score) anchors. Calibrated against a Core 2 Duo / DDR2 / HDD
# laptop of 2008 (~3) and a 2022 12-thread laptop with NVMe (~5.5).
ANCHORS = {
    # MB/s of hashing+compressing, all cores together
    "cpu": [(5, 1.0), (25, 2.0), (70, 3.0), (200, 4.0), (550, 5.0), (1300, 5.6), (2500, 5.9)],
    # GB/s of memory copy, one thread
    "memory": [(0.3, 1.0), (1.0, 2.0), (2.5, 3.0), (5.0, 4.0), (10.0, 5.0), (18.0, 5.6), (25.0, 5.9)],
    # frames/s of the glass desktop scene
    "graphics": [(5, 1.0), (15, 2.0), (40, 3.0), (100, 4.0), (250, 5.0), (500, 5.6), (800, 5.9)],
    # frames/s of the heavier 3D-style scene
    "gaming": [(2, 1.0), (6, 2.0), (15, 3.0), (40, 4.0), (110, 5.0), (220, 5.6), (350, 5.9)],
    # sequential MB/s (read+write averaged)
    "disk_seq": [(5, 1.0), (20, 2.0), (60, 3.0), (180, 4.0), (600, 5.0), (1500, 5.6), (2500, 5.9)],
    # random 4 KB reads per second
    "disk_rand": [(20, 1.0), (60, 2.0), (150, 3.0), (2000, 4.0), (8000, 5.0), (20000, 5.6), (40000, 5.9)],
}
# Vista also capped the memory score by how much there is.
RAM_CAPS = [(1.0, 2.0), (2.0, 3.5), (4.0, 4.5), (8.0, 5.4)]     # (GB less than, max score)


def interpolate(anchors, x):
    """Piecewise-linear in log10(x) through the anchors, clamped, rounded to 0.1."""
    if x is None or x <= 0:
        return 1.0
    if x <= anchors[0][0]:
        s = anchors[0][1]
    elif x >= anchors[-1][0]:
        s = anchors[-1][1]
    else:
        lx = math.log10(x)
        for (x0, s0), (x1, s1) in zip(anchors, anchors[1:]):
            if x0 <= x <= x1:
                t = (lx - math.log10(x0)) / (math.log10(x1) - math.log10(x0))
                s = s0 + t * (s1 - s0)
                break
    # floor rather than round, like Vista: 5.95 is still a 5.9
    return max(1.0, min(5.9, math.floor(s * 10 + 1e-9) / 10))


def score(kind, raw):
    return interpolate(ANCHORS[kind], raw)


def memory_score(gbps, ram_gb):
    s = score("memory", gbps)
    for limit, cap in RAM_CAPS:
        if ram_gb < limit:
            return min(s, cap)
    return s


def disk_score(seq, rand):
    """Average of the sequential and random scores, floored to 0.1."""
    return math.floor((score("disk_seq", seq) + score("disk_rand", rand)) / 2 * 10 + 1e-9) / 10


def base_score(subscores):
    """Vista's rule: the base score is the lowest subscore."""
    vals = [v for v in subscores.values() if v is not None]
    return min(vals) if vals else None


# ------------------------------------------------------------ descriptions ---
def cpu_name():
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return " ".join(line.split(":", 1)[1].split())
    except OSError:
        pass
    return "Processor"


def ram_gb():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024 / 1024
    except (OSError, ValueError):
        pass
    return 0.0


def gpu_names():
    """Graphics adapters from /sys (no lspci needed): vendor + device ids -> a readable name if lspci knows it."""
    names = []
    import subprocess
    try:
        out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            if any(k in line for k in ("VGA compatible controller", "3D controller", "Display controller")):
                name = line.split(": ", 1)[-1]
                name = name.split(" (rev")[0]
                names.append(name.replace("Corporation ", ""))
    except (OSError, subprocess.TimeoutExpired):
        pass
    return names or ["Graphics adapter"]


def mount_source(path, mountinfo="/proc/self/mountinfo"):
    """The block device behind the mount holding path (st_dev is virtual on btrfs, so use the mount table)."""
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


def disk_name(path=None):
    """The disk holding the home folder: model and size."""
    src = mount_source(path or DISK_DIR.parent)
    try:
        part = Path("/sys/class/block") / os.path.basename(os.path.realpath(src))
        disk = part.resolve().parent if (part / "partition").exists() else part.resolve()
        model_file = disk / "device" / "model"
        model = model_file.read_text().strip() if model_file.exists() else ""
        size = int((disk / "size").read_text()) * 512 / 1e9
        return f"{model or disk.name} ({size:.0f} GB)"
    except (OSError, ValueError):
        return "Primary hard disk"


GL_RENDERER = ""


def describe():
    gpu = renderer_name(GL_RENDERER) or gpu_names()[0]
    return {"cpu": cpu_name(), "memory": f"{ram_gb():.1f} GB", "graphics": gpu, "gaming": gpu,
            "disk": disk_name()}


def renderer_name(r):
    """Mesa says e.g. 'Mesa Intel(R) Graphics (ADL GT2)'; drop the driver prefix."""
    r = (r or "").strip()
    for prefix in ("Mesa ", "llvmpipe"):
        if r.startswith(prefix) and prefix != "llvmpipe":
            r = r[len(prefix):]
    return "" if r.startswith("llvmpipe") else r


# -------------------------------------------------------------- benchmarks ---
def bench_cpu(seconds=3.0):
    """Hash and compress in one thread per core; MB/s for all cores together.
    hashlib and zlib release the GIL on big buffers, so threads use every core."""
    block = os.urandom(1 << 20)
    half = block[: 1 << 18] * 4          # compressible but not trivially
    n = os.cpu_count() or 1
    done = [0] * n
    stop = time.perf_counter() + seconds

    def work(i):
        mb = 0
        while time.perf_counter() < stop:
            hashlib.sha256(block).digest()
            zlib.compress(half, 6)
            mb += 2
        done[i] = mb

    threads = [threading.Thread(target=work, args=(i,)) for i in range(n)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return sum(done) / (time.perf_counter() - t0)


def bench_memory(seconds=2.0, size=128 << 20):
    """Large block copies (memcpy speed), GB/s."""
    src = bytearray(os.urandom(1 << 20)) * (size >> 20)
    dst = bytearray(size)
    dst[:] = src                         # touch the pages first
    copies, t0 = 0, time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        dst[:] = src
        copies += 1
    return copies * size / (time.perf_counter() - t0) / 1e9


def _desktop_scene(p, w, h, frame, heavy):
    """A frame of glass windows (graphics) or many blended, rotated shapes (gaming)."""
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QColor, QLinearGradient, QRadialGradient
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor("#0b3d6e"))
    g.setColorAt(1, QColor("#58b6e8"))
    p.fillRect(0, 0, w, h, g)
    rnd = random.Random(frame % 7)
    count = 160 if heavy else 14
    for i in range(count):
        x, y = rnd.uniform(-100, w), rnd.uniform(-100, h)
        if heavy:
            p.save()
            p.translate(x, y)
            p.rotate((frame * 3 + i * 11) % 360)
            rg = QRadialGradient(QPointF(0, 0), 60)
            rg.setColorAt(0, QColor(255, 255, 255, 200))
            rg.setColorAt(1, QColor(rnd.randrange(256), rnd.randrange(256), 255, 40))
            p.setBrush(rg)
            p.setPen(QColor(255, 255, 255, 90))
            p.drawRoundedRect(QRectF(-60, -40, 120, 80), 18, 18)
            p.restore()
        else:
            r = QRectF(x, y, rnd.uniform(200, 500), rnd.uniform(150, 380))
            glass = QLinearGradient(r.topLeft(), r.bottomLeft())
            glass.setColorAt(0, QColor(255, 255, 255, 150))
            glass.setColorAt(0.5, QColor(160, 200, 240, 90))
            glass.setColorAt(1, QColor(40, 90, 160, 120))
            p.setBrush(glass)
            p.setPen(QColor(255, 255, 255, 160))
            p.drawRoundedRect(r, 8, 8)
            p.fillRect(QRectF(r.x() + 8, r.y() + 28, r.width() - 16, r.height() - 36), QColor(250, 252, 255, 235))


def _frames(paint_target, finish, w, h, heavy, seconds):
    from PySide6.QtGui import QPainter
    frames, t0 = 0, time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        p = QPainter(paint_target)
        p.setRenderHint(QPainter.Antialiasing)
        _desktop_scene(p, w, h, frames, heavy)
        p.end()
        finish()
        frames += 1
    return frames / (time.perf_counter() - t0)


def bench_graphics(heavy, seconds=2.5, w=1280, h=720):
    """Frames/s of a scene drawn on the graphics card (OpenGL framebuffer).
    Returns (fps, on_gpu): falls back to software drawing when OpenGL isn't available."""
    try:
        from PySide6.QtGui import QOffscreenSurface, QOpenGLContext, QSurfaceFormat
        from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat, QOpenGLPaintDevice
        ctx = QOpenGLContext()
        if not ctx.create():
            raise RuntimeError("no OpenGL")
        surf = QOffscreenSurface()
        surf.setFormat(ctx.format())
        surf.create()
        if not surf.isValid() or not ctx.makeCurrent(surf):
            raise RuntimeError("no OpenGL surface")
        try:
            fmt = QOpenGLFramebufferObjectFormat()
            fmt.setSamples(4)
            fmt.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
            fbo = QOpenGLFramebufferObject(w, h, fmt)
            fbo.bind()
            dev = QOpenGLPaintDevice(w, h)
            fns = ctx.functions()
            global GL_RENDERER
            GL_RENDERER = fns.glGetString(0x1F01) or ""          # GL_RENDERER: the card that actually drew
            fps = _frames(dev, fns.glFinish, w, h, heavy, seconds)
            fbo.release()
            return fps, True
        finally:
            ctx.doneCurrent()
    except Exception:
        from PySide6.QtGui import QImage
        img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        return _frames(img, lambda: None, w, h, heavy, seconds), False


def bench_disk(size_mb=256, rand_seconds=2.0):
    """Sequential write (with fsync) and read of a file in the cache folder,
    then random 4 KB reads. The file is dropped from the page cache before
    reading, so the disk itself is measured. Returns (seq MB/s, random reads/s)."""
    DISK_DIR.mkdir(parents=True, exist_ok=True)
    path = DISK_DIR / "rating.tmp"
    chunk = os.urandom(4 << 20)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        t0 = time.perf_counter()
        for _ in range(size_mb // 4):
            os.write(fd, chunk)
        os.fsync(fd)
        write = size_mb / (time.perf_counter() - t0)
        os.close(fd)

        fd = os.open(path, os.O_RDONLY)
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        t0 = time.perf_counter()
        while os.read(fd, 4 << 20):
            pass
        read = size_mb / (time.perf_counter() - t0)

        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_RANDOM)
        blocks = size_mb * 256
        rnd = random.Random(1)
        n, t0 = 0, time.perf_counter()
        while time.perf_counter() - t0 < rand_seconds:
            os.pread(fd, 4096, rnd.randrange(blocks) * 4096)
            n += 1
        rand = n / (time.perf_counter() - t0)
        os.close(fd)
        return (write + read) / 2, rand
    finally:
        try:
            path.unlink()
        except OSError:
            pass


STEPS = [("cpu", "Rating the processor…"), ("memory", "Rating memory…"),
         ("graphics", "Rating desktop graphics…"), ("gaming", "Rating gaming graphics…"),
         ("disk", "Rating the primary hard disk…")]


def assess(progress=None):
    """Run every benchmark (about 20 seconds). progress(step index, message) is called before each.
    Graphics needs a QGuiApplication; call from the thread that owns it or a worker
    with its own OpenGL context (QOffscreenSurface must be created on the GUI thread
    on some platforms, so the app runs graphics there)."""
    raw, sub, notes = {}, {}, {}
    for i, (key, msg) in enumerate(STEPS):
        if progress:
            progress(i, msg)
        if key == "cpu":
            raw[key] = round(bench_cpu(), 1)
            sub[key] = score("cpu", raw[key])
        elif key == "memory":
            raw[key] = round(bench_memory(), 2)
            sub[key] = memory_score(raw[key], ram_gb())
        elif key in ("graphics", "gaming"):
            fps, gpu = bench_graphics(heavy=key == "gaming")
            raw[key] = round(fps, 1)
            sub[key] = score(key, fps)
            if not gpu:
                notes[key] = "Measured without the graphics card (OpenGL wasn't available)"
        else:
            seq, rnd = bench_disk()
            raw[key] = {"sequential_mbps": round(seq, 1), "random_reads": round(rnd)}
            sub[key] = disk_score(seq, rnd)
    return {"date": datetime.datetime.now().isoformat(timespec="seconds"), "raw": raw, "scores": sub,
            "base": base_score(sub), "notes": notes, "components": describe()}


def save(result):
    SCORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SCORE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=1))
    tmp.replace(SCORE_FILE)


def load():
    try:
        r = json.loads(SCORE_FILE.read_text())
        return r if isinstance(r, dict) and "scores" in r else None
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- selftest ---
def _selftest():
    for kind, anchors in ANCHORS.items():
        xs = sorted({a[0] * 10 ** (k / 8) for a in anchors for k in range(-8, 9)})
        prev = 0
        for x in xs:
            s = score(kind, x)
            assert 1.0 <= s <= 5.9, (kind, x, s)
            assert s >= prev, f"{kind} not monotonic at {x}"
            assert s == round(s, 1)
            prev = s
        for x, expect in anchors:
            assert abs(score(kind, x) - expect) < 0.11, (kind, x, score(kind, x), expect)
        assert all(a[0] < b[0] and a[1] < b[1] for a, b in zip(anchors, anchors[1:])), kind
    assert score("cpu", 0) == 1.0 and score("cpu", None) == 1.0 and score("cpu", 10 ** 9) == 5.9
    assert interpolate([(1, 1.0), (10, 5.9)], 10 ** 0.5) == 3.4          # halfway on the log scale: 3.45 floors
    assert memory_score(30, 1.5) == 3.5 and memory_score(30, 16) == 5.9 and memory_score(0.3, 16) == 1.0
    assert disk_score(2500, 40000) == 5.9 and disk_score(60, 150) == 3.0
    assert base_score({"a": 4.2, "b": 3.1, "c": 5.9}) == 3.1 and base_score({}) is None
    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write("22 1 0:21 / / rw - btrfs /dev/nvme0n1p3 rw\n"
                "40 22 0:35 / /home rw - btrfs /dev/nvme0n1p3 rw\n"
                "41 22 0:36 / /tmp rw - tmpfs tmpfs rw\n"
                "42 22 0:37 / /mnt/my\\040disk rw - ext4 /dev/sdb1 rw\n")
    assert mount_source("/home/someone/.cache", f.name) == "/dev/nvme0n1p3"
    assert mount_source("/tmp/x", f.name) == "tmpfs"
    assert mount_source("/mnt/my disk/a", f.name) == "/dev/sdb1"
    os.unlink(f.name)
    assert renderer_name("Mesa Intel(R) Graphics (ADL GT2)") == "Intel(R) Graphics (ADL GT2)"
    assert renderer_name("llvmpipe (LLVM 18.1.8, 256 bits)") == ""
    print("bench selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        # --run: what the app starts in a separate process (OpenGL wants its own main
        # thread), printing "STEP <i> <message>" lines and saving the result.
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication(sys.argv[:1])
        quiet = "--run" in sys.argv
        r = assess(lambda i, m: print(f"STEP {i} {m}" if quiet else m, flush=True))
        if quiet:
            save(r)
            print("DONE", flush=True)
        else:
            print(json.dumps(r, indent=1))
