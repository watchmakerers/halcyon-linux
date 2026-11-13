"""Halcyon Network and Sharing Center, after Windows Vista's.

Top: the network map (this computer -> network -> Internet, with a red X where
the chain breaks). Below: the current connection (access, signal, status),
Sharing and Discovery switches, and a left task pane. "Diagnose and repair"
walks through the usual checks in plain language. State comes from nmcli
(netinfo.py) and refreshes every few seconds."""
import os
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import netinfo

APP = "Network and Sharing Center"
TITLE = "#1e3287"
GREEN = "#2a7d12"
LINK = "#0066cc"
TEXT = "#1e1e1e"
MUTED = "#5a6a7e"
REFRESH_MS = 3000


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def link(text, on_click, size=None):
    lbl = QLabel(f'<a href="x" style="color:{LINK}; text-decoration:none">{esc(text)}</a>')
    lbl.setTextFormat(Qt.RichText)
    lbl.setCursor(Qt.PointingHandCursor)
    lbl.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
    lbl.linkActivated.connect(lambda _=None: on_click())
    if size:
        f = lbl.font()
        f.setPointSizeF(size)
        lbl.setFont(f)
    return lbl


def spawn(cmd):
    try:
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def kcm(name):
    return ["kcmshell6", name] if netinfo.shutil.which("kcmshell6") else ["systemsettings", name]


def icon(name, size, fallback="network-workgroup"):
    return QIcon.fromTheme(name, QIcon.fromTheme(fallback)).pixmap(size)


class Bus(QObject):
    snapshot = Signal(object)        # object, not dict: a QVariantMap would sort the keys
    step = Signal(int, bool, str, str)
    finished = Signal()


# ------------------------------------------------------------------ chrome ---
class Header(QWidget):
    """The glass address bar: Control Panel ▸ Network and Internet ▸ Network and Sharing Center."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(40)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
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
        p.drawPixmap(int(box.x()) + 5, int(box.y()) + 4, icon("network-workgroup", 16))
        p.setPen(QColor(TEXT))
        p.drawText(box.adjusted(28, 0, 0, 0), Qt.AlignVCenter,
                   "Control Panel  ▸  Network and Internet  ▸  Network and Sharing Center")


class TaskPane(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(210)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 16, 12, 16)
        self.lay.setSpacing(7)

    def heading(self, text):
        lbl = QLabel(f"<b>{esc(text)}</b>")
        lbl.setStyleSheet(f"color: {TEXT};")
        self.lay.addWidget(lbl)

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


class Bars(QWidget):
    """Wi-Fi signal strength as five rising bars."""
    def __init__(self, bars=0):
        super().__init__()
        self.bars = bars
        self.setFixedSize(26, 16)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for i in range(5):
            h = 3 + i * 3
            r = QRectF(1 + i * 5, self.height() - h, 4, h)
            if i < self.bars:
                g = QLinearGradient(0, r.top(), 0, r.bottom())
                g.setColorAt(0, QColor("#7fe07a"))
                g.setColorAt(1, QColor("#1f8f1a"))
                p.setBrush(g)
                p.setPen(QColor("#176e14"))
            else:
                p.setBrush(QColor("#e4e8ee"))
                p.setPen(QColor("#a6b0bc"))
            p.drawRect(r)


# ---------------------------------------------------------------- the map ---
class NetworkMap(QWidget):
    """Computer — network — Internet, joined by lines; a red X where it breaks."""
    clicked = Signal(int)            # node index: 0 computer, 1 network, 2 internet

    def __init__(self):
        super().__init__()
        self.setFixedHeight(130)
        self.setMouseTracking(True)
        self.names = ["This computer", "Network", "Internet"]
        self.state = "unknown"
        self.kind = "ethernet"
        self.hot = -1

    def set_state(self, host, network, state, kind):
        self.names = [host, network or "Not connected", "Internet"]
        self.state, self.kind = state, kind
        self.update()

    def _centres(self):
        w = self.width()
        return [QPointF(w * f, 48) for f in (0.17, 0.5, 0.83)]

    def _broken(self):
        """Index of the broken link (0: computer-network, 1: network-Internet) or None."""
        if self.state == "none":
            return 0
        if self.state in ("local", "portal", "unknown"):
            return 1
        return None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = self._centres()
        broken = self._broken()
        for i in range(2):
            a, b = QPointF(c[i].x() + 40, c[i].y()), QPointF(c[i + 1].x() - 40, c[i + 1].y())
            ok = broken is None or i < broken
            pen = QPen(QColor("#3f8f2a" if ok else "#9aa6b4"), 2.2)
            if not ok:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawLine(a, b)
            if broken == i:
                m = (a + b) / 2
                g = QLinearGradient(0, m.y() - 10, 0, m.y() + 10)
                g.setColorAt(0, QColor("#ff6a5a"))
                g.setColorAt(1, QColor("#c4120a"))
                p.setPen(QPen(QColor("#7a0a04"), 1))
                p.setBrush(g)
                p.drawEllipse(m, 10, 10)
                p.setPen(QPen(QColor("white"), 2.4, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(m + QPointF(-4, -4), m + QPointF(4, 4))
                p.drawLine(m + QPointF(4, -4), m + QPointF(-4, 4))
        icons = ["computer", "network-wireless" if self.kind == "wifi" else "network-wired", "applications-internet"]
        for i, (pt, name) in enumerate(zip(c, self.names)):
            if i == self.hot:
                p.setPen(QColor("#b8d6fb"))
                p.setBrush(QColor("#eef5fd"))
                p.drawRoundedRect(QRectF(pt.x() - 70, 6, 140, 118), 4, 4)
            dim = (broken is not None and i > broken)
            px = icon(icons[i], 48, "network-workgroup")
            p.setOpacity(0.45 if dim else 1)
            p.drawPixmap(int(pt.x() - 24), int(pt.y() - 30), px)
            p.setOpacity(1)
            p.setPen(QColor(TEXT if not dim else MUTED))
            r = QRectF(pt.x() - 80, pt.y() + 22, 160, 20)
            p.drawText(r, Qt.AlignHCenter | Qt.AlignTop, p.fontMetrics().elidedText(name, Qt.ElideMiddle, 156))
            sub = ["(this computer)", "", ""][i]
            if sub:
                p.setPen(QColor(MUTED))
                p.drawText(r.translated(0, 18), Qt.AlignHCenter | Qt.AlignTop, sub)

    def _at(self, pos):
        for i, pt in enumerate(self._centres()):
            if abs(pos.x() - pt.x()) < 70 and 6 < pos.y() < 124:
                return i
        return -1

    def mouseMoveEvent(self, e):
        h = self._at(e.position())
        if h != self.hot:
            self.hot = h
            self.setCursor(Qt.PointingHandCursor if h >= 0 else Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self.hot = -1
        self.update()

    def mouseReleaseEvent(self, e):
        i = self._at(e.position())
        if i >= 0:
            self.clicked.emit(i)


class Panel(QFrame):
    """A rounded box with a light gradient, like Vista's grouped sections."""
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#fbfdff"))
        g.setColorAt(1, QColor("#eef4fb"))
        p.setPen(QColor("#c5d5e8"))
        p.setBrush(g)
        p.drawRoundedRect(r, 5, 5)


# ---------------------------------------------------------------- dialogs ---
class StatusDialog(QDialog):
    """Connection status: details on top, live activity below, like Vista's."""
    def __init__(self, parent, snap):
        super().__init__(parent)
        prim = snap["primary"]
        self.dev = prim["device"]
        self.setWindowTitle(f"{prim['connection']} Status")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        d = snap["details"]
        rows = [("Connection", netinfo.TYPE_NAMES.get(prim["type"], prim["type"].title()) + " network"),
                ("Network", prim["connection"]), ("Access", snap["access"])]
        if snap.get("wifi"):
            ssid, sig, rate, sec = snap["wifi"]
            rows += [("Signal quality", f"{sig}%" if sig is not None else "Unknown"),
                     ("Speed", rate.replace("Mbit/s", "Mbps") or "Unknown"), ("Security", sec or "None")]
        else:
            speed = netinfo.link_speed(self.dev)
            if speed:
                rows.append(("Speed", speed))
        v4 = d.get("IP4.ADDRESS", [])
        v6 = [a for a in d.get("IP6.ADDRESS", []) if not a.startswith("fe80")]
        rows += [("IPv4 address", v4[0].split("/")[0] if v4 else "None"),
                 ("Default gateway", d.get("IP4.GATEWAY") or "None"),
                 ("DNS servers", ", ".join(d.get("IP4.DNS", []) + d.get("IP6.DNS", [])) or "None"),
                 ("IPv6 address", v6[0].split("/")[0] if v6 else "None"),
                 ("Physical address", d.get("GENERAL.HWADDR", "") or "Unknown"),
                 ("Adapter", self.dev)]
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        for i, (k, v) in enumerate(rows):
            a, b = QLabel(k + ":"), QLabel(v)
            a.setStyleSheet(f"color: {MUTED};")
            b.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(a, i, 0)
            grid.addWidget(b, i, 1)
        lay.addLayout(self._group("Details", grid))

        act = QGridLayout()
        act.setHorizontalSpacing(12)
        sent, recv = QLabel("Sent"), QLabel("Received")
        for w in (sent, recv):
            w.setAlignment(Qt.AlignCenter)
            w.setStyleSheet(f"color: {MUTED};")
        pc = QLabel()
        pc.setPixmap(icon("network-transmit-receive", 40, "network-workgroup"))
        pc.setAlignment(Qt.AlignCenter)
        self.sent, self.recv = QLabel("—"), QLabel("—")
        for w in (self.sent, self.recv):
            w.setAlignment(Qt.AlignCenter)
        act.addWidget(sent, 0, 0)
        act.addWidget(pc, 0, 1, 2, 1)
        act.addWidget(recv, 0, 2)
        act.addWidget(self.sent, 1, 0)
        act.addWidget(self.recv, 1, 2)
        lay.addLayout(self._group("Activity", act))

        btns = QHBoxLayout()
        dis = QPushButton(QIcon.fromTheme("network-disconnect"), "Disable")
        dis.clicked.connect(self._disable)
        diag = QPushButton("Diagnose")
        diag.clicked.connect(lambda: (self.accept(), parent.diagnose()))
        close = QPushButton("Close")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        btns.addWidget(dis)
        btns.addWidget(diag)
        btns.addStretch(1)
        btns.addWidget(close)
        lay.addLayout(btns)
        self.timer = QTimer(self, interval=1000, timeout=self._tick)
        self.timer.start()
        self._tick()

    def _group(self, title, inner):
        box = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color: {TITLE}; font-weight: bold;")
        box.addWidget(t)
        frame = Panel()
        frame.setLayout(inner)
        inner.setContentsMargins(14, 10, 14, 10)
        box.addWidget(frame)
        return box

    def _tick(self):
        c = netinfo.counters(self.dev)
        if c:
            self.recv.setText(netinfo.human_bytes(c[0]))
            self.sent.setText(netinfo.human_bytes(c[1]))

    def _disable(self):
        if QMessageBox.question(self, "Disable connection",
                                f"Disconnect {self.dev}? You'll lose this network connection until you reconnect.") \
                == QMessageBox.Yes:
            subprocess.run(["nmcli", "device", "disconnect", self.dev], capture_output=True)
            self.accept()


class DiagnoseDialog(QDialog):
    """Runs the checks one by one and explains what's wrong, Vista-style."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Network Diagnostics")
        self.setMinimumSize(520, 380)
        self.bus = Bus()
        self.bus.step.connect(self._step)
        self.bus.finished.connect(self._done)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        self.title = QLabel("Identifying the problem…")
        f = self.title.font()
        f.setPointSizeF(13)
        self.title.setFont(f)
        self.title.setStyleSheet(f"color: {TITLE};")
        lay.addWidget(self.title)
        self.steps = netinfo.diagnose_steps()
        self.rows = []
        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        for i, (title, _) in enumerate(self.steps):
            ic, lbl, res = QLabel(), QLabel(title), QLabel("")
            ic.setFixedSize(20, 20)
            res.setWordWrap(True)
            res.setStyleSheet(f"color: {MUTED};")
            grid.addWidget(ic, i * 2, 0)
            grid.addWidget(lbl, i * 2, 1)
            grid.addWidget(res, i * 2 + 1, 1)
            self.rows.append((ic, lbl, res))
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        self.fix = QLabel("")
        self.fix.setWordWrap(True)
        lay.addWidget(self.fix)
        lay.addStretch(1)
        btns = QHBoxLayout()
        self.reset = QPushButton(QIcon.fromTheme("view-refresh"), "Reset the network adapter")
        self.reset.hide()
        self.reset.clicked.connect(self._reset)
        self.again = QPushButton("Check again")
        self.again.clicked.connect(self.start)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        btns.addWidget(self.reset)
        btns.addStretch(1)
        btns.addWidget(self.again)
        btns.addWidget(close)
        lay.addLayout(btns)
        self.problem = None
        self.start()

    def start(self):
        self.again.setEnabled(False)
        self.reset.hide()
        self.fix.setText("")
        self.problem = None
        self.title.setText("Identifying the problem…")
        for ic, lbl, res in self.rows:
            ic.clear()
            res.setText("")
            lbl.setStyleSheet(f"color: {MUTED};")
        self.rows[0][0].setPixmap(icon("view-refresh", 16))

        def work():
            stop = False
            for i, (_, check) in enumerate(self.steps):
                if stop:
                    self.bus.step.emit(i, None, "Skipped.", "")
                    continue
                try:
                    ok, msg, fix = check()
                except Exception as err:            # a check must never take the dialog down with it
                    ok, msg, fix = False, f"The check failed: {err}", ""
                self.bus.step.emit(i, ok, msg, fix)
                stop = not ok
            self.bus.finished.emit()
        threading.Thread(target=work, daemon=True).start()

    def _step(self, i, ok, msg, fix):
        ic, lbl, res = self.rows[i]
        lbl.setStyleSheet(f"color: {TEXT};")
        name = {True: "dialog-ok-apply", False: "dialog-error"}.get(ok, "go-next")
        ic.setPixmap(icon(name, 16, "dialog-information"))
        res.setText(msg)
        if ok is False and self.problem is None:
            self.problem = (msg, fix)
        if i + 1 < len(self.rows) and ok:
            self.rows[i + 1][0].setPixmap(icon("view-refresh", 16))

    def _done(self):
        self.again.setEnabled(True)
        if self.problem is None:
            self.title.setText("No problems were found")
            self.fix.setText("Your network connection is working.")
            return
        msg, fix = self.problem
        self.title.setText("A problem was found")
        self.fix.setText(f"<b>{esc(msg)}</b><br>{esc(fix)}" if fix else f"<b>{esc(msg)}</b>")
        self.reset.show()

    def _reset(self):
        if QMessageBox.question(self, "Reset the network adapter",
                                "Turn the network off and back on? You'll be disconnected for a few seconds.") \
                != QMessageBox.Yes:
            return
        self.title.setText("Resetting the network adapter…")
        self.reset.hide()
        self.again.setEnabled(False)

        def work():
            subprocess.run(["nmcli", "networking", "off"], capture_output=True)
            subprocess.run(["nmcli", "networking", "on"], capture_output=True)
            # give NetworkManager a moment to reconnect before checking again
            subprocess.run(["nmcli", "--wait", "15", "device", "wait"], capture_output=True)
        t = threading.Thread(target=work, daemon=True)
        t.start()

        def poll():
            if t.is_alive():
                QTimer.singleShot(300, poll)
            else:
                self.start()
        poll()


# ------------------------------------------------------------------ window ---
class Center(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setWindowIcon(QIcon.fromTheme("network-workgroup"))
        self.resize(900, 640)
        self.snap = None
        self.busy = False
        self.bus = Bus()
        self.bus.snapshot.connect(self._show)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(Header())
        body = QHBoxLayout()
        body.setSpacing(0)
        outer.addLayout(body, 1)

        pane = TaskPane()
        pane.heading("Tasks")
        for text, fn in (("View computers and devices", lambda: spawn(["dolphin", "network:/"])),
                         ("Connect to a network", lambda: spawn(kcm("kcm_networkmanagement"))),
                         ("Manage network connections", lambda: spawn(kcm("kcm_networkmanagement"))),
                         ("Diagnose and repair", self.diagnose)):
            pane.lay.addWidget(link(text, fn))
        pane.lay.addStretch(1)
        see = QLabel("See also")
        see.setStyleSheet(f"color: {MUTED};")
        pane.lay.addWidget(see)
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #b4c6de;")
        pane.lay.addWidget(line)
        pane.lay.addWidget(link("Internet Options", lambda: spawn(kcm("kcm_proxy"))))
        pane.lay.addWidget(link("Bluetooth Devices", lambda: spawn(kcm("kcm_bluetooth"))))
        if netinfo.shutil.which("halcyon-control"):
            pane.lay.addWidget(link("Control Panel", lambda: spawn(["halcyon-control", "network"])))
        body.addWidget(pane)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        page = QWidget()
        page.setObjectName("page")
        page.setStyleSheet("#page { background: white; }")
        scroll.setWidget(page)
        body.addWidget(scroll, 1)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 18, 26, 22)
        lay.setSpacing(10)

        top = QHBoxLayout()
        t = QLabel("Network and Sharing Center")
        f = t.font()
        f.setPointSizeF(15)
        t.setFont(f)
        t.setStyleSheet(f"color: {TITLE};")
        top.addWidget(t)
        top.addStretch(1)
        top.addWidget(link("View full map", lambda: spawn(["dolphin", "network:/"])))
        lay.addLayout(top)

        self.map = NetworkMap()
        self.map.clicked.connect(self._map_clicked)
        lay.addWidget(self.map)

        # the current connection
        self.conn_box = Panel()
        cb = QGridLayout(self.conn_box)
        cb.setContentsMargins(16, 12, 16, 12)
        cb.setHorizontalSpacing(16)
        cb.setVerticalSpacing(8)
        self.conn_icon = QLabel()
        self.conn_title = QLabel()
        self.conn_title.setStyleSheet(f"color: {TEXT}; font-weight: bold;")
        self.conn_kind = QLabel()
        self.conn_kind.setStyleSheet(f"color: {MUTED};")
        self.customize = link("Connect or disconnect", lambda: spawn(kcm("kcm_networkmanagement")))
        head = QHBoxLayout()
        head.addWidget(self.conn_icon)
        head.setSpacing(6)
        head.addWidget(self.conn_title)
        head.addWidget(self.conn_kind)
        head.addStretch(1)
        head.addWidget(self.customize)
        cb.addLayout(head, 0, 0, 1, 3)
        self.access = QLabel()
        self.conn_dev = QLabel()
        self.bars = Bars()
        self.status_link = link("View status", self.view_status)
        for r, (k, w) in enumerate((("Access", self.access), ("Connection", None)), start=1):
            a = QLabel(k)
            a.setStyleSheet(f"color: {MUTED};")
            a.setFixedWidth(110)
            cb.addWidget(a, r, 0)
            if w is not None:
                cb.addWidget(w, r, 1, 1, 2)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.conn_dev)
        row.addWidget(self.bars)
        row.addSpacing(10)
        row.addWidget(self.status_link)
        row.addStretch(1)
        cb.addLayout(row, 2, 1, 1, 2)
        cb.setColumnStretch(2, 1)
        lay.addWidget(self.conn_box)

        # Sharing and Discovery
        sd = QLabel("Sharing and Discovery")
        sd.setStyleSheet(f"color: {TITLE}; font-weight: bold;")
        lay.addSpacing(6)
        lay.addWidget(sd)
        self.share_box = Panel()
        self.share_grid = QGridLayout(self.share_box)
        self.share_grid.setContentsMargins(16, 10, 16, 10)
        self.share_grid.setHorizontalSpacing(16)
        self.share_grid.setVerticalSpacing(8)
        self.share_rows = {}
        lay.addWidget(self.share_box)
        hint = QLabel("Changing these asks for your password.")
        hint.setStyleSheet(f"color: {MUTED};")
        lay.addWidget(hint)
        lay.addStretch(1)

        self.timer = QTimer(self, interval=REFRESH_MS, timeout=self.refresh)
        self.timer.start()
        self.refresh()

    # -- data
    def refresh(self):
        if self.busy:
            return
        self.busy = True

        def work():
            try:
                snap = netinfo.snapshot()
            except Exception:                       # keep the last view rather than crash the timer
                snap = None
            self.busy = False
            if snap:
                self.bus.snapshot.emit(snap)
        threading.Thread(target=work, daemon=True).start()

    def _show(self, snap):
        self.snap = snap
        prim = snap["primary"]
        kind = prim["type"] if prim else ""
        name = prim["connection"] if prim else ""
        self.map.set_state(snap["host"], name, snap["map"], kind)
        if prim:
            what = netinfo.TYPE_NAMES.get(kind, kind.title())
            self.conn_icon.setPixmap(icon("network-wireless" if kind == "wifi" else "network-wired", 32))
            self.conn_title.setText(esc(name))
            self.conn_kind.setText(f"({what} network)")
            self.access.setText(snap["access"])
            self.conn_dev.setText(f"{what} connection ({prim['device']})")
            wifi = snap.get("wifi")
            self.bars.bars = netinfo.signal_bars(wifi[1]) if wifi else 0
            self.bars.setVisible(bool(wifi))
            self.bars.update()
            self.status_link.show()
        else:
            self.conn_icon.setPixmap(icon("network-disconnect", 32))
            self.conn_title.setText("You are currently not connected to any networks.")
            self.conn_kind.setText("")
            self.access.setText("No network access" if snap["networking"] else "Networking is turned off")
            self.conn_dev.setText("Not connected")
            self.bars.hide()
            self.status_link.hide()
        self._sharing(snap["sharing"])

    def _sharing(self, rows):
        for r, (name, (state, on, cmd)) in enumerate(rows.items()):
            if name not in self.share_rows:
                a = QLabel(name)
                a.setFixedWidth(150)
                dot, val = QLabel(), QLabel()
                btn = QPushButton()
                btn.setFixedWidth(90)
                btn.clicked.connect(lambda _=False, n=name: self._toggle(n))
                self.share_grid.addWidget(a, r, 0)
                self.share_grid.addWidget(dot, r, 1)
                self.share_grid.addWidget(val, r, 2)
                self.share_grid.addWidget(btn, r, 3)
                self.share_grid.setColumnStretch(2, 1)
                self.share_rows[name] = (dot, val, btn)
            dot, val, btn = self.share_rows[name]
            dot.setText(f'<span style="color:{"#2fa024" if on else "#9aa6b4"}; font-size:14pt">●</span>')
            val.setText(state)
            btn.setText("Turn off" if on else "Turn on")
            btn.setVisible(cmd is not None)

    def _toggle(self, name):
        state, on, cmd = self.snap["sharing"][name]
        if not cmd:
            return

        def work():
            subprocess.run(cmd, capture_output=True)
            self.refresh()
        threading.Thread(target=work, daemon=True).start()

    # -- actions
    def _map_clicked(self, i):
        if i == 0:
            spawn(["halcyon-control", "system"] if netinfo.shutil.which("halcyon-control") else kcm("kcm_about-distro"))
        elif i == 1:
            if self.snap and self.snap["primary"]:
                self.view_status()
            else:
                spawn(kcm("kcm_networkmanagement"))
        elif self.snap and self.snap["map"] == "internet":
            spawn(["xdg-open", "https://kde.org/"])
        else:
            self.diagnose()

    def view_status(self):
        if self.snap and self.snap["primary"]:
            StatusDialog(self, self.snap).exec()
            self.refresh()

    def diagnose(self):
        DiagnoseDialog(self).exec()
        self.refresh()


def icon_theme_fallback():
    """Outside a Plasma session Qt may not know the icon theme; use the one Plasma is set to."""
    if QIcon.themeName() and QIcon.themeName() != "hicolor":
        return
    out = netinfo.run("kreadconfig6", "--group", "Icons", "--key", "Theme").strip()
    paths = QIcon.themeSearchPaths()
    for d in (os.path.expanduser("~/.local/share/icons"), "/usr/share/icons"):
        if d not in paths:
            paths.append(d)
    QIcon.setThemeSearchPaths(paths)
    QIcon.setThemeName(out or "oxygen")


def main():
    app = QApplication(sys.argv[:1])
    icon_theme_fallback()
    app.setApplicationName("halcyon-network")
    app.setApplicationDisplayName(APP)
    app.setDesktopFileName("halcyon-network")
    w = Center()
    w.show()
    if "--diagnose" in sys.argv:
        QTimer.singleShot(0, w.diagnose)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
