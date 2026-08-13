#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/helpers/common.py —— 数据层共用工具

仓库根目录与全部数据路径的唯一解析点：
  - 脚本运行（python pipeline/helpers/*.py）→ 相对本文件定位仓库根；
  - 打包运行（personal-wiki.exe）→ 以可执行文件所在目录为仓库根；
  - 环境变量 PW_ROOT 可显式覆盖（便于把 exe 与数据分离）。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("PW_ROOT")
    if env:
        return Path(env).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


ROOT = repo_root()
DATA = ROOT / "data"
MEMORIES = DATA / "memories"
PRIVATE = DATA / "private"
PEOPLE = DATA / "people"
META = DATA / "meta"
ALIASES = DATA / "aliases.md"
REGISTER = META / "register.json"
PSEUDONYMS = META / "pseudonyms.md"
SCHEMA = ROOT / "input" / "form-schema.json"
TEMPLATES = ROOT / "dashboard" / "templates"
ASSETS = ROOT / "dashboard" / "assets"
OUTPUT = ROOT / "dashboard" / "output"


def load_json(p: Path) -> dict:
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def write_json_smart(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.move(str(tmp), str(p))


def append_line(p: Path, text: str) -> None:
    if p.exists() and p.stat().st_size > 0:
        p.open("a", encoding="utf-8").write("\n" + text)
    else:
        p.open("w", encoding="utf-8").write(text)


def read(p: Path) -> str:
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def parse_aliases(p: Path) -> dict[str, str]:
    mapping = {}
    for line in read(p).splitlines():
        m = re.match(r"^\s*(.+?)\s*(?:\(.*\))?\s*→\s*([a-zA-Z0-9_-]+)\s*$", line)
        if m:
            mapping[m.group(1).strip()] = m.group(2).strip()
    return mapping


def parse_pseudonyms(p: Path) -> dict[str, str]:
    mapping = {}
    for line in read(p).splitlines():
        m = re.match(r"^\s*([a-zA-Z0-9_-]+)\s*→\s*(.+?)\s*$", line)
        if m:
            mapping[m.group(1).strip()] = m.group(2).strip()
    return mapping


def pinyin_ref(name: str) -> str | None:
    try:
        from pypinyin import lazy_pinyin  # type: ignore
        return "".join(lazy_pinyin(name)).lower().strip().replace(" ", "")
    except Exception:
        return None


def infer_ref(name: str) -> str | None:
    ready = re.sub(r"\s+", "", name.strip())
    if re.fullmatch(r"[A-Za-z0-9_-]+", ready):
        return ready.lower()
    return pinyin_ref(ready)


def setup_stdout_utf8() -> None:
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass