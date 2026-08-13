# -*- coding: utf-8 -*-
"""app/gui/widgets.py —— 通用控件与工具。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from .assets import colored_icon, icon
from .style import C


def btn(text: str, accent: bool = False, danger: bool = False,
        quiet: bool = False, icon_name: str | None = None) -> QPushButton:
    b = QPushButton(text)
    if icon_name:
        b.setIcon(icon(icon_name))
    if accent:
        b.setProperty("accent", True)
    if danger:
        b.setProperty("danger", True)
    if quiet:
        b.setProperty("quiet", True)
    return b


class StatCard(QFrame):
    """概览数字卡片：图标 + 数值 + 标签。"""

    def __init__(self, title: str, icon_name: str, color: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setMinimumHeight(92)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)

        ic = QLabel()
        ic.setPixmap(colored_icon(icon_name, color).pixmap(30, 30))
        right = QVBoxLayout()
        right.setSpacing(2)
        self.value_label = QLabel("–")
        self.value_label.setObjectName("StatValue")
        self.value_label.setStyleSheet(f"color: {color};")
        cap = QLabel(title)
        cap.setObjectName("StatLabel")
        right.addWidget(self.value_label)
        right.addWidget(cap)
        lay.addWidget(ic, 0, Qt.AlignVCenter)
        lay.addLayout(right, 1)

    def set_value(self, value: object) -> None:
        self.value_label.setText(str(value))


class SectionTitle(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("SectionTitle")


class FormRow(QWidget):
    """一行：左侧必填标签 + 右侧控件。"""

    def __init__(self, label: str, control: QWidget, required: bool = False,
                 hint: str = ""):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(10)
        lab = QLabel(label)
        lab.setObjectName("FormLabel")
        if required:
            lab.setStyleSheet(f"color: {C['danger']}; font-weight: 600;")
        lab.setMinimumWidth(110)
        lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(control)
        if hint:
            h = QLabel(hint)
            h.setObjectName("Hint")
            col.addWidget(h)
        lay.addWidget(lab)
        lay.addLayout(col, 1)


def info(title: str, text: str, parent: QWidget | None = None) -> None:
    QMessageBox.information(parent, title, text)


def warn(title: str, text: str, parent: QWidget | None = None) -> None:
    QMessageBox.warning(parent, title, text)


def ask_yes(parent: QWidget | None, title: str, text: str) -> bool:
    return QMessageBox.question(parent, title, text,
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) == QMessageBox.Yes


class TextDialog(QDialog):
    """展示多行文本（档案内容 / 结果信息），可复制。"""

    def __init__(self, title: str, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 560)
        from PySide6.QtWidgets import QPlainTextEdit

        edit = QPlainTextEdit(text)
        edit.setReadOnly(True)
        edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        lay = QVBoxLayout(self)
        lay.addWidget(edit)
        row = QHBoxLayout()
        row.addStretch()
        close = btn("关闭")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)


def open_path(path: Path) -> None:
    import os
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except OSError as e:  # noqa: PERF203
        warn("无法打开", str(e))


def toggle_check(text: str, checked: bool = False) -> QCheckBox:
    cb = QCheckBox(text)
    cb.setChecked(checked)
    return cb
