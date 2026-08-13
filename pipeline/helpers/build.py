#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/helpers/build.py —— 看板构建脚本（DESIGN.md §7）

读取 data/（register.json、pseudonyms.md、people/*.md、memories/**/*.json），
套用 dashboard/templates/*.j2 生成单页静态看板 dashboard/output/index.html，并拷贝静态资源。
产物内嵌 JSON，不依赖后端；双击打开即可，也可以 python -m http.server 获得完整体验。
另做展示层脱敏：依据 pseudonyms.md 将页面中的真名替换为假名；无法落实的残留标"未脱敏"。

用法：python pipeline/helpers/build.py
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

if __package__:
    from .common import (ALIASES, ASSETS, MEMORIES, OUTPUT, PEOPLE,
                         PSEUDONYMS, REGISTER, TEMPLATES, load_json,
                         parse_aliases, parse_pseudonyms, read,
                         setup_stdout_utf8)
else:
    from common import (ALIASES, ASSETS, MEMORIES, OUTPUT, PEOPLE,
                        PSEUDONYMS, REGISTER, TEMPLATES, load_json,
                        parse_aliases, parse_pseudonyms, read,
                        setup_stdout_utf8)

EMOTION = {
    "color": {"calm": "#94a3b8", "positive": "#22c55e", "tense": "#f59e0b",
              "excited": "#fb923c", "frustrated": "#ef4444", "angry": "#b91c1c"},
    "sentiment": {"calm": 3.0, "positive": 4.0, "tense": 2.0, "excited": 5.0,
                  "frustrated": 1.5, "angry": 1.0},
}
BIG5_LABELS = ["开放性", "尽责性", "外向性", "宜人性", "神经质"]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s: str) -> str:
    t = esc(s)
    z = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    z = re.sub(r"`(.+?)`", r"<code>\1</code>", z)
    return z


def md_to_html(text: str) -> str:
    out = []
    in_list = in_quote = False

    def guard():
        nonlocal in_list, in_quote
        if in_list:
            out.append("</ul>")
            in_list = False
        if in_quote:
            out.append("</blockquote>")
            in_quote = False

    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            guard()
            continue
        if s.startswith("### "):
            guard()
            out.append(f"<h4>{inline(s[4:])}</h4>")
        elif s.startswith("## "):
            guard()
            out.append(f"<h3>{inline(s[2:])}</h3>")
        elif s.startswith("# "):
            guard()
            out.append(f"<h2>{inline(s[2:])}</h2>")
        elif s.startswith("> "):
            if not in_quote:
                out.append("<blockquote>")
                in_quote = True
            out.append(f"<p>{inline(s[2:])}</p>")
        elif re.match(r"^\s*[-*]\s+", s):
            if not in_list:
                out.append("<ul>")
                in_list = True
            clean = re.sub(r"^\s*[-*]\s+", "", s)
            out.append(f"<li>{inline(clean)}</li>")
        elif re.match(r"^---+$", s):
            guard()
            out.append("<hr>")
        else:
            guard()
            out.append(f"<p>{inline(s)}</p>")
    guard()
    return "".join(out)


def build_mask(people: list[dict], pseudos: dict[str, str]) -> list[tuple[str, str]]:
    subs = []
    for p in people:
        ref, name, pseudo = p["ref"], p["name"], pseudos.get(p["ref"])
        if ref and pseudo and name and name != pseudo:
            subs.append((name, pseudo))
    subs.sort(key=lambda x: len(x[0]), reverse=True)
    return subs


def mask(text: str, subs: list[tuple[str, str]]) -> str:
    for real, fake in subs:
        text = text.replace(real, fake)
    return text


def parse_big5(profile: str) -> dict | None:
    m = re.search(
        r"开放性\s*([\d.]+)\s*/\s*尽责性\s*([\d.]+)\s*/\s*外向性\s*([\d.]+)"
        r"\s*/\s*宜人性\s*([\d.]+)\s*/\s*神经质\s*([\d.]+)",
        profile)
    if not m:
        return None
    vals = [float(x) for x in m.groups()]
    return dict(zip(BIG5_LABELS, vals))


def parse_tags(profile: str) -> list[str]:
    m = re.search(r"关键标签[^：:]*[：:]\s*(.+)$", profile, re.M)
    if not m:
        return []
    tags = [t.strip() for t in re.split(r"[\/／、,，]", m.group(1)) if t.strip()]
    return tags[:4]


def parse_info(profile: str) -> dict:
    info = {}
    r = re.search(r"relation:\s*([^\s].*?)\s{2,}首次记录", profile)
    if r:
        info["relation"] = r.group(1).strip()
    r = re.search(r"首次记录:\s*([\d-]+)", profile)
    if r:
        info["first"] = r.group(1)
    r = re.search(r"最近互动:\s*([\d-]+)", profile)
    if r:
        info["last"] = r.group(1)
    return info


def aggregate_people(memories: list[dict], profiles: dict[str, str],
                     ref_names: dict[str, str], pseudos: dict[str, str]) -> list[dict]:
    by_ref: dict[str, list[dict]] = {}
    for rec in memories:
        by_ref.setdefault(rec["ref"], []).append(rec)

    subs = build_mask([{"ref": k, "name": v} for k, v in ref_names.items()], pseudos)

    people = []
    for ref, recs in sorted(by_ref.items()):
        recs = sorted(recs, key=lambda x: x["created_at"])
        profile = profiles.get(ref, "")
        big5 = parse_big5(profile)
        tags = parse_tags(profile)
        info = parse_info(profile)
        if not tags:
            from collections import Counter
            cnt = Counter()
            for r in recs:
                cnt.update(r.get("tags", []))
            tags = [t for t, _ in cnt.most_common(4)]
        latest = recs[-1]
        emotion = latest.get("observation", {}).get("emotion", "calm")
        pseudo = pseudos.get(ref, ref)
        person_unmasked = ref not in pseudos
        profile_clean = re.sub(r"真名:\s*[^  　]+", "", profile)
        profile_display = mask(profile_clean, subs)
        mem_view = []
        for r in recs:
            unmasked = False
            related = [x for x in r.get("related_person_refs", []) if x not in pseudos]
            if r["ref"] not in pseudos:
                unmasked = True
            q = r.get("subject", {}).get("quote", "")
            sit = r.get("subject", {}).get("situation", "")
            ctx = r.get("scene", {}).get("context", "")
            if related:
                unmasked = True
            mem_view.append({
                "m": r["_m"], "id": r["id"], "date": r["created_at"][:10],
                "time": r["created_at"][11:16], "record_type": r.get("record_type", ""),
                "situation": mask(sit, subs), "quote": mask(q, subs),
                "action": mask(r.get("subject", {}).get("action", ""), subs),
                "result": mask(r.get("subject", {}).get("result", ""), subs),
                "context": mask(ctx, subs),
                "emotion": emotion_of(r),
                "unmasked": unmasked,
            })
        people.append({
            "ref": ref,
            "name": mask(ref_names.get(ref, ref), subs),
            "pseudo": pseudo,
            "initial": pseudo[:1],
            "relation": info.get("relation", ""),
            "first": info.get("first", recs[0]["created_at"][:10]),
            "last": info.get("last", recs[-1]["created_at"][:10]),
            "memory_count": len(recs),
            "tags": tags,
            "big5": big5,
            "emotion": emotion,
            "emotion_color": EMOTION["color"].get(emotion, "#94a3b8"),
            "unmasked": person_unmasked,
            "profile_text": profile_display,
            "profile_html": md_to_html(profile_display),
            "memories": mem_view,
        })
    return people


def emotion_of(rec: dict) -> str:
    return rec.get("observation", {}).get("emotion", "calm")


def build_dashboard() -> tuple[bool, str]:
    """生成静态看板 dashboard/output/。返回 (是否成功, 结果消息)。"""
    if not REGISTER.exists():
        return False, "register.json 不存在，请先在「索引」页重算"

    register = load_json(REGISTER)

    pseudos = parse_pseudonyms(PSEUDONYMS)
    aliases = parse_aliases(ALIASES)
    ref_names = {p["ref"]: p["name"] for p in register.get("people", [])}

    raw_memories = []
    for m in register.get("memories", []):
        ym = m["date"][:7].replace("-", "/")
        paths = list((MEMORIES / ym).glob(m["id"] + ".json"))
        if not paths:
            continue
        rec = load_json(paths[0])
        rec["_m"] = m["m"]
        rec["ref"] = rec["person"]["ref"]
        raw_memories.append(rec)

    profiles = {}
    for p in PEOPLE.glob("*.md"):
        profiles[p.stem] = read(p)

    people = aggregate_people(raw_memories, profiles, ref_names, pseudos)

    today = date.today()
    month_new = sum(1 for m in raw_memories if m["created_at"][:7] == today.strftime("%Y-%m"))
    followups = sum(1 for r in raw_memories if r.get("follow_up"))
    timeline = []
    for rec in sorted(raw_memories, key=lambda x: x["created_at"], reverse=True)[:12]:
        ref = rec["ref"]
        subs = build_mask([{"ref": r, "name": n} for r, n in ref_names.items()], pseudos)
        timeline.append({
            "m": rec.get("_m", ""), "ref": ref, "person": pseudos.get(ref, ref_names.get(ref, ref)),
            "date": rec["created_at"][:10], "record_type": rec.get("record_type", ""),
            "context": mask(rec.get("scene", {}).get("context", ""), subs),
            "situation": mask(rec.get("subject", {}).get("situation", ""), subs),
        })

    kpis = {
        "people_total": len(people),
        "memories_total": register.get("total", len(raw_memories)),
        "month_new": month_new,
        "followups": followups,
    }

    payload = {
        "kpis": kpis,
        "people": people,
        "timeline": timeline,
        "emotions": {"color": EMOTION["color"], "sentiment": EMOTION["sentiment"]},
        "labels": BIG5_LABELS,
        "built": today.strftime("%Y-%m-%d"),
    }

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)),
                      autoescape=False, trim_blocks=True, lstrip_blocks=True)
    env.globals["big5_keys"] = BIG5_LABELS
    out_html = env.get_template("index.html.j2").render(
        kpis=kpis, people=people, timeline=timeline,
        payload=json.dumps(payload, ensure_ascii=False))

    (OUTPUT / "assets").mkdir(parents=True, exist_ok=True)
    for asset in ASSETS.glob("*"):
        if asset.is_file():
            shutil.copy2(asset, OUTPUT / "assets" / asset.name)

    out_index = OUTPUT / "index.html"
    out_index.write_text(out_html, encoding="utf-8")
    return True, (f"看板已生成: {out_index}\n"
                  f"  人物 {kpis['people_total']} / 记忆 {kpis['memories_total']}"
                  f" / 本月新增 {kpis['month_new']} / 待跟进 {kpis['followups']}")


def main() -> int:
    setup_stdout_utf8()
    ok, msg = build_dashboard()
    print(msg)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())