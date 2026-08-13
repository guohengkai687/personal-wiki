# -*- coding: utf-8 -*-
"""app/gui/overview_tab.py —— 概览页：人物卡片统计 + 人物表格。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from pipeline.helpers import common, ingest

from .style import C
from .widgets import (SectionTitle, StatCard, TextDialog, btn, info, open_path,
                      warn)


class OverviewTab(QWidget):
    def __init__(self, switch_tab=None):
        super().__init__()
        self._switch = switch_tab
        self._rows: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        head = QHBoxLayout()
        head.addWidget(SectionTitle("人物概览"))
        head.addStretch()
        ref = btn("刷新", quiet=True, icon_name="refresh")
        ref.clicked.connect(self.refresh)
        head.addWidget(ref)
        outer.addLayout(head)

        # 统计卡片
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.c_people = StatCard("人物", "users", C["accent"])
        self.c_total = StatCard("记忆总数", "database", C["accent2"])
        self.c_month = StatCard("本月新增", "plus", C["ok"])
        self.c_follow = StatCard("待跟进", "clock", C["warn"])
        for c in (self.c_people, self.c_total, self.c_month, self.c_follow):
            cards.addWidget(c)
        outer.addLayout(cards)

        # 表格
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["假名", "ref", "关系", "记忆数", "最近互动", "档案"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(lambda _: self.show_profile())
        outer.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.b_profile = btn("查看档案", icon_name="folder-open")
        self.b_profile.clicked.connect(self.show_profile)
        self.b_people_dir = btn("打开档案目录", quiet=True, icon_name="external-link")
        self.b_people_dir.clicked.connect(lambda: open_path(common.PEOPLE))
        self.b_dash = btn("前往看板页", quiet=True, icon_name="chart-bar")
        self.b_dash.clicked.connect(lambda: self._switch(3))
        bottom.addWidget(self.b_profile)
        bottom.addWidget(self.b_people_dir)
        bottom.addStretch()
        bottom.addWidget(self.b_dash)
        outer.addLayout(bottom)

    def refresh(self):
        s = ingest.register_summary()
        if not s.get("ok"):
            warn("无数据", s.get("msg", ""), self)
            self._clear()
            return
        self.c_people.set_value(s["people_count"])
        self.c_total.set_value(s["total"])
        self.c_month.set_value(s["month_new"])
        self.c_follow.set_value(s["followups"])
        rows = s.get("rows", [])
        self._rows = rows
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            cells = [
                row.get("pseudonym") or "—",
                row.get("ref", ""),
                row.get("relation") or "—",
                row.get("count", 0),
                row.get("last", "—"),
                "有" if row.get("has_profile") else "无",
            ]
            for c, txt in enumerate(cells):
                item = QTableWidgetItem(str(txt))
                if c == 3:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()

    def _clear(self):
        self.table.setRowCount(0)
        self._rows = []

    def current_ref(self) -> str | None:
        r = self.table.currentRow()
        if 0 <= r < len(self._rows):
            return self._rows[r].get("ref")
        return None

    def show_profile(self):
        ref = self.current_ref()
        if not ref:
            info("提示", "请先选择一行人物", self)
            return
        profile = common.PEOPLE / f"{ref}.md"
        if not profile.exists():
            TextDialog("档案不存在", f"暂无 {ref} 的档案。\n请在 opencode 中执行「分析 {ref}」生成。", self).exec()
            return
        TextDialog(f"档案 · {ref}", common.read(profile), self).exec()