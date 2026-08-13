# -*- coding: utf-8 -*-
"""app/gui/record_tab.py —— 录入页：四区块规范化录入 → 校验 → 落盘 → 重算索引。"""
from __future__ import annotations

import datetime as dt
import subprocess

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateTimeEdit, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QScrollArea, QSlider,
                               QVBoxLayout, QWidget)

from pipeline.helpers import common, ingest

from .widgets import FormRow, btn, info, warn

EMOTION_LABELS = {
    "calm": "平静 calm", "positive": "积极 positive", "tense": "紧张 tense",
    "excited": "兴奋 excited", "frustrated": "沮丧 frustrated", "angry": "愤怒 angry",
}


def local_offset(d: dt.datetime) -> str:
    off = dt.datetime.now().astimezone().utcoffset()
    total = int(off.total_seconds()) if off else 0
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return f"{sign}{total // 3600:02d}:{total % 3600 // 60:02d}"


class RecordTab(QWidget):
    def __init__(self, schema: dict):
        super().__init__()
        self.schema = schema
        self.on_saved = None
        self._build_ui()
        self.refresh_people()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 8, 4, 8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(8, 4, 8, 8)
        lay.setSpacing(10)

        lay.addWidget(self._block_basic())
        lay.addWidget(self._block_subject())
        lay.addWidget(self._block_observation())
        lay.addWidget(self._block_evaluation())
        lay.addWidget(self._block_extra())
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        bottom = QHBoxLayout()
        self.cb_commit = QCheckBox("保存成功后自动 git 提交（仅 ref 提交信息，私密记忆永不提交）")
        self.cb_commit.setChecked(False)
        self.b_save = btn("校验并保存", accent=True, icon_name="check")
        self.b_save.clicked.connect(self.save)
        self.b_clear = btn("清空表单", quiet=True)
        self.b_clear.clicked.connect(self.clear_form)
        bottom.addWidget(self.cb_commit, 1)
        bottom.addWidget(self.b_clear)
        bottom.addWidget(self.b_save)
        outer.addLayout(bottom)

    def _block_basic(self) -> QGroupBox:
        g = QGroupBox("① 基础信息")
        grid = QGridLayout(g)
        grid.setVerticalSpacing(6)

        self.cb_name = QComboBox()
        self.cb_name.setEditable(True)
        self.cb_name.setInsertPolicy(QComboBox.NoInsert)
        self.cb_name.setPlaceholderText("人物（真名）")
        self.in_relation = QLineEdit()
        self.in_relation.setPlaceholderText("如：同事-产品线总监")
        self.cb_new = QCheckBox("新建人物")
        self.cb_new.toggled.connect(lambda on: self.in_pseudo.setEnabled(on))
        self.in_pseudo = QLineEdit()
        self.in_pseudo.setPlaceholderText("展示用假名（新建时登记）")
        self.in_pseudo.setEnabled(False)
        self.in_ref = QLineEdit()
        self.in_ref.setPlaceholderText("留空自动推断（如 zhangsan）")

        self.dt = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt.setCalendarPopup(True)
        self.cb_record = QComboBox()
        self.cb_record.addItems(self.schema["record_type"]["options"])
        self.cb_scene_type = QComboBox()
        self.cb_scene_type.addItems(self.schema["scene"]["type"]["options"])
        self.in_location = QLineEdit()
        self.in_location.setPlaceholderText("如：上海-会议室A")
        self.in_context = QLineEdit()
        self.in_context.setPlaceholderText("如：季度项目复盘会")

        grid.addWidget(self._lab("人物"), 0, 0)
        grid.addWidget(self.cb_name, 0, 1, 1, 3)
        grid.addWidget(self._lab("关系"), 1, 0)
        grid.addWidget(self.in_relation, 1, 1, 1, 3)
        grid.addWidget(self._lab("日期时间"), 2, 0)
        grid.addWidget(self.dt, 2, 1, 1, 3)
        grid.addWidget(self._lab("记录类型"), 3, 0)
        grid.addWidget(self.cb_record, 3, 1, 1, 3)
        grid.addWidget(self._lab("场景类型"), 4, 0)
        grid.addWidget(self.cb_scene_type, 4, 1, 1, 3)
        grid.addWidget(self._lab("地点"), 5, 0)
        grid.addWidget(self.in_location, 5, 1, 1, 3)
        grid.addWidget(self._lab("场景说明"), 6, 0)
        grid.addWidget(self.in_context, 6, 1, 1, 3)
        grid.addWidget(self.cb_new, 7, 0)
        grid.addWidget(self.in_pseudo, 7, 1, 1, 1)
        grid.addWidget(self._lab("ref"), 7, 2)
        grid.addWidget(self.in_ref, 7, 3)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(3, 2)
        return g

    def _block_subject(self) -> QGroupBox:
        g = QGroupBox("② 事件主体（STAR，客观还原）")
        v = QVBoxLayout(g)
        self.in_situation = QPlainTextEdit()
        self.in_situation.setPlaceholderText("情境 S：背景是什么？（必填）")
        self.in_situation.setFixedHeight(60)
        self.in_quote = QPlainTextEdit()
        self.in_quote.setPlaceholderText("原话引用 Q：原话，可粘贴聊天记录（可选）")
        self.in_quote.setFixedHeight(60)
        self.in_action = QPlainTextEdit()
        self.in_action.setPlaceholderText("行动 A：他/她做了什么？（可选）")
        self.in_action.setFixedHeight(60)
        self.in_result = QPlainTextEdit()
        self.in_result.setPlaceholderText("结果 R：最后怎么样了？（可选）")
        self.in_result.setFixedHeight(60)
        v.addWidget(self._lab("情境 S（必填）"))
        v.addWidget(self.in_situation)
        v.addWidget(self._lab("原话引用 Q"))
        v.addWidget(self.in_quote)
        v.addWidget(self._lab("行动 A"))
        v.addWidget(self.in_action)
        v.addWidget(self._lab("结果 R"))
        v.addWidget(self.in_result)
        h = QLabel("原话与行动至少填写其一")
        h.setObjectName("Hint")
        v.addWidget(h)
        return g

    def _block_observation(self) -> QGroupBox:
        g = QGroupBox("③ 人物观察")
        v = QVBoxLayout(g)
        self.sliders: dict[str, QSlider] = {}
        self.slider_labels: dict[str, QLabel] = {}
        for dim in self.schema["observation"]["demeanor"]:
            row = QHBoxLayout()
            lab = QLabel(f"{dim['label']}（1={dim['low']} … 5={dim['high']}）")
            lab.setMinimumWidth(170)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(1, 5)
            sl.setValue(3)
            sl.setTickPosition(QSlider.TicksBelow)
            sl.setTickInterval(1)
            val = QLabel("3")
            val.setMinimumWidth(22)
            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet("font-weight:700; color:#4F46E5;")
            sl.valueChanged.connect(lambda x, l=val: l.setText(str(x)))
            self.sliders[dim["key"]] = sl
            self.slider_labels[dim["key"]] = val
            row.addWidget(lab)
            row.addWidget(sl, 1)
            row.addWidget(val)
            v.addLayout(row)

        self.cb_emotion = QComboBox()
        for key in self.schema["observation"]["emotion"]["options"]:
            self.cb_emotion.addItem(EMOTION_LABELS.get(key, key), key)
        v.addWidget(self._lab("情绪状态"))
        v.addWidget(self.cb_emotion)
        self.in_notes = QPlainTextEdit()
        self.in_notes.setPlaceholderText("补充观察（可选）")
        self.in_notes.setFixedHeight(60)
        v.addWidget(self._lab("补充观察"))
        v.addWidget(self.in_notes)
        return g

    def _block_evaluation(self) -> QGroupBox:
        g = QGroupBox("④ 评价与后续")
        v = QVBoxLayout(g)
        self.in_strengths = QPlainTextEdit()
        self.in_strengths.setPlaceholderText("优点：基于观察依据，避免空泛词（必填）")
        self.in_strengths.setFixedHeight(54)
        self.in_weaknesses = QPlainTextEdit()
        self.in_weaknesses.setPlaceholderText("弱点：基于观察依据（可选）")
        self.in_weaknesses.setFixedHeight(54)
        self.in_summary = QLineEdit()
        self.in_summary.setPlaceholderText("总结：一句话（必填）")
        self.in_follow = QPlainTextEdit()
        self.in_follow.setPlaceholderText("待跟进事项（可选）")
        self.in_follow.setFixedHeight(54)
        v.addWidget(self._lab("优点（必填）"))
        v.addWidget(self.in_strengths)
        v.addWidget(self._lab("弱点"))
        v.addWidget(self.in_weaknesses)
        v.addWidget(self._lab("总结（必填）"))
        v.addWidget(self.in_summary)
        v.addWidget(self._lab("待跟进"))
        v.addWidget(self.in_follow)
        return g

    def _block_extra(self) -> QGroupBox:
        g = QGroupBox("标签 / 关联 / 私密")
        v = QVBoxLayout(g)
        self.in_tags = QLineEdit()
        self.in_tags.setPlaceholderText("标签（逗号分隔，最多 8 个）")
        v.addWidget(self.in_tags)
        chips = QHBoxLayout()
        for t in self.schema["tags"]["suggestions"]:
            b = btn(t, quiet=True)
            b.clicked.connect(lambda _, x=t: self._add_tag(x))
            chips.addWidget(b)
        v.addLayout(chips)
        self.in_related = QLineEdit()
        self.in_related.setPlaceholderText("关联人物 ref（逗号分隔，可选）")
        v.addWidget(self.in_related)
        self.cb_sensitive = QCheckBox(
            "敏感/私密记忆：仅落盘 data/private/，永不进入 git、register、分析与看板")
        self.cb_sensitive.setStyleSheet("color:#B45309;")
        v.addWidget(self.cb_sensitive)
        return g

    @staticmethod
    def _lab(text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("Hint")
        return lab

    # ------------------------------------------------------------ 数据
    def _add_tag(self, tag: str):
        tags = [t.strip() for t in self.in_tags.text().split(",") if t.strip()]
        if tag not in tags:
            tags.append(tag)
            self.in_tags.setText(", ".join(tags))

    def refresh_people(self):
        s = ingest.register_summary()
        if not s.get("ok"):
            return
        names = sorted({r["name"] for r in s.get("rows", []) if r["name"]})
        self.cb_name.clear()
        self.cb_name.addItem("")
        self.cb_name.addItems(names)

    def build_record(self) -> dict:
        now = self.dt.dateTime().toPython()
        name = self.cb_name.currentText().strip()
        is_new = self.cb_new.isChecked() or name not in common.parse_aliases(common.ALIASES)
        sensitive = self.cb_sensitive.isChecked()
        pseudo = self.in_pseudo.text().strip()
        ref = self.in_ref.text().strip()
        staple = now.strftime("%Y%m%d-H%H%M")
        rec = {
            "id": staple + ("-PRIVATE" if sensitive else ""),
            "schema_version": self.schema.get("schema_version", 1),
            "created_at": now.strftime("%Y-%m-%dT%H:%M:%S") + local_offset(now),
            "person": {"name": name, "ref": ("" if is_new else ref),
                       "relation": self.in_relation.text().strip(),
                       "pseudonym": (pseudo if is_new and not sensitive else "")},
            "scene": {"type": self.cb_scene_type.currentText(),
                      "location": self.in_location.text().strip(),
                      "context": self.in_context.text().strip()},
            "record_type": self.cb_record.currentText(),
            "subject": {"situation": self.in_situation.toPlainText().strip(),
                        "quote": self.in_quote.toPlainText().strip(),
                        "action": self.in_action.toPlainText().strip(),
                        "result": self.in_result.toPlainText().strip()},
            "observation": {"demeanor": {k: sl.value() for k, sl in self.sliders.items()},
                            "emotion": self.cb_emotion.currentData(),
                            "notes": self.in_notes.toPlainText().strip()},
            "evaluation": {"strengths": self.in_strengths.toPlainText().strip(),
                           "weaknesses": self.in_weaknesses.toPlainText().strip(),
                           "summary": self.in_summary.text().strip()},
            "tags": [t.strip() for t in self.in_tags.text().replace("，", ",").split(",") if t.strip()],
            "follow_up": self.in_follow.toPlainText().strip(),
            "sensitive": sensitive,
            "related_person_refs": [r.strip() for r in
                                    self.in_related.text().replace("，", ",").split(",") if r.strip()],
        }
        return rec

    def save(self):
        rec = self.build_record()
        errs = ingest.validate(rec, self.schema)
        if errs:
            warn("校验未通过", "请修正后重试：\n" + "\n".join(f"• {e}" for e in errs), self)
            return
        ref_override = self.in_ref.text().strip() or None
        ok, msgs = ingest.ingest(rec, ref_override=ref_override, add_alias=True, overwrite=False)
        if not ok:
            warn("保存失败", "\n".join(msgs), self)
            return
        info("保存成功", "\n".join(msgs), self)
        if rec["sensitive"]:
            self.clear_form(keep_people=True)
        elif self.cb_commit.isChecked():
            self._git_commit(rec, msgs)
        self.clear_form(keep_people=True)
        if self.on_saved:
            self.on_saved()

    def _git_commit(self, rec: dict, msgs: list[str]):
        ref = rec["person"]["ref"]
        day = rec["created_at"][:10]
        brief = rec["scene"].get("context") or rec["record_type"]
        targets = ["data/memories", "data/meta/register.json",
                   "data/meta/pseudonyms.md", "data/aliases.md"]
        try:
            r = subprocess.run(["git", "-C", str(common.ROOT), "add", "--"] + targets,
                               capture_output=True, text=True)
            if r.returncode != 0:
                warn("git add 失败", r.stderr.strip(), self)
                return
            r = subprocess.run(["git", "-C", str(common.ROOT), "commit", "-m",
                                f"mem: 录入 {ref} {day} {brief}"],
                               capture_output=True, text=True)
            info("git 提交", (r.stdout or r.stderr).strip(), self)
        except FileNotFoundError:
            warn("git 未安装", "未找到 git，请手动执行上方提交建议。", self)

    def clear_form(self, keep_people: bool = False):
        self.cb_name.setCurrentIndex(0)
        self.in_relation.clear()
        self.cb_new.setChecked(False)
        self.in_pseudo.clear()
        self.in_ref.clear()
        self.dt.setDateTime(QDateTime.currentDateTime())
        self.cb_record.setCurrentIndex(0)
        self.cb_scene_type.setCurrentIndex(0)
        self.in_location.clear()
        self.in_context.clear()
        for w in (self.in_situation, self.in_quote, self.in_action, self.in_result):
            w.clear()
        for sl in self.sliders.values():
            sl.setValue(3)
        self.cb_emotion.setCurrentIndex(0)
        self.in_notes.clear()
        for w in (self.in_strengths, self.in_weaknesses, self.in_follow):
            w.clear()
        self.in_summary.clear()
        self.in_tags.clear()
        self.in_related.clear()
        self.cb_sensitive.setChecked(False)
        self.cb_commit.setChecked(False)
        if not keep_people:
            self.refresh_people()