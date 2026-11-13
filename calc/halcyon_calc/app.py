"""Halcyon Calculator: Standard and Scientific, after the Windows calculator
of the Vista era. The maths is in engine.py."""
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QGridLayout, QHBoxLayout, QMainWindow,
                               QMessageBox, QPushButton, QRadioButton, QSizePolicy, QVBoxLayout, QWidget, QFrame)

from .engine import DIGITS, Engine, group

CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "halcyon" / "calc.json"
BLUE, RED, PURPLE = "#0b3a9e", "#b0140a", "#6a1a8a"     # digit, operator and memory key colours


class Display(QWidget):
    """The recessed number display, with memory and parenthesis indicators."""
    def __init__(self, engine):
        super().__init__()
        self.e = engine
        self.grouping = False
        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#dfe8f2"))
        g.setColorAt(0.12, QColor("#ffffff"))
        g.setColorAt(1, QColor("#f2f7fc"))
        p.setPen(QPen(QColor("#7f9db9"), 1))
        p.setBrush(g)
        p.drawRoundedRect(r, 3, 3)
        small = QFont(self.font())
        small.setPointSizeF(max(7, small.pointSizeF() - 1))
        p.setFont(small)
        p.setPen(QColor("#5a6a7e"))
        tags = []
        if self.e.has_memory:
            tags.append("M")
        if self.e.parens:
            tags.append(f"(={self.e.parens}")
        p.drawText(r.adjusted(8, 4, -8, -4), Qt.AlignLeft | Qt.AlignTop, "   ".join(tags))
        big = QFont(self.font())
        big.setPointSizeF(big.pointSizeF() + 7)
        text = self.e.display()
        if self.grouping and not self.e.error:
            text = group(text, self.e.base if self.e.mode == "scientific" else "dec")
        fm_w = r.width() - 16
        while big.pointSizeF() > 8:
            p.setFont(big)
            if p.fontMetrics().horizontalAdvance(text) <= fm_w:
                break
            big.setPointSizeF(big.pointSizeF() - 1)
        p.setPen(QColor("#000000"))
        p.drawText(r.adjusted(8, 2, -8, -4), Qt.AlignRight | Qt.AlignBottom, text)


class Key(QPushButton):
    """A glossy calculator key."""
    def __init__(self, text, key, color=BLUE, wide=1):
        super().__init__(text)
        self.key = key
        self.setFocusPolicy(Qt.NoFocus)
        self.setMinimumSize(QSize(38 * wide + (wide - 1) * 4, 30))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            QPushButton {{ color: {color}; border: 1px solid #8ea6c4; border-radius: 4px; padding: 0 4px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.45 #eef3f9,
                stop:0.5 #dde7f2, stop:1 #ecf2f9); }}
            QPushButton:hover {{ border-color: #3c7fb1; background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f4faff, stop:0.45 #dcefff, stop:0.5 #c3e2fb, stop:1 #d9ecfc); }}
            QPushButton:pressed {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b9d9f4,
                stop:1 #d6e9f8); padding-top: 1px; }}
            QPushButton:disabled {{ color: #a9b3bf; }}""")


class Calculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calculator")
        self.setWindowIcon(QIcon.fromTheme("accessories-calculator"))
        self.e = Engine()
        self.keys = {}
        self.cfg = self._load()
        self.e.angle = self.cfg.get("angle", "deg")

        edit = self.menuBar().addMenu("&Edit")
        edit.addAction("&Copy", self.copy, QKeySequence.Copy)
        edit.addAction("&Paste", self.paste, QKeySequence.Paste)
        view = self.menuBar().addMenu("&View")
        grp = QActionGroup(self)
        self.std = QAction("&Standard", self, checkable=True)
        self.sci = QAction("S&cientific", self, checkable=True)
        for a, mode, key in ((self.std, "standard", "Alt+1"), (self.sci, "scientific", "Alt+2")):
            a.setShortcut(QKeySequence(key))
            grp.addAction(a)
            view.addAction(a)
            a.triggered.connect(lambda _=False, m=mode: self.set_mode(m))
        view.addSeparator()
        self.grouping = view.addAction("&Digit grouping", self.refresh)
        self.grouping.setCheckable(True)
        self.grouping.setChecked(self.cfg.get("grouping", False))
        self.grouping.toggled.connect(lambda on: self._save(grouping=on))
        help_ = self.menuBar().addMenu("&Help")
        help_.addAction("&About Calculator", lambda: QMessageBox.about(
            self, "Calculator", "<b>Calculator</b><p>Part of Halcyon. Standard and Scientific modes; "
            "Scientific respects precedence and parentheses and works in Hex, Dec, Oct and Bin.</p>"
            "<p>Keyboard: digits, + - * / and Enter, Esc clears, Delete clears the entry, "
            "Backspace, %, ( ), F9 changes sign, R is 1/x, @ is square root.</p>"))

        central = QWidget()
        central.setObjectName("calc")
        central.setStyleSheet("#calc { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f3f7fc, "
                              "stop:1 #dfe8f3); }")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)
        self.display = Display(self.e)
        outer.addWidget(self.display)
        self.body = QHBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body, 1)
        self.sci_panel = self._scientific()
        self.body.addWidget(self.sci_panel, 3)
        self.body.addLayout(self._standard(), 2)
        self.set_mode(self.cfg.get("mode", "standard"))

    # ------------------------------------------------------------ layout ---
    def _add(self, grid, text, key, row, col, color=BLUE, span=1):
        b = Key(text, key, color, span)
        b.clicked.connect(lambda _=False, k=key: self.press(k))
        grid.addWidget(b, row, col, 1, span)
        self.keys[key] = b
        return b

    def _standard(self):
        g = QGridLayout()
        g.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(4)
        for text, key in (("Backspace", "back"), ("CE", "CE"), ("C", "clear")):
            b = Key(text, key, RED)
            b.clicked.connect(lambda _=False, k=key: self.press(k))
            self.keys[key] = b
            top.addWidget(b)
        g.addLayout(top, 0, 0, 1, 6)
        rows = [[("MC", "MC", PURPLE), ("7", "7"), ("8", "8"), ("9", "9"), ("/", "/", RED), ("sqrt", "sqrt")],
                [("MR", "MR", PURPLE), ("4", "4"), ("5", "5"), ("6", "6"), ("*", "*", RED), ("%", "%")],
                [("MS", "MS", PURPLE), ("1", "1"), ("2", "2"), ("3", "3"), ("-", "-", RED), ("1/x", "recip")],
                [("M+", "M+", PURPLE), ("0", "0"), ("+/-", "neg"), (".", "."), ("+", "+", RED), ("=", "=", RED)]]
        for r, row in enumerate(rows, start=1):
            for c, item in enumerate(row):
                self._add(g, item[0], item[1], r, c, item[2] if len(item) > 2 else BLUE)
        return g

    def _scientific(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        radios = QHBoxLayout()
        self.base_group = QButtonGroup(self)
        box = self._frame(radios)
        for text, base in (("Hex", "hex"), ("Dec", "dec"), ("Oct", "oct"), ("Bin", "bin")):
            rb = QRadioButton(text)
            rb.setProperty("base", base)
            rb.setChecked(base == "dec")
            self.base_group.addButton(rb)
            radios.addWidget(rb)
        self.base_group.buttonClicked.connect(lambda b: self.set_base(b.property("base")))
        angles = QHBoxLayout()
        self.angle_group = QButtonGroup(self)
        abox = self._frame(angles)
        for text, a in (("Degrees", "deg"), ("Radians", "rad"), ("Grads", "grad")):
            rb = QRadioButton(text)
            rb.setProperty("angle", a)
            rb.setChecked(a == self.e.angle)
            self.angle_group.addButton(rb)
            angles.addWidget(rb)
        self.angle_group.buttonClicked.connect(lambda b: self._set_angle(b.property("angle")))
        top = QHBoxLayout()
        top.addWidget(box)
        top.addWidget(abox)
        lay.addLayout(top)
        checks = QHBoxLayout()
        self.inv = QCheckBox("Inv")
        self.hyp = QCheckBox("Hyp")
        self.inv.toggled.connect(lambda on: setattr(self.e, "inv", on))
        self.hyp.toggled.connect(lambda on: setattr(self.e, "hyp", on))
        checks.addWidget(self.inv)
        checks.addWidget(self.hyp)
        checks.addStretch(1)
        lay.addLayout(checks)
        g = QGridLayout()
        g.setSpacing(4)
        rows = [[("(", "("), (")", ")"), ("sin", "sin"), ("cos", "cos"), ("tan", "tan")],
                [("x^y", "x^y", RED), ("x^3", "x^3"), ("x^2", "x^2"), ("ln", "ln"), ("log", "log")],
                [("n!", "n!"), ("pi", "pi"), ("Exp", "Exp"), ("Mod", "Mod", RED), ("Not", "Not", RED)],
                [("And", "And", RED), ("Or", "Or", RED), ("Xor", "Xor", RED), ("Lsh", "Lsh", RED), ("A", "A")],
                [("B", "B"), ("C", "C_hex"), ("D", "D"), ("E", "E"), ("F", "F")]]
        for r, row in enumerate(rows):
            for c, item in enumerate(row):
                key = "C" if item[1] == "C_hex" else item[1]       # the hex digit C ("clear" is the C key)
                b = Key(item[0], key, item[2] if len(item) > 2 else BLUE)
                b.clicked.connect(lambda _=False, k=key: self.press(k))
                g.addWidget(b, r, c)
                self.keys[item[1]] = b
        lay.addLayout(g, 1)
        return w

    def _frame(self, inner):
        f = QFrame()
        f.setObjectName("radios")
        f.setStyleSheet("#radios { border: 1px solid #a9bfd6; border-radius: 4px; background: rgba(255,255,255,0.5); }")
        inner.setContentsMargins(8, 3, 8, 3)
        f.setLayout(inner)
        return f

    # -------------------------------------------------------------- modes ---
    def set_mode(self, mode):
        self.e.set_mode(mode)
        (self.sci if mode == "scientific" else self.std).setChecked(True)
        self.sci_panel.setVisible(mode == "scientific")
        if mode == "standard":
            for b in self.base_group.buttons():
                b.setChecked(b.property("base") == "dec")
        self._save(mode=mode)
        self._enable()
        self.refresh()
        self.adjustSize()
        self.resize(self.minimumSizeHint())

    def set_base(self, base):
        self.e.set_base(base)
        self._enable()
        self.refresh()

    def _set_angle(self, a):
        self.e.angle = a
        self._save(angle=a)

    def _enable(self):
        """Only the keys that make sense in this base."""
        radix = self.e.radix
        for d in "0123456789ABCDEF":
            b = self.keys.get("C_hex" if d == "C" else d)
            if b:
                b.setEnabled(DIGITS.index(d) < radix)
        decimal_only = radix == 10
        for k in (".", "Exp", "pi", "sin", "cos", "tan", "ln", "log", "sqrt", "%", "recip"):
            if k in self.keys:
                self.keys[k].setEnabled(decimal_only)
        for w in (self.inv, self.hyp) + tuple(self.angle_group.buttons()):
            w.setEnabled(decimal_only)

    # -------------------------------------------------------------- input ---
    def press(self, key):
        self.e.press(key)
        self.inv.setChecked(self.e.inv)                 # the engine unticks Inv/Hyp after one use
        self.hyp.setChecked(self.e.hyp)
        self.refresh()

    def refresh(self):
        self.display.grouping = self.grouping.isChecked()
        self.display.update()

    def keyPressEvent(self, ev):
        k, t = ev.key(), ev.text()
        mapping = {Qt.Key_Return: "=", Qt.Key_Enter: "=", Qt.Key_Escape: "clear", Qt.Key_Delete: "CE",
                   Qt.Key_Backspace: "back", Qt.Key_F9: "neg"}
        if k in mapping:
            self.press(mapping[k])
        elif t and t.upper() in DIGITS and DIGITS.index(t.upper()) < self.e.radix:
            self.press(t.upper())
        elif t in ("+", "-", "*", "/", "%", ".", ",", "(", ")", "=", "@", "r", "R", "^", "!"):
            self.press({",": ".", "@": "sqrt", "r": "recip", "R": "recip", "^": "x^y", "!": "n!"}.get(t, t))
        else:
            super().keyPressEvent(ev)

    def copy(self):
        QApplication.clipboard().setText(self.e.display())

    def paste(self):
        self.e.paste(QApplication.clipboard().text())
        self.refresh()

    # ----------------------------------------------------------- settings ---
    def _load(self):
        try:
            return json.loads(CONFIG.read_text())
        except (OSError, ValueError):
            return {}

    def _save(self, **kw):
        self.cfg.update(kw)
        try:
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.write_text(json.dumps(self.cfg))
        except OSError:
            pass


def main():
    app = QApplication(sys.argv[:1])
    app.setApplicationName("halcyon-calc")
    app.setApplicationDisplayName("Calculator")
    app.setDesktopFileName("halcyon-calc")
    w = Calculator()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
