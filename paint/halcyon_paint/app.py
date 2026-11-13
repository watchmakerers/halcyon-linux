"""Halcyon Paint, after Paint in Windows Vista: the toolbox on the left with
its options box underneath, the colour box at the bottom, menus for the
image, and a canvas you can zoom and resize by its handles.

    halcyon-paint [FILE]
"""
import math
import os
import random
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QActionGroup, QBrush, QColor, QCursor, QFont, QIcon, QImage, QKeySequence,
                           QPainter, QPainterPath, QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QColorDialog, QDialog, QDialogButtonBox, QFileDialog,
                               QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
                               QRadioButton, QScrollArea, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from . import imageops as ops

TOOLS = [("freesel", "Free-Form Select"), ("select", "Select"), ("eraser", "Eraser/Color Eraser"),
         ("fill", "Fill With Color"), ("picker", "Pick Color"), ("zoom", "Magnifier"), ("pencil", "Pencil"),
         ("brush", "Brush"), ("airbrush", "Airbrush"), ("text", "Text"), ("line", "Line"), ("curve", "Curve"),
         ("rect", "Rectangle"), ("polygon", "Polygon"), ("ellipse", "Ellipse"), ("rrect", "Rounded Rectangle")]
SHAPES = {"rect", "ellipse", "rrect", "polygon"}
PALETTE = ["#000000", "#808080", "#800000", "#808000", "#008000", "#008080", "#000080", "#800080",
           "#808040", "#004040", "#0080ff", "#004080", "#8000ff", "#804000",
           "#ffffff", "#c0c0c0", "#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff",
           "#ffff80", "#00ff80", "#80ffff", "#8080ff", "#ff0080", "#ff8040"]
ZOOMS = [1, 2, 4, 6, 8]
HANDLE = 5


# ------------------------------------------------------------- tool icons ---
def tool_icon(tool):
    """Small drawn icons, so the toolbox looks the same with any icon theme."""
    pm = QPixmap(44, 44)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    ink = QPen(QColor("#1f2b3a"), 1.4)
    p.setPen(ink)
    blue, yellow, red = QColor("#3d8fe0"), QColor("#f2c330"), QColor("#d0281e")
    if tool == "select":
        p.setPen(QPen(QColor("#1f2b3a"), 1.2, Qt.DashLine))
        p.drawRect(QRectF(3, 4, 15, 13))
    elif tool == "freesel":
        p.setPen(QPen(QColor("#1f2b3a"), 1.2, Qt.DashLine))
        path = QPainterPath(QPointF(4, 10))
        path.cubicTo(2, 2, 14, 1, 17, 6)
        path.cubicTo(20, 12, 12, 20, 7, 17)
        path.closeSubpath()
        p.drawPath(path)
    elif tool == "eraser":
        p.setBrush(QColor("#f4a6b8"))
        p.drawPolygon(QPolygonF([QPointF(4, 14), QPointF(11, 6), QPointF(18, 11), QPointF(11, 19)]))
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(QPolygonF([QPointF(4, 14), QPointF(7.5, 10), QPointF(14.5, 15), QPointF(11, 19)]))
    elif tool == "fill":
        p.setBrush(QColor("#c9d6e6"))
        p.drawPolygon(QPolygonF([QPointF(4, 10), QPointF(10, 4), QPointF(16, 10), QPointF(10, 16)]))
        p.setBrush(blue)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(15, 12, 4, 6))
    elif tool == "picker":
        p.setBrush(QColor("#c9d6e6"))
        p.drawRoundedRect(QRectF(12, 3, 5, 8), 2, 2)
        p.drawLine(QPointF(13, 10), QPointF(5, 18))
        p.setBrush(blue)
        p.drawEllipse(QRectF(3.5, 16.5, 3, 3))
    elif tool == "zoom":
        p.setBrush(QColor(200, 230, 255, 160))
        p.drawEllipse(QRectF(3, 3, 11, 11))
        p.setPen(QPen(QColor("#1f2b3a"), 2.6, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(13, 13), QPointF(19, 19))
    elif tool == "pencil":
        p.setBrush(yellow)
        p.drawPolygon(QPolygonF([QPointF(6, 18), QPointF(4, 19), QPointF(5, 16), QPointF(16, 5),
                                 QPointF(18, 7), QPointF(7, 18)]))
    elif tool == "brush":
        p.setBrush(QColor("#a0703a"))
        p.drawRoundedRect(QRectF(11, 2, 4, 10), 1.5, 1.5)
        p.setBrush(red)
        path = QPainterPath(QPointF(10, 12))
        path.lineTo(16, 12)
        path.cubicTo(16, 17, 12, 20, 7, 20)
        path.cubicTo(10, 17, 10, 15, 10, 12)
        p.drawPath(path)
    elif tool == "airbrush":
        p.setBrush(QColor("#c9d6e6"))
        p.drawRoundedRect(QRectF(10, 7, 7, 12), 2, 2)
        p.drawRect(QRectF(12, 4, 3, 3))
        p.setPen(Qt.NoPen)
        p.setBrush(blue)
        for x, y in ((4, 6), (6, 4), (3, 9), (7, 8), (5, 11), (2, 5)):
            p.drawEllipse(QRectF(x, y, 1.6, 1.6))
    elif tool == "text":
        f = QFont("serif")
        f.setPixelSize(17)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 0, 22, 22), Qt.AlignCenter, "A")
    elif tool == "line":
        p.setPen(QPen(QColor("#1f2b3a"), 1.8))
        p.drawLine(QPointF(4, 18), QPointF(18, 4))
    elif tool == "curve":
        p.setPen(QPen(QColor("#1f2b3a"), 1.8))
        path = QPainterPath(QPointF(3, 17))
        path.cubicTo(6, 0, 14, 22, 19, 5)
        p.drawPath(path)
    elif tool == "rect":
        p.drawRect(QRectF(3.5, 5.5, 15, 11))
    elif tool == "polygon":
        p.drawPolygon(QPolygonF([QPointF(4, 17), QPointF(6, 5), QPointF(13, 9), QPointF(18, 4), QPointF(17, 17)]))
    elif tool == "ellipse":
        p.drawEllipse(QRectF(3, 5, 16, 12))
    elif tool == "rrect":
        p.drawRoundedRect(QRectF(3.5, 5.5, 15, 11), 4, 4)
    p.end()
    return QIcon(pm)


# ----------------------------------------------------------------- canvas ---
class Canvas(QWidget):
    """The picture: drawing, selections, zoom and resize handles."""
    changed = Signal()
    moved = Signal(str, str)                  # position text, size text

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.image = ops.blank(640, 480)
        self.history = ops.History(30)
        self.zoom = 1
        self.grid = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.drag = None                      # what the mouse is doing: (kind, data)
        self.preview = None                   # function(painter) drawing the shape being dragged
        self.sel = None                       # QRect selection in image coords
        self.sel_mask = None                  # QPainterPath for a free-form selection
        self.floating = None                  # lifted pixels (QImage) while moving/pasting
        self.float_pos = QPoint()
        self.ants = 0
        self.ant_timer = QTimer(self, interval=150, timeout=self._march)
        self.spray_timer = QTimer(self, interval=30, timeout=self._spray)
        self.curve = []                       # points while bending a curve
        self.poly = []                        # a polygon's corners so far
        self.poly_cursor = None               # where its rubber-band edge ends
        self.text_box = None
        self.resize_canvas()

    # -- coordinates
    def to_img(self, pos):
        return QPoint(int(pos.x() // self.zoom), int(pos.y() // self.zoom))

    def resize_canvas(self):
        w, h = self.image.width() * self.zoom, self.image.height() * self.zoom
        self.setFixedSize(w + HANDLE * 3, h + HANDLE * 3)
        self.update()

    def set_zoom(self, z, keep=None):
        self.commit_text()
        self.zoom = z
        self.resize_canvas()
        self.win.zoom_changed(z)

    # -- history
    def snapshot(self):
        self.history.push(self.image)
        self.win.modified = True

    def replace(self, img, record=True):
        if record:
            self.snapshot()
        self.drop_selection(commit=False)
        self.image = img.convertToFormat(ops.FORMAT)
        self.resize_canvas()
        self.changed.emit()

    def undo(self):
        self.commit_floating()
        img = self.history.undo(self.image)
        if img is not None:
            self.image = img
            self.sel = self.sel_mask = None
            self.resize_canvas()

    def redo(self):
        img = self.history.redo(self.image)
        if img is not None:
            self.image = img
            self.resize_canvas()

    # -- colours for a mouse button
    def colors(self, button):
        a, b = self.win.primary, self.win.secondary
        return (a, b) if button != Qt.RightButton else (b, a)

    # ------------------------------------------------------------ selection ---
    def select_all(self):
        self.win.set_tool("select")
        self.commit_floating()
        self.sel, self.sel_mask = self.image.rect(), None
        self._ants_on()

    def _ants_on(self):
        if not self.ant_timer.isActive():
            self.ant_timer.start()
        self.win.selection_changed(bool(self.sel))
        self.update()

    def _march(self):
        self.ants = (self.ants + 1) % 8
        self.update()

    def lift(self):
        """Pick the selected pixels up so they can move; the hole gets the secondary colour."""
        if self.floating is not None or not self.sel:
            return
        self.snapshot()
        self.floating = ops.copy_region(self.image, self.sel, self.sel_mask)
        if self.win.opt("transparent"):
            self._clear_color(self.floating, self.win.secondary)
        ops.erase_region(self.image, self.sel, self.win.secondary, self.sel_mask)
        self.float_pos = self.sel.topLeft()

    @staticmethod
    def _clear_color(img, color):
        key = QColor(color).rgb()
        for y in range(img.height()):
            for x in range(img.width()):
                if img.pixel(x, y) == key:
                    img.setPixelColor(x, y, Qt.transparent)

    def commit_floating(self):
        if self.floating is not None:
            ops.paste(self.image, self.floating, self.float_pos)
            self.floating = None
            self.changed.emit()
        self.update()

    def drop_selection(self, commit=True):
        if commit:
            self.commit_floating()
        else:
            self.floating = None
        self.sel = self.sel_mask = None
        self.ant_timer.stop()
        self.win.selection_changed(False)
        self.update()

    def delete_selection(self):
        if self.floating is not None:
            self.floating = None
        elif self.sel:
            self.snapshot()
            ops.erase_region(self.image, self.sel, self.win.secondary, self.sel_mask)
        self.drop_selection(commit=False)
        self.changed.emit()

    def selection_image(self):
        if self.floating is not None:
            return self.floating.copy()
        if self.sel:
            return ops.copy_region(self.image, self.sel, self.sel_mask)
        return None

    def paste_image(self, img):
        self.win.set_tool("select")
        self.commit_floating()
        if img.width() > self.image.width() or img.height() > self.image.height():
            if QMessageBox.question(self, "Paint", "The image in the clipboard is larger than the bitmap. "
                                    "Would you like the bitmap enlarged?") == QMessageBox.Yes:
                self.replace(ops.resized_canvas(self.image, max(img.width(), self.image.width()),
                                                max(img.height(), self.image.height()), self.win.secondary))
        self.snapshot()
        self.floating = img.convertToFormat(ops.FORMAT)
        view = self.win.scroll.viewport().rect()
        top_left = self.to_img(self.win.scroll.widget().mapFrom(self.win.scroll.viewport(), view.topLeft()))
        self.float_pos = QPoint(max(0, top_left.x()), max(0, top_left.y()))
        self.sel = QRect(self.float_pos, self.floating.size())
        self.sel_mask = None
        self._ants_on()

    def crop_to_selection(self):
        img = self.selection_image()
        if img is not None:
            bg = ops.blank(img.width(), img.height(), self.win.secondary)
            ops.paste(bg, img, QPoint(0, 0))
            self.replace(bg)

    # --------------------------------------------------------------- text ---
    def start_text(self, pos):
        self.commit_text()
        box = QLineEdit(self)
        box.setFrame(False)
        f = QFont(self.win.text_font)
        f.setPixelSize(max(6, int(self.win.opt("text_size") * self.zoom)))
        box.setFont(f)
        c = QColor(self.win.primary)
        box.setStyleSheet(f"QLineEdit {{ background: rgba(255,255,255,0); color: {c.name()}; "
                          f"border: 1px dashed #3c7fb1; }}")
        box.setMinimumWidth(120)
        box.move(pos.x() * self.zoom, pos.y() * self.zoom)
        box.resize(max(120, 20 * self.zoom * 4), int(f.pixelSize() * 1.6) + 4)
        box.textChanged.connect(lambda t: box.resize(max(box.width(), box.fontMetrics().horizontalAdvance(t) + 24),
                                                     box.height()))
        box.returnPressed.connect(self.commit_text)
        box.setProperty("at", pos)
        box.show()
        box.setFocus()
        self.text_box = box

    def commit_text(self):
        box, self.text_box = self.text_box, None
        if box is None:
            return
        text = box.text()
        at = box.property("at")
        box.hide()                            # deleteLater waits for the event loop; don't leave it on screen
        box.deleteLater()
        if text:
            self.snapshot()
            p = QPainter(self.image)
            p.setRenderHint(QPainter.TextAntialiasing)
            f = QFont(self.win.text_font)
            f.setPixelSize(self.win.opt("text_size"))
            p.setFont(f)
            p.setPen(QColor(self.win.primary))
            fm = p.fontMetrics()
            p.drawText(QPoint(at.x() + 2, at.y() + 2 + fm.ascent()), text)
            p.end()
            self.changed.emit()
        self.update()

    # ------------------------------------------------------------- drawing ---
    def pen(self, color, width=1, aa=False, cap=Qt.RoundCap):
        return QPen(QColor(color), width, Qt.SolidLine, cap, Qt.RoundJoin)

    def painter(self, aa=False):
        p = QPainter(self.image)
        p.setRenderHint(QPainter.Antialiasing, aa)
        return p

    def stroke(self, a, b, button):
        """Pencil, brush and eraser segments."""
        tool = self.win.tool
        fg, bg = self.colors(button)
        p = self.painter()
        if tool == "pencil":
            p.setPen(self.pen(fg, 1, cap=Qt.SquareCap))
        elif tool == "brush":
            size = self.win.opt("brush_size")
            shape = self.win.opt("brush_shape")
            p.setPen(self.pen(fg, size, cap=Qt.RoundCap if shape == "round" else Qt.SquareCap))
        elif tool == "eraser":
            size = self.win.opt("eraser_size")
            p.setPen(self.pen(self.win.secondary, size, cap=Qt.SquareCap))
        p.drawLine(a, b)
        if a == b:
            p.drawPoint(a)
        p.end()
        self.update()

    def _spray(self):
        if not self.drag or self.drag[0] != "spray":
            return
        _, (pos, button) = self.drag
        r = self.win.opt("spray_size")
        fg, _ = self.colors(button)
        p = self.painter()
        p.setPen(QPen(QColor(fg), 1))
        for _ in range(r):
            a, d = random.uniform(0, math.tau), r * math.sqrt(random.random())
            p.drawPoint(QPointF(pos.x() + math.cos(a) * d, pos.y() + math.sin(a) * d))
        p.end()
        self.update()

    def shape(self, p, tool, a, b, button, shift=False):
        """Rectangles and ellipses with the fill style; lines with the line width."""
        fg, bg = self.colors(button)
        width = self.win.opt("line_width")
        if tool == "line":
            if shift:
                b = snap45(a, b)
            p.setPen(self.pen(fg, width))
            p.drawLine(a, b)
            return
        r = QRect(a, b).normalized()
        if shift:
            side = min(r.width(), r.height())
            r = QRect(a.x() if b.x() >= a.x() else a.x() - side, a.y() if b.y() >= a.y() else a.y() - side,
                      side, side)
        style = self.win.opt("fill_style")
        p.setPen(self.pen(fg, width, cap=Qt.SquareCap) if style != "fill" else Qt.NoPen)
        p.setBrush(QColor(bg if style == "both" else fg) if style != "outline" else Qt.NoBrush)
        if tool == "rect":
            p.drawRect(r)
        elif tool == "ellipse":
            p.drawEllipse(r)
        elif tool == "rrect":
            p.drawRoundedRect(r, 10, 10)

    def draw_polygon(self, p, pts, button, closed):
        fg, bg = self.colors(button)
        style = self.win.opt("fill_style")
        p.setPen(self.pen(fg, self.win.opt("line_width")) if style != "fill" or not closed else Qt.NoPen)
        if closed:
            p.setBrush(QColor(bg if style == "both" else fg) if style != "outline" else Qt.NoBrush)
            p.drawPolygon(QPolygonF([QPointF(q) for q in pts]))
        else:
            p.drawPolyline(QPolygonF([QPointF(q) for q in pts]))

    def draw_curve(self, p, pts, button):
        fg, _ = self.colors(button)
        p.setPen(self.pen(fg, self.win.opt("line_width")))
        a, b = pts[0], pts[1]
        c1 = pts[2] if len(pts) > 2 else a
        c2 = pts[3] if len(pts) > 3 else c1
        path = QPainterPath(QPointF(a))
        path.cubicTo(QPointF(c1), QPointF(c2), QPointF(b))
        p.drawPath(path)

    # --------------------------------------------------------------- mouse ---
    def handle_at(self, pos):
        w, h = self.image.width() * self.zoom, self.image.height() * self.zoom
        if QRect(w, h, HANDLE * 2, HANDLE * 2).contains(pos):
            return "corner"
        if QRect(w, h // 2 - HANDLE, HANDLE * 2, HANDLE * 2).contains(pos):
            return "right"
        if QRect(w // 2 - HANDLE, h, HANDLE * 2, HANDLE * 2).contains(pos):
            return "bottom"
        return None

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        button = e.button()
        tool = self.win.tool
        handle = self.handle_at(pos)
        if handle and button == Qt.LeftButton:
            self.commit_text()
            self.drop_selection()
            self.drag = ("resize", handle)
            return
        ip = self.to_img(pos)
        if tool != "text":
            self.commit_text()
        if tool in ("select", "freesel"):
            if self.sel and self._in_selection(ip) and button == Qt.LeftButton:
                self.lift()
                self.drag = ("move", ip - self.float_pos)
                return
            self.drop_selection()
            self.drag = ("select", [ip])
        elif tool in ("pencil", "brush", "eraser"):
            self.snapshot()
            self.drag = ("stroke", (ip, button))
            self.stroke(ip, ip, button)
        elif tool == "airbrush":
            self.snapshot()
            self.drag = ("spray", (ip, button))
            self._spray()
            self.spray_timer.start()
        elif tool == "fill":
            fg, _ = self.colors(button)
            before = self.image.copy()
            if ops.flood_fill(self.image, ip.x(), ip.y(), fg):
                self.history.push(before)
                self.win.modified = True
                self.changed.emit()
            self.update()
        elif tool == "picker":
            if self.image.rect().contains(ip):
                c = self.image.pixelColor(ip)
                if button == Qt.RightButton:
                    self.win.set_secondary(c)
                else:
                    self.win.set_primary(c)
            self.win.set_tool(self.win.previous_tool)
        elif tool == "zoom":
            i = ZOOMS.index(self.zoom) if self.zoom in ZOOMS else 0
            z = ZOOMS[min(len(ZOOMS) - 1, i + 1)] if button == Qt.LeftButton else ZOOMS[max(0, i - 1)]
            self.set_zoom(z)
            self.win.scroll.ensureVisible(int(ip.x() * z), int(ip.y() * z), 200, 200)
        elif tool == "text":
            if self.text_box and self.text_box.geometry().contains(pos):
                return
            self.commit_text()
            self.start_text(ip)
        elif tool in ("line", "rect", "ellipse", "rrect"):
            self.drag = ("shape", (ip, ip, button))
        elif tool == "curve":
            if not self.curve:
                self.drag = ("curve", (button,))
                self.curve = [ip, ip]
            else:
                self.curve.append(ip)
                self.drag = ("curve", (button,))
        elif tool == "polygon":
            if not self.poly:                 # the first edge is dragged out like a line
                self.poly = [ip]
                self.poly_button = button
            else:
                self.poly.append(ip)          # then each click adds a corner
            self.poly_cursor = ip
            self.drag = ("poly", button)
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        ip = self.to_img(pos)
        h = self.handle_at(pos)
        self.setCursor({"corner": Qt.SizeFDiagCursor, "right": Qt.SizeHorCursor,
                        "bottom": Qt.SizeVerCursor}.get(h, self.win.tool_cursor()))
        size_text = ""
        if self.drag:
            kind, data = self.drag
            if kind == "resize":
                w = max(1, ip.x()) if data in ("right", "corner") else self.image.width()
                hh = max(1, ip.y()) if data in ("bottom", "corner") else self.image.height()
                self.preview = ("resize", QSize(w, hh))
                size_text = f"{w} x {hh}"
            elif kind == "select":
                if self.win.tool == "freesel":
                    data.append(ip)
                else:
                    data[1:] = [ip]
                r = self._drag_rect(data)
                size_text = f"{r.width()} x {r.height()}"
            elif kind == "move":
                self.float_pos = ip - data
                self.sel = QRect(self.float_pos, self.floating.size())
            elif kind == "stroke":
                last, button = data
                self.stroke(last, ip, button)
                self.drag = ("stroke", (ip, button))
            elif kind == "spray":
                self.drag = ("spray", (ip, data[1]))
            elif kind == "shape":
                a, _, button = data
                self.drag = ("shape", (a, ip, button))
                size_text = f"{abs(ip.x() - a.x())} x {abs(ip.y() - a.y())}"
            elif kind == "curve":
                self.curve[-1] = ip
            elif kind == "poly":
                self.poly_cursor = ip
            self.update()
        elif self.poly:
            self.poly_cursor = ip
            self.update()
        inside = self.image.rect().contains(ip)
        self.moved.emit(f"{ip.x()}, {ip.y()}" if inside else "", size_text)

    def mouseReleaseEvent(self, e):
        if not self.drag:
            return
        kind, data = self.drag
        self.drag = None
        ip = self.to_img(e.position().toPoint())
        if kind == "resize":
            _, size = self.preview
            self.preview = None
            self.replace(ops.resized_canvas(self.image, size.width(), size.height(), self.win.secondary))
        elif kind == "select":
            r = self._drag_rect(data).intersected(self.image.rect())
            if r.width() > 0 and r.height() > 0:
                self.sel = r
                if self.win.tool == "freesel" and len(data) > 2:
                    path = QPainterPath(QPointF(data[0]))
                    for q in data[1:]:
                        path.lineTo(QPointF(q))
                    path.closeSubpath()
                    self.sel_mask = path
                self._ants_on()
        elif kind == "move":
            self.changed.emit()
        elif kind in ("stroke",):
            self.changed.emit()
        elif kind == "spray":
            self.spray_timer.stop()
            self.changed.emit()
        elif kind == "shape":
            a, b, button = data
            if a != b:
                self.snapshot()
                p = self.painter(aa=False)
                self.shape(p, self.win.tool, a, b, button, bool(e.modifiers() & Qt.ShiftModifier))
                p.end()
                self.changed.emit()
        elif kind == "poly":
            if len(self.poly) == 1 and ip != self.poly[0]:
                self.poly.append(ip)          # end of the first, dragged edge
        elif kind == "curve":
            # a curve is finished after the line and two bends
            if len(self.curve) >= 4 or (len(self.curve) == 2 and self.curve[0] == self.curve[1]):
                self._finish_curve(data[0])
        self.update()

    def mouseDoubleClickEvent(self, e):
        if self.win.tool == "polygon" and len(self.poly) >= 3:
            # the double-click's first press already added its corner
            self.snapshot()
            p = self.painter()
            self.draw_polygon(p, self.poly, self.poly_button, closed=True)
            p.end()
            self.poly = []
            self.drag = None
            self.changed.emit()
            self.update()

    def _finish_curve(self, button):
        if len(self.curve) >= 2 and self.curve[0] != self.curve[1]:
            self.snapshot()
            p = self.painter(aa=False)
            self.draw_curve(p, self.curve, button)
            p.end()
            self.changed.emit()
        self.curve = []

    def cancel_shape(self):
        """Esc: drop an unfinished curve or polygon (or a selection)."""
        if self.curve or self.poly:
            self.curve, self.poly = [], []
        elif self.text_box:
            self.text_box.deleteLater()
            self.text_box = None
        else:
            self.drop_selection()
        self.update()

    def finish_pending(self):
        """Switching tools completes what's half done."""
        self.commit_text()
        self.commit_floating()
        if self.curve:
            self._finish_curve(Qt.LeftButton)
        if len(self.poly) >= 3:
            self.snapshot()
            p = self.painter()
            self.draw_polygon(p, self.poly, self.poly_button, closed=True)
            p.end()
        self.poly = []
        self.update()

    def _drag_rect(self, pts):
        if self.win.tool == "freesel":
            xs, ys = [q.x() for q in pts], [q.y() for q in pts]
            return QRect(QPoint(min(xs), min(ys)), QPoint(max(xs), max(ys)))
        return QRect(pts[0], pts[-1]).normalized()

    def _in_selection(self, ip):
        if self.sel_mask is not None and self.floating is None:
            return self.sel_mask.contains(QPointF(ip))
        return self.sel.contains(ip)

    # ---------------------------------------------------------------- paint ---
    def paintEvent(self, e):
        p = QPainter(self)
        z = self.zoom
        w, h = self.image.width() * z, self.image.height() * z
        p.drawImage(QRect(0, 0, w, h), self.image)
        if self.floating is not None:
            p.drawImage(QRect(self.float_pos.x() * z, self.float_pos.y() * z, self.floating.width() * z,
                              self.floating.height() * z), self.floating)
        # what's being drawn right now
        if self.drag and self.drag[0] == "shape":
            a, b, button = self.drag[1]
            p.save()
            p.scale(z, z)
            self.shape(p, self.win.tool, a, b, button, bool(QApplication.keyboardModifiers() & Qt.ShiftModifier))
            p.restore()
        if self.curve:
            p.save()
            p.scale(z, z)
            self.draw_curve(p, self.curve, self.drag[1][0] if self.drag and self.drag[0] == "curve" else Qt.LeftButton)
            p.restore()
        if self.poly:
            p.save()
            p.scale(z, z)
            self.draw_polygon(p, self.poly + [self.poly_cursor or self.poly[-1]],
                              getattr(self, "poly_button", Qt.LeftButton), closed=False)
            p.restore()
        if self.grid and z >= 4:
            p.setPen(QColor(128, 128, 128, 110))
            for x in range(0, w + 1, z):
                p.drawLine(x, 0, x, h)
            for y in range(0, h + 1, z):
                p.drawLine(0, y, w, y)
        # selection: marching ants
        pts = None
        if self.drag and self.drag[0] == "select":
            pts = self.drag[1]
        if self.sel or pts:
            for color, dash in ((QColor("white"), None), (QColor("black"), self.ants)):
                pen = QPen(color, 1)
                if dash is not None:
                    pen.setDashPattern([4, 4])
                    pen.setDashOffset(dash)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                if pts is not None and self.win.tool == "freesel":
                    p.drawPolyline(QPolygonF([QPointF(q.x() * z, q.y() * z) for q in pts]))
                elif self.sel_mask is not None and self.floating is None and pts is None:
                    p.save()
                    p.scale(z, z)
                    pen.setWidthF(1 / z)
                    p.setPen(pen)
                    p.drawPath(self.sel_mask)
                    p.restore()
                else:
                    r = self._drag_rect(pts) if pts is not None else self.sel
                    p.drawRect(QRect(r.x() * z, r.y() * z, r.width() * z, r.height() * z))
        # canvas resize preview and handles
        if self.preview and self.preview[0] == "resize":
            s = self.preview[1]
            p.setPen(QPen(QColor("#1f2b3a"), 1, Qt.DotLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(0, 0, s.width() * z, s.height() * z)
        p.setPen(QColor("#1f2b3a"))
        p.setBrush(QColor("#3c7fb1"))
        for r in (QRect(w, h, HANDLE, HANDLE), QRect(w, h // 2 - HANDLE // 2, HANDLE, HANDLE),
                  QRect(w // 2 - HANDLE // 2, h, HANDLE, HANDLE)):
            p.drawRect(r)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancel_shape()
        elif e.key() == Qt.Key_Delete and self.sel:
            self.delete_selection()
        else:
            super().keyPressEvent(e)


def snap45(a, b):
    """Shift-drag: keep lines horizontal, vertical or diagonal."""
    dx, dy = b.x() - a.x(), b.y() - a.y()
    ang = round(math.atan2(dy, dx) / (math.pi / 4)) * (math.pi / 4)
    d = math.hypot(dx, dy)
    return QPoint(a.x() + round(math.cos(ang) * d), a.y() + round(math.sin(ang) * d))


# ------------------------------------------------------------ tool options ---
class OptionsBox(QFrame):
    """The box under the toolbox; what's in it depends on the tool."""
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setFixedSize(54, 72)
        self.setStyleSheet("OptionsBox { background: white; border: 1px solid #8ea6c4; border-radius: 2px; }")
        self.items = []

    def set_tool(self, tool):
        w = self.win
        if tool in ("brush",):
            self.items = [("brush_size", s, "round") for s in (7, 4, 1)] + \
                         [("brush_size", s, "square") for s in (7, 4, 1)]
        elif tool == "eraser":
            self.items = [("eraser_size", s, None) for s in (4, 6, 8, 10)]
        elif tool == "airbrush":
            self.items = [("spray_size", s, None) for s in (4, 8, 12)]
        elif tool in ("line", "curve"):
            self.items = [("line_width", s, None) for s in (1, 2, 3, 4, 5)]
        elif tool in SHAPES:
            self.items = [("fill_style", s, None) for s in ("outline", "both", "fill")]
        elif tool == "zoom":
            self.items = [("zoom", z, None) for z in (1, 2, 6, 8)]
        elif tool in ("select", "freesel"):
            self.items = [("transparent", False, None), ("transparent", True, None)]
        elif tool == "text":
            self.items = [("text_size", s, None) for s in (10, 16, 24, 36)]
        else:
            self.items = []
        self.update()

    def _rects(self):
        n = len(self.items)
        if not n:
            return []
        if self.items[0][0] == "brush_size":
            return [QRectF(4 + (i % 3) * 16, 6 + (i // 3) * 30, 14, 26) for i in range(n)]
        return [QRectF(4, 4 + i * (64 / n), 46, 64 / n - 2) for i in range(n)]

    def _selected(self, item):
        key, val, extra = item
        if key == "zoom":
            return self.win.canvas.zoom == val
        if key == "brush_size":
            return self.win.opt("brush_size") == val and self.win.opt("brush_shape") == extra
        return self.win.opt(key) == val

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for item, r in zip(self.items, self._rects()):
            key, val, extra = item
            sel = self._selected(item)
            if sel:
                p.fillRect(r, QColor("#3c7fb1"))
            ink = QColor("white" if sel else "black")
            p.setPen(Qt.NoPen)
            p.setBrush(ink)
            c = r.center()
            if key == "brush_size":
                s = val * 0.9 + 1
                (p.drawEllipse if extra == "round" else p.drawRect)(QRectF(c.x() - s / 2, c.y() - s / 2, s, s))
            elif key in ("eraser_size",):
                p.drawRect(QRectF(c.x() - val / 2, c.y() - val / 2, val, val))
            elif key == "spray_size":
                rnd = random.Random(val)
                for _ in range(val * 2):
                    a, d = rnd.uniform(0, math.tau), val * 0.8 * math.sqrt(rnd.random())
                    p.drawEllipse(QPointF(c.x() + math.cos(a) * d, c.y() + math.sin(a) * d), 0.7, 0.7)
            elif key == "line_width":
                p.drawRect(QRectF(r.left() + 6, c.y() - val / 2, r.width() - 12, val))
            elif key == "fill_style":
                box = QRectF(r.left() + 8, r.top() + 4, r.width() - 16, r.height() - 8)
                p.setPen(QPen(ink, 1))
                p.setBrush(Qt.NoBrush if val == "outline" else QColor("#808080") if val == "both" else ink)
                if val == "fill":
                    p.setPen(Qt.NoPen)
                p.drawRect(box)
            else:
                f = QFont(self.font())
                f.setPixelSize(10)
                p.setFont(f)
                p.setPen(ink)
                label = {"zoom": f"{val}x", "text_size": f"{val}px",
                         "transparent": "Transparent" if val else "Opaque"}.get(key, str(val))
                p.drawText(r, Qt.AlignCenter, label)

    def mousePressEvent(self, e):
        for item, r in zip(self.items, self._rects()):
            if r.contains(e.position()):
                key, val, extra = item
                if key == "zoom":
                    self.win.canvas.set_zoom(val)
                else:
                    self.win.set_opt(key, val)
                    if key == "brush_size":
                        self.win.set_opt("brush_shape", extra)
                self.update()


# --------------------------------------------------------------- colour box ---
class ColorBox(QWidget):
    """Primary/secondary indicator and the 28 colours."""
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.colors = [QColor(c) for c in PALETTE]
        self.setFixedHeight(40)
        self.setMinimumWidth(330)

    def _cells(self):
        return [QRect(36 + (i % 14) * 17, 3 + (i // 14) * 17, 16, 16) for i in range(28)]

    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(QColor("#5d6c80"))
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 2, 30, 33)
        p.setBrush(self.win.secondary)
        p.drawRect(12, 15, 14, 14)
        p.setBrush(self.win.primary)
        p.drawRect(5, 7, 14, 14)
        for c, r in zip(self.colors, self._cells()):
            p.setPen(QColor("#5d6c80"))
            p.setBrush(c)
            p.drawRect(r.adjusted(0, 0, -1, -1))

    def _at(self, pos):
        for i, r in enumerate(self._cells()):
            if r.contains(pos):
                return i
        return -1

    def mousePressEvent(self, e):
        i = self._at(e.position().toPoint())
        if i >= 0:
            if e.button() == Qt.RightButton:
                self.win.set_secondary(self.colors[i])
            else:
                self.win.set_primary(self.colors[i])

    def mouseDoubleClickEvent(self, e):
        i = self._at(e.position().toPoint())
        if i >= 0:
            self.edit(i)

    def edit(self, i=None):
        start = self.colors[i] if i is not None else self.win.primary
        c = QColorDialog.getColor(start, self, "Edit Colors")
        if c.isValid():
            if i is not None:
                self.colors[i] = c
            self.win.set_primary(c)
            self.update()


# -------------------------------------------------------------- dialogs ---
def ask(parent, title, rows, extra=None):
    """A small form dialog; rows are (label, widget)."""
    d = QDialog(parent)
    d.setWindowTitle(title)
    lay = QVBoxLayout(d)
    grid = QGridLayout()
    for i, (label, w) in enumerate(rows):
        grid.addWidget(QLabel(label), i, 0)
        grid.addWidget(w, i, 1)
    lay.addLayout(grid)
    if extra:
        lay.addWidget(extra)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    lay.addWidget(bb)
    return d.exec() == QDialog.Accepted


def spin(lo, hi, val, suffix=""):
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setValue(val)
    s.setSuffix(suffix)
    return s


# ---------------------------------------------------------------- window ---
class Paint(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        self.setWindowIcon(QIcon.fromTheme("kolourpaint", QIcon.fromTheme("applications-graphics")))
        self.primary, self.secondary = QColor("black"), QColor("white")
        self.options = {"brush_size": 4, "brush_shape": "round", "eraser_size": 8, "spray_size": 8,
                        "line_width": 1, "fill_style": "outline", "transparent": False, "text_size": 16}
        self.text_font = QFont(self.font().family())
        self.tool = "pencil"
        self.previous_tool = "pencil"
        self.path = None
        self.modified = False

        self.canvas = Canvas(self)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setStyleSheet("QScrollArea { background: #8a9cb6; border: none; }")
        self.scroll.viewport().setStyleSheet("background: #8a9cb6;")
        self.canvas.move(4, 4)
        self.scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        mid = QHBoxLayout()
        mid.setSpacing(0)
        mid.addWidget(self._toolbox())
        mid.addWidget(self.scroll, 1)
        lay.addLayout(mid, 1)
        self.colorbox = ColorBox(self)
        bottom = QWidget()
        bottom.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eef3f9, stop:1 #dbe5f1);")
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(6, 4, 6, 4)
        bl.addWidget(self.colorbox)
        bl.addStretch(1)
        lay.addWidget(bottom)
        self.setCentralWidget(central)

        self.pos_label, self.size_label = QLabel(), QLabel()
        for l in (self.pos_label, self.size_label):
            l.setMinimumWidth(110)
        self.statusBar().addWidget(QLabel("For Help, click Help Topics on the Help Menu."), 1)
        self.statusBar().addPermanentWidget(self.pos_label)
        self.statusBar().addPermanentWidget(self.size_label)
        self.canvas.moved.connect(lambda a, b: (self.pos_label.setText(a), self.size_label.setText(b)))
        self.canvas.changed.connect(self._changed)
        self._menus()
        self.set_tool("pencil")
        self.resize(900, 680)
        if path:
            self.load(path)
        self._title()

    # -- ui
    def _toolbox(self):
        box = QWidget()
        box.setFixedWidth(64)
        box.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #eef3f9, stop:1 #dbe5f1);")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(5, 6, 5, 6)
        grid = QGridLayout()
        grid.setSpacing(2)
        self.tool_buttons = QButtonGroup(self)
        self.tool_buttons.setExclusive(True)
        for i, (tid, tip) in enumerate(TOOLS):
            b = QToolButton()
            b.setIcon(tool_icon(tid))
            b.setIconSize(QSize(22, 22))
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setFixedSize(26, 26)
            b.setProperty("tool", tid)
            b.setStyleSheet("QToolButton { border: 1px solid transparent; border-radius: 2px; background: transparent; }"
                            "QToolButton:hover { border-color: #8fb8e6; background: #e6f1fc; }"
                            "QToolButton:checked { border-color: #3c7fb1; background: #c9e0f7; }")
            self.tool_buttons.addButton(b)
            grid.addWidget(b, i // 2, i % 2)
        self.tool_buttons.buttonClicked.connect(lambda b: self.set_tool(b.property("tool")))
        lay.addLayout(grid)
        lay.addSpacing(6)
        self.options_box = OptionsBox(self)
        lay.addWidget(self.options_box, 0, Qt.AlignHCenter)
        lay.addStretch(1)
        return box

    def _menus(self):
        m = self.menuBar()
        f = m.addMenu("&File")
        f.addAction("&New", self.new, QKeySequence.New)
        f.addAction("&Open…", self.open, QKeySequence.Open)
        f.addAction("&Save", self.save, QKeySequence.Save)
        f.addAction("Save &As…", self.save_as, QKeySequence("Ctrl+Shift+S"))
        f.addSeparator()
        f.addAction("E&xit", self.close)
        e = m.addMenu("&Edit")
        e.addAction("&Undo", self.canvas.undo, QKeySequence.Undo)
        e.addAction("&Repeat", self.canvas.redo, QKeySequence("Ctrl+Y"))
        e.addSeparator()
        self.cut_a = e.addAction("Cu&t", self.cut, QKeySequence.Cut)
        self.copy_a = e.addAction("&Copy", self.copy, QKeySequence.Copy)
        e.addAction("&Paste", self.paste, QKeySequence.Paste)
        self.clear_a = e.addAction("C&lear Selection", self.canvas.delete_selection, QKeySequence("Del"))
        e.addAction("Select &All", self.canvas.select_all, QKeySequence.SelectAll)
        v = m.addMenu("&View")
        zm = v.addMenu("&Zoom")
        self.zoom_group = QActionGroup(self)
        for z in ZOOMS:
            a = QAction(f"{z * 100}%", self, checkable=True)
            a.setData(z)
            a.triggered.connect(lambda _=False, z=z: self.canvas.set_zoom(z))
            self.zoom_group.addAction(a)
            zm.addAction(a)
        zm.addSeparator()
        zm.addAction("Zoom &In", lambda: self.step_zoom(1), QKeySequence("Ctrl+PgUp"))
        zm.addAction("Zoom &Out", lambda: self.step_zoom(-1), QKeySequence("Ctrl+PgDown"))
        self.grid_a = zm.addAction("Show &Grid", self.toggle_grid, QKeySequence("Ctrl+G"))
        self.grid_a.setCheckable(True)
        i = m.addMenu("&Image")
        i.addAction("&Flip/Rotate…", self.flip_rotate, QKeySequence("Ctrl+R"))
        i.addAction("&Resize/Skew…", self.resize_skew, QKeySequence("Ctrl+W"))
        i.addAction("&Invert Colors", lambda: self.canvas.replace(ops.inverted(self.canvas.image)), QKeySequence("Ctrl+I"))
        i.addAction("&Attributes…", self.attributes, QKeySequence("Ctrl+E"))
        i.addAction("&Clear Image", self.clear_image, QKeySequence("Ctrl+Shift+N"))
        self.crop_a = i.addAction("Cro&p", self.canvas.crop_to_selection, QKeySequence("Ctrl+Shift+X"))
        c = m.addMenu("&Colors")
        c.addAction("&Edit Colors…", lambda: self.colorbox.edit())
        h = m.addMenu("&Help")
        h.addAction("&About Paint", lambda: QMessageBox.about(
            self, "About Paint", "<b>Paint</b><p>Part of Halcyon. Left-click draws with the primary colour, "
            "right-click with the secondary. Shift keeps lines straight and shapes square; double-click finishes "
            "a polygon; a curve is a line plus two clicks to bend it; Esc cancels.</p>"))
        self.selection_changed(False)

    # -- state
    def opt(self, key):
        return self.options[key]

    def set_opt(self, key, val):
        self.options[key] = val
        self.options_box.update()

    def set_tool(self, tool):
        if tool != self.tool:
            self.canvas.finish_pending()
            if tool == "picker":
                self.previous_tool = self.tool          # Pick Color returns to this tool afterwards
            if tool not in ("select", "freesel"):
                self.canvas.drop_selection()
        self.tool = tool
        for b in self.tool_buttons.buttons():
            b.setChecked(b.property("tool") == tool)
        self.options_box.set_tool(tool)
        self.canvas.setCursor(self.tool_cursor())

    def tool_cursor(self):
        return {"text": Qt.IBeamCursor, "zoom": Qt.PointingHandCursor, "picker": Qt.CrossCursor,
                "fill": Qt.CrossCursor}.get(self.tool, Qt.CrossCursor)

    def set_primary(self, c):
        self.primary = QColor(c)
        self.colorbox.update()

    def set_secondary(self, c):
        self.secondary = QColor(c)
        self.colorbox.update()

    def selection_changed(self, on):
        for a in (getattr(self, "cut_a", None), getattr(self, "copy_a", None), getattr(self, "clear_a", None),
                  getattr(self, "crop_a", None)):
            if a:
                a.setEnabled(on)

    def zoom_changed(self, z):
        for a in self.zoom_group.actions():
            a.setChecked(a.data() == z)
        self.options_box.update()

    def step_zoom(self, d):
        i = ZOOMS.index(self.canvas.zoom) if self.canvas.zoom in ZOOMS else 0
        self.canvas.set_zoom(ZOOMS[max(0, min(len(ZOOMS) - 1, i + d))])

    def toggle_grid(self):
        self.canvas.grid = self.grid_a.isChecked()
        self.canvas.update()

    def _changed(self):
        self.modified = True
        self._title()

    def _title(self):
        name = Path(self.path).name if self.path else "Untitled"
        self.setWindowTitle(f"{'*' if self.modified else ''}{name} - Paint")

    # -- clipboard
    def copy(self):
        img = self.canvas.selection_image()
        if img is not None:
            QApplication.clipboard().setImage(img)

    def cut(self):
        self.copy()
        self.canvas.delete_selection()

    def paste(self):
        img = QApplication.clipboard().image()
        if not img.isNull():
            self.canvas.paste_image(img)

    # -- image menu
    def flip_rotate(self):
        d = QDialog(self)
        d.setWindowTitle("Flip and Rotate")
        lay = QVBoxLayout(d)
        choices = [("Flip horizontal", "h"), ("Flip vertical", "v"), ("Rotate by 90°", 90),
                   ("Rotate by 180°", 180), ("Rotate by 270°", 270)]
        grp = QButtonGroup(d)
        for i, (t, v) in enumerate(choices):
            r = QRadioButton(t)
            r.setProperty("v", v)
            r.setChecked(i == 0)
            grp.addButton(r)
            lay.addWidget(r)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        if d.exec():
            v = grp.checkedButton().property("v")
            img = self.canvas.image
            self.canvas.replace(ops.flipped(img, v == "h") if v in ("h", "v") else ops.rotated(img, v))

    def resize_skew(self):
        h, v = spin(1, 500, 100, " %"), spin(1, 500, 100, " %")
        sh, sv = spin(-89, 89, 0, "°"), spin(-89, 89, 0, "°")
        if ask(self, "Resize and Skew", [("Resize horizontal:", h), ("Resize vertical:", v),
                                         ("Skew horizontal:", sh), ("Skew vertical:", sv)]):
            self.canvas.replace(ops.stretched(self.canvas.image, h.value(), v.value(), sh.value(), sv.value(),
                                              self.secondary))

    def attributes(self):
        img = self.canvas.image
        w, h = spin(1, 10000, img.width(), " px"), spin(1, 10000, img.height(), " px")
        info = QLabel(f"File: {self.path or 'not saved yet'}")
        info.setStyleSheet("color: #5a6a7e;")
        if ask(self, "Attributes", [("Width:", w), ("Height:", h)], info):
            if (w.value(), h.value()) != (img.width(), img.height()):
                self.canvas.replace(ops.resized_canvas(img, w.value(), h.value(), self.secondary))

    def clear_image(self):
        img = self.canvas.image
        self.canvas.replace(ops.blank(img.width(), img.height(), self.secondary))

    # -- files
    def maybe_save(self):
        if not self.modified:
            return True
        r = QMessageBox.question(self, "Paint", f"Save changes to {Path(self.path).name if self.path else 'Untitled'}?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save()
        return r == QMessageBox.Discard

    def new(self):
        if self.maybe_save():
            self.canvas.history.clear()
            self.canvas.replace(ops.blank(640, 480), record=False)
            self.path, self.modified = None, False
            self._title()

    def open(self):
        if not self.maybe_save():
            return
        p, _ = QFileDialog.getOpenFileName(self, "Open", str(Path.home() / "Pictures"),
                                           "Pictures (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp);;All files (*)")
        if p:
            self.load(p)

    def load(self, path):
        img = QImage(str(path))
        if img.isNull():
            QMessageBox.warning(self, "Paint", f"Paint cannot read this file.\n\n{path}")
            return False
        self.canvas.history.clear()
        self.canvas.replace(img, record=False)
        self.path, self.modified = str(path), False
        self._title()
        return True

    def save(self):
        if not self.path:
            return self.save_as()
        return self._write(self.path)

    def save_as(self):
        start = self.path or str(Path.home() / "Pictures" / "Untitled.png")
        p, filt = QFileDialog.getSaveFileName(self, "Save As", start,
                                              "PNG (*.png);;JPEG (*.jpg *.jpeg);;Bitmap (*.bmp);;GIF (*.gif)")
        if not p:
            return False
        if not Path(p).suffix:
            p += {"JPEG": ".jpg", "Bitmap": ".bmp", "GIF": ".gif"}.get(filt.split(" ")[0], ".png")
        return self._write(p)

    def _write(self, path):
        self.canvas.commit_text()
        self.canvas.commit_floating()
        img = self.canvas.image
        if Path(path).suffix.lower() in (".jpg", ".jpeg", ".bmp"):
            img = img.convertToFormat(QImage.Format_RGB32)       # no alpha in these formats
        if not img.save(path, quality=92):
            QMessageBox.warning(self, "Paint", f"The file couldn't be saved.\n\n{path}")
            return False
        self.path, self.modified = path, False
        self._title()
        return True

    def closeEvent(self, e):
        if self.maybe_save():
            e.accept()
        else:
            e.ignore()


def main():
    app = QApplication(sys.argv[:1])
    app.setApplicationName("halcyon-paint")
    app.setApplicationDisplayName("Paint")
    app.setDesktopFileName("halcyon-paint")
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    w = Paint(args[0] if args else None)
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
