# -*- coding: utf-8 -*-
"""app/gui/analyze_tab.py —— 分析页：生成 opencode 指令 + 待跟进清单。"""
from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLabel,
                               QPlainTextEdit, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from pipeline.helpers import common, ingest

from .widgets import SectionTitle, btn, info


class AnalyzeTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)

        head = QHBoxLayout()
        head.addWidget(SectionTitle("交给 opencode 分析"))
        head.addStretch()
        b = btn("刷新", quiet=True, icon_name="refresh")
        b.clicked.connect(self.refresh)
        head.addWidget(b)
        v.addLayout(head)

        row = QHBoxLayout()
        row.addWidget(QLabel("选择人物"))
        self.cb_person = QComboBox()
        row.addWidget(self.cb_person, 1)
        gen = btn("生成并复制分析指令", accent=True, icon_name="copy")
        gen.clicked.connect(self.copy_command)
        row.addWidget(gen)
        v.addLayout(row)

        hint = QLabel("在 opencode（本项目仓库内）中粘贴短指令即可触发人物分析任务书（pipeline/analyze.md）。\n"
                      "任务：读 aliases.md → 已有档案 → 全部记忆 → 归纳画像/策略/变化，每条结论标注 m 序号证据；"
                      "下结论前自动过滤「把推断当事实」的记录。")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        v.addWidget(hint)

        self.prompt = QPlainTextEdit()
        self.prompt.setReadOnly(True)
        self.prompt.setPlaceholderText("生成的指令会显示在这里")
        v.addWidget(self.prompt, 1)

        h2 = QHBoxLayout()
        h2.addWidget(SectionTitle("待跟进事项"))
        h2.addStretch()
        b2 = btn("复制选中条目", quiet=True, icon_name="copy")
        b2.clicked.connect(self.copy_followup)
        h2.addWidget(b2)
        v.addLayout(h2)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["人物", "日期", "待跟进"])
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        v.addWidget(self.tbl, 1)
        self._followups: list[dict] = []

    def refresh(self):
        self._followups = ingest.followups_list()
        rows = [{k: r[k] for k in ("ref", "pseudonym", "date", "text")} for r in self._followups]

        cur = self.cb_person.currentData()
        self.cb_person.blockSignals(True)
        self.cb_person.clear()
        s = ingest.register_summary()
        people = s.get("rows", []) if s.get("ok") else []
        for p in sorted(people, key=lambda x: x["ref"]):
            label = p.get("pseudonym") or p["ref"]
            self.cb_person.addItem(f"{label}（{p['ref']}）", p["ref"])
        if cur:
            idx = self.cb_person.findData(cur)
            if idx >= 0:
                self.cb_person.setCurrentIndex(idx)
        self.cb_person.blockSignals(False)

        self.tbl.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(row["pseudonym"]))
            self.tbl.setItem(r, 1, QTableWidgetItem(row["date"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(row["text"]))

        self.render_prompt()

    def current_ref(self) -> str | None:
        return self.cb_person.currentData()

    def render_prompt(self):
        ref = self.current_ref()
        if not ref:
            self.prompt.setPlainText("请先录入人物后回到本页")
            return
        s = ingest.register_summary()
        pseudo = ""
        if s.get("ok"):
            for p in s["rows"]:
                if p["ref"] == ref:
                    pseudo = p.get("pseudonym", "")
        name = pseudo or ref
        self.prompt.setPlainText(
            f"分析{name}\n\n"
            f"（对应短指令：在 opencode 中执行「分析 {name}」；"
            f"任务书见 pipeline/analyze.md；输入为 aliases.md、people/{ref}.md、全部 memories）")

    def copy_command(self):
        text = self.prompt.toPlainText().strip()
        if not text:
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text.splitlines()[0])
        info("已复制", f"指令「{text.splitlines()[0]}」已复制到剪贴板。\n\n请在 opencode 项目中粘贴执行。", self)

    def copy_followup(self):
        r = self.tbl.currentRow()
        if 0 <= r < len(self._followups):
            row = self._followups[r]
            line = f"[{row['date']}] {row['pseudonym']}：{row['text']}"
        elif len(self._followups) == 1:
            row = self._followups[0]
            line = f"[{row['date']}] {row['pseudonym']}：{row['text']}"
        else:
            info("提示", "请先在表格中选择一条待跟进事项", self)
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(line)
        info("已复制", line, self)