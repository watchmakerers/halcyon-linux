"""Halcyon Backup and Restore Center, after Windows Vista's.

    halcyon-backup           the window
    halcyon-backup --run     make a backup now with the saved settings (the schedule runs this)
"""
import datetime
import os
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QDir, QObject, QSortFilterProxyModel, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFileSystemModel, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
                               QRadioButton, QSpinBox, QTimeEdit, QTreeView, QVBoxLayout, QWidget, QWizard,
                               QWizardPage)

from . import core

APP = "Backup and Restore Center"
TITLE = "#1e3287"
GREEN = "#2a7d12"
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


def short_path(p, keep=3):
    """/run/media/me/My Passport -> .../media/me/My Passport, so status lines stay one line."""
    parts = Path(p).parts
    return p if len(parts) <= keep + 1 else "\u2026/" + "/".join(parts[-keep:])


def when(dt):
    return dt.strftime("%-m/%-d/%Y %-I:%M %p") if dt else "Never"


class Bus(QObject):
    progress = Signal(int, str)
    done = Signal(bool, str)
    sizes = Signal(str, str)


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
        p.setPen(QColor("#7f9db9"))
        p.setBrush(QColor(255, 255, 255, 240))
        box = self.rect().adjusted(10, 8, -10, -8)
        p.drawRect(box)
        p.drawPixmap(box.x() + 5, box.y() + 4, QIcon.fromTheme("document-save").pixmap(16))
        p.setPen(QColor(TEXT))
        p.drawText(box.adjusted(28, 0, 0, 0), Qt.AlignVCenter,
                   "Control Panel  ▸  System and Maintenance  ▸  Backup and Restore Center")


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


class Section(QFrame):
    """A big task block: icon, green heading, text, status lines and a button."""
    def __init__(self, icon, title, text, button, on_click):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(16)
        ic = QLabel()
        ic.setPixmap(QIcon.fromTheme(icon, QIcon.fromTheme("document-save")).pixmap(48))
        ic.setAlignment(Qt.AlignTop)
        lay.addWidget(ic)
        col = QVBoxLayout()
        col.setSpacing(4)
        h = QLabel(title)
        f = h.font()
        f.setPointSizeF(12)
        h.setFont(f)
        h.setStyleSheet(f"color: {GREEN};")
        col.addWidget(h)
        t = QLabel(text)                 # broken by hand: word-wrapped labels don't grow nested frames
        col.addWidget(t)
        self.status = QLabel()
        self.status.setStyleSheet(f"color: {MUTED};")
        col.addWidget(self.status)
        lay.addLayout(col, 1)
        self.button = QPushButton(QIcon.fromTheme(icon), button)
        self.button.setMinimumWidth(170)
        self.button.clicked.connect(on_click)
        lay.addWidget(self.button, 0, Qt.AlignVCenter)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#fbfdff"))
        g.setColorAt(1, QColor("#eef4fb"))
        p.setPen(QColor("#c5d5e8"))
        p.setBrush(g)
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 5, 5)


# ------------------------------------------------------------------ wizard ---
class WherePage(QWizardPage):
    def __init__(self, cfg):
        super().__init__()
        self.setTitle("Where do you want to save your backup?")
        self.setSubTitle("Use a drive that isn't the one your files are on, like an external hard disk or USB drive, "
                         "so a disk failure can't take both.")
        lay = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setIconSize(QIcon.fromTheme("drive-removable-media").pixmap(32).size())
        lay.addWidget(self.list)
        row = QHBoxLayout()
        pick = QPushButton(QIcon.fromTheme("folder-open"), "Choose another location…")
        pick.clicked.connect(self._pick)
        refresh = QPushButton(QIcon.fromTheme("view-refresh"), "Refresh")
        refresh.clicked.connect(self._fill)
        row.addWidget(pick)
        row.addWidget(refresh)
        row.addStretch(1)
        lay.addLayout(row)
        self.problem = QLabel()
        self.problem.setWordWrap(True)
        self.problem.setStyleSheet("color: #b0231a;")
        lay.addWidget(self.problem)
        self.chosen = cfg.get("destination", "")
        self.list.currentItemChanged.connect(self._changed)
        self._fill()

    def _fill(self):
        self.list.clear()
        paths = []
        for path, name, free, total in core.drives():
            it = QListWidgetItem(QIcon.fromTheme("drive-removable-media"),
                                 f"{name}\n{core.human(free)} free of {core.human(total)}")
            it.setData(Qt.UserRole, path)
            self.list.addItem(it)
            paths.append(path)
        if self.chosen and self.chosen not in paths:
            it = QListWidgetItem(QIcon.fromTheme("folder"), self.chosen)
            it.setData(Qt.UserRole, self.chosen)
            self.list.addItem(it)
        if not self.list.count():
            self.problem.setText("No backup drives are connected. Plug one in and click Refresh, "
                                 "or choose another location.")
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == self.chosen:
                self.list.setCurrentRow(i)

    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, "Choose where to save the backup", self.chosen or "/")
        if d:
            self.chosen = d
            self._fill()

    def _changed(self, cur, prev):
        self.chosen = cur.data(Qt.UserRole) if cur else ""
        ok, msg = core.check_destination(self.chosen) if self.chosen else (False, "")
        self.problem.setText(msg)
        self.completeChanged.emit()

    def isComplete(self):
        return bool(self.chosen) and core.check_destination(self.chosen)[0]


class WhatPage(QWizardPage):
    def __init__(self, cfg):
        super().__init__()
        self.setTitle("Which files do you want to back up?")
        self.setSubTitle("Backups include every file of the kinds you choose in your home folder.")
        lay = QVBoxLayout(self)
        self.boxes = {}
        self.bus = Bus()
        self.bus.sizes.connect(self._size)
        grid = QGridLayout()
        for r, (cid, label, _) in enumerate(core.CATEGORIES):
            b = QCheckBox(label)
            b.setChecked(cid in cfg.get("categories", []))
            b.toggled.connect(self.completeChanged)
            size = QLabel("")
            size.setStyleSheet(f"color: {MUTED};")
            grid.addWidget(b, r, 0)
            grid.addWidget(size, r, 1)
            self.boxes[cid] = (b, size)
        grid.setColumnStretch(0, 1)
        lay.addLayout(grid)
        note = QLabel("Caches, the Trash and games' downloaded files are never backed up.")
        note.setStyleSheet(f"color: {MUTED};")
        lay.addWidget(note)
        lay.addStretch(1)

        def measure():
            for cid, _, _ in core.CATEGORIES:
                if cid != "home":
                    p = core.category_path(cid)
                    self.bus.sizes.emit(cid, core.human(core.folder_size(p)) if p.exists() else "Not found")
        threading.Thread(target=measure, daemon=True).start()

    def _size(self, cid, text):
        self.boxes[cid][1].setText(text)

    def chosen(self):
        return [cid for cid, (b, _) in self.boxes.items() if b.isChecked()]

    def isComplete(self):
        return bool(self.chosen())


class WhenPage(QWizardPage):
    def __init__(self, cfg):
        super().__init__()
        self.setTitle("How often do you want to back up?")
        self.setSubTitle("New and changed files are added to your backup on this schedule. "
                         "Unchanged files don't take up extra space.")
        s = cfg["schedule"]
        lay = QVBoxLayout(self)
        self.auto = QCheckBox("Back up automatically")
        self.auto.setChecked(bool(s.get("enabled", True)) or not cfg.get("destination"))
        lay.addWidget(self.auto)
        grid = QGridLayout()
        self.how = QComboBox()
        self.how.addItems(["Daily", "Weekly", "Monthly"])
        self.how.setCurrentIndex(["daily", "weekly", "monthly"].index(s.get("how", "weekly")))
        self.weekday = QComboBox()
        self.weekday.addItems(core.DAY_NAMES)
        self.weekday.setCurrentIndex(int(s.get("day", 6)) % 7 if s.get("how") != "monthly" else 6)
        self.monthday = QSpinBox()
        self.monthday.setRange(1, 28)
        self.monthday.setValue(int(s.get("day", 1)) if s.get("how") == "monthly" else 1)
        self.time = QTimeEdit(QTime.fromString(s.get("time", "19:00"), "H:mm"))
        self.time.setDisplayFormat("h:mm AP")
        self.day_label = QLabel("What day:")
        for r, (k, w) in enumerate((("How often:", self.how), (self.day_label, None), ("What time:", self.time))):
            grid.addWidget(QLabel(k) if isinstance(k, str) else k, r, 0)
            if w:
                grid.addWidget(w, r, 1)
        day = QHBoxLayout()
        day.addWidget(self.weekday)
        day.addWidget(self.monthday)
        grid.addLayout(day, 1, 1)
        grid.setColumnStretch(2, 1)
        lay.addLayout(grid)
        self.keep = QSpinBox()
        self.keep.setRange(1, 999)
        self.keep.setValue(int(cfg.get("keep", 30)))
        kr = QHBoxLayout()
        kr.addWidget(QLabel("Keep the newest"))
        kr.addWidget(self.keep)
        kr.addWidget(QLabel("backups (older ones are removed to save space)"))
        kr.addStretch(1)
        lay.addSpacing(10)
        lay.addLayout(kr)
        lay.addStretch(1)
        self.how.currentIndexChanged.connect(self._sync)
        self.auto.toggled.connect(self._sync)
        self._sync()

    def _sync(self):
        on = self.auto.isChecked()
        how = self.how.currentIndex()
        for w in (self.how, self.weekday, self.monthday, self.time):
            w.setEnabled(on)
        self.weekday.setVisible(how == 1)
        self.monthday.setVisible(how == 2)
        self.day_label.setVisible(how != 0)

    def schedule(self):
        how = ["daily", "weekly", "monthly"][self.how.currentIndex()]
        day = self.weekday.currentIndex() if how == "weekly" else self.monthday.value()
        return {"enabled": self.auto.isChecked(), "how": how, "day": day, "time": self.time.time().toString("HH:mm")}


class ReviewPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Review your backup settings")
        lay = QVBoxLayout(self)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.RichText)
        lay.addWidget(self.text)
        self.now = QCheckBox("Back up my files now")
        self.now.setChecked(True)
        lay.addWidget(self.now)
        lay.addStretch(1)

    def initializePage(self):
        w = self.wizard()
        labels = dict((c, l) for c, l, _ in core.CATEGORIES)
        self.text.setText(
            f"<p><b>Backup location:</b> {esc(w.where.chosen)}</p>"
            f"<p><b>Files:</b> {esc(', '.join(labels[c] for c in w.what.chosen()))}</p>"
            f"<p><b>Schedule:</b> {esc(core.describe_schedule(w.when.schedule()))}</p>"
            f"<p><b>Keep:</b> the newest {w.when.keep.value()} backups</p>")


class BackupWizard(QWizard):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.setWindowTitle("Back Up Files")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(620, 480)
        self.where, self.what, self.when, self.review = WherePage(cfg), WhatPage(cfg), WhenPage(cfg), ReviewPage()
        for p in (self.where, self.what, self.when, self.review):
            self.addPage(p)
        self.setButtonText(QWizard.FinishButton, "Save settings")

    def settings(self, cfg):
        out = dict(cfg)
        out.update(destination=self.where.chosen, categories=self.what.chosen(), schedule=self.when.schedule(),
                   keep=self.when.keep.value())
        return out


# ------------------------------------------------------------ run / restore ---
class RunDialog(QDialog):
    """Backs up now, showing progress; Stop cancels and removes the unfinished backup."""
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.setWindowTitle("Backing up files")
        self.setMinimumWidth(460)
        self.cancelled = False
        self.ok = False
        lay = QVBoxLayout(self)
        t = QLabel("Backing up your files…")
        t.setStyleSheet(f"color: {TITLE}; font-size: 12pt;")
        lay.addWidget(t)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        lay.addWidget(self.bar)
        self.status = QLabel("Preparing…")
        self.status.setStyleSheet(f"color: {MUTED};")
        lay.addWidget(self.status)
        self.btn = QDialogButtonBox()
        self.stop = self.btn.addButton("Stop backup", QDialogButtonBox.RejectRole)
        self.stop.clicked.connect(self._stop)
        lay.addWidget(self.btn)
        self.bus = Bus()
        self.bus.progress.connect(lambda p, s: (self.bar.setValue(p), self.status.setText(s)))
        self.bus.done.connect(self._done)
        threading.Thread(target=lambda: self.bus.done.emit(*core.run_backup(
            cfg, progress=self.bus.progress.emit, stop=lambda: self.cancelled)), daemon=True).start()

    def _stop(self):
        self.cancelled = True
        self.stop.setEnabled(False)
        self.status.setText("Stopping…")

    def reject(self):                  # Esc / close button = Stop, never leave rsync running unseen
        if not self.btn.property("finished"):
            self._stop()
        else:
            super().reject()

    def _done(self, ok, msg):
        self.ok = ok
        self.btn.setProperty("finished", True)
        self.bar.setValue(100 if ok else self.bar.value())
        self.status.setText(msg)
        self.status.setStyleSheet(f"color: {GREEN if ok else '#b0231a'};")
        self.btn.clear()
        self.btn.addButton(QDialogButtonBox.Close).clicked.connect(self.accept)


class RestoreDialog(QDialog):
    """Pick a backup by date, select files and folders, restore them."""
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.setWindowTitle("Restore Files")
        self.resize(720, 520)
        self.backups = core.list_backups(cfg["destination"]) if cfg.get("destination") else []
        lay = QVBoxLayout(self)
        t = QLabel("Restore files and folders from a backup")
        t.setStyleSheet(f"color: {TITLE}; font-size: 12pt;")
        lay.addWidget(t)
        row = QHBoxLayout()
        row.addWidget(QLabel("Backup from:"))
        self.dates = QComboBox()
        for dt, path in self.backups:
            self.dates.addItem(when(dt), str(path))
        row.addWidget(self.dates, 1)
        lay.addLayout(row)
        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setColumnWidth(0, 340)
        self.tree.setSortingEnabled(True)
        lay.addWidget(self.tree, 1)
        hint = QLabel("Select the files and folders to restore. Hold Ctrl to select several.")
        hint.setStyleSheet(f"color: {MUTED};")
        lay.addWidget(hint)
        grp = QHBoxLayout()
        self.original = QRadioButton("In their original location")
        self.original.setChecked(True)
        self.other = QRadioButton("In another folder…")
        grp.addWidget(QLabel("Restore:"))
        grp.addWidget(self.original)
        grp.addWidget(self.other)
        grp.addStretch(1)
        lay.addLayout(grp)
        bb = QDialogButtonBox()
        self.go = bb.addButton("Restore", QDialogButtonBox.AcceptRole)
        bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(self._restore)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.dates.currentIndexChanged.connect(self._show)
        if self.backups:
            self._show()
        else:
            self.go.setEnabled(False)
            hint.setText("No backups were found. Is the backup drive connected?")

    def _show(self):
        path = self.dates.currentData()
        self.tree.setRootIndex(self.model.setRootPath(path))

    def _restore(self):
        items = sorted({self.model.filePath(i) for i in self.tree.selectionModel().selectedRows(0)})
        if not items:
            QMessageBox.information(self, "Restore Files", "Select the files or folders you want to restore.")
            return
        target = None
        if self.other.isChecked():
            target = QFileDialog.getExistingDirectory(self, "Restore to")
            if not target:
                return
        ans = QMessageBox.question(
            self, "Restore Files", "If a file with the same name is already there, replace it with the backed-up "
            "copy?\n\nYes: replace it.   No: keep the file that's there now.",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
        if ans == QMessageBox.Cancel:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok, msg = core.restore(items, self.dates.currentData(), target, overwrite=ans == QMessageBox.Yes)
        finally:
            QApplication.restoreOverrideCursor()
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Restore Files", msg)
        if ok:
            self.accept()


# ------------------------------------------------------------------ window ---
class Center(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setWindowIcon(QIcon.fromTheme("document-save"))
        self.resize(960, 620)
        self.cfg = core.load()
        self.tool = core.snapshot_tool()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(Header())
        body = QHBoxLayout()
        body.setSpacing(0)
        outer.addLayout(body, 1)
        pane = TaskPane()
        pane.lay.addWidget(QLabel("<b>Tasks</b>"))
        pane.lay.addWidget(link("Change backup settings", self.setup))
        pane.lay.addWidget(link("Back up now", self.backup_now))
        pane.lay.addWidget(link("Restore files", self.restore))
        if self.tool:
            pane.lay.addWidget(link("Create a restore point", self.restore_point))
        pane.lay.addWidget(link("Open the backup location", self.open_location))
        pane.lay.addStretch(1)
        body.addWidget(pane)

        page = QWidget()
        page.setObjectName("page")
        page.setStyleSheet("#page { background: white; }")
        body.addWidget(page, 1)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 18, 26, 18)
        lay.setSpacing(12)
        t = QLabel("Protect your files and computer by backing them up")
        f = t.font()
        f.setPointSizeF(15)
        t.setFont(f)
        t.setStyleSheet(f"color: {TITLE};")
        lay.addWidget(t)
        self.backup_box = Section("document-save", "Back up files",
                                  "Make copies of your pictures, music, documents and e-mail on another\n"
                                  "drive, so you can get them back if something happens to this computer.",
                                  "Back up files", self.backup_clicked)
        lay.addWidget(self.backup_box)
        self.restore_box = Section("document-revert", "Restore files",
                                   "Bring back files and folders from a backup, either where they were\n"
                                   "or somewhere else.", "Restore files", self.restore)
        lay.addWidget(self.restore_box)
        self.point_box = Section("system-software-update", "Restore points",
                                 "A restore point records the system so you can undo changes, such as\n"
                                 "an update that went wrong. It doesn't include your personal files.",
                                 "Create a restore point", self.restore_point)
        lay.addWidget(self.point_box)
        lay.addStretch(1)
        self.refresh()

    def refresh(self):
        c = self.cfg
        dest = c.get("destination")
        if not dest:
            self.backup_box.status.setText("Backups haven't been set up yet.")
            self.backup_box.button.setText("Set up backup")
            self.restore_box.status.setText("")
        else:
            backups = core.list_backups(dest)
            available = Path(dest).is_dir()
            last = backups[0][0] if backups else None
            nxt = core.next_run() if c["schedule"].get("enabled") else ""
            lines = [f"Last successful backup: {when(last)}",
                     f"Next backup: {nxt or core.describe_schedule(c['schedule'])}",
                     f"Backup location: {short_path(dest)}" + ("" if available else "  (not connected)")]
            self.backup_box.status.setText("\n".join(lines))
            self.backup_box.button.setText("Back up files")
            self.restore_box.status.setText(f"{len(backups)} backup{'s' if len(backups) != 1 else ''} available"
                                            if available else "Connect the backup drive to restore files.")
        if self.tool:
            snaps = core.list_snapshots(self.tool)
            self.point_box.status.setText(f"Uses {self.tool}. " + (f"Latest: {snaps[0][0]}" if snaps else ""))
        else:
            self.point_box.status.setText("Restore points need Snapper or Timeshift, which aren't installed.")
            self.point_box.button.setEnabled(False)

    def backup_clicked(self):
        if self.cfg.get("destination"):
            self.backup_now()
        else:
            self.setup()

    def setup(self):
        w = BackupWizard(self, self.cfg)
        if w.exec() != QDialog.Accepted:
            return
        self.cfg = w.settings(self.cfg)
        core.save(self.cfg)
        err = core.apply_schedule(self.cfg["schedule"])
        if err:
            QMessageBox.warning(self, APP, "The schedule couldn't be turned on:\n\n" + err)
        self.refresh()
        if w.review.now.isChecked():
            self.backup_now()

    def backup_now(self):
        if not self.cfg.get("destination"):
            return self.setup()
        ok, msg = core.check_destination(self.cfg["destination"])
        if not ok:
            QMessageBox.warning(self, APP, msg)
            return
        RunDialog(self, self.cfg).exec()
        self.refresh()

    def restore(self):
        if not self.cfg.get("destination"):
            QMessageBox.information(self, APP, "There are no backups yet. Set up a backup first.")
            return
        RestoreDialog(self, self.cfg).exec()

    def restore_point(self):
        cmd = core.create_snapshot_cmd(self.tool)
        if not cmd:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
        finally:
            QApplication.restoreOverrideCursor()
        if r.returncode == 0:
            QMessageBox.information(self, APP, "The restore point was created.")
        elif r.returncode not in (126, 127):          # 126/127: the password prompt was cancelled
            QMessageBox.warning(self, APP, "The restore point couldn't be created.\n\n" + r.stderr[-500:])
        self.refresh()

    def open_location(self):
        dest = self.cfg.get("destination")
        if dest:
            root = core.backup_root(dest)
            subprocess.Popen(["xdg-open", str(root if root.is_dir() else dest)], start_new_session=True)


def run_scheduled():
    """--run: one backup with the saved settings, reported as a notification."""
    cfg = core.load()

    def notify(title, body, icon):
        try:
            subprocess.run(["notify-send", "-a", APP, "-i", icon, title, body], timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
    if not cfg.get("destination"):
        return 1
    ok, msg = core.run_backup(cfg)
    if ok:
        notify("Backup complete", msg, "document-save")
    else:
        notify("Backup didn't run", msg, "dialog-warning")
    return 0 if ok else 1


def icon_theme_fallback():
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
    if "--run" in sys.argv:
        return run_scheduled()
    app = QApplication(sys.argv[:1])
    icon_theme_fallback()
    app.setApplicationName("halcyon-backup")
    app.setApplicationDisplayName(APP)
    app.setDesktopFileName("halcyon-backup")
    w = Center()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
