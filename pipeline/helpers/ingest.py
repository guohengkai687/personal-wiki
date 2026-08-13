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
  python src ingest.py <memory.json> [<memory2.json> ...]
  python src ingest.py --ref zhangsan <memory.json>
  python src ingest.py --add-alias <memory.json>     # 新人物时同时写入 aliases.md
  python src ingest.py --reindex                      # 仅根据 memories/ 重算 register.json
  python src ingest.py --validate <memory.json>       # 只校验不落盘
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
MEMORIES = DATA / "memories"
PRIVATE = DATA / "private"
META = DATA / "meta"
ALIASES = DATA / "aliases.md"
PSEUDONYMS = META / "pseudonyms.md"
REGISTER = META / "register.json"
SCHEMA = ROOT / "input" / "form-schema.json"

EMOTIONS = {"calm", "positive", "tense", "excited", "frustrated", "angry"}


# ---------------------------------------------------------------- 工具
def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_smart(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.move(str(tmp), str(path))


def parse_aliases(path: Path) -> dict[str, str]:
    """aliases.md 行格式：`名字 → ref   (关系: ...)` → {名字: ref}"""
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*(.+?)\s*(?:\(.*\))?\s*→\s*([a-zA-Z0-9_-]+)\s*$", line)
        if m:
            mapping[m.group(1).strip()] = m.group(2).strip()
    return mapping


def parse_pseudonyms(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([a-zA-Z0-9_-]+)\s*→\s*(.+?)\s*$", line)
        if m:
            mapping[m.group(1).strip()] = m.group(2).strip()
    return mapping


def pinyin_ref(name: str) -> str | None:
    """尽力推断拼音 ref（依赖 pypinyin，缺失时返回 None）"""
    try:
        from pypinyin import lazy_pinyin  # type: ignore
        return "".join(lazy_pinyin(name)).lower().strip().replace(" ", "")
    except Exception:
        return None


def infer_ref(name: str) -> str | None:
    """按优先级推断 ref：别名表内 / ASCII 小写 / pypinyin / 回退占位"""
    ready = re.sub(r"\s+", "", name.strip())
    if re.fullmatch(r"[A-Za-z0-9_-]+", ready):
        return ready.lower()
    return pinyin_ref(ready)


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


def rebuild_register() -> None:
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
    print(f"  register.json 已重算: {len(memories)} 条记忆 / {len(people)} 人（m1~m{len(memories)}）")


# ---------------------------------------------------------------- 摄入
def ingest(rec: dict, ref_override: str | None, add_alias: bool, overwrite: bool):
    aliases = parse_aliases(ALIASES)
    name = rec["person"]["name"].strip()
    ref = ref_override or aliases.get(name) or (name.strip() if infer_ref(name) else None)

    if not ref:
        ref = "pending"
        print(f"  ! 无法推断 ref（缺少 pypinyin，也未在 aliases.md）：暂时用 'pending'，"
              f"请用 --ref <ref> 指定并将其写入 aliases.md")
        sys.exit(2)

    if ref == "pending":
        print(f"  ! 新人物「{name}」尚未归一化，ref = pending，请用 --ref 或经 opencode 判断后重跑")
        sys.exit(2)

    ref = ref_override or aliases.get(name) or ref

    # 填 ref / id
    rec["person"]["ref"] = ref
    staple = re.match(r"^(\d{8}-H\d{4})", rec["id"])
    if not staple:
        print(f"  ! id 格式非法: {rec['id']!r}")
        sys.exit(2)
    staple = staple.group(1)
    rec["id"] = staple + "-" + ref + ("-PRIVATE" if rec["sensitive"] else "")

    # 落盘目录
    try:
        created = dt.datetime.fromisoformat(rec["created_at"])
    except ValueError:
        print("  ! created_at 格式非法")
        sys.exit(2)
    base = PRIVATE if rec["sensitive"] else MEMORIES
    target_dir = base / f"{created.year:04d}" / f"{created.month:02d}"
    filename = staple + "-" + ref + ("-PRIVATE" if rec["sensitive"] else "") + ".json"
    target = target_dir / filename

    if target.exists() and not overwrite:
        print(f"  ✗ 目标已存在: {target}（用 --overwrite 覆盖）")
        sys.exit(2)

    target_dir.mkdir(parents=True, exist_ok=True)
    write_json_smart(target, rec)

    # 别名/假名登记（新人物；私密记忆一律不写 git 内文件，保持隐私）
    if add_alias and not rec["sensitive"] and name not in aliases:
        append_line(ALIASES, f"{name} → {ref}\n")
        print(f"  + aliases.md 已追加: {name} → {ref}")
    pseudo = rec.get("person", {}).get("pseudonym", "")
    if pseudo and not rec["sensitive"] and ref not in parse_pseudonyms(PSEUDONYMS):
        append_line(PSEUDONYMS, f"{ref} → {pseudo}\n")
        print(f"  + pseudonyms.md 已追加: {ref} → {pseudo}")

    kind = "PRIVATE" if rec["sensitive"] else "memories"
    print(f"  ✓ 已落盘 [{kind}] {target.relative_to(ROOT)}")
    rebuild_register()
    print_suggest(target, rec)


def append_line(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write("\n" + text if path.stat().st_size > 0 else text)


def print_suggest(target: Path, rec: dict) -> None:
    if rec["sensitive"]:
        print("\n[私密记忆] 已落盘 data/private/（gitignore），不进 git、register、分析与看板，无需提交。")
        return
    ref = rec["person"]["ref"]
    day = rec["created_at"][:10]
    brief = rec["scene"].get("context", "") or rec["record_type"]
    adds = ['data/memories/', 'data/meta/register.json']
    if rec.get("person", {}).get("pseudonym"):
        adds.append('data/meta/pseudonyms.md')
    print("\n[提交建议]（供用户确认后执行，勿自动 commit）")
    print(f'  git add ' + " ".join(f'"{a}"' for a in adds) + f' "{target}"')
    print(f'  git commit -m "mem: 录入 {ref} {day} {brief}"')
    print("\n  注意：提交信息只用 ref；aliases.md 若有改动请一起 add。")


# ---------------------------------------------------------------- 入口
def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="personal-wiki 摄入脚本")
    ap.add_argument("files", nargs="*", help="待摄入的记忆 JSON")
    ap.add_argument("--ref", help="人名归一化 ref（新人物时）")
    ap.add_argument("--add-alias", action="store_true", help="新人物时追加写入 aliases.md")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已存在的同名目标")
    ap.add_argument("--reindex", action="store_true", help="仅重算 register.json")
    ap.add_argument("--validate", action="store_true", help="仅校验，不落盘不索引")
    args = ap.parse_args()

    if args.reindex:
        rebuild_register()
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
        ingest(rec, args.ref, args.add_alias, args.overwrite)

    return 0


if __name__ == "__main__":
    sys.exit(main())