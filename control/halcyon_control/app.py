"""Halcyon Control Panel: Vista's Category View over KDE System Settings.

The home page lists categories with a green heading and a few common tasks;
a category page lists all its tasks under green group headings. Classic View
shows every task as an icon. Each task opens the right System Settings page
(kcmshell6) or Halcyon tool, and only tasks available here are shown."""
import os
import subprocess
import sys

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QScrollArea,
                               QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from . import catalog

APP = "Control Panel"
GREEN = "#2a7d12"          # Vista's category headings
LINK = "#0066cc"
TEXT = "#1e1e1e"
MUTED = "#5a6a7e"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def links_html(items, sep=True):
    """Clickable task links, flowing like Vista's (key, text) pairs."""
    joiner = '&nbsp;&nbsp;<span style="color:#a0b0c4">|</span>&nbsp;&nbsp;' if sep else "<br>"
    return joiner.join(f'<a href="{esc(k)}" style="color:{LINK}; text-decoration:none">{esc(t)}</a>'
                       for k, t in items)


def link_label(html, size=None, wrap=True):
    lbl = QLabel(html)
    lbl.setTextFormat(Qt.RichText)
    lbl.setWordWrap(wrap)
    lbl.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
    lbl.setCursor(Qt.PointingHandCursor)
    if size:
        f = lbl.font()
        f.setPointSizeF(size)
        lbl.setFont(f)
    return lbl


def heading_label(text, key, size=12.5):
    return link_label(f'<a href="{esc(key)}" style="color:{GREEN}; text-decoration:none">{esc(text)}</a>', size)


def icon_label(name, size):
    lbl = QLabel()
    lbl.setPixmap(QIcon.fromTheme(name, QIcon.fromTheme("preferences-system")).pixmap(size))
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignTop)
    return lbl


# ------------------------------------------------------------------- chrome ---
class NavButton(QToolButton):
    """Vista's round glass Back / Forward buttons."""
    def __init__(self, forward):
        super().__init__()
        self.forward = forward
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Forward" if forward else "Back")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        on = self.isEnabled()
        hot = on and self.underMouse()
        g = QLinearGradient(0, r.top(), 0, r.bottom())
        if on:
            g.setColorAt(0, QColor("#7fc0f4" if hot else "#5aa6e6"))
            g.setColorAt(0.5, QColor("#1f74c8" if hot else "#1a5fae"))
            g.setColorAt(1, QColor("#4fb0ff" if hot else "#2f88d8"))
        else:
            g.setColorAt(0, QColor("#e2e8ef"))
            g.setColorAt(1, QColor("#b9c4d0"))
        p.setPen(QPen(QColor("#0e3a6a" if on else "#8a97a6"), 1))
        p.setBrush(g)
        p.drawEllipse(r)
        gl = QLinearGradient(0, r.top(), 0, r.center().y())
        gl.setColorAt(0, QColor(255, 255, 255, 190))
        gl.setColorAt(1, QColor(255, 255, 255, 20))
        p.setPen(Qt.NoPen)
        p.setBrush(gl)
        p.drawEllipse(QRectF(r.left() + 3, r.top() + 1.5, r.width() - 6, r.height() * 0.5))
        # arrow
        c = r.center()
        d = 1 if self.forward else -1
        path = QPainterPath()
        path.moveTo(c.x() + 5 * d, c.y())
        path.lineTo(c.x() - 1 * d, c.y() - 6)
        path.lineTo(c.x() - 1 * d, c.y() - 2.5)
        path.lineTo(c.x() - 6 * d, c.y() - 2.5)
        path.lineTo(c.x() - 6 * d, c.y() + 2.5)
        path.lineTo(c.x() - 1 * d, c.y() + 2.5)
        path.lineTo(c.x() - 1 * d, c.y() + 6)
        path.closeSubpath()
        p.setBrush(QColor("#ffffff" if on else "#f4f6f8"))
        p.setPen(QPen(QColor(0, 0, 0, 60), 0.8))
        p.drawPath(path)


class Crumbs(QWidget):
    """The address box: Control Panel ▸ Category, each part clickable."""
    clicked = Signal(int)

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hot = -1
        self.boxes = []
        self.setMouseTracking(True)
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_parts(self, parts):
        self.parts = parts
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QColor("#7f9db9"))
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRect(r)
        p.drawPixmap(6, 4, QIcon.fromTheme("preferences-system").pixmap(16))
        fm = p.fontMetrics()
        x = 28
        self.boxes = []
        for i, part in enumerate(self.parts):
            w = fm.horizontalAdvance(part) + 10
            box = QRectF(x, 2, w, self.height() - 4)
            self.boxes.append(box)
            if i == self.hot and i < len(self.parts) - 1:
                p.setPen(QColor("#9cc3ea"))
                p.setBrush(QColor("#e5f1fc"))
                p.drawRoundedRect(box, 2, 2)
            p.setPen(QColor(TEXT))
            p.drawText(box, Qt.AlignCenter, part)
            x += w
            if i < len(self.parts) - 1:
                p.setPen(QColor("#4a5a6e"))
                p.drawText(QRectF(x, 0, 14, self.height()), Qt.AlignCenter, "▸")
                x += 14

    def _at(self, pos):
        for i, b in enumerate(self.boxes):
            if b.contains(pos):
                return i
        return -1

    def mouseMoveEvent(self, e):
        h = self._at(e.position())
        if h != self.hot:
            self.hot = h
            self.setCursor(Qt.PointingHandCursor if 0 <= h < len(self.parts) - 1 else Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self.hot = -1
        self.update()

    def mousePressEvent(self, e):
        i = self._at(e.position())
        if 0 <= i < len(self.parts) - 1:
            self.clicked.emit(i)


class NavBar(QWidget):
    """Glass strip across the top: back/forward, the address and search."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 10, 6)
        lay.setSpacing(4)
        self.back, self.fwd = NavButton(False), NavButton(True)
        lay.addWidget(self.back)
        lay.addWidget(self.fwd)
        lay.addSpacing(6)
        self.crumbs = Crumbs()
        lay.addWidget(self.crumbs, 1)
        lay.addSpacing(6)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(200)
        self.search.setFixedHeight(24)
        self.search.setStyleSheet("QLineEdit { border: 1px solid #7f9db9; background: white; padding: 0 4px; }"
                                  "QLineEdit:focus { border-color: #3c7fb1; }")
        lay.addWidget(self.search)

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#c9dcf3"))
        g.setColorAt(0.5, QColor("#b6cdec"))
        g.setColorAt(0.51, QColor("#a8c1e5"))
        g.setColorAt(1, QColor("#bed3ef"))
        p.fillRect(self.rect(), g)
        p.setPen(QColor("#8aa5c9"))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


class TaskPane(QWidget):
    """The pale blue pane down the left side."""
    def __init__(self):
        super().__init__()
        self.setFixedWidth(210)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 16, 12, 16)
        self.lay.setSpacing(6)

    def clear(self):
        while self.lay.count():
            w = self.lay.takeAt(0).widget()
            if w:
                w.hide()               # deleteLater alone would leave it drawn until the next event loop pass
                w.deleteLater()

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#e9f0fa"))
        g.setColorAt(1, QColor("#cddcf0"))
        p.fillRect(self.rect(), g)
        p.setRenderHint(QPainter.Antialiasing)
        # a soft light sweep, like Vista's task panes
        path = QPainterPath()
        w, h = self.width(), self.height()
        path.moveTo(0, h * 0.55)
        path.cubicTo(w * 0.4, h * 0.45, w * 0.7, h * 0.7, w, h * 0.6)
        path.lineTo(w, h)
        path.lineTo(0, h)
        path.closeSubpath()
        p.fillPath(path, QColor(255, 255, 255, 60))
        p.setPen(QColor("#b4c6de"))
        p.drawLine(w - 1, 0, w - 1, h)


class Tile(QWidget):
    """One icon in Classic View, highlighted the Vista way."""
    activated = Signal(object)

    def __init__(self, task, icon):
        super().__init__()
        self.task, self.hover = task, False
        self.setAttribute(Qt.WA_Hover)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(220, 44)
        self.setToolTip(task[0])
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(8)
        lay.addWidget(icon_label(icon, 32))
        lbl = QLabel(task[0], wordWrap=True)
        lbl.setStyleSheet(f"color: {TEXT};")
        lay.addWidget(lbl, 1)

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.activated.emit(self.task)

    def paintEvent(self, e):
        if not self.hover:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#f8fbfe"))
        g.setColorAt(1, QColor("#e8f1fc"))
        p.setPen(QPen(QColor("#b8d6fb"), 1))
        p.setBrush(g)
        p.drawRoundedRect(r, 3, 3)


# ------------------------------------------------------------------ window ---
class ControlPanel(QWidget):
    def __init__(self, start=None):
        super().__init__()
        self.setWindowTitle(APP)
        self.setWindowIcon(QIcon.fromTheme("preferences-system"))
        self.resize(940, 660)
        self.cats = catalog.build()
        self.by_id = {c[0]: c for c in self.cats}
        self.history, self.pos = [], -1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.nav = NavBar()
        outer.addWidget(self.nav)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)
        self.pane = TaskPane()
        body.addWidget(self.pane)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: white; }")
        body.addWidget(self.scroll, 1)

        self.nav.back.clicked.connect(lambda: self.step(-1))
        self.nav.fwd.clicked.connect(lambda: self.step(1))
        self.nav.crumbs.clicked.connect(lambda i: self.go(("home",)) if i == 0 else None)
        self.nav.search.textChanged.connect(self._searched)
        QShortcut(QKeySequence.Back, self, lambda: self.step(-1))
        QShortcut(QKeySequence.Forward, self, lambda: self.step(1))
        QShortcut(QKeySequence("Alt+Left"), self, lambda: self.step(-1))
        QShortcut(QKeySequence("Alt+Right"), self, lambda: self.step(1))
        QShortcut(QKeySequence.Find, self, self.nav.search.setFocus)
        QShortcut(QKeySequence("Ctrl+L"), self, self.nav.search.setFocus)
        self.go(start or ("home",))

    # -- navigation
    def go(self, page):
        if 0 <= self.pos < len(self.history) and self.history[self.pos] == page:
            return self.show_page(page)
        if page[0] == "search" and self.pos >= 0 and self.history[self.pos][0] == "search":
            self.history[self.pos] = page          # typing refines one search, not a trail of them
        else:
            del self.history[self.pos + 1:]
            self.history.append(page)
            self.pos += 1
        self.show_page(page)

    def step(self, d):
        n = self.pos + d
        if 0 <= n < len(self.history):
            self.pos = n
            page = self.history[n]
            if page[0] != "search" and self.nav.search.text():
                self.nav.search.blockSignals(True)
                self.nav.search.clear()
                self.nav.search.blockSignals(False)
            self.show_page(page)

    def _searched(self, text):
        if text.strip():
            self.go(("search", text))
        elif self.pos >= 0 and self.history[self.pos][0] == "search":
            self.step(-1)

    def show_page(self, page):
        self.nav.back.setEnabled(self.pos > 0)
        self.nav.fwd.setEnabled(self.pos < len(self.history) - 1)
        kind = page[0]
        if kind == "cat" and page[1] in self.by_id:
            content, crumbs = self.category_page(self.by_id[page[1]]), ["Control Panel", self.by_id[page[1]][1]]
        elif kind == "classic":
            content, crumbs = self.classic_page(), ["Control Panel", "All Control Panel Items"]
        elif kind == "search":
            content, crumbs = self.search_page(page[1]), ["Control Panel", "Search Results"]
        else:
            content, crumbs = self.home_page(), ["Control Panel"]
        self.fill_pane(page)
        self.nav.crumbs.set_parts(crumbs)
        self.scroll.setWidget(content)
        self.scroll.verticalScrollBar().setValue(0)

    def fill_pane(self, page):
        self.pane.clear()
        lay = self.pane.lay

        def nav_link(text, target, bold=False):
            if bold:
                lbl = QLabel(f"<b>{esc(text)}</b>", wordWrap=True)
                lbl.setStyleSheet(f"color: {TEXT};")
            else:
                lbl = link_label(links_html([("x", text)]))
                lbl.linkActivated.connect(lambda _=None, t=target: self.go(t))
            lay.addWidget(lbl)

        nav_link("Control Panel Home", ("home",), page[0] == "home")
        if page[0] == "cat":
            lay.addSpacing(8)
            for cid, title, *_ in self.cats:
                nav_link(title, ("cat", cid), cid == page[1])
        else:
            nav_link("Classic View", ("classic",), page[0] == "classic")
        lay.addStretch(1)
        see = QLabel("See also")
        see.setStyleSheet(f"color: {MUTED};")
        lay.addWidget(see)
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #b4c6de;")
        lay.addWidget(line)
        for title, cmd in (("Halcyon Update", "halcyon-update"), ("Welcome Center", "halcyon-welcome"),
                           ("All settings", "systemsettings")):
            if catalog.shutil.which(cmd):
                lbl = link_label(links_html([("x", title)]))
                lbl.linkActivated.connect(lambda _=None, c=cmd: self.launch(("", "app:" + c)))
                lay.addWidget(lbl)

    # -- pages
    def _page(self, title=None, intro=None):
        w = QWidget()
        w.setStyleSheet("background: white;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(10)
        if title:
            t = QLabel(title)
            f = t.font()
            f.setPointSizeF(15)
            t.setFont(f)
            t.setStyleSheet("color: #1e3287;")
            lay.addWidget(t)
        if intro:
            i = QLabel(intro, wordWrap=True)
            i.setStyleSheet(f"color: {MUTED};")
            lay.addWidget(i)
            lay.addSpacing(6)
        return w, lay

    def home_page(self):
        w, lay = self._page()
        grid = QGridLayout()
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(22)
        for n, (cid, title, icon, blurbs, groups) in enumerate(self.cats):
            cell = QHBoxLayout()
            cell.setSpacing(12)
            cell.addWidget(icon_label(icon, 48), 0, Qt.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(3)
            h = heading_label(title, cid)
            h.linkActivated.connect(lambda _=None, c=cid: self.go(("cat", c)))
            col.addWidget(h)
            tasks = {t[0]: t for _, ts in groups for t in ts}
            for b in blurbs:
                lbl = link_label(links_html([("x", b)]))
                lbl.linkActivated.connect(lambda _=None, t=tasks[b]: self.launch(t))
                col.addWidget(lbl)
            col.addStretch(1)
            cell.addLayout(col, 1)
            grid.addLayout(cell, n // 2, n % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        lay.addStretch(1)
        return w

    def category_page(self, cat):
        cid, title, icon, _, groups = cat
        w, lay = self._page()
        for heading, tasks in groups:
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(icon_label(icon, 40), 0, Qt.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(3)
            h = heading_label(heading, "first")
            h.linkActivated.connect(lambda _=None, t=tasks[0]: self.launch(t))
            col.addWidget(h)
            lbl = link_label(links_html([(str(i), t[0]) for i, t in enumerate(tasks)]))
            lbl.linkActivated.connect(lambda k, ts=tasks: self.launch(ts[int(k)]))
            col.addWidget(lbl)
            row.addLayout(col, 1)
            lay.addLayout(row)
            sep = QWidget()
            sep.setFixedHeight(1)
            sep.setStyleSheet("background: #e3eaf3;")
            lay.addSpacing(4)
            lay.addWidget(sep)
            lay.addSpacing(4)
        lay.addStretch(1)
        return w

    def classic_page(self):
        w, lay = self._page("All Control Panel Items", "Click an item to open it.")
        lay.addLayout(self._tiles(catalog.all_tasks(self.cats)))
        lay.addStretch(1)
        return w

    def search_page(self, text):
        hits = catalog.search(self.cats, text)
        w, lay = self._page(f"Search results for “{text.strip()}”",
                            None if hits else "No items match your search. Check the spelling or try other words.")
        for task, cid, icon in hits:
            row = QHBoxLayout()
            row.setSpacing(10)
            row.addWidget(icon_label(icon, 32), 0, Qt.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(0)
            lbl = link_label(links_html([("x", task[0])]), 10.5)
            lbl.linkActivated.connect(lambda _=None, t=task: self.launch(t))
            col.addWidget(lbl)
            where = link_label(f'<span style="color:{MUTED}">in </span>'
                               f'<a href="c" style="color:{GREEN}; text-decoration:none">{esc(self.by_id[cid][1])}</a>')
            where.linkActivated.connect(lambda _=None, c=cid: self.go(("cat", c)))
            col.addWidget(where)
            row.addLayout(col, 1)
            lay.addLayout(row)
        lay.addStretch(1)
        return w

    def _tiles(self, items):
        grid = QGridLayout()
        grid.setSpacing(4)
        cols = max(1, (self.scroll.viewport().width() - 56) // 224)
        for n, (task, _, icon) in enumerate(items):
            t = Tile(task, icon)
            t.activated.connect(self.launch)
            grid.addWidget(t, n // cols, n % cols)
        grid.setColumnStretch(cols, 1)
        return grid

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.pos >= 0 and self.history[self.pos][0] == "classic" and e.oldSize().width() != e.size().width():
            self.show_page(self.history[self.pos])

    # -- actions
    def launch(self, task):
        cmd = catalog.command(task[1])
        try:
            subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as err:
            QMessageBox.warning(self, APP, f"Couldn't open “{task[0]}”.\n\n{err}")


def icon_theme_fallback():
    """Outside a Plasma session Qt may not know the icon theme; use the one Plasma is set to."""
    if QIcon.themeName() and QIcon.themeName() != "hicolor":
        return
    try:
        out = subprocess.run(["kreadconfig6", "--group", "Icons", "--key", "Theme"],
                             capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    paths = QIcon.themeSearchPaths()
    for d in (os.path.expanduser("~/.local/share/icons"), "/usr/share/icons"):
        if d not in paths:
            paths.append(d)
    QIcon.setThemeSearchPaths(paths)
    QIcon.setThemeName(out or "oxygen")


def main():
    app = QApplication(sys.argv[:1])
    icon_theme_fallback()
    app.setApplicationName("halcyon-control")
    app.setApplicationDisplayName(APP)
    app.setDesktopFileName("halcyon-control")
    args = sys.argv[1:]
    start = None
    if args and args[0] == "--classic":
        start = ("classic",)
    elif args and args[0] in {c[0] for c in catalog.CATEGORIES}:
        start = ("cat", args[0])          # e.g. halcyon-control hardware
    w = ControlPanel(start)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
