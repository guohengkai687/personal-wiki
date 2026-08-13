# -*- coding: utf-8 -*-
"""app/gui/assets.py —— 素材访问（图标 / 字体，随 app/assets 打包）。"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication


def _base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "app" / "assets"
    return Path(__file__).resolve().parents[1] / "assets"


BASE = _base()
ICONS = BASE / "icons"
FONTS = BASE / "fonts"


def icon_path(name: str) -> str:
    return str(ICONS / f"{name}.svg")


def icon(name: str) -> QIcon:
    return QIcon(icon_path(name))


def colored_icon(name: str, color: str) -> QIcon:
    """读取 Tabler SVG 并给 currentColor 着色。"""
    p = ICONS / f"{name}.svg"
    if not p.exists():
        return QIcon()
    svg = p.read_text(encoding="utf-8").replace("currentColor", color)
    pm = QPixmap()
    pm.loadFromData(svg.encode("utf-8"), "svg")
    return QIcon(pm)


def load_fonts() -> list[str]:
    """注册 bundle 字体，返回已加载的字体族列表。"""
    from PySide6.QtGui import QFontDatabase

    fams: list[str] = []
    for f in sorted(FONTS.glob("*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(f))
        if fid >= 0:
            fams.extend(QFontDatabase.applicationFontFamilies(fid))
    return fams


def pick_family(fams: list[str]) -> str:
    """中文优先 Noto Sans SC，其次系统微软雅黑。"""
    if "Noto Sans SC" in fams:
        return "Noto Sans SC"
    return "Microsoft YaHei"


def apply_theme(app: QApplication) -> None:
    from PySide6.QtGui import QFont

    from .style import build_qss

    fams = load_fonts()
    family = pick_family(fams)
    app.setFont(QFont(family, 10))
    app.setStyleSheet(build_qss(family))