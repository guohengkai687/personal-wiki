# -*- coding: utf-8 -*-
"""app/gui/avatars.py —— 人物形象图标。

当前阶段用「性别小人」占位（男蓝 / 女粉 / 未知灰）。
后续迭代：按性格画像（大五人格等）绘制数字人，仅需替换 avatar_icon 内部实现，
调用方（概览列表）无感。
"""
from __future__ import annotations

from PySide6.QtGui import QIcon

from .assets import colored_icon

GENDER_COLORS = {"male": "#3B82F6", "female": "#EC4899", "unknown": "#94A3B8"}


def avatar_icon(gender: str | None) -> QIcon:
    """按性别返回形象图标。"""
    g = (gender or "").strip().lower()
    if g not in GENDER_COLORS:
        g = "unknown"
    if g == "unknown":
        return colored_icon("user-question", GENDER_COLORS["unknown"])
    icon_name = "gender-male" if g == "male" else "gender-female"
    return colored_icon(icon_name, GENDER_COLORS[g])