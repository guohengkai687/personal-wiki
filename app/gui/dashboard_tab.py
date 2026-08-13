# -*- coding: utf-8 -*-
"""app/gui/dashboard_tab.py —— 看板页：生成静态看板 + 打开。"""
from __future__ import annotations

import datetime as dt

from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout,
                               QWidget)

from pipeline.helpers import build, common

from .widgets import SectionTitle, StatCard, btn, info, open_path, warn


class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        head = QHBoxLayout()
        head.addWidget(SectionTitle("展示看板"))
        head.addStretch()
        self.b_ref = btn("刷新", quiet=True, icon_name="refresh")
        self.b_ref.clicked.connect(self.refresh)
        head.addWidget(self.b_ref)
        v.addLayout(head)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.c_status = StatCard("状态", "eye", "#4F46E5")
        self.c_size = StatCard("体积", "database", "#7C3AED")
        self.c_built = StatCard("生成时间", "calendar", "#16A34A")
        for c in (self.c_status, self.c_size, self.c_built):
            cards.addWidget(c)
        v.addLayout(cards)

        self.out_label = QLabel()
        self.out_label.setObjectName("Mono")
        self.out_label.setWordWrap(True)
        v.addWidget(self.out_label)

        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("生成结果将显示在这里")
        v.addWidget(self.result, 1)

        row = QHBoxLayout()
        self.b_build = btn("生成 / 重新生成看板", accent=True, icon_name="chart-bar")
        self.b_build.clicked.connect(self.on_build)
        self.b_open = btn("在浏览器打开看板", icon_name="external-link")
        self.b_open.clicked.connect(self.open_dashboard)
        self.b_dir = btn("打开输出目录", quiet=True, icon_name="folder-open")
        self.b_dir.clicked.connect(lambda: open_path(common.OUTPUT))
        row.addWidget(self.b_build)
        row.addWidget(self.b_open)
        row.addWidget(self.b_dir)
        row.addStretch()
        v.addLayout(row)

    def refresh(self):
        out = common.OUTPUT / "index.html"
        if out.exists():
            st = out.stat()
            self.c_status.set_value("已生成")
            self.c_size.set_value(f"{st.st_size // 1024} KB")
            self.c_built.set_value(dt.datetime.fromtimestamp(
                st.st_mtime).strftime("%Y-%m-%d %H:%M"))
        else:
            self.c_status.set_value("未生成")
            self.c_size.set_value("–")
            self.c_built.set_value("–")
        self.out_label.setText(f"输出 → {out}（脱敏为假名，离线可打开，不入库）")
        self.b_open.setEnabled(out.exists())

    def on_build(self):
        ok, msg = build.build_dashboard()
        self.refresh()
        if not ok:
            warn("生成失败", msg, self)
        else:
            info("生成看板", msg, self)
        self.result.setPlainText(msg)

    def open_dashboard(self):
        out = common.OUTPUT / "index.html"
        if not out.exists():
            warn("尚未生成", "请先「生成看板」", self)
            return
        open_path(out)
        self.result.setPlainText(f"已在系统浏览器打开：{out}")