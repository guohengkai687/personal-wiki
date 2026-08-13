# personal-wiki

个人人际关系记忆与人格分析系统 —— 以「文件即数据库、opencode 即 Agent、静态页即看板」为原则的极简落地项目。

- 设计文档：见 [DESIGN.md](DESIGN.md)
- 当前阶段：**P0 骨架 + 桌面 GUI**（`personal-wiki.exe` 提供完整界面化输入与展示）

## 目录结构

```
data/            ★ 数据唯一事实源（入库）
  aliases.md       人名归一化映射
  people/          人物档案（Agent 生成）
  memories/        原始记忆 JSON（摄入层落盘）
  private/         私密记忆（gitignore，永不入库）
  meta/            register.json（生成物）、pseudonyms.md（展示脱敏）
app/              应用包（源码 → 打包 personal-wiki.exe）
  main.py          入口：默认启动桌面 GUI；源码下带参数走 CLI
  gui/             PySide6 界面（概览 / 录入 / 索引 / 看板 / 分析 五页签）
  assets/          打包素材：Tabler 图标 + Inter / Noto Sans SC 字体（见其 README）
input/            HTML 录入表单（可选辅助，纯前端生成器，不写盘）
  index.html       浏览器打开 → 填写 → 下载记忆 JSON
  form-schema.json 字段 schema（驱动表单、GUI 录入与校验）
pipeline/        Agent 工作区 + 脚本
  helpers/          common.py（路径/别名/编码）ingest.py（摄入）build.py（看板）
dashboard/       展示层（P2 进行中）
docs/            使用手册（P4）、分析维度说明（P1）
```

## 快速开始

### 1. 环境
- Windows：双击 `personal-wiki.exe`（PySide6 桌面界面，57MB 左右，离线可用）
- 源码方式：`pip install PySide6 jinja2`（可选 `pypinyin`）
- ECharts 已 vendor 到 `dashboard/assets/echarts.min.js`（本地离线可用）

### 2. 日常使用（GUI 主入口）
双击运行后弹出窗口，五个页签：

| 页签 | 功能 |
|---|---|
| 概览 | 人物/记忆统计卡 + 人物表格（形象/假名/ref/关系/记忆数/最近互动/档案），打开即自动刷新，双击看档案 |
| 录入 | 四区块表单（基础信息 / STAR / 人物观察 / 评价与后续）→ 校验 → 落盘 → 重算索引 → 可选 git 提交 |
| 索引 | register 状态、月度分布、私密记忆数；重算 register、打开数据目录 |
| 看板 | 生成 / 重新生成静态看板，一键在浏览器打开 |
| 分析 | 生成「分析 <ref>」opencode 指令并复制；待跟进事项清单 |

> 私密记忆：录入页勾选「敏感/私密」→ 仅落盘 `data/private/`，**永不进 git、register、分析与看板**。

### 3. 命令行（源码模式）
```
python app/main.py --menu              # 传统交互菜单
python app/main.py --people            # 人物概览
python app/main.py --reindex           # 重算 register.json
python app/main.py --build             # 生成看板
python app/main.py --pw-root D:\path   # 指定数据根目录（等价环境变量 PW_ROOT）
```
exe 内带 `--reindex / --build / --entry / --people` 时仍启动 GUI，并自动定位到对应页 / 执行动作。

### 4. HTML 表单（可选辅助）
浏览器打开 `input/index.html` → 填写 → 下载 `.json`，然后交给 exe/脚本摄入：
   ```
   python pipeline/helpers/ingest.py <下载的.json>
   # 新人物需指定 ref：
   python pipeline/helpers/ingest.py --ref wangwu --add-alias <下载的.json>
   ```

### 5. 源码维护命令
```
python pipeline/helpers/ingest.py --reindex        # 重算 register.json（改档案后调用）
python pipeline/helpers/ingest.py --validate <f>   # 只校验不落盘
python pipeline/helpers/build.py                   # 生成看板
```

### 6. 重新打包 exe
```
pip install pyinstaller PySide6
pyinstaller --noconfirm --windowed --onefile --name personal-wiki --paths . `
  --add-data "app\assets;app\assets" app\main.py
copy dist\personal-wiki.exe .     # 放到仓库根目录即可使用
```

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

- [x] P0 骨架：README / DESIGN / .gitignore / 目录 / app（exe 主入口）/ ingest+build / 示例记忆
- [ ] P1 Agent 分析：analyze.md 定稿，产出首份人物档案
- [ ] P2 看板：templates + build.py，列表页 + 详情页
- [ ] P3 打磨：搜索/筛选/雷达交互/明暗主题/回顾机制
- [ ] P4 常态化：全流程写入使用手册
