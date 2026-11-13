"""Halcyon Performance Rating: Vista's "Rate and improve your computer's
performance" page. Five components get a 1.0-5.9 subscore and the lowest is
the base score. The assessment runs in a separate process (bench.py --run),
so the window stays responsive and OpenGL gets its own main thread.

    halcyon-experience            the window
    halcyon-experience --score    print the saved base score (for other apps)
"""
import datetime
import os
import subprocess
import sys

from PySide6.QtCore import QProcess, QProcessEnvironment, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel,
                               QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget)

from . import bench

APP = "Performance Information and Tools"
TITLE = "#1e3287"
LINK = "#0066cc"
TEXT = "#1e1e1e"
MUTED = "#5a6a7e"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def link(text, on_click):
    lbl = QLabel(f'<a href="x" style="color:{LINK}; text-decoration:none">{esc(text)}</a>')
    lbl.setTextFormat(Qt.RichText)
    lbl.setCursor(Qt.PointingHandCursor)
    lbl.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
    lbl.linkActivated.connect(lambda _=None: on_click())
    return lbl


def spawn(cmd):
    try:
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def kcm(name):
    import shutil
    return ["kcmshell6", name] if shutil.which("kcmshell6") else ["systemsettings", name]


def nice_date(iso):
    try:
        d = datetime.datetime.fromisoformat(iso)
        return d.strftime("%-m/%-d/%Y %-I:%M %p")
    except (TypeError, ValueError):
        return ""


# ------------------------------------------------------------------ chrome ---
class Header(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(40)

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
        box = QRectF(10, 8, self.width() - 20, self.height() - 16)
        p.setPen(QColor("#7f9db9"))
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRect(box)
        p.drawPixmap(int(box.x()) + 5, int(box.y()) + 4, QIcon.fromTheme("computer").pixmap(16))
        p.setPen(QColor(TEXT))
        p.drawText(box.adjusted(28, 0, 0, 0), Qt.AlignVCenter,
                   "Control Panel  ▸  System and Maintenance  ▸  Performance Information and Tools")


class TaskPane(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(210)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 16, 12, 16)
        self.lay.setSpacing(7)

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#e9f0fa"))
        g.setColorAt(1, QColor("#cddcf0"))
        p.fillRect(self.rect(), g)
        p.setRenderHint(QPainter.Antialiasing)
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


# -------------------------------------------------------------- the table ---
class ScoreTable(QWidget):
    """Component | What is rated | Subscore, and the base score box on the right."""
    ROW = 34
    HEAD = 28

    def __init__(self):
        super().__init__()
        self.result = None
        self.running = -1            # index of the component being rated, or -1
        self.setMinimumHeight(self.HEAD + self.ROW * len(bench.COMPONENTS) + 2)
        self.setMinimumWidth(560)

    def set_result(self, r):
        self.result = r
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        base_w = 150
        table = QRectF(0.5, 0.5, w - 1, self.HEAD + self.ROW * len(bench.COMPONENTS))
        p.setPen(QColor("#a9bfd6"))
        p.setBrush(QColor("white"))
        p.drawRect(table)
        # header
        hg = QLinearGradient(0, 0, 0, self.HEAD)
        hg.setColorAt(0, QColor("#ffffff"))
        hg.setColorAt(1, QColor("#e3ecf6"))
        p.fillRect(QRectF(1, 1, w - 2, self.HEAD - 1), hg)
        p.setPen(QColor("#c5d5e8"))
        p.drawLine(1, self.HEAD, w - 1, self.HEAD)
        cols = [(12, "Component"), (170, "What is rated"), (w - base_w - 86, "Subscore"), (w - base_w + 12, "Base score")]
        f = QFont(self.font())
        p.setFont(f)
        p.setPen(QColor("#4c607a"))
        for x, t in cols:
            p.drawText(QRectF(x, 0, 200, self.HEAD), Qt.AlignVCenter, t)
        p.setPen(QColor("#dfe7f0"))
        p.drawLine(w - base_w, 1, w - base_w, table.bottom())

        scores = (self.result or {}).get("scores", {})
        low = bench.base_score(scores) if scores else None
        for i, (key, name, what) in enumerate(bench.COMPONENTS):
            y = self.HEAD + i * self.ROW
            if i:
                p.setPen(QColor("#edf1f6"))
                p.drawLine(1, y, w - base_w, y)
            r = QRectF(12, y, 150, self.ROW)
            p.setPen(QColor(TEXT))
            p.drawText(r, Qt.AlignVCenter, name)
            p.setPen(QColor(MUTED))
            wr = QRectF(170, y, w - base_w - 270, self.ROW)
            p.drawText(wr, Qt.AlignVCenter, p.fontMetrics().elidedText(what, Qt.ElideRight, int(wr.width())))
            sr = QRectF(w - base_w - 86, y, 70, self.ROW)
            if i == self.running:
                p.setPen(QColor(LINK))
                p.drawText(sr, Qt.AlignVCenter, "Rating…")
            elif key in scores:
                bf = QFont(f)
                bf.setBold(scores[key] == low)
                p.setFont(bf)
                p.setPen(QColor(TEXT))
                p.drawText(sr, Qt.AlignVCenter, f"{scores[key]:.1f}")
                p.setFont(f)
            else:
                p.setPen(QColor(MUTED))
                p.drawText(sr, Qt.AlignVCenter, "—")
        self._base_box(p, QRectF(w - base_w + 14, self.HEAD + 14, base_w - 28,
                                 self.ROW * len(bench.COMPONENTS) - 28), low)

    def _base_box(self, p, r, base):
        """The big glossy number, Vista's Experience Index badge."""
        size = min(r.width(), r.height() - 34)
        box = QRectF(r.center().x() - size / 2, r.top(), size, size)
        g = QLinearGradient(0, box.top(), 0, box.bottom())
        rated = base is not None
        g.setColorAt(0, QColor("#6fc2f4" if rated else "#c9d3de"))
        g.setColorAt(0.48, QColor("#1f7cc8" if rated else "#9aa8b8"))
        g.setColorAt(0.52, QColor("#145fa8" if rated else "#8796a8"))
        g.setColorAt(1, QColor("#3aa0e8" if rated else "#b2bfcd"))
        p.setPen(QPen(QColor("#0c3e72" if rated else "#6f7e90"), 1.2))
        p.setBrush(g)
        p.drawRoundedRect(box, 10, 10)
        gl = QLinearGradient(0, box.top(), 0, box.center().y())
        gl.setColorAt(0, QColor(255, 255, 255, 170))
        gl.setColorAt(1, QColor(255, 255, 255, 25))
        p.setPen(Qt.NoPen)
        p.setBrush(gl)
        p.drawRoundedRect(QRectF(box.left() + 3, box.top() + 3, box.width() - 6, box.height() / 2 - 3), 8, 8)
        f = QFont(self.font())
        f.setPointSizeF(size * 0.3 if rated else size * 0.13)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(0, 0, 0, 70))
        text = f"{base:.1f}" if rated else "Unrated"
        p.drawText(box.translated(0, 2), Qt.AlignCenter, text)
        p.setPen(QColor("white"))
        p.drawText(box, Qt.AlignCenter, text)
        f2 = QFont(self.font())
        f2.setPointSizeF(max(7.5, f2.pointSizeF() - 1))
        p.setFont(f2)
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(r.left() - 10, box.bottom() + 6, r.width() + 20, 30), Qt.AlignHCenter | Qt.AlignTop,
                   "Determined by\nlowest subscore" if rated else "Rate this computer\nto get a score")


# ---------------------------------------------------------------- dialogs ---
def explain(parent):
    QMessageBox.information(parent, "What do these numbers mean?",
        "<p>The performance rating measures how well this computer's hardware and software "
        "work together. Each part gets a <b>subscore from 1.0 to 5.9</b>; higher is faster.</p>"
        "<p>The <b>base score</b> is the lowest subscore, because a computer is only as quick as its "
        "slowest part.</p>"
        "<ul><li><b>1.0–2.9</b>: everyday tasks like writing documents and browsing.</li>"
        "<li><b>3.0–3.9</b>: the glass desktop and its effects, and playing HD video.</li>"
        "<li><b>4.0–4.9</b>: demanding work: photo editing, many programs at once, most games.</li>"
        "<li><b>5.0–5.9</b>: high-end gaming, video editing and other heavy work.</li></ul>"
        "<p>The tests take about 20 seconds. Results can vary a little between runs.</p>")


class Details(QDialog):
    """View details: each component's hardware and what it measured."""
    def __init__(self, parent, r):
        super().__init__(parent)
        self.setWindowTitle("Performance details")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        t = QLabel("Performance details for this computer")
        t.setStyleSheet(f"color: {TITLE}; font-size: 13pt;")
        lay.addWidget(t)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        raw, comps, notes = r.get("raw", {}), r.get("components", {}), r.get("notes", {})
        units = {"cpu": "{:,.0f} MB/s hashed and compressed", "memory": "{:.1f} GB/s copied",
                 "graphics": "{:.0f} frames/s", "gaming": "{:.0f} frames/s"}
        for i, (key, name, _) in enumerate(bench.COMPONENTS):
            a = QLabel(f"<b>{esc(name)}</b>")
            v = raw.get(key)
            if key == "disk" and isinstance(v, dict):
                meas = f"{v.get('sequential_mbps', 0):,.0f} MB/s in sequence, {v.get('random_reads', 0):,} random reads/s"
            elif isinstance(v, (int, float)):
                meas = units[key].format(v)
            else:
                meas = ""
            b = QLabel(f"{esc(comps.get(key, ''))}<br><span style='color:{MUTED}'>{esc(meas)}"
                       f"{'<br>' + esc(notes[key]) if key in notes else ''}</span>")
            b.setTextInteractionFlags(Qt.TextSelectableByMouse)
            s = QLabel(f"{r.get('scores', {}).get(key, 0):.1f}")
            grid.addWidget(a, i, 0, Qt.AlignTop)
            grid.addWidget(b, i, 1)
            grid.addWidget(s, i, 2, Qt.AlignTop)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        when = QLabel(f"Rated {nice_date(r.get('date'))}")
        when.setStyleSheet(f"color: {MUTED};")
        lay.addWidget(when)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


# ------------------------------------------------------------------ window ---
class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setWindowIcon(QIcon.fromTheme("utilities-system-monitor", QIcon.fromTheme("computer")))
        self.resize(900, 560)
        self.proc = None
        self.result = bench.load()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(Header())
        body = QHBoxLayout()
        body.setSpacing(0)
        outer.addLayout(body, 1)

        pane = TaskPane()
        head = QLabel("<b>Tasks</b>")
        pane.lay.addWidget(head)
        for text, cmd in (("Manage startup programs", kcm("kcm_autostart")),
                          ("Adjust visual effects", kcm("kcm_kwin_effects")),
                          ("Adjust indexing options", kcm("kcm_baloofile")),
                          ("Adjust power settings", kcm("kcm_powerdevilprofilesconfig")),
                          ("Advanced tools", ["kinfocenter"])):
            pane.lay.addWidget(link(text, lambda c=cmd: spawn(c)))
        pane.lay.addStretch(1)
        body.addWidget(pane)

        page = QWidget()
        page.setObjectName("page")
        page.setStyleSheet("#page { background: white; }")
        body.addWidget(page, 1)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 18, 26, 18)
        lay.setSpacing(10)
        t = QLabel("Rate and improve your computer's performance")
        f = t.font()
        f.setPointSizeF(15)
        t.setFont(f)
        t.setStyleSheet(f"color: {TITLE};")
        lay.addWidget(t)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        lay.addSpacing(4)
        self.table = ScoreTable()
        self.table.set_result(self.result)
        lay.addWidget(self.table)

        row = QHBoxLayout()
        row.addWidget(link("What do these numbers mean?", lambda: explain(self)))
        row.addSpacing(18)
        self.details = link("View details", lambda: Details(self, self.result).exec())
        row.addWidget(self.details)
        row.addStretch(1)
        self.when = QLabel()
        self.when.setStyleSheet(f"color: {MUTED};")
        row.addWidget(self.when)
        lay.addLayout(row)

        act = QHBoxLayout()
        self.status = QLabel()
        self.status.setStyleSheet(f"color: {MUTED};")
        self.bar = QProgressBar()
        self.bar.setRange(0, len(bench.STEPS))
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(14)
        self.bar.hide()
        act.addWidget(self.status)
        act.addWidget(self.bar, 1)
        act.addStretch(0)
        self.go = QPushButton(QIcon.fromTheme("view-refresh"), "")
        self.go.clicked.connect(self.toggle)
        act.addWidget(self.go)
        lay.addLayout(act)
        note = QLabel("Close other programs before rating: they slow the tests down and lower the scores.")
        note.setStyleSheet(f"color: {MUTED};")
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addStretch(1)
        self.refresh()

    def refresh(self):
        r = self.result
        running = self.proc is not None
        if r and r.get("base") is not None:
            self.summary.setText(f"Your computer has a performance rating base score of <b>{r['base']:.1f}</b>.")
            self.when.setText(f"Last update: {nice_date(r.get('date'))}")
        else:
            self.summary.setText("Your computer hasn't been rated yet. Rate it to see how well it runs "
                                 "programs and features.")
            self.when.setText("")
        self.details.setVisible(bool(r))
        self.go.setText("Cancel" if running else ("Re-run the assessment" if r else "Rate this computer"))
        self.bar.setVisible(running)
        if not running:
            self.status.setText("")
            self.table.running = -1
        self.table.set_result(r)

    def toggle(self):
        if self.proc:
            self.proc.kill()
            return
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.SeparateChannels)
        env = QProcessEnvironment.systemEnvironment()     # processEnvironment() starts out empty
        env.insert("PYTHONPATH", os.pathsep.join(p for p in sys.path if p))
        self.proc.setProcessEnvironment(env)
        self.proc.readyReadStandardOutput.connect(self._output)
        self.proc.finished.connect(self._finished)
        self.bar.setValue(0)
        self.proc.start(sys.executable, ["-m", "halcyon_experience.bench", "--run"])
        self.refresh()

    def _output(self):
        while self.proc and self.proc.canReadLine():
            line = bytes(self.proc.readLine()).decode(errors="replace").strip()
            if line.startswith("STEP "):
                _, i, msg = line.split(" ", 2)
                self.table.running = int(i)
                self.bar.setValue(int(i))
                self.status.setText(msg)
                self.table.update()

    def _finished(self, code, status):
        ok = status == QProcess.NormalExit and code == 0
        err = bytes(self.proc.readAllStandardError()).decode(errors="replace").strip()
        self.proc = None
        if ok:
            self.result = bench.load()
        elif err:
            QMessageBox.warning(self, APP, "The assessment couldn't finish.\n\n" + err[-600:])
        self.refresh()

    def closeEvent(self, e):
        if self.proc:
            self.proc.kill()
            self.proc.waitForFinished(2000)
        super().closeEvent(e)


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
    if "--score" in sys.argv:
        r = bench.load()
        print(f"{r['base']:.1f}" if r and r.get("base") is not None else "unrated")
        return 0
    app = QApplication(sys.argv[:1])
    icon_theme_fallback()
    app.setApplicationName("halcyon-experience")
    app.setApplicationDisplayName(APP)
    app.setDesktopFileName("halcyon-experience")
    w = Window()
    w.show()
    if "--rate" in sys.argv:
        w.toggle()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
