"""Halcyon Hearts: you against three computer players on the green table.
Pass three cards, follow suit, avoid hearts and the Queen of spades; the
game ends when someone reaches 100 and the lowest score wins.

Rules and computer players are in hearts_engine.py."""
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, QElapsedTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QTransform
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QRadioButton,
                               QVBoxLayout, QWidget)

from . import cards as C
from . import common
from .hearts_engine import QUEEN, Match, Player, hint, pass_target, points

NAMES = ["You", "Ana", "Ben", "Cleo"]           # bottom, left, top, right
WHERE = {"left": "left", "right": "right", "across": "across"}
SPEEDS = {"slow": 1.6, "normal": 1.0, "fast": 0.5}

HELP = """<p><b>Goal:</b> take as few points as you can. Each heart is 1 point and the Queen of spades is 13.
The game ends when someone reaches 100 points; the lowest score wins.</p>
<p><b>Passing:</b> before each hand, choose three cards to pass (left, then right, then across, then no pass).</p>
<p><b>Playing:</b> whoever has the 2 of clubs leads it. Everyone must follow the suit that was led if they can;
if not, they may play anything. The highest card of the suit led takes the trick and leads the next one.
No hearts or Queen of spades on the first trick, and hearts can't be led until a heart has been played
(unless you have nothing else).</p>
<p><b>Shooting the moon:</b> take all 13 hearts <i>and</i> the Queen, and everyone else gets 26 points instead.</p>
<p>Press <b>H</b> for a hint.</p>"""


def ui_rank(card):
    """cards.py counts Ace as 1."""
    return 1 if card[0] == 14 else card[0]


class Table(QWidget):
    """Draws the four hands, the trick in the middle and the moving cards."""
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setMouseTracking(True)
        self.setMinimumSize(720, 540)
        self.deck = C.Deck(72)
        self.side_back = None
        self.hover = -1
        self.hinted = set()
        self.flying = []                # [card, from QRectF, to QRectF, start ms, duration ms, then()]
        self.clock = QElapsedTimer()
        self.clock.start()
        self.timer = QTimer(self, interval=15, timeout=self._tick)
        self.button_rect = QRectF()

    # ----------------------------------------------------------- geometry ---
    def metrics(self):
        W, H = self.width(), self.height()
        cw = int(max(48, min(W / 12.5, H / 6.6)))
        if cw != self.deck.w:
            self.deck = C.Deck(cw)
            self.side_back = None
        return W, H, self.deck.w, self.deck.h

    def hand_rects(self, seat):
        W, H, cw, ch = self.metrics()
        n = len(self.win.hand.hands[seat]) if self.win.hand else 0
        m = cw * 0.35
        if seat == 0:
            step = min(cw * 0.52, (W - 2 * m - cw) / max(1, n - 1))
            x0 = (W - (step * (n - 1) + cw)) / 2
            y = H - ch - m
            out = []
            for i, c in enumerate(self.win.hand.hands[0]):
                up = c in self.win.selected or c in self.win.received or (i == self.hover and self.win.clickable(c))
                out.append(QRectF(x0 + i * step, y - (ch * 0.2 if up else 0), cw, ch))
            return out
        if seat == 2:
            step = cw * 0.24
            x0 = (W - (step * (n - 1) + cw)) / 2
            return [QRectF(x0 + i * step, m - ch * 0.45, cw, ch) for i in range(n)]
        step = ch * 0.1                                       # left / right: cards turned sideways
        y0 = (H - (step * (n - 1) + cw)) / 2 - ch * 0.15
        x = m - ch * 0.45 if seat == 1 else W - m - ch * 0.55
        return [QRectF(x, y0 + i * step, ch, cw) for i in range(n)]

    def seat_point(self, seat):
        """Where a seat's cards come from and tricks go to."""
        W, H, cw, ch = self.metrics()
        return {0: QPointF(W / 2, H - ch * 0.6), 1: QPointF(ch * 0.3, H / 2 - ch * 0.15),
                2: QPointF(W / 2, ch * 0.2), 3: QPointF(W - ch * 0.3, H / 2 - ch * 0.15)}[seat]

    def trick_rect(self, seat):
        W, H, cw, ch = self.metrics()
        cx, cy = W / 2, H / 2 - ch * 0.15
        pos = {0: (cx - cw / 2, cy + ch * 0.05), 1: (cx - cw * 1.35, cy - ch / 2),
               2: (cx - cw / 2, cy - ch * 1.05), 3: (cx + cw * 0.35, cy - ch / 2)}[seat]
        return QRectF(pos[0], pos[1], cw, ch)

    def label_rect(self, seat):
        W, H, cw, ch = self.metrics()
        w, h = cw * 1.9, 24
        if seat == 0:
            return QRectF(W / 2 - w / 2, H - ch * 1.62, w, h)
        if seat == 2:                                          # under the top player's cards
            return QRectF(W / 2 - w / 2, cw * 0.35 + ch * 0.55 + 8, w, h)
        hand = self.hand_rects(seat)
        bottom = hand[-1].bottom() if hand else H / 2
        x = ch * 0.15 if seat == 1 else W - ch * 0.15 - w
        return QRectF(x, bottom + 8, w, h)

    # ------------------------------------------------------------ painting ---
    def _sideways(self):
        if self.side_back is None:
            self.side_back = self.deck.back().transformed(QTransform().rotate(90), Qt.SmoothTransformation)
        return self.side_back

    def paintEvent(self, e):
        win = self.win
        W, H, cw, ch = self.metrics()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        common.felt(p, self.rect(), win.store.opt("felt", "#1f6b33"))
        h = win.hand
        if not h:
            return
        flying = {f[0] for f in self.flying}
        # other players' cards, face down
        for seat in (1, 2, 3):
            for r in self.hand_rects(seat):
                p.drawPixmap(r.toRect(), self._sideways() if seat != 2 else self.deck.back())
        # your hand
        dim = win.store.opt("dim", True) and win.state == "play" and h.turn == 0
        legal = set(h.legal(0)) if dim else set()
        for i, (r, c) in enumerate(zip(self.hand_rects(0), h.hands[0])):
            if c in flying:
                continue
            p.drawPixmap(r.toRect(), self.deck.face(ui_rank(c), c[1]))
            if dim and c not in legal:
                p.fillRect(r.adjusted(1, 1, -1, -1), QColor(0, 0, 0, 70))
            if c in self.hinted:
                p.setPen(QPen(QColor("#ffd84a"), 3))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(r.adjusted(-1, -1, 1, 1), cw * 0.08, cw * 0.08)
        # the trick on the table
        for seat, c in win.on_table:
            if c not in flying:
                p.drawPixmap(self.trick_rect(seat).toRect(), self.deck.face(ui_rank(c), c[1]))
        # cards in the air
        now = self.clock.elapsed()
        for card, a, b, t0, dur, _ in self.flying:
            t = min(1.0, max(0.0, (now - t0) / dur))
            t = 1 - (1 - t) ** 3                               # ease out
            r = QRectF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t,
                       a.width() + (b.width() - a.width()) * t, a.height() + (b.height() - a.height()) * t)
            p.drawPixmap(r.toRect(), self.deck.face(ui_rank(card), card[1]) if card[1] else self.deck.back())
        # names and scores
        taken = h.points_taken()
        for seat in range(4):
            self._label(p, self.label_rect(seat), NAMES[seat], win.match.totals[seat], taken[seat],
                        seat == h.turn and win.state == "play")
        self._banner(p, W, H, cw, ch)

    def _label(self, p, r, name, total, now, active):
        g = QLinearGradient(0, r.top(), 0, r.bottom())
        g.setColorAt(0, QColor(255, 255, 255, 60 if not active else 120))
        g.setColorAt(1, QColor(0, 0, 0, 60))
        p.setPen(QPen(QColor(255, 255, 255, 110 if not active else 220), 1))
        p.setBrush(g)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        f = QFont(self.font())
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("white"))
        extra = f"  (+{now})" if now else ""
        p.drawText(r, Qt.AlignCenter, f"{name}  {total}{extra}")

    def _banner(self, p, W, H, cw, ch):
        """Instructions in the middle of the table, and the Pass button."""
        text = self.win.banner
        self.button_rect = QRectF()
        if not text:
            return
        f = QFont(self.font())
        f.setPointSizeF(f.pointSizeF() + 2)
        p.setFont(f)
        fm = p.fontMetrics()
        cy = H / 2 - ch * 0.15
        tw = fm.horizontalAdvance(text) + 40
        r = QRectF(W / 2 - tw / 2, cy - 22, tw, 34)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 20, 10, 120))
        p.drawRoundedRect(r, 10, 10)
        p.setPen(QColor("white"))
        p.drawText(r, Qt.AlignCenter, text)
        if self.win.button_text:
            bw = fm.horizontalAdvance(self.win.button_text) + 44
            b = QRectF(W / 2 - bw / 2, r.bottom() + 12, bw, 32)
            on = self.win.button_enabled()
            g = QLinearGradient(0, b.top(), 0, b.bottom())
            g.setColorAt(0, QColor("#f4faff" if on else "#c7cfd8"))
            g.setColorAt(0.5, QColor("#d6ebfb" if on else "#b0b9c4"))
            g.setColorAt(0.51, QColor("#a9d3f4" if on else "#9ea8b4"))
            g.setColorAt(1, QColor("#cfe8fb" if on else "#b4bdc8"))
            p.setPen(QPen(QColor("#2b5f92" if on else "#6b7684"), 1))
            p.setBrush(g)
            p.drawRoundedRect(b, 6, 6)
            p.setPen(QColor("#10304f" if on else "#5b6470"))
            p.drawText(b, Qt.AlignCenter, self.win.button_text)
            self.button_rect = b

    # ------------------------------------------------------------- motion ---
    def fly(self, card, a, b, ms, then=None):
        self.flying.append([card, a, b, self.clock.elapsed(), max(1, ms * self.win.speed()), then])
        if not self.timer.isActive():
            self.timer.start()

    def _tick(self):
        now = self.clock.elapsed()
        done = [f for f in self.flying if now - f[3] >= f[4]]
        self.flying = [f for f in self.flying if f not in done]
        for f in done:
            if f[5]:
                f[5]()
        if not self.flying:
            self.timer.stop()
        self.update()

    # -------------------------------------------------------------- input ---
    def _card_at(self, pos):
        if not self.win.hand:
            return -1
        rects = self.hand_rects(0)
        for i in range(len(rects) - 1, -1, -1):                # topmost first
            if rects[i].contains(pos):
                return i
        return -1

    def mouseMoveEvent(self, e):
        i = self._card_at(e.position())
        over_button = self.button_rect.contains(e.position())
        if i != self.hover:
            self.hover = i
            self.update()
        h = self.win.hand
        clickable = over_button or (i >= 0 and self.win.clickable(h.hands[0][i]))
        self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)

    def leaveEvent(self, e):
        self.hover = -1
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or self.flying:
            return
        if self.button_rect.contains(e.position()):
            self.win.button_clicked()
            return
        i = self._card_at(e.position())
        self.win.card_clicked(self.win.hand.hands[0][i] if i >= 0 else None)

    def resizeEvent(self, e):
        self.update()


class ScoreSheet(QDialog):
    """Points per hand and the running totals."""
    def __init__(self, parent, match, note):
        super().__init__(parent)
        self.setWindowTitle("Score")
        lay = QVBoxLayout(self)
        if note:
            t = QLabel(note)
            t.setStyleSheet(f"color: {common.TEXT}; font-size: 12pt;")
            lay.addWidget(t)
        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        for c, name in enumerate(NAMES):
            lbl = QLabel(f"<b>{name}</b>")
            lbl.setAlignment(Qt.AlignRight)
            grid.addWidget(lbl, 0, c + 1)
        for r, row in enumerate(match.history[-12:], start=1):
            grid.addWidget(QLabel(f"Hand {len(match.history) - len(match.history[-12:]) + r}"), r, 0)
            for c, v in enumerate(row):
                lbl = QLabel(str(v))
                lbl.setAlignment(Qt.AlignRight)
                grid.addWidget(lbl, r, c + 1)
        last = len(match.history[-12:]) + 1
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #8ea6c4;")
        grid.addWidget(line, last, 0, 1, 5)
        grid.addWidget(QLabel("<b>Total</b>"), last + 1, 0)
        low = min(match.totals)
        for c, v in enumerate(match.totals):
            lbl = QLabel(f"<b>{v}</b>" if v != low else f"<b style='color:#1d7a12'>{v}</b>")
            lbl.setAlignment(Qt.AlignRight)
            grid.addWidget(lbl, last + 1, c + 1)
        lay.addLayout(grid)
        bb = QDialogButtonBox(QDialogButtonBox.Ok)
        bb.button(QDialogButtonBox.Ok).setText("Continue")
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


class Hearts(common.GameWindow):
    NAME = "Hearts"
    ICON = "kpat"
    HELP = HELP

    def __init__(self):
        super().__init__("hearts")
        self.match = None
        self.hand = None
        self.players = []
        self.state = "idle"              # pass, received, play, between
        self.selected = set()
        self.received = set()
        self.on_table = []               # [(seat, card)] cards lying in the middle
        self.banner = ""
        self.button_text = ""
        self.table = Table(self)
        self.setCentralWidget(self.table)
        self.standard_menu(hint=self.hint)
        self.add(self.game_menu, "Score", self.show_score, "F3")
        self.status = QLabel()
        self.statusBar().addWidget(self.status, 1)
        self.resize(980, 720)
        QTimer.singleShot(0, self.new_game)

    # ------------------------------------------------------------ helpers ---
    def speed(self):
        return SPEEDS.get(self.store.opt("speed", "normal"), 1.0)

    def in_progress(self):
        return bool(self.match and not self.match.over and (len(self.match.history) or self.hand.tricks_played))

    def clickable(self, card):
        if self.state == "pass":
            return True
        if self.state == "play" and self.hand.turn == 0 and not self.table.flying and len(self.on_table) < 4:
            return card in self.hand.legal(0)
        return False

    def button_enabled(self):
        return self.state != "pass" or len(self.selected) == 3

    def update_status(self):
        h = self.hand
        if not h:
            return
        passing = "no passing" if h.direction == "none" else f"passing {h.direction}"
        broken = "hearts broken" if h.hearts_broken else "hearts not broken yet"
        self.status.setText(f"Hand {self.match.number} ({passing})  ·  trick {min(13, h.tricks_played + 1)} of 13"
                            f"  ·  {broken}")

    # -------------------------------------------------------------- flow ---
    def new_game(self):
        self.match = Match()
        self.start_hand()

    def start_hand(self):
        self.hand = self.match.hand
        self.players = [None] + [Player(i) for i in (1, 2, 3)]
        self.selected, self.received, self.on_table = set(), set(), []
        self.table.hinted = set()
        self.sounds.play("deal")
        if self.hand.passing:
            who = NAMES[pass_target(0, self.hand.direction)]
            self.state = "pass"
            self.banner = f"Choose three cards to pass {WHERE[self.hand.direction]} to {who}"
            self.button_text = f"Pass {WHERE[self.hand.direction].title()}"
        else:
            self.begin_play()
        self.update_status()
        self.table.update()

    def do_pass(self):
        h = self.hand
        for seat in (1, 2, 3):
            h.choose_pass(seat, self.players[seat].choose_pass(h.hands[seat]))
        h.choose_pass(0, sorted(self.selected))
        self.selected = set()
        self.received = set(h.received[0])
        self.sounds.play("flip")
        self.state = "received"
        frm = NAMES[[s for s in range(4) if pass_target(s, h.direction) == 0][0]]
        self.banner = f"{frm} passed you these cards"
        self.button_text = "OK"
        self.table.update()

    def begin_play(self):
        for seat in (1, 2, 3):
            self.players[seat].plan_moon(self.hand.hands[seat])
        self.received = set()
        self.state = "play"
        self.banner = ""
        self.button_text = ""
        self.advance()

    def advance(self):
        h = self.hand
        self.update_status()
        if h.done:
            QTimer.singleShot(int(400 * self.speed()), self.end_hand)
            return
        if h.turn == 0:
            if h.tricks_played == 0 and not h.trick:
                self.banner = "You have the 2 of clubs: lead it to start"
            self.table.update()
            return
        QTimer.singleShot(int(450 * self.speed()), self.computer_turn)

    def computer_turn(self):
        if self.state != "play" or self.hand.turn in (None, 0):
            return
        seat = self.hand.turn
        self.play(seat, self.players[seat].choose(self.hand))

    def play(self, seat, card):
        """Move the card to the middle; when it lands, count it in."""
        h = self.hand
        start = (self.table.hand_rects(0)[h.hands[0].index(card)] if seat == 0 else
                 QRectF(self.table.seat_point(seat) - QPointF(self.table.deck.w / 2, self.table.deck.h / 2),
                        self.table.trick_rect(seat).size()))
        self.banner = ""
        win = h.play(seat, card)
        self.on_table.append((seat, card))
        self.sounds.play("place")

        def landed():
            if win is None:
                self.advance()
            else:
                QTimer.singleShot(int(900 * self.speed()), lambda: self.collect(win))
        self.table.fly(card, start, self.table.trick_rect(seat), 260, landed)
        self.update_status()

    def collect(self, winner):
        """Sweep the finished trick to whoever took it."""
        cards = self.on_table
        self.on_table = []
        target = self.table.seat_point(winner)
        tr = QRectF(target.x() - self.table.deck.w / 4, target.y() - self.table.deck.h / 4,
                    self.table.deck.w / 2, self.table.deck.h / 2)
        took = sum(points(c) for _, c in cards)
        if took:
            self.sounds.play("capture" if (QUEEN not in [c for _, c in cards]) else "bad")
        for i, (seat, c) in enumerate(cards):
            self.table.fly(c, self.table.trick_rect(seat), tr, 320, self.advance if i == len(cards) - 1 else None)

    def end_hand(self):
        h = self.hand
        moon = h.moon()
        self.match.finish_hand()
        if moon == 0:
            note = "You shot the moon! Everyone else gets 26 points."
        elif moon is not None:
            note = f"{NAMES[moon]} shot the moon! Everyone else gets 26 points."
        else:
            pts = h.points_taken()
            note = "You took no points this hand." if pts[0] == 0 else f"You took {pts[0]} point{'s' if pts[0] != 1 else ''} this hand."
        self.state = "between"
        self.table.update()
        ScoreSheet(self, self.match, note).exec()
        if self.match.over:
            winners = self.match.winners()
            if 0 in winners:
                self.won(score=100 - self.match.totals[0])
            else:
                names = " and ".join(NAMES[w] for w in winners)
                self.lost(f"{names} won with {self.match.totals[winners[0]]} points. You had {self.match.totals[0]}.")
            return
        self.match.new_hand()
        self.start_hand()

    # ------------------------------------------------------------- input ---
    def card_clicked(self, card):
        if self.state == "received":
            self.begin_play()
            return
        if card is None:
            return
        if self.state == "pass":
            if card in self.selected:
                self.selected.discard(card)
            elif len(self.selected) < 3:
                self.selected.add(card)
            self.sounds.play("click")
            self.table.update()
        elif self.clickable(card):
            self.table.hinted = set()
            self.play(0, card)
        elif self.state == "play" and self.hand.turn == 0:
            self.sounds.play("bad")
            self.explain(card)

    def explain(self, card):
        h = self.hand
        if h.trick:
            why = f"You have to follow suit: play a {dict(C=' club', D=' diamond', S=' spade', H=' heart')[h.trick[0][1][1]].strip()}."
            if h.first_trick and points(card):
                why = "No hearts or Queen of spades on the first trick."
        elif h.tricks_played == 0:
            why = "Lead the 2 of clubs to start."
        else:
            why = "Hearts can't be led until a heart has been played."
        self.banner = why
        self.table.update()
        QTimer.singleShot(2200, lambda: (setattr(self, "banner", "") if self.banner == why else None,
                                         self.table.update()))

    def button_clicked(self):
        if self.state == "pass" and len(self.selected) == 3:
            self.do_pass()
        elif self.state == "received":
            self.begin_play()

    def hint(self):
        if self.state in ("pass", "play") and (self.state == "pass" or self.hand.turn == 0):
            self.table.hinted = set(hint(self.hand, 0))
            self.table.update()
            QTimer.singleShot(1800, lambda: (setattr(self.table, "hinted", set()), self.table.update()))

    def show_score(self):
        if self.match and self.match.history:
            ScoreSheet(self, self.match, "").exec()

    def options(self):
        d = QDialog(self)
        d.setWindowTitle("Options")
        lay = QVBoxLayout(d)
        lay.addWidget(QLabel("<b>Animation speed</b>"))
        grp = QButtonGroup(d)
        cur = self.store.opt("speed", "normal")
        for key, label in (("slow", "Slow"), ("normal", "Normal"), ("fast", "Fast")):
            b = QRadioButton(label)
            b.setChecked(key == cur)
            b.setProperty("key", key)
            grp.addButton(b)
            lay.addWidget(b)
        dim = QCheckBox("Dim the cards you can't play")
        dim.setChecked(self.store.opt("dim", True))
        lay.addSpacing(8)
        lay.addWidget(dim)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        if d.exec():
            self.store.set_opt("speed", grp.checkedButton().property("key"))
            self.store.set_opt("dim", dim.isChecked())
            self.table.update()


def main():
    return common.run(Hearts, "halcyon-hearts")


if __name__ == "__main__":
    import sys
    sys.exit(main())
