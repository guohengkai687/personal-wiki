# personal-wiki

个人人际关系记忆与人格分析系统 —— 以「文件即数据库、opencode 即 Agent、静态页即看板」为原则的极简落地项目。

- 设计文档：见 [DESIGN.md](DESIGN.md)
- 当前阶段：**P0 骨架**（录入表单 + 摄入脚本 + 数据骨架已可用）

## 目录结构

```
data/            ★ 数据唯一事实源（入库）
  aliases.md       人名归一化映射
  people/          人物档案（Agent 生成）
  memories/        原始记忆 JSON（摄入层落盘）
  private/         私密记忆（gitignore，永不入库）
  meta/            register.json（生成物）、pseudonyms.md（展示脱敏）
input/           录入表单（纯前端生成器，不写盘）
  index.html       浏览器打开 → 填写 → 下载记忆 JSON
  form-schema.json 字段 schema（驱动表单与校验）
pipeline/        Agent 工作区 + 脚本
  helpers/ingest.py  摄入：校验 → 归一化 → 落盘 → 重算 register
dashboard/       展示层（P2 进行中）
docs/            使用手册（P4）、分析维度说明（P1）
```

## 快速开始（P0）

### 1. 环境
- Python 3（建议 ≥3.9）+ Jinja2：`pip install jinja2`
- 可选 pypinyin（人名自动转拼音 ref，装不装都能用）：`pip install pypinyin`
- ECharts 已 vendor 到 `dashboard/assets/echarts.min.js`（本地离线可用）

### 2. 录入一条记忆
1. 浏览器打开 `input/index.html`（双击即可，无服务器）；
2. 按四区块填写：基础信息 / 事件主体(STAR) / 人物观察 / 评价与后续；
3. 点「校验并生成 JSON」→ 浏览器自动下载 `.json` 文件；
4. 摄入：
   ```
   python pipeline/helpers/ingest.py <下载的.json>
   # 新人物需指定 ref：
   python pipeline/helpers/ingest.py --ref wangwu --add-alias <下载的.json>
   ```
5. 按脚本给出的「提交建议」人工确认后提交 git（脚本不自动 commit）。

> 私密记忆：表单里勾选「敏感/私密」，落盘 `data/private/`，**永不进 git、register、分析与看板**。

### 3. 维护命令
```
python pipeline/helpers/ingest.py --reindex        # 重算 register.json（改档案后调用）
python pipeline/helpers/ingest.py --validate <f>   # 只校验不落盘
```

## 提交约定

| 前缀 | 场景 | 示例 |
|---|---|---|
| `docs:` | 改设计/文档 | `docs: 输入表单字段表更新` |
| `mem:` | 新增/修正记忆 | `mem: 录入 zhangsan 20260813 复盘记录` |
| `analysis:` | 档案/分析更新 | `analysis: zhangsan 画像更新（证据 m1,m4）` |
| `feat:` | 表单/看板/构建脚本改动 | `feat: 详情页新增情绪时间线` |

提交信息一律用 **ref / 假名**，禁止出现真名。

## ⚠ 隐私须知

`data/` 存真名并纳入 git 管理（可追溯）。**仓库仅限本机私有，严禁推到公开远端或共享他人**。
展示看板 `dashboard/output/` 会按 `pseudonyms.md` 脱敏为假名，且本身不入库。

## 路线图

- [x] P0 骨架：README / DESIGN / .gitignore / 目录 / 表单 + schema / ingest.py / 示例记忆
- [ ] P1 Agent 分析：analyze.md 定稿，产出首份人物档案
- [ ] P2 看板：templates + build.py，列表页 + 详情页
- [ ] P3 打磨：搜索/筛选/雷达交互/明暗主题/回顾机制
- [ ] P4 常态化：全流程写入使用手册
