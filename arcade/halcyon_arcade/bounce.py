"""Glow Bounce: steer glowing balls into pockets of their colour by drawing
lines of light for them to bounce off. An original Halcyon game.

Rules, physics and levels are in bounce_world.py."""
import math
import random

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QMessageBox, QVBoxLayout, QWidget

from . import bounce_world as BW
from . import common

HELP = """<p><b>Goal:</b> get every glowing ball into a pocket of the same colour.
Grey pockets take any colour (for fewer points).</p>
<p><b>Drawing:</b> drag on the table to draw a line of light. Balls bounce off it; it fades after a few
seconds. You can have three lines at a time.</p>
<p>A ball in the wrong pocket costs a life and starts over. Watch for sliding blocks, one-way gates
(the arrows show the way through) and coloured tiles that repaint balls rolling over them.</p>
<p>Clear all twelve levels to win. Finishing a level quickly earns a bonus.</p>
<p><b>P</b> pauses, <b>R</b> restarts the level.</p>"""


def qc(name, alpha=255):
    r, g, b = BW.COLORS.get(name, (200, 200, 210))
    return QColor(r, g, b, alpha)


class Table(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setMinimumSize(640, 448)
        self.setMouseTracking(True)
        self.drawing = None                  # start point of the line being dragged
        self.cursor_pt = None
        self.sparks = []                     # [x, y, vx, vy, life, colour]

    # -- coordinates: the table keeps its 800 x 560 shape, letterboxed
    def frame(self):
        s = min(self.width() / BW.W, self.height() / BW.H)
        ox, oy = (self.width() - BW.W * s) / 2, (self.height() - BW.H * s) / 2
        return s, ox, oy

    def to_world(self, pos):
        s, ox, oy = self.frame()
        return (pos.x() - ox) / s, (pos.y() - oy) / s

    # -- input
    def mousePressEvent(self, e):
        w = self.win.world
        if e.button() == Qt.LeftButton and w and self.win.playing:
            self.drawing = self.to_world(e.position())
            self.cursor_pt = self.drawing

    def mouseMoveEvent(self, e):
        self.cursor_pt = self.to_world(e.position())

    def mouseReleaseEvent(self, e):
        if self.drawing and self.win.world:
            x1, y1 = self.drawing
            x2, y2 = self.to_world(e.position())
            if self.win.world.add_line(x1, y1, x2, y2):
                self.win.sounds.play("click")
        self.drawing = None

    # -- effects
    def burst(self, x, y, color, n=26):
        for _ in range(n):
            a, v = random.uniform(0, math.tau), random.uniform(40, 200)
            self.sparks.append([x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(0.4, 0.9), color])

    def step_sparks(self, dt):
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[2] *= 0.94
            s[3] *= 0.94
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]

    # -- painting
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#060b14"))
        s, ox, oy = self.frame()
        p.translate(ox, oy)
        p.scale(s, s)
        self._table(p)
        w = self.win.world
        if not w:
            return
        for x, y, tw, th, color in w.tiles:
            r = QRectF(x, y, tw, th)
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, qc(color, 90))
            g.setColorAt(1, qc(color, 30))
            p.setPen(QPen(qc(color, 160), 1.5, Qt.DashLine))
            p.setBrush(g)
            p.drawRoundedRect(r, 8, 8)
        for px, py, color in w.pockets:
            self._pocket(p, px, py, color)
        for x1, y1, x2, y2 in w.walls:
            self._wall(p, x1, y1, x2, y2)
        for m in w.movers:
            x, y, mw, mh = w.mover_rect(m)
            g = QLinearGradient(x, y, x + mw, y)
            g.setColorAt(0, QColor("#4a5a70"))
            g.setColorAt(0.5, QColor("#8da2bc"))
            g.setColorAt(1, QColor("#4a5a70"))
            p.setPen(QPen(QColor("#c9d8ea"), 1.2))
            p.setBrush(g)
            p.drawRoundedRect(QRectF(x, y, mw, mh), 6, 6)
        for g in w.gates:
            self._gate(p, *g)
        for x1, y1, x2, y2, age in w.lines:
            fade = max(0.0, 1 - age / BW.LINE_LIFE)
            for width, alpha in ((14, 40), (7, 90), (2.5, 255)):
                p.setPen(QPen(QColor(220, 245, 255, int(alpha * fade)), width, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        if self.drawing and self.cursor_pt:
            x1, y1 = self.drawing
            x2, y2 = self.cursor_pt
            d = math.hypot(x2 - x1, y2 - y1)
            if d > BW.LINE_MAX:
                x2, y2 = x1 + (x2 - x1) / d * BW.LINE_MAX, y1 + (y2 - y1) / d * BW.LINE_MAX
            p.setPen(QPen(QColor(220, 245, 255, 140), 2, Qt.DashLine, Qt.RoundCap))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        for b in w.balls:
            self._ball(p, b)
        for x, y, vx, vy, life, color in self.sparks:
            p.setPen(Qt.NoPen)
            p.setBrush(qc(color, int(255 * min(1, life * 1.5))))
            p.drawEllipse(QPointF(x, y), 2.2, 2.2)
        self._hud(p, w)
        if self.win.paused or self.win.banner:
            self._banner(p, "Paused — press P to carry on" if self.win.paused else self.win.banner)

    def _table(self, p):
        r = QRectF(0, 0, BW.W, BW.H)
        g = QRadialGradient(QPointF(BW.W / 2, BW.H * 0.4), BW.W * 0.75)
        g.setColorAt(0, QColor("#163252"))
        g.setColorAt(1, QColor("#08121f"))
        p.setPen(QPen(QColor("#5d86b3"), 2))
        p.setBrush(g)
        p.drawRoundedRect(r, 14, 14)
        p.setPen(QPen(QColor(120, 170, 230, 18), 1))         # a faint grid in the glass
        for x in range(40, BW.W, 40):
            p.drawLine(x, 4, x, BW.H - 4)
        for y in range(40, BW.H, 40):
            p.drawLine(4, y, BW.W - 4, y)
        gl = QLinearGradient(0, 0, 0, BW.H * 0.4)
        gl.setColorAt(0, QColor(255, 255, 255, 30))
        gl.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(gl)
        p.drawRoundedRect(QRectF(6, 4, BW.W - 12, BW.H * 0.4), 12, 12)

    def _pocket(self, p, x, y, color):
        R = BW.POCKET_R
        glow = QRadialGradient(QPointF(x, y), R * 2)
        glow.setColorAt(0, qc(color, 70) if color != "any" else QColor(200, 210, 225, 50))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(x, y), R * 2, R * 2)
        hole = QRadialGradient(QPointF(x, y - R * 0.3), R)
        hole.setColorAt(0, QColor("#000000"))
        hole.setColorAt(1, QColor("#111a28"))
        p.setBrush(hole)
        ring = qc(color) if color != "any" else QColor("#b8c4d4")
        p.setPen(QPen(ring, 3))
        p.drawEllipse(QPointF(x, y), R, R)

    def _wall(self, p, x1, y1, x2, y2):
        p.setPen(QPen(QColor("#2c3d55"), 9, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        p.setPen(QPen(QColor("#8fa9c9"), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _gate(self, p, x1, y1, x2, y2):
        p.setPen(QPen(QColor(255, 220, 120, 160), 3, Qt.DashLine, Qt.RoundCap))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        # arrows showing the way through (towards the line's left side)
        lx, ly = x2 - x1, y2 - y1
        ln = math.hypot(lx, ly) or 1
        nx, ny = ly / ln, -lx / ln
        p.setPen(QPen(QColor(255, 220, 120, 200), 2))
        for t in (0.25, 0.5, 0.75):
            cx, cy = x1 + lx * t, y1 + ly * t
            tip = QPointF(cx + nx * 14, cy + ny * 14)
            p.drawLine(QPointF(cx - nx * 6, cy - ny * 6), tip)
            p.drawLine(tip, QPointF(tip.x() - nx * 6 + ny * 5, tip.y() - ny * 6 - nx * 5))
            p.drawLine(tip, QPointF(tip.x() - nx * 6 - ny * 5, tip.y() - ny * 6 + nx * 5))

    def _ball(self, p, b):
        R = BW.BALL_R
        c = qc(b.color)
        if self.win.store.opt("trails", True):
            for i, (tx, ty) in enumerate(b.trail):
                p.setPen(Qt.NoPen)
                p.setBrush(qc(b.color, int(60 * (i + 1) / max(1, len(b.trail)))))
                p.drawEllipse(QPointF(tx, ty), R * 0.6, R * 0.6)
        halo = QRadialGradient(QPointF(b.x, b.y), R * 2.6)
        halo.setColorAt(0, qc(b.color, 120))
        halo.setColorAt(1, qc(b.color, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(b.x, b.y), R * 2.6, R * 2.6)
        body = QRadialGradient(QPointF(b.x - R * 0.35, b.y - R * 0.4), R * 1.2)
        body.setColorAt(0, QColor(255, 255, 255))
        body.setColorAt(0.35, c.lighter(115))
        body.setColorAt(1, c.darker(160))
        p.setBrush(body)
        p.setPen(QPen(c.darker(200), 1))
        p.drawEllipse(QPointF(b.x, b.y), R, R)

    def _hud(self, p, w):
        f = QFont(self.font())
        f.setPixelSize(15)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(200, 225, 255, 220))
        p.drawText(QRectF(16, 8, 400, 24), Qt.AlignLeft | Qt.AlignVCenter,
                   f"Level {w.index + 1}: {w.name}")
        p.drawText(QRectF(BW.W - 416, 8, 400, 24), Qt.AlignRight | Qt.AlignVCenter,
                   f"Score {self.win.score + w.points}")

    def _banner(self, p, text):
        f = QFont(self.font())
        f.setPixelSize(26)
        p.setFont(f)
        r = QRectF(BW.W / 2 - 260, BW.H / 2 - 36, 520, 72)
        p.setPen(QPen(QColor(150, 200, 255, 160), 1.5))
        p.setBrush(QColor(4, 12, 26, 210))
        p.drawRoundedRect(r, 16, 16)
        p.setPen(QColor("#e8f4ff"))
        p.drawText(r, Qt.AlignCenter, text)


class GlowBounce(common.GameWindow):
    NAME = "Glow Bounce"
    ICON = "applications-games"
    HELP = HELP

    def __init__(self):
        super().__init__("bounce")
        self.world = None
        self.score = 0
        self.paused = False
        self.banner = ""
        self.playing = False
        self.table = Table(self)
        self.setCentralWidget(self.table)
        self.standard_menu()
        self.add(self.game_menu, "Restart Level", self.restart_level, "R")
        self.add(self.game_menu, "Pause", self.toggle_pause, "P")
        self.levels_menu = self.menuBar().addMenu("&Levels")
        self.levels_menu.aboutToShow.connect(self._fill_levels)
        self.status = QLabel()
        self.statusBar().addWidget(self.status, 1)
        self.clock = QElapsedTimer()
        self.timer = QTimer(self, interval=16, timeout=self.tick)
        self.resize(900, 680)
        QTimer.singleShot(0, self.new_game)

    # ------------------------------------------------------------- flow ---
    def in_progress(self):
        return bool(self.world and (self.world.index > 0 or self.world.time > 2))

    def new_game(self):
        self.score = 0
        self.start_level(0)

    def start_level(self, i):
        self.world = BW.World(i)
        self.table.sparks = []
        self.paused = False
        self.banner = f"Level {i + 1}: {self.world.name}"
        self.playing = False
        self.timer.start()
        self.clock.restart()
        self.sounds.play("deal")
        QTimer.singleShot(1300, self._go)
        self._status()

    def _go(self):
        self.banner = ""
        self.playing = True
        self.clock.restart()

    def restart_level(self):
        if self.world:
            self.start_level(self.world.index)

    def toggle_pause(self):
        if self.playing:
            self.paused = not self.paused
            self.clock.restart()
            self.table.update()

    def tick(self):
        dt = min(0.05, self.clock.restart() / 1000) if self.clock.isValid() else 0
        w = self.world
        if w and self.playing and not self.paused:
            w.update(dt)
            for b in w.balls:
                b.trail.append((b.x, b.y))
                del b.trail[:-8]
            for kind, x, y in w.events:
                if kind == "sunk":
                    self.sounds.play("win" if not w.balls else "capture")
                    self.table.burst(x, y, "amber" if not w.balls else "cyan")
                elif kind == "wrong":
                    self.sounds.play("bad")
                    self.table.burst(x, y, "magenta", 14)
                elif kind == "paint":
                    self.sounds.play("flip")
            w.events.clear()
            if w.done:
                self.level_cleared()
            elif w.lost:
                self.playing = False
                self.banner = "Out of lives"
                QTimer.singleShot(1200, lambda: self.lost(f"You ran out of lives on level {w.index + 1}. "
                                                          f"Score: {self.score + w.points}."))
        self.table.step_sparks(dt)
        self.table.update()
        self._status()

    def level_cleared(self):
        w = self.world
        self.playing = False
        bonus = w.bonus()
        self.score += w.points + bonus
        unlocked = max(self.store.opt("unlocked", 1), w.index + 2)
        self.store.set_opt("unlocked", min(len(BW.LEVELS), unlocked))
        if w.index + 1 >= len(BW.LEVELS):
            self.banner = "All twelve levels cleared!"
            QTimer.singleShot(1500, lambda: self.won(score=self.score))
            return
        self.banner = f"Level cleared!  Bonus {bonus}"
        QTimer.singleShot(1800, lambda: self.start_level(w.index + 1))

    def _status(self):
        w = self.world
        if w:
            # lives live down here: pockets sit near every edge of the table
            lives = "♥ " * w.lives + "♡ " * (BW.LIVES - w.lives)
            self.status.setText(f"Lives: {lives.strip()}   ·   lines: {len(w.lines)} of {BW.MAX_LINES}"
                                f"   ·   balls left: {len(w.balls)}   ·   time {int(w.time)} s")

    def _fill_levels(self):
        self.levels_menu.clear()
        unlocked = self.store.opt("unlocked", 1)
        for i, L in enumerate(BW.LEVELS):
            a = self.levels_menu.addAction(f"{i + 1}. {L['name']}")
            a.setEnabled(i < unlocked)
            a.triggered.connect(lambda _=False, i=i: self._choose(i))

    def _choose(self, i):
        self.score = 0
        self.start_level(i)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self.paused:
            self.toggle_pause()
        else:
            super().keyPressEvent(e)

    def options(self):
        d = QDialog(self)
        d.setWindowTitle("Options")
        lay = QVBoxLayout(d)
        trails = QCheckBox("Show glowing trails behind the balls")
        trails.setChecked(self.store.opt("trails", True))
        lay.addWidget(trails)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        was = self.paused
        self.paused = True
        if d.exec():
            self.store.set_opt("trails", trails.isChecked())
        self.paused = was
        self.clock.restart()


def main():
    return common.run(GlowBounce, "halcyon-bounce")


if __name__ == "__main__":
    import sys
    sys.exit(main())
