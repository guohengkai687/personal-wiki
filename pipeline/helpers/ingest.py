#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/helpers/ingest.py —— personal-wiki 摄入脚本

职责（见 DESIGN.md §5.5 / §4.4）：
  1. 按 schema 校验记忆 JSON（必填 / 枚举 / 标尺 / 空泛词）；
  2. 人名归一化：查 aliases.md 得 ref；新名字可 --ref 指定或自动推断；
  3. 落盘：sensitive=true → data/private/YYYY/MM/，否则 → data/memories/YYYY/MM/；
  4. 重算 register.json（生成物，分配 m 序号），不手工编辑；
  5. 输出 mem: 提交信息建议（不自动 commit）。

用法：
  python pipeline/helpers/ingest.py <memory.json> [<memory2.json> ...]
  python pipeline/helpers/ingest.py --ref zhangsan <memory.json>
  python pipeline/helpers/ingest.py --add-alias <memory.json>     # 新人物时同时写入 aliases.md
  python pipeline/helpers/ingest.py --reindex                      # 仅根据 memories/ 重算 register.json
  python pipeline/helpers/ingest.py --validate <memory.json>       # 只校验不落盘
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

if __package__:
    from .common import (ALIASES, MEMORIES, PEOPLE, PRIVATE, PSEUDONYMS, REGISTER,
                         ROOT, SCHEMA, append_line, infer_ref, load_json,
                         parse_aliases, parse_pseudonyms, setup_stdout_utf8,
                         write_json_smart)
else:
    from common import (ALIASES, MEMORIES, PEOPLE, PRIVATE, PSEUDONYMS, REGISTER,
                        ROOT, SCHEMA, append_line, infer_ref, load_json,
                        parse_aliases, parse_pseudonyms, setup_stdout_utf8,
                        write_json_smart)

EMOTIONS = {"calm", "positive", "tense", "excited", "frustrated", "angry"}


# ---------------------------------------------------------------- 校验
def validate(rec: dict, schema: dict) -> list[str]:
    errs: list[str] = []
    need = schema.get("validation", {})

    # 必填
    if not str(rec.get("person", {}).get("name", "")).strip():
        errs.append("person.name 必填")
    if not str(rec.get("person", {}).get("relation", "")).strip():
        errs.append("person.relation 必填")
    if not str(rec.get("scene", {}).get("type", "")).strip():
        errs.append("scene.type 必填")
    if not str(rec.get("scene", {}).get("context", "")).strip():
        errs.append("scene.context 必填")
    if not str(rec.get("subject", {}).get("situation", "")).strip():
        errs.append("subject.situation 必填")
    if not str(rec.get("evaluation", {}).get("strengths", "")).strip():
        errs.append("evaluation.strengths 必填")
    if not str(rec.get("evaluation", {}).get("summary", "")).strip():
        errs.append("evaluation.summary 必填")
    if not str(rec.get("created_at", "")).strip():
        errs.append("created_at 必填")
    if not str(rec.get("id", "")).strip():
        errs.append("id 必填")

    # 原话/行动至少其一
    q = str(rec.get("subject", {}).get("quote", "")).strip()
    a = str(rec.get("subject", {}).get("action", "")).strip()
    if need.get("quote_or_action_required") and not q and not a:
        errs.append("subject.quote 与 subject.action 至少其一")

    # 枚举
    if rec.get("record_type") not in schema["record_type"]["options"]:
        errs.append(f"record_type 非法: {rec.get('record_type')!r}")
    if rec.get("scene", {}).get("type") not in schema["scene"]["type"]["options"]:
        errs.append(f"scene.type 非法: {rec.get('scene', {}).get('type')!r}")
    if rec.get("observation", {}).get("emotion") not in EMOTIONS:
        errs.append(f"observation.emotion 非法: {rec.get('observation', {}).get('emotion')!r}")

    # 行为标尺 1-5
    for dim in schema["observation"]["demeanor"]:
        v = rec.get("observation", {}).get("demeanor", {}).get(dim["key"])
        if not isinstance(v, int) or not 1 <= v <= 5:
            errs.append(f"demeanor.{dim['key']} 须为 1-5 整数，实际 {v!r}")

    # 空泛词
    for word in need.get("ban_words", []):
        for key in ("strengths", "summary"):
            text = str(rec.get("evaluation", {}).get(key, ""))
            if word in text:
                errs.append(f"evaluation.{key} 含空泛词「{word}」，请改具体依据")

    # sensitive 布尔
    if not isinstance(rec.get("sensitive"), bool):
        errs.append("sensitive 须为布尔")

    # tags 类型与去重
    if not isinstance(rec.get("tags", []), list):
        errs.append("tags 须为数组")
    unique = list(dict.fromkeys(rec.get("tags", [])))
    if len(unique) != len(rec.get("tags", [])):
        rec["tags"] = unique

    return errs


# ---------------------------------------------------------------- register
def _scan_json_records(root: Path) -> list[dict]:
    recs = []
    for p in sorted(root.rglob("*.json")):
        try:
            data = load_json(p)
        except json.JSONDecodeError:
            print(f"  ! 跳过无法解析的文件: {p}")
            continue
        if not isinstance(data, dict):
            continue
        if data.get("sensitive"):
            p.unlink(missing_ok=True)
            print(f"  ! 移除误入非私密目录的 sensitive 记忆: {p}")
            continue
        recs.append(data)
    return recs


def rebuild_register() -> str:
    """按 data/memories/ 重算 register.json（生成物）。返回结果摘要文本。"""
    recs = _scan_json_records(MEMORIES)
    recs.sort(key=lambda r: r.get("created_at", ""))

    memories = []
    people: dict[str, dict] = {}
    for i, r in enumerate(recs, start=1):
        ref = r.get("person", {}).get("ref", "") or "unknown"
        date = (r.get("created_at", ""))[:10]
        time = (r.get("created_at", ""))[11:16]
        memories.append({
            "m": f"m{i}",
            "id": r.get("id", ""),
            "ref": ref,
            "date": date,
            "time": time,
            "record_type": r.get("record_type", ""),
            "sensitive": bool(r.get("sensitive", False)),
        })
        person = people.setdefault(ref, {"ref": ref, "name": r.get("person", {}).get("name", ""),
                                         "memory_count": 0, "last_updated": ""})
        person["memory_count"] += 1
        if date > person["last_updated"]:
            person["last_updated"] = date

    for p in people.values():
        if not p["name"]:
            p["name"] = p["ref"]

    register = {
        "m": len(memories),
        "total": len(memories),
        "people": sorted(people.values(), key=lambda p: p["ref"]),
        "memories": memories,
    }
    REGISTER.parent.mkdir(parents=True, exist_ok=True)
    write_json_smart(REGISTER, register)
    return f"register.json 已重算: {len(memories)} 条记忆 / {len(people)} 人（m1~m{len(memories)}）"


def register_summary() -> dict:
    """汇总 register + 记忆文件，供 GUI 概览 / 索引展示。"""
    if not REGISTER.exists():
        return {"ok": False, "msg": "register.json 不存在，请先「重算索引」", "rows": [],
                "total": 0, "people_count": 0, "month_new": 0, "followups": 0,
                "private_count": 0, "months": {}}
    reg = load_json(REGISTER)
    pseudos = parse_pseudonyms(PSEUDONYMS)
    this_month = dt.date.today().strftime("%Y-%m")
    months: dict[str, int] = {}
    by_ref: dict[str, dict] = {}
    month_new = followups = 0
    for m in reg.get("memories", []):
        ym = m["date"][:7].replace("-", "/")
        path = MEMORIES / ym / (m["id"] + ".json")
        if not path.exists():
            continue
        rec = load_json(path)
        months[m["date"][:7]] = months.get(m["date"][:7], 0) + 1
        if m["date"][:7] == this_month:
            month_new += 1
        if rec.get("follow_up"):
            followups += 1
        agg = by_ref.setdefault(m["ref"], {
            "ref": m["ref"], "name": rec.get("person", {}).get("name", m["ref"]),
            "relation": "", "count": 0, "last": "", "gender": ""})
        agg["count"] += 1
        if m["date"] > agg["last"]:
            agg["last"] = m["date"]
        if not agg["relation"]:
            agg["relation"] = rec.get("person", {}).get("relation", "")
        if not agg["gender"]:
            agg["gender"] = rec.get("person", {}).get("gender", "") or "unknown"
    rows = []
    for p in sorted(by_ref.values(), key=lambda x: x["ref"]):
        row = {**p, "pseudonym": pseudos.get(p["ref"], "")}
        row["has_profile"] = (PEOPLE / (p["ref"] + ".md")).exists()
        rows.append(row)
    private_count = sum(1 for _ in PRIVATE.rglob("*.json")) if PRIVATE.exists() else 0
    return {"ok": True, "rows": rows, "total": reg.get("total", 0),
            "people_count": len(rows), "month_new": month_new, "followups": followups,
            "private_count": private_count, "months": dict(sorted(months.items()))}


def followups_list() -> list[dict]:
    """扫描记忆中的待跟进事项，返回按日期倒序列表（供 GUI 分析页展示）。"""
    items: list[dict] = []
    if not REGISTER.exists():
        return items
    reg = load_json(REGISTER)
    pseudos = parse_pseudonyms(PSEUDONYMS)
    for m in reg.get("memories", []):
        ym = m["date"][:7].replace("-", "/")
        path = MEMORIES / ym / (m["id"] + ".json")
        if not path.exists():
            continue
        rec = load_json(path)
        fu = rec.get("follow_up")
        if fu:
            items.append({"ref": m["ref"], "pseudonym": pseudos.get(m["ref"], m["ref"]),
                          "date": m["date"], "text": fu, "id": m["id"]})
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


# ---------------------------------------------------------------- 摄入
class IngestError(Exception):
    """摄入失败（信息性），消息可直接展示给用户。"""


def ingest(rec: dict, ref_override: str | None = None, add_alias: bool = False,
           overwrite: bool = False) -> tuple[bool, list[str]]:
    """摄入一条记忆：校验由调用方完成。返回 (是否成功, 结果消息列表)。"""
    msgs: list[str] = []
    try:
        aliases = parse_aliases(ALIASES)
        name = rec["person"]["name"].strip()
        ref = (ref_override or "").strip() or aliases.get(name) or infer_ref(name)
        if not ref:
            raise IngestError("无法推断 ref（未装 pypinyin 且未在 aliases.md），请手动填写 ref")
        ref = ref.lower()

        rec["person"]["ref"] = ref
        m0 = re.match(r"^(\d{8}-H\d{4})", rec["id"])
        if not m0:
            raise IngestError(f"id 格式非法: {rec['id']!r}")
        staple = m0.group(1)
        rec["id"] = staple + "-" + ref + ("-PRIVATE" if rec["sensitive"] else "")

        try:
            created = dt.datetime.fromisoformat(rec["created_at"])
        except ValueError:
            raise IngestError("created_at 格式非法")

        base = PRIVATE if rec["sensitive"] else MEMORIES
        target_dir = base / f"{created.year:04d}" / f"{created.month:02d}"
        filename = staple + "-" + ref + ("-PRIVATE" if rec["sensitive"] else "") + ".json"
        target = target_dir / filename
        if target.exists() and not overwrite:
            raise IngestError(f"目标已存在: {target.relative_to(ROOT)}（请勿重复提交）")

        target_dir.mkdir(parents=True, exist_ok=True)
        write_json_smart(target, rec)
        kind = "PRIVATE" if rec["sensitive"] else "memories"
        msgs.append(f"已落盘 [{kind}] {target.relative_to(ROOT)}")

        # 别名/假名登记（新人物；私密记忆一律不写 git 内文件，保持隐私）
        if add_alias and not rec["sensitive"] and name not in aliases:
            append_line(ALIASES, f"{name} → {ref}\n")
            msgs.append(f"aliases.md 已追加: {name} → {ref}")
        pseudo = rec.get("person", {}).get("pseudonym", "")
        if pseudo and not rec["sensitive"] and ref not in parse_pseudonyms(PSEUDONYMS):
            append_line(PSEUDONYMS, f"{ref} → {pseudo}\n")
            msgs.append(f"pseudonyms.md 已追加: {ref} → {pseudo}")

        msgs.append(rebuild_register())
        suggest = build_suggest(target, rec)
        if suggest:
            msgs.append(suggest)
        return True, msgs
    except IngestError as e:
        return False, [str(e)]


def build_suggest(target: Path, rec: dict) -> str:
    """生成 git 提交建议文本（私密记忆返回空串）。"""
    if rec["sensitive"]:
        return ""
    ref = rec["person"]["ref"]
    day = rec["created_at"][:10]
    brief = rec["scene"].get("context", "") or rec["record_type"]
    rel = target.relative_to(ROOT)
    return ("提交建议：\n"
            f'  git add data/memories/ data/meta/register.json "{rel}"\n'
            f'  git commit -m "mem: 录入 {ref} {day} {brief}"\n'
            f"  注意：提交信息只用 ref；提交前请 git status 核对，私密文件绝不加入。")


# ---------------------------------------------------------------- 入口
def main() -> int:
    setup_stdout_utf8()
    ap = argparse.ArgumentParser(description="personal-wiki 摄入脚本")
    ap.add_argument("files", nargs="*", help="待摄入的记忆 JSON")
    ap.add_argument("--ref", help="人名归一化 ref（新人物时）")
    ap.add_argument("--add-alias", action="store_true", help="新人物时追加写入 aliases.md")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已存在的同名目标")
    ap.add_argument("--reindex", action="store_true", help="仅重算 register.json")
    ap.add_argument("--validate", action="store_true", help="仅校验，不落盘不索引")
    args = ap.parse_args()

    if args.reindex:
        print(rebuild_register())
        return 0

    if not args.files:
        ap.print_help()
        return 2

    schema = load_json(SCHEMA)

    for f in args.files:
        path = Path(f)
        if not path.exists():
            print(f"✗ 文件不存在: {path}")
            return 2
        rec = load_json(path)
        errs = validate(rec, schema)
        if errs:
            print(f"✗ 校验未通过: {path}")
            for e in errs:
                print(f"  • {e}")
            return 2
        print(f"✓ 校验通过: {path.name}")
        if args.validate:
            continue
        ok, msgs = ingest(rec, args.ref, args.add_alias, args.overwrite)
        for m in msgs:
            print(("✓ " if ok else "✗ ") + m)
        if not ok:
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())