---
name: daily-hot-article
description: 搜集今日全网热点，提炼 Top 5，等待用户选择。当用户提到"今日文章"、"热点文章"、"生成今日文章"、"今天有什么热点"、"写一篇今日热点"、"把今天的热点写成文章"等时触发。选定热点后自动生成头条文章（.md 格式）。
---

# 今日热点 → 头条文章

一站式流程：搜集热点 → 提炼 Top 5 → 用户确认 → 素材调研 → 文章写作 → 导出 md。（不插入配图）

## 前置依赖

- **newsnow CLI**（需全局安装）：`npm install -g newsnow`
- **Python 依赖**：`pip install requests`
- **tianapi-toutiao skill**（**必需**）：用于获取头条热搜榜热度指数，详见 `../tianapi-toutiao/SKILL.md`

## 工作流程

按顺序执行以下 6 步，执行每一步时**先读取对应的详情文件**获取完整指令：

| 步骤 | 内容 | 详情文件 |
|------|------|----------|
| 1 | **搜集热点** — 运行 `python ./scripts/fetch_and_analyze.py` | `references/step1-fetch.md` |
| 2 | **提炼 Top 5** — AI 二次审视 + 五维点击吸引力评分 | `references/step2-top5.md` |
| 3 | **用户确认选题** — 等待用户选择，不要自动选 | `references/step3-confirm.md` |
| 4 | **素材深度调研** — 纵向脉络 + 横向切片 + 文章骨架 | `references/step4-research.md` |
| 5 | **生成头条文章** — 犀利尖锐风格，约 800 字 | `references/step5-writing.md` |
| 6 | **输出结果** — 文件路径 + 文章概要 | `references/step8-output.md` |

## 写作规范

文章写作严格执行 `./khazix-writer/SKILL.md` 中的全部规范（四阶段工作流、禁用词列表、风格要求等）。

## 输出约束

- **标题不超过28字**（含标点），必须有锋芒
- **只输出 .md**，不生成 HTML、PDF 或 Docx
- 文章风格：**犀利、尖锐、发人深思**
- 约 800 字，极限不超过 1000 字
- 每个核心观点必须有事实/数据支撑
- **不插入配图**，纯文本输出

## 文件结构

```
daily-hot-article/
├── SKILL.md                       ← 入口文件（你正在读）
├── references/                    ← 渐进式披露详情
│   ├── step1-fetch.md
│   ├── step2-top5.md
│   ├── step3-confirm.md
│   ├── step4-research.md
│   ├── step5-writing.md
│   ├── step6-images.md
│   ├── step7-verify.md
│   └── step8-output.md
├── scripts/
│   ├── fetch_and_analyze.py       ← 热点抓取+交叉分析
│   ├── image_search.py            ← 图片搜索模块
│   ├── verify_md_images.py        ← MD 图片验证脚本
│   └── md_to_pdf.py               ← MD→PDF 转换（备用）
└── khazix-writer/
    ├── SKILL.md                   ← 鲲写作完整规范
    ├── scripts/
    │   └── md_to_pdf.py
    └── references/
        ├── style_examples.md
        └── content_methodology.md
```

## 注意事项

- newsnow 某源拉取失败时跳过该源继续，不影响整体
- Top 5 核心标准是"点击吸引力"而非"纯热度"——有刺痛感、有争议、有信息差优先
- 素材调研至少查 3-5 个来源，交叉验证关键事实
- 用户可以不选 Top 5，自己指定任意热点话题
- 头条热度指数获取为强制步骤，由 tianapi-toutiao skill 自动完成
