# -*- coding: utf-8 -*-
"""app/gui/style.py —— 全局配色与 QSS 样式（现代浅色、靛蓝点缀）。"""
from __future__ import annotations

PALETTE = {
    "bg": "#F4F6FB",
    "card": "#FFFFFF",
    "border": "#E5E9F2",
    "text": "#1E293B",
    "muted": "#64748B",
    "accent": "#4F46E5",
    "accent2": "#7C3AED",
    "ok": "#16A34A",
    "warn": "#D97706",
    "danger": "#DC2626",
}
C = PALETTE


def build_qss(font_family: str) -> str:
    return f"""
* {{ font-family: "{font_family}"; }}
QMainWindow, QDialog {{ background: {C["bg"]}; }}
QWidget {{ color: {C["text"]}; font-size: 13px; }}

/* ---------- 顶部标签页 ---------- */
QTabWidget::pane {{ border: none; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
  background: transparent; color: {C["muted"]};
  padding: 9px 16px; margin-right: 4px;
  border: none; border-radius: 10px; font-size: 13px;
}}
QTabBar::tab:selected {{ background: {C["accent"]}; color: white; font-weight: 600; }}
QTabBar::tab:hover:!selected {{ background: #E7EAF6; color: {C["text"]}; }}

/* ---------- 标题 ---------- */
QLabel#AppTitle {{ font-size: 17px; font-weight: 700; color: {C["text"]}; }}
QLabel#AppSub {{ font-size: 11px; color: {C["muted"]}; }}
QLabel#SectionTitle {{ font-size: 14px; font-weight: 700; color: {C["text"]}; }}
QLabel#Hint {{ font-size: 11px; color: {C["muted"]}; }}
QLabel#Mono {{ font-family: "Consolas"; font-size: 12px; color: {C["muted"]}; }}

/* ---------- 卡片 ---------- */
QFrame#StatCard {{
  background: {C["card"]}; border: 1px solid {C["border"]};
  border-radius: 12px;
}}
QLabel#StatValue {{ font-size: 24px; font-weight: 800; }}
QLabel#StatLabel {{ font-size: 12px; color: {C["muted"]}; }}

QFrame#Panel {{
  background: {C["card"]}; border: 1px solid {C["border"]};
  border-radius: 12px;
}}

/* ---------- 分组框 ---------- */
QGroupBox {{
  background: {C["card"]}; border: 1px solid {C["border"]};
  border-radius: 12px; margin-top: 10px; padding-top: 12px;
  font-weight: 700; font-size: 13px;
}}
QGroupBox::title {{
  subcontrol-origin: margin; left: 12px; padding: 0 6px;
  color: {C["accent"]};
}}

/* ---------- 输入控件 ---------- */
QLineEdit, QPlainTextEdit, QTextEdit, QDateTimeEdit, QComboBox {{
  background: #FBFCFE; border: 1px solid {C["border"]};
  border-radius: 8px; padding: 6px 9px; selection-background-color: #C7D2FE;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QDateTimeEdit:focus, QComboBox:focus {{ border: 1px solid {C["accent"]}; }}
QLabel[required="true"] {{ font-weight: 600; }}
QLabel[required="true"]::after {{ content: ""; }}
QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled
  {{ background: #F1F5F9; color: #94A3B8; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: white; border: 1px solid {C["border"]}; selection-background-color: #E7EAF6; selection-color: {C["text"]}; }}

/* ---------- 按钮 ---------- */
QPushButton {{
  background: #EDEFF5; border: none; border-radius: 8px;
  padding: 7px 16px; font-weight: 600;
}}
QPushButton:hover {{ background: #DFE3EE; }}
QPushButton:pressed {{ background: #D3D8E6; }}
QPushButton[accent="true"] {{ background: {C["accent"]}; color: white; }}
QPushButton[accent="true"]:hover {{ background: #4338CA; }}
QPushButton[accent="true"]:pressed {{ background: #3730A3; }}
QPushButton[danger="true"] {{ background: #FEE2E2; color: {C["danger"]}; }}
QPushButton[danger="true"]:hover {{ background: #FECACA; }}
QPushButton[quiet="true"] {{ background: transparent; color: {C["accent"]}; }}
QPushButton[quiet="true"]:hover {{ background: #E7EAF6; }}

/* ---------- 表格 ---------- */
QTableWidget {{
  background: {C["card"]}; border: 1px solid {C["border"]};
  border-radius: 10px; gridline-color: transparent;
  selection-background-color: #E7EAF6; selection-color: {C["text"]};
}}
QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid #F1F5F9; }}
QHeaderView::section {{
  background: #F8FAFC; color: {C["muted"]}; font-weight: 600;
  border: none; border-bottom: 1px solid {C["border"]}; padding: 7px 8px;
}}

/* ---------- 滚动区 ---------- */
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #D3D8E6; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- 滑块 ---------- */
QSlider::groove:horizontal {{
  height: 6px; background: #E2E8F0; border-radius: 3px;
}}
QSlider::handle:horizontal {{
  background: {C["accent"]}; width: 16px; height: 16px;
  margin: -5px 0; border-radius: 8px;
}}
QSlider::sub-page:horizontal {{ background: {C["accent"]}; border-radius: 3px; }}

/* ---------- 复选框 ---------- */
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
  width: 17px; height: 17px; border: 1px solid {C["border"]};
  border-radius: 5px; background: #FBFCFE;
}}
QCheckBox::indicator:checked {{
  background: {C["accent"]}; border-color: {C["accent"]};
}}

/* ---------- 状态栏 ---------- */
QStatusBar {{ background: #EDEFF5; color: {C["muted"]}; }}
QStatusBar::item {{ border: none; }}
QMenuBar {{ background: #EDEFF5; }}
QMenuBar::item:selected {{ background: {C["accent"]}; color: white; border-radius: 6px; }}
QMenu {{ background: white; border: 1px solid {C["border"]}; }}
QMenu::item:selected {{ background: {C["accent"]}; color: white; }}
"""