"""Image operations for Paint, on QImage (no widgets): flood fill, undo
history, flips, rotations, resize/skew and colour inversion.

    python3 -m halcyon_paint.imageops --selftest
"""
import sys
from array import array

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QTransform

FORMAT = QImage.Format_ARGB32


def blank(w, h, color=Qt.white):
    img = QImage(max(1, w), max(1, h), FORMAT)
    img.fill(color)
    return img


def flood_fill(img, x, y, color):
    """Fill the area of the same colour around (x, y). Works on a copy of the
    pixels as 32-bit words with a scanline stack, fast enough in pure Python."""
    w, h = img.width(), img.height()
    if not (0 <= x < w and 0 <= y < h):
        return False
    if img.format() != FORMAT:
        img.swap(img.convertToFormat(FORMAT))
    bpl = img.bytesPerLine() // 4
    px = array("I", bytes(img.constBits())[: bpl * 4 * h])
    target = px[y * bpl + x]
    new = QColor(color).rgba() & 0xFFFFFFFF
    if target == new:
        return False
    stack = [(x, y)]
    while stack:
        sx, sy = stack.pop()
        row = sy * bpl
        if px[row + sx] != target:
            continue
        lx = sx
        while lx > 0 and px[row + lx - 1] == target:
            lx -= 1
        rx = sx
        while rx < w - 1 and px[row + rx + 1] == target:
            rx += 1
        for i in range(lx, rx + 1):
            px[row + i] = new
        for ny in (sy - 1, sy + 1):
            if 0 <= ny < h:
                nrow = ny * bpl
                i = lx
                while i <= rx:
                    if px[nrow + i] == target:
                        stack.append((i, ny))
                        while i <= rx and px[nrow + i] == target:
                            i += 1
                    i += 1
    out = QImage(px.tobytes(), w, h, bpl * 4, FORMAT).copy()
    img.swap(out)
    return True


class History:
    """Undo/redo as whole-image snapshots (cheap at Paint's sizes)."""
    def __init__(self, depth=30):
        self.depth = depth
        self.undo_stack, self.redo_stack = [], []

    def push(self, img):
        self.undo_stack.append(img.copy())
        del self.undo_stack[:-self.depth]
        self.redo_stack.clear()

    def undo(self, current):
        if not self.undo_stack:
            return None
        self.redo_stack.append(current.copy())
        return self.undo_stack.pop()

    def redo(self, current):
        if not self.redo_stack:
            return None
        self.undo_stack.append(current.copy())
        return self.redo_stack.pop()

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()


def flipped(img, horizontal):
    return img.flipped(Qt.Horizontal if horizontal else Qt.Vertical)


def rotated(img, degrees):
    return img.transformed(QTransform().rotate(degrees))


def resized_canvas(img, w, h, fill=Qt.white):
    """Change the canvas size, keeping the pixels at the top-left."""
    out = blank(w, h, fill)
    p = QPainter(out)
    p.drawImage(0, 0, img)
    p.end()
    return out


def stretched(img, sx_pct, sy_pct, skew_x=0, skew_y=0, fill=Qt.white):
    """Image > Resize/Skew: stretch by percent, skew by degrees."""
    import math
    w = max(1, round(img.width() * sx_pct / 100))
    h = max(1, round(img.height() * sy_pct / 100))
    out = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    if skew_x or skew_y:
        t = QTransform().shear(math.tan(math.radians(skew_x)), math.tan(math.radians(skew_y)))
        sk = out.transformed(t, Qt.SmoothTransformation)
        bg = blank(sk.width(), sk.height(), fill)
        p = QPainter(bg)
        p.drawImage(0, 0, sk)
        p.end()
        out = bg
    return out.convertToFormat(FORMAT)


def inverted(img):
    out = img.copy()
    out.invertPixels(QImage.InvertRgb)
    return out


def copy_region(img, rect, mask=None):
    """The pixels inside rect (and inside a free-form mask path, if given), transparent elsewhere."""
    part = img.copy(rect).convertToFormat(FORMAT)
    if mask is not None:
        clip = QImage(part.size(), FORMAT)
        clip.fill(Qt.transparent)
        p = QPainter(clip)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setClipPath(mask.translated(-rect.x(), -rect.y()))
        p.drawImage(0, 0, part)
        p.end()
        part = clip
    return part


def erase_region(img, rect, color, mask=None):
    p = QPainter(img)
    if mask is not None:
        p.setClipPath(mask)
    p.fillRect(rect, QColor(color))
    p.end()


def paste(img, piece, pos):
    p = QPainter(img)
    p.drawImage(pos, piece)
    p.end()


def _selftest():
    import time
    from PySide6.QtGui import QGuiApplication, QPainterPath
    app = QGuiApplication.instance() or QGuiApplication([])
    img = blank(640, 480)
    p = QPainter(img)
    p.setPen(QColor("black"))
    p.drawRect(100, 100, 200, 100)                  # a closed box
    p.end()
    t = time.time()
    assert flood_fill(img, 150, 150, QColor("red"))
    full = time.time() - t
    assert QColor(img.pixel(150, 150)) == QColor("red") and QColor(img.pixel(299, 199)) == QColor("red")
    assert QColor(img.pixel(50, 50)) == QColor("white")                 # outside the box untouched
    assert QColor(img.pixel(100, 100)) == QColor("black")               # the border untouched
    assert not flood_fill(img, 150, 150, QColor("red"))                 # same colour: nothing to do
    t = time.time()
    flood_fill(img, 5, 5, QColor("blue"))                               # nearly the whole canvas
    big = time.time() - t
    assert QColor(img.pixel(639, 479)) == QColor("blue") and QColor(img.pixel(150, 150)) == QColor("red")
    assert big < 3.0, f"flood fill too slow: {big:.2f}s"

    h = History(depth=20)
    cur = blank(10, 10)
    for i in range(25):
        h.push(cur)
        cur = blank(10, 10, QColor(i, 0, 0))
    assert len(h.undo_stack) == 20
    prev = h.undo(cur)
    assert QColor(prev.pixel(0, 0)) == QColor(23, 0, 0)
    again = h.redo(prev)
    assert QColor(again.pixel(0, 0)) == QColor(24, 0, 0)
    h.push(again)
    assert h.redo(again) is None                                        # a new change drops the redo trail

    r = rotated(blank(30, 10), 90)
    assert (r.width(), r.height()) == (10, 30)
    f = blank(4, 1)
    f.setPixelColor(0, 0, QColor("red"))
    assert flipped(f, True).pixelColor(3, 0) == QColor("red")
    small = blank(5, 5, QColor("green"))
    grown = resized_canvas(small, 8, 6)
    assert grown.size().width() == 8 and grown.pixelColor(4, 4) == QColor("green") and \
        grown.pixelColor(7, 5) == QColor("white")
    s = stretched(blank(100, 50), 50, 200)
    assert (s.width(), s.height()) == (50, 100)
    assert inverted(blank(2, 2, QColor("black"))).pixelColor(0, 0) == QColor("white")

    # cut and paste round trip, rectangle and free-form
    src = blank(20, 20)
    src.setPixelColor(5, 5, QColor("red"))
    piece = copy_region(src, QRect(4, 4, 4, 4))
    erase_region(src, QRect(4, 4, 4, 4), "white")
    assert src.pixelColor(5, 5) == QColor("white")
    paste(src, piece, QPoint(10, 10))
    assert src.pixelColor(11, 11) == QColor("red")
    tri = QPainterPath()
    tri.moveTo(0, 0)
    tri.lineTo(10, 0)
    tri.lineTo(0, 10)
    tri.closeSubpath()
    part = copy_region(blank(10, 10, QColor("blue")), QRect(0, 0, 10, 10), tri)
    assert part.pixelColor(1, 1).alpha() == 255 and part.pixelColor(9, 9).alpha() == 0
    print(f"imageops selftest ok (fill: box {full * 1000:.0f} ms, whole canvas {big * 1000:.0f} ms)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
