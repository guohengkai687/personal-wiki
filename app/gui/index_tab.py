# -*- coding: utf-8 -*-
"""app/gui/index_tab.py —— 索引页：register 状态、月度分布、重算/定位。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from pipeline.helpers import common, ingest

from .widgets import SectionTitle, StatCard, btn, info, open_path, warn


class IndexTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        head = QHBoxLayout()
        head.addWidget(SectionTitle("索引与数据"))
        head.addStretch()
        self.b_go = btn("刷新", quiet=True, icon_name="refresh")
        self.b_go.clicked.connect(self.refresh)
        head.addWidget(self.b_go)
        v.addLayout(head)

        path_lab = QLabel()
        path_lab.setObjectName("Mono")
        path_lab.setWordWrap(True)
        self.path_lab = path_lab
        v.addWidget(path_lab)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.c_total = StatCard("记忆总数", "database", "#7C3AED")
        self.c_people = StatCard("人物", "users", "#4F46E5")
        self.c_month = StatCard("本月新增", "plus", "#16A34A")
        self.c_private = StatCard("私密记忆", "lock", "#D97706")
        self.c_follow = StatCard("待跟进", "clock", "#DC2626")
        for c in (self.c_total, self.c_people, self.c_month, self.c_private, self.c_follow):
            cards.addWidget(c)
        v.addLayout(cards)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["月份", "记忆数"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(self.table, 1)

        row = QHBoxLayout()
        b_reindex = btn("重算索引 register", accent=True, icon_name="refresh")
        b_reindex.clicked.connect(self.reindex)
        b_data = btn("打开数据目录", quiet=True, icon_name="folder-open")
        b_data.clicked.connect(lambda: open_path(common.DATA))
        b_reg = btn("打开 register 目录", quiet=True, icon_name="external-link")
        b_reg.clicked.connect(lambda: open_path(common.META))
        row.addWidget(b_reindex)
        row.addWidget(b_data)
        row.addWidget(b_reg)
        row.addStretch()
        v.addLayout(row)

    def refresh(self):
        s = ingest.register_summary()
        self.path_lab.setText(f"register.json → {common.REGISTER}（生成物，可随时重算）")
        if not s.get("ok"):
            warn("无数据", s.get("msg", ""), self)
            for c in (self.c_total, self.c_people, self.c_month, self.c_private, self.c_follow):
                c.set_value("–")
            self.table.setRowCount(0)
            return
        self.c_total.set_value(s["total"])
        self.c_people.set_value(s["people_count"])
        self.c_month.set_value(s["month_new"])
        self.c_private.set_value(s["private_count"])
        self.c_follow.set_value(s["followups"])
        months = s.get("months", {})
        self.table.setRowCount(len(months))
        for r, (m, n) in enumerate(months.items()):
            self.table.setItem(r, 0, QTableWidgetItem(m))
            it = QTableWidgetItem(str(n))
            it.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 1, it)

    def reindex(self):
        msg = ingest.rebuild_register()
        self.refresh()
        info("重算完成", msg, self)