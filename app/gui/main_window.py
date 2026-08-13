# -*- coding: utf-8 -*-
"""app/gui/main_window.py —— 主窗口装配 + 启动入口。"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QTabWidget, QVBoxLayout, QWidget)

from pipeline.helpers import common

from .assets import apply_theme, colored_icon, icon
from .analyze_tab import AnalyzeTab
from .dashboard_tab import DashboardTab
from .index_tab import IndexTab
from .overview_tab import OverviewTab
from .record_tab import RecordTab
from .widgets import TextDialog, info


class MainWindow(QMainWindow):
    TAB_INDEX = {"overview": 0, "entry": 1, "index": 2, "dashboard": 3, "analyze": 4}

    def __init__(self, schema: dict, start_tab: str = "overview", action: str | None = None):
        super().__init__()
        self.setWindowTitle("个人关系记忆 · personal-wiki")
        self.setWindowIcon(colored_icon("brain", "#4F46E5"))
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)
        self._pending_action = action
        self._build_ui(schema)
        if start_tab in self.TAB_INDEX:
            self.tabs.setCurrentIndex(self.TAB_INDEX[start_tab])

    def _build_ui(self, schema):
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)

        # 头部
        head = QFrame()
        head.setObjectName("Panel")
        head.setStyleSheet("QFrame#Panel { border: none; border-radius: 0;"
                           " background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                           " stop:0 #EEF2FF, stop:1 #F5F3FF); }")
        head_lay = QHBoxLayout(head)
        head_lay.setContentsMargins(16, 10, 16, 10)
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        t = QLabel("人际记忆 · personal-wiki")
        t.setObjectName("AppTitle")
        sub = QLabel(f"以「文件即数据库 · opencode 即 Agent」方式管理你的人际记忆   数据根: {common.DATA}")
        sub.setObjectName("AppSub")
        title_col.addWidget(t)
        title_col.addWidget(sub)
        head_lay.addLayout(title_col)
        head_lay.addStretch()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.overview = OverviewTab(switch_tab=self.tabs.setCurrentIndex)
        self.record = RecordTab(schema)
        self.index = IndexTab()
        self.dashboard = DashboardTab()
        self.analyze = AnalyzeTab()
        self.tabs.addTab(self.overview, icon("users"), "概览")
        self.tabs.addTab(self.record, icon("plus"), "录入")
        self.tabs.addTab(self.index, icon("database"), "索引")
        self.tabs.addTab(self.dashboard, icon("chart-bar"), "看板")
        self.tabs.addTab(self.analyze, icon("brain"), "分析")

        outer.addLayout(head_lay)
        outer.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        # 状态栏
        bar = self.statusBar()
        bar.showMessage(f"register: {common.REGISTER}")

        # 菜单
        self._build_menu()

        self.record.on_saved = self.overview.refresh

    def _build_menu(self):
        m = self.menuBar()
        help_m = m.addMenu("帮助")
        a_privacy = QAction("隐私说明", self)
        a_privacy.triggered.connect(self._privacy)
        help_m.addAction(a_privacy)
        a_about = QAction("关于", self)
        a_about.triggered.connect(self._about)
        help_m.addAction(a_about)

    def _privacy(self):
        TextDialog("隐私说明",
                   common.read(common.ROOT / "README.md")[:4000] or
                   "见仓库 README.md 的「隐私须知」。\n"
                   "要点：data/ 存真名仅限本机；data/private/ 永不入库；"
                   "看板按假名脱敏且不入库。", self).exec()

    def _about(self):
        TextDialog("关于",
                   "personal-wiki 个人关系记忆与人格分析系统\n\n"
                   f"数据根目录: {common.DATA}\n"
                   "录入 → 校验 → 落盘 data/ → 重算 register → 生成看板 → opencode 分析\n\n"
                   "设计文档见仓库 DESIGN.md。", self).exec()

    # ------------------------------------------------------------------
    def showEvent(self, ev):
        super().showEvent(ev)
        if getattr(self, "_pending_action", None):
            a = self._pending_action
            self._pending_action = None
            if a == "reindex":
                self.tabs.setCurrentWidget(self.index)
                QTimer.singleShot(150, self.index.reindex)
            elif a == "build":
                self.tabs.setCurrentWidget(self.dashboard)
                QTimer.singleShot(150, self.dashboard.on_build)
            elif a == "entry":
                self.tabs.setCurrentWidget(self.record)
            else:
                self.overview.refresh()


def launch(start_tab: str = "overview", action: str | None = None,
           argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName("personal-wiki")
    apply_theme(app)
    schema = common.load_json(common.SCHEMA)
    win = MainWindow(schema, start_tab=start_tab, action=action)
    win.show()
    return app.exec()