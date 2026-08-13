#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app/main.py —— personal-wiki 应用入口（打包为 personal-wiki.exe）

默认启动 PySide6 桌面界面（app/gui/）；在源码命令行下带参数时执行传统 CLI：
  - --people / --reindex / --build / --entry / --menu（交互菜单）
  - --pw-root <路径>：指定仓库/数据根目录（等价环境变量 PW_ROOT）
exe 内带以上参数时仍启动界面，并自动定位到对应页 / 执行动作。
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys

from pipeline.helpers import build, common, ingest

EMOTIONS = ["calm", "positive", "tense", "excited", "frustrated", "angry"]


def bootstrap() -> None:
    if sys.argv and "--pw-root" in sys.argv:
        i = sys.argv.index("--pw-root")
        if i + 1 < len(sys.argv):
            os.environ["PW_ROOT"] = os.path.abspath(sys.argv[i + 1])
    root = Path_r()
    if root not in sys.path:
        sys.path.insert(0, str(root))


def Path_r():
    from pathlib import Path
    return Path(__file__).resolve().parents[1]


bootstrap()


# ---------------------------------------------------------------- CLI 工具
def ask(prompt: str, cast=str, default=None, validator=None):
    while True:
        hint = f" [{default}]" if default is not None else ""
        try:
            raw = input(f"{prompt}{hint} > ").strip()
        except EOFError:
            if default is not None:
                print("  （输入流结束，采用默认值）")
                return default
            raise SystemExit("输入流结束，中止。")
        if not raw and default is not None:
            raw = str(default)
        if not raw:
            print("  （不能为空，重新输入）")
            continue
        try:
            val = cast(raw)
        except ValueError:
            print("  （格式不对）")
            continue
        if validator and not validator(val):
            print("  （取值不合法）")
            continue
        return val


def ask_index(prompt: str, options: list) -> str:
    print(prompt)
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    n = ask("选择序号", int, default=1, validator=lambda v: 1 <= v <= len(options))
    return options[n - 1]


def ask_yes(prompt: str, default: bool = False) -> bool:
    d = "y" if default else "n"
    try:
        raw = input(f"{prompt} (y/n, 默认 {d}) > ").strip().lower()
    except EOFError:
        return default
    if not raw:
        return default
    return raw.startswith("y")


def local_offset(d: dt.datetime) -> str:
    off = dt.datetime.now().astimezone().utcoffset()
    total = int(off.total_seconds()) if off else 0
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return f"{sign}{total // 3600:02d}:{total % 3600 // 60:02d}"


# ---------------------------------------------------------------- CLI 命令
def cmd_entry(schema) -> int:
    print("\n=== 录入新记忆 ===")
    aliases = common.parse_aliases(common.ALIASES)

    name = ask("人物（真名）", default="")
    is_new = name not in aliases
    if is_new:
        print(f"  （新人：{name} 不在 aliases.md 中）")
        hint = common.infer_ref(name)
        ref = ask("归一化 ref" + (f"（建议：{hint}）" if hint else ""), default=hint or "")
        pseudo = ask("展示用假名", default=ref or "")
    else:
        ref = aliases[name]
        pseudo = ""
    relation = ask("关系（如：同事-产品线总监）", default="")
    pseudo = pseudo or ref

    date_str = ask("日期时间 YYYY-MM-DD HH:MM", default=dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    try:
        created = dt.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        created = dt.datetime.now()
    sensitive = ask_yes("是否私密记忆（敏感，不进 git）", default=False)

    scene_type = ask_index("场景类型", schema["scene"]["type"]["options"])
    record_type = ask_index("记录类型", schema["record_type"]["options"])
    location = input("地点（可选） > ").strip()
    context = ask("场景说明", default="")
    situation = ask("情境 S（客观描述背景）", default="")
    quote = input("原话引用 Q（可选，可粘贴） > ").strip()
    action = input("行动 A（可选） > ").strip()
    if not quote and not action:
        print("  （原话与行动至少其一，请补）")
        action = ask("行动 A", default="")
    result = input("结果 R（可选） > ").strip()

    demeanor = {}
    for dim in schema["observation"]["demeanor"]:
        v = ask(f"行为标尺 {dim['label']}（1={dim['low']} … 5={dim['high']}）",
                int, default=3, validator=lambda x: 1 <= x <= 5)
        demeanor[dim["key"]] = v
    emotion = ask_index("情绪状态", EMOTIONS)
    notes = input("补充观察（可选） > ").strip()

    strengths = ask("优点（依据观察，避免空泛词）", default="")
    weaknesses = input("弱点（可选） > ").strip()
    summary = ask("总结（一句话）", default="")
    tags = [t.strip() for t in input("标签（逗号分隔） > ").split(",") if t.strip()]
    follow_up = input("待跟进事项（可选） > ").strip()
    related = [r.strip() for r in input("关联人物 ref（逗号分隔，可选） > ").split(",") if r.strip()]

    staple = created.strftime("%Y%m%d-H%H%M")
    rec = {
        "id": staple + ("-PRIVATE" if sensitive else ""),
        "schema_version": schema.get("schema_version", 1),
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%S") + local_offset(created),
        "person": {"name": name, "ref": (ref if not is_new else ""),
                   "relation": relation,
                   "pseudonym": (pseudo if is_new and not sensitive else "")},
        "scene": {"type": scene_type, "location": location, "context": context},
        "record_type": record_type,
        "subject": {"situation": situation, "quote": quote, "action": action, "result": result},
        "observation": {"demeanor": demeanor, "emotion": emotion, "notes": notes},
        "evaluation": {"strengths": strengths, "weaknesses": weaknesses, "summary": summary},
        "tags": tags, "follow_up": follow_up, "sensitive": sensitive,
        "related_person_refs": related,
    }

    errs = ingest.validate(rec, schema)
    if errs:
        print("\n✗ 校验未通过：")
        for e in errs:
            print(f"  • {e}")
        return 1

    ok, msgs = ingest.ingest(rec, (ref if is_new else None), add_alias=(is_new and not sensitive),
                             overwrite=False)
    for m in msgs:
        print(("✓ " if ok else "✗ ") + m)
    if not ok:
        return 1
    if not sensitive and ask_yes("是否现在 git 提交？", default=True):
        git_commit(rec, ref)
    return 0


def git_commit(rec: dict, ref: str) -> None:
    root = common.ROOT
    brief = rec["scene"].get("context") or rec["record_type"]
    day = rec["created_at"][:10]
    targets = ["data/memories", "data/meta/register.json", "data/meta/pseudonyms.md", "data/aliases.md"]
    try:
        r = subprocess.run(["git", "-C", str(root), "add", "--"] + targets, capture_output=True, text=True)
        if r.returncode != 0:
            print("  git add 失败：", r.stderr.strip())
            return
        r = subprocess.run(["git", "-C", str(root), "commit", "-m",
                            f"mem: 录入 {ref} {day} {brief}"], capture_output=True, text=True)
        print("  " + (r.stdout or r.stderr).strip().replace("\n", "\n  "))
    except FileNotFoundError:
        print("  未找到 git，跳过提交。")


def cmd_people() -> int:
    if not common.REGISTER.exists():
        print("register.json 不存在，先重算索引。")
        return 1
    reg = common.load_json(common.REGISTER)
    pseudos = common.parse_pseudonyms(common.PSEUDONYMS)
    print(f"\n人物 {reg.get('total', len(reg['memories']))} 条记忆 / {len(reg['people'])} 人")
    print(f"{'ref':<14} {'假名':<8} {'记忆数':<6} {'最近互动':<12} 关系")
    for p in sorted(reg["people"], key=lambda x: x["ref"]):
        print(f"{p['ref']:<14} {pseudos.get(p['ref'], ''):<8} {p['memory_count']:<6} "
              f"{p['last_updated']:<12} {p.get('name', '')}")
    return 0


def cmd_reindex() -> int:
    print(ingest.rebuild_register())
    return 0


def cmd_build(interactive: bool = False) -> int:
    ok, msg = build.build_dashboard()
    print(msg)
    if ok and interactive and ask_yes("\n是否用浏览器打开看板？", default=True):
        import webbrowser
        webbrowser.open((common.OUTPUT / "index.html").as_uri())
    return 0 if ok else 2


def cmd_analyze() -> int:
    if not common.REGISTER.exists():
        print("register.json 不存在。")
        return 1
    reg = common.load_json(common.REGISTER)
    refs = sorted({p["ref"] for p in reg["people"]})
    if not refs:
        print("暂无人物。")
        return 1
    print("\n人物列表：")
    for i, ref in enumerate(refs, 1):
        print(f"  {i}. {ref}")
    n = ask("选择要分析的人物", int, default=1, validator=lambda v: 1 <= v <= len(refs))
    ref = refs[n - 1]
    print("\n请在 opencode 中执行以下指令（任务书：pipeline/analyze.md）：")
    print(f"\n  分析 {ref}\n")
    return 0


def cmd_menu(schema) -> int:
    while True:
        print("\n" + "=" * 42)
        print("  personal-wiki（命令行菜单）")
        print(f"  数据根: {common.DATA}")
        print("=" * 42)
        print("  1) 录入新记忆")
        print("  2) 人物/记忆概览")
        print("  3) 重算索引 register")
        print("  4) 生成看板")
        print("  5) 生成分析提示（交给 opencode）")
        print("  0) 退出")
        print("-" * 42)
        choice = ask("选择", int, default=0, validator=lambda v: 0 <= v <= 5)
        if choice == 1:
            cmd_entry(schema)
        elif choice == 2:
            cmd_people()
        elif choice == 3:
            cmd_reindex()
        elif choice == 4:
            cmd_build(interactive=True)
        elif choice == 5:
            cmd_analyze()
        else:
            print("再见。")
            return 0


def run_cli(args, schema) -> int:
    if args.people:
        return cmd_people()
    if args.reindex:
        return cmd_reindex()
    if args.build:
        return cmd_build(interactive=False)
    if args.entry:
        return cmd_entry(schema)
    if args.menu:
        return cmd_menu(schema)
    print("未指定动作；默认启动图形界面，或用 --menu 打开命令行菜单。")
    return 0


def main(argv: list[str] | None = None) -> int:
    common.setup_stdout_utf8()
    ap = argparse.ArgumentParser(description="personal-wiki 个人关系记忆系统")
    ap.add_argument("--people", action="store_true", help="人物/记忆概览（CLI）")
    ap.add_argument("--reindex", action="store_true", help="重算 register.json")
    ap.add_argument("--build", action="store_true", help="生成看板")
    ap.add_argument("--entry", action="store_true", help="录入新记忆（CLI）")
    ap.add_argument("--menu", action="store_true", help="命令行交互菜单（CLI）")
    ap.add_argument("--pw-root", help="指定仓库/数据根目录（等价环境变量 PW_ROOT）")
    args, _ = ap.parse_known_args(argv)

    if not common.DATA.exists() or not (common.ALIASES.exists() or common.REGISTER.exists()):
        msg = (f"未在 {common.ROOT} 找到 data/ 数据目录。\n"
               "请将程序放到项目根目录，或用 --pw-root <仓库根目录> 指定。")
        if getattr(sys, "frozen", False):
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.warning(None, "personal-wiki", msg)
            return 2
        print(msg)
        return 2

    schema = common.load_json(common.SCHEMA)

    # 源码 + 显式 CLI 参数 → 传统命令行；否则一律 GUI
    use_cli = (not getattr(sys, "frozen", False)) and \
              (args.people or args.reindex or args.build or args.entry or args.menu)
    if use_cli:
        return run_cli(args, schema)

    from app.gui.main_window import launch
    action = None
    start = "overview"
    if args.reindex:
        action, start = "reindex", "index"
    elif args.build:
        action, start = "build", "dashboard"
    elif args.entry:
        start = "entry"
    return launch(start_tab=start, action=action)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\n已中止。")
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(1)