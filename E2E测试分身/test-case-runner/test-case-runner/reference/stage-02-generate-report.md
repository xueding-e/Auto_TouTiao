# 阶段二：报告生成

> ⛔ **进入本阶段前，必须已用 Read 工具完整读取本文件全文 + `assets/sample-report.html` 全文**。这是全局硬性约束，不可跳过。凭记忆执行 = 违规执行。
>
> ⏸️ **准入条件**：阶段一已执行完毕，所有用例已完成即时双重验证判定，每个用例具有 `final_result`（PASS/FAIL/NOT_RUN）。
>
> 本阶段为最终阶段，完成后输出产物文件。
>
> 📌 **格式参考**：完整报告样例见 [`assets/sample-report.md`](../assets/sample-report.md)（MD 五段式）和 [`assets/sample-report.html`](../assets/sample-report.html)（HTML 交互式模板）。**MD 格式以 sample-report.md 为样例，HTML 以 sample-report.html 为模板**。本文件定义生成流程、计算公式、红线规则、字段映射和自检清单。

---

## 🔴 3.0 准入前强制校验（不可跳过 / 操作步骤强制执行）

> ⛔ **本节已改为操作步骤强制执行模式。不再依赖"检查清单自评"，而是用具体工具调用强制验证。**

### 3.0.0 步骤 A: 读取模板（强制执行，不可跳过）

用 Read 工具**不限 limit（或 limit ≥ 3000）** 读取 `assets/sample-report.html`。读取完成后，必须同时在工具响应中确认以下两个信号，缺一不可：

| 信号 | 确认方式 | 含义 |
|------|---------|------|
| S1 读到末尾 | 检查 Read 响应是否包含最后一段内容（必须包含 `function openLightbox`、`closeLightbox`、`Escape` 等 JS 关键词） | Read 确实覆盖了文件末尾 |
| S2 结构完整 | 检查 Read 响应是否同时包含：CSS 变量块 `:root{`、`.case-panel` 模板、`.defect-card` 模板、`.artifact-index` 模板、`<script>` 交互代码块 | Read 覆盖了全部关键结构段 |

> ⛔ **S1 不通过（未读到末尾）**: 重新 Read，直到读到末尾为止。**严禁用"我可以推断剩余部分"的理由跳过。**
>
> ⛔ **S2 不通过（结构不完整）**: 说明 limit 太小导致中间截断，增大 limit 重新 Read，直到一次调用覆盖所有关键结构段。

### 3.0.1 步骤 B: 确认模板总行数

Read 完成后，记录模板总行数（如 `sample-report.html` 为 644 行）。后续生成时，不得创建结构少于该模板的 HTML。

### 3.0.2 原有校验（在步骤 A/B 之后执行）

> **数据来源**: 以下校验和后续报告生成均从 `progress.yaml` + `execution-results.yaml` 读取数据,**不依赖对话记忆**。两个文件位于 `screenshots/<模块名>-<运行编号>/` 下。

| # | 校验项 | 校验方式 | 通过标准 |
|---|--------|---------|---------|
| 1 | 全量执行 | Read `progress.yaml`,遍历 `cases` 统计 `value == null` 的用例数 | 无 `value == null` 的用例(即全部完成) |
| 2 | 用例无遗漏 | 对比 `progress.yaml` 的 `cases` 顶级 key 集合与 `.md` 用例编号 | 每条用例在 `progress.yaml` 中均有 `final_result` 非 null 的值 |
| 3 | NOT_RUN 合法性 | Read `execution-results.yaml` 中所有 `not_run_reason` 非 null 的条目 | 每条 NOT_RUN 的原因必须是技术性原因（浏览器断连/MCP 不可用/页面崩溃/登录态丢失），不得出现"优先级低""类似功能""关键流程已覆盖""时间不足""Token限制"等非技术性理由 |
| 4 | 截图覆盖（若用户要求截图） | 统计 `execution-results.yaml` 中 `screenshot_path` 非 null 的条目数 | 已执行用例（PASS + FAIL）的截图覆盖率 ≥ 80% |

### 3.0.3 校验不通过时的处理

```
if 步骤A S1/S2 未通过: → 🔴 重新 Read 直到通过（这是最高优先级阻断项）
if 校验1不通过:        → 🔴 回阶段一，继续执行剩余 final_result == null 的用例
if 校验2不通过:        → 🔴 回阶段一，补充遗漏用例的执行
if 校验3不通过:        → 🔴 将违规 NOT_RUN 用例改为 null（同步更新 progress.yaml），回阶段一执行
if 校验4不通过:        → ⚠️ 允许继续，报告中注明截图缺失原因
```

---

## 3.1 Markdown 报告生成

### 3.1.0 生成前

用 Read 工具读取 [`assets/sample-report.md`](../assets/sample-report.md) 作为格式参考。**不要复制其内容**，仅参考其结构和样式。

### 3.1.1 五段式结构（固定顺序，不可调换）

| 段落 | 内容 |
|------|------|
| 一、执行摘要 | 总览统计（含失败类型拆分：├执行失败 / └内容不一致） + 功能点覆盖 + 按优先级统计 + 执行环境 |
| 二、功能点测试矩阵 | FP→用例映射与状态总览 |
| 三、用例执行明细 | 逐用例步骤级结果（含双重验证：MCP 操作结果 + 内容验证） |
| 四、缺陷汇总 | 失败用例的缺陷记录（含失败类型） |
| 五、可追溯性附录 | 产物索引 + 数据链路校验 |

### 3.1.2 报告头

```markdown
# <模块名> - E2E 测试执行报告

> **报告生成时间**: <ISO8601>  ← 必须用 `Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"` 精确获取，禁止估算
> **目标 URL**: <URL>
> **报告生成者**: UI自动化测试
```

### 3.1.3 字段数据来源映射

> ⛔ 以下字段有明确的唯一数据来源，不可自行推断。
>
> 执行结果相关字段从 `progress.yaml` + `execution-results.yaml` 读取,**不依赖对话记忆**。`execution-results.yaml` 仅含 FAIL/NOT_RUN 用例条目(PASS 不记录),读取失败用例详情时直接按 case_id 查找即可。

| 报告字段 | 数据来源 | 说明 |
|---------|---------|------|
| 模块名 | `progress.yaml` 的 `module` 或 `.md` 文件名 | |
| 目标 URL | `progress.yaml` 的 `url`（若 `null` 则从用例上下文推断） | |
| 功能点ID | `.page-structure.yaml` 的 `features[].id` | 如 FP-001 |
| 功能点名称 | `.page-structure.yaml` 的 `features[].name` | |
| 关联用例 | `.page-structure.yaml` 的 `features[].cases` | 逗号分隔的用例编号列表 |
| 用例编号/步骤/预期 | `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md` 的测试用例表格 | |
| **用例执行结果** | `progress.yaml` 的 `cases[<id>]` 值 | PASS/FAIL/NOT_RUN(值为 null 表示未完成,不应出现在阶段C) |
| **报告头统计**(总数/通过/失败/未执行/通过率) | 从 `progress.yaml` 的 `cases` 实时计算 | 遍历 `cases` 统计: total=key总数, pass=PASS数, fail=FAIL数, not_run=NOT_RUN数, 通过率=pass/(pass+fail)*100% |
| **失败用例的失败步骤** | `execution-results.yaml` 的 `results[<id>].failed_step` | FAIL 时填,对应报告"步骤"列 |
| **失败用例的失败现象(snapshot 实际内容)** | `execution-results.yaml` 的 `results[<id>].error` | FAIL 时填,对应报告"snapshot 实际内容"列 |
| **失败用例的差异说明** | `execution-results.yaml` 的 `results[<id>].defect.expected_vs_actual` | FAIL 时填,对应报告"差异说明" |
| **缺陷描述** | `execution-results.yaml` 的 `results[<id>].defect.description` | FAIL 时填,对应报告"缺陷描述"列 |
| **缺陷严重程度** | `execution-results.yaml` 的 `results[<id>].defect.severity` | 高/中/低 |
| **失败类型** | `execution-results.yaml` 的 `results[<id>].defect.failure_type` | 执行失败/内容不一致 |
| **NOT_RUN 原因** | `execution-results.yaml` 的 `results[<id>].not_run_reason` | NOT_RUN 时填 |
| **截图文件名** | `execution-results.yaml` 的 `results[<id>].screenshot_path` | 从绝对路径提取文件名;null 时填"—" |
| PASS 用例的"snapshot 实际内容" | AI 根据 final_result=PASS 生成"与预期一致"描述 | 无需从 yaml 读取详细 snapshot |

### 3.1.4 计算公式与规则

| 指标 | 公式/规则 |
|------|----------|
| 通过率 | `PASS数 / (PASS数 + FAIL数) × 100%` |
| 内容验证通过率 | `内容验证 PASS 数 / 已执行 snapshot 验证的用例数 × 100%` |
| 缺陷生成 | **仅 FAIL 的用例**产生缺陷记录（BUG-NNN 格式，按发现顺序编号） |
| NOT_RUN | 仅限技术性原因使用，必须如实填写具体技术原因 |

#### ⛔ NOT_RUN 红线

- 仅允许：浏览器断连、Chrome DevTools MCP 不可用、页面崩溃、登录态丢失
- **严禁**："执行时间过长""已被其他用例覆盖""优先级低""功能类似"等非技术性理由
- **严禁**：用"已完成核心验证""主要流程已覆盖"等话术掩盖未执行
- "说明"字段必须如实填写具体技术原因，不得写"未执行""时间不足"等模糊描述

#### ⛔ 产物索引红线

| 产物类型 | 文件路径 | 说明（固定值，不可改） |
|---------|---------|------|
| 原始用例 | `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md` | `test-case-generator 产出` |
| 功能点清单 | `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.page-structure.yaml` | `test-case-generator 产出` |
| 截图目录 | `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/` | `执行证据` |
| 测试报告 | `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.md` | `本报告` |

> ⚠️ **常见错误**：截图目录路径错误、产物索引中残留 playwright-cli 等已废弃工具引用。

### 3.1.5 状态图标对照

| 图标 | 状态 | 用于 |
|------|------|------|
| ✅ | PASS | 用例最终结果、步骤判定、功能点全部通过、内容验证一致 |
| ❌ | FAIL | 用例最终结果、步骤判定、内容验证不一致 |
| 👁️ | 内容不一致 | FAIL 细分标记（MCP 操作成功但 snapshot 不符） |
| 🔧 | 执行失败 | FAIL 细分标记（MCP 操作层面失败） |
| ⬜ | NOT_RUN | 用例结果、功能点未执行 |
| ⚠️ | 部分通过 | 功能点状态（该 FP 下存在 PASS 但也存在 FAIL/NOT_RUN） |

### 3.1.6 功能点状态判定

| 图标 | 含义 | 判定条件 |
|------|------|---------|
| ✅ | 全部通过 | 该功能点下所有用例均为 PASS |
| ⚠️ | 部分通过 | 该功能点下存在 PASS，但也存在 FAIL/NOT_RUN |
| ❌ | 全部失败 | 该功能点下所有用例均为 FAIL |
| ⬜ | 未执行 | 该功能点下所有用例均为 NOT_RUN |

### 3.1.7 步骤明细表字段定义

> 每条用例的步骤明细表包含以下 7 列，列名固定不可改。

| 字段 | 来源 | 说明 |
|------|------|------|
| 步骤 | 阶段一用例步骤序号 | 与测试用例步骤编号对齐 |
| 操作 | 用例步骤的自然语言描述 | 来自 test-case-generator 的"点击步骤"列 |
| 预期结果 | test-case-generator 的"预期结果" | 拆分为逐步骤的预期 |
| snapshot 实际内容 | Chrome DevTools MCP `take_snapshot` 输出 | 页面 a11y 树文本关键内容 |
| 内容验证 | AI 语义判断 | 语义满足 / **不满足**（写明差异）/ 无法判断 |
| 判定 | 逐步骤判定 | ✅ / ❌ / —，MCP 操作通过且 AI 语义满足为 ✅ |
| 证据 | 截图文件名 | 无截图填 "—"（默认不截图属正常） |

### 3.1.8 缺陷字段说明

| 字段 | 说明 |
|------|------|
| 缺陷ID | BUG-NNN 格式，按发现顺序编号 |
| 关联用例 | 触发该缺陷的用例编号 |
| 功能点 | 关联的功能点ID |
| 失败类型 | **执行失败** / **内容不一致** |
| 严重程度 | 高=核心功能不可用；中=功能异常但有变通；低=UI/体验问题 |
| 缺陷描述 | 简明描述缺陷现象 |
| 状态 | 新发现 / 已确认 / 已修复 / 待确认 |

### 3.1.9 截图引用格式

报告位于 `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/`，截图位于 `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/`，相对路径为：

```markdown
![描述](../screenshots/<模块名>-<运行编号>/<文件名>.png)
```

### 3.1.10 输出文件

写入 `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.md`

---

## 3.2 HTML 报告生成与校验

> 模板已在 3.0 校验0 中读取，此处直接基于模板生成。

### 3.2.1 生成铁律

| # | 规则 |
|---|------|
| 🔴1 | **复制模板为基底**：CSS 块与 DOM 骨架**一行不改**。 |
| 🔴2 | **仅替换数据**：允许修改的只有 `<title>`/`<h1>` 模块名、`.meta` 元信息、`.header-stats` 数值、`.stat-cards` 卡片数值、各 `<table>` 行、`.case-panel` 面板内容、`.defect-card` 缺陷信息、`.artifact-index` 文件树、截图 `src`。**其他一律不可改。** |
| 🔴3 | **截图必须有 `<img>` 标签（若用户要求截图）**：用户要求截图时，有截图的用例必须包含 `<img class="screenshot-thumb" src="..." onclick="openLightbox(this.src)">`。用户未要求截图时，无截图属正常。 |
| 🔴4 | **截图路径格式**：`../screenshots/<模块名>-<运行编号>/<文件名>.png`，**严禁**使用 `.playwright-cli/` 等路径。 |
| 🔴5 | **数据与 MD 报告一致**：HTML 报告的所有统计数据、用例结果、缺陷信息必须与 MD 报告完全一致。 |
| 🔴6 | **单文件内联**：所有 CSS/JS 内联在 `<style>` / `<script>` 标签中，不引用任何外部文件。 |

### 🔴 HTML 生成后自检（强制执行，不可跳过）

> ⛔ **HTML 文件写入磁盘后，必须立即用以下 Grep 命令逐项验证。每一项都必须返回预期结果，否则必须修正后重新验证。**

#### 自检操作步骤

**步骤 1: 用 Grep 验证模板结构完整性**

对生成的 HTML 文件执行以下 Grep 命令（逐条执行，缺一不可）：

| # | Grep 命令 | 预期结果 | 不通过时的含义 |
|---|----------|---------|--------------|
| 1 | `Grep "case-panel" <报告路径>` - output_mode: count | count ≥ 总用例数 | 缺失用例面板 |
| 2 | `Grep "case-header" <报告路径>` - output_mode: count | count ≥ 总用例数 | 缺失用例头部 |
| 3 | `Grep "case-body" <报告路径>` - output_mode: count | count ≥ 总用例数 | 缺失用例内容区 |
| 4 | `Grep "toggle-arrow" <报告路径>` - output_mode: count | count ≥ 总用例数 | 缺失折叠箭头 |
| 5 | `Grep "dual-summary" <报告路径>` - output_mode: count | count ≥ (PASS数 + FAIL数) | 缺失双重验证标签（PASS 和 FAIL 用例必须有） |
| 6 | `Grep "visual-inconsistency" <报告路径>` - output_mode: count | count ≥ FAIL(内容不一致)数 | 缺失差异分析块 |
| 7 | `Grep "defect-card" <报告路径>` - output_mode: count | count ≥ 缺陷数 | 缺失缺陷卡片 |
| 8 | `Grep "artifact-index" <报告路径>` - output_mode: count | count = 1 | 缺失产物索引 |
| 9 | `Grep "function openLightbox" <报告路径>` - output_mode: count | count = 1 | 缺失灯箱 JS |
| 10 | `Grep "closeLightbox" <报告路径>` - output_mode: count | count = 1 | 缺失灯箱关闭 JS |
| 11 | `Grep "nav-link" <报告路径>` - output_mode: count | count = 5 | 缺失侧边栏导航（固定5项） |
| 12 | `Grep "open\(" <报告路径>` - output_mode: count | count = 1 | `.case-panel.open` 样式缺失，折叠功能不工作 |

**步骤 2: 用 Grep 验证无自创类名**

| # | Grep 命令（精确匹配） | 预期结果 |
|---|---------------------|---------|
| 13 | `Grep "case-card\|s-pass\|pass-badge\|container\|case-block\|coverage-item\|p0-badge" <报告路径>` - output_mode: count | count = 0 |

> ⛔ **步骤 1 第 1-12 项和步骤 2 第 13 项全部通过 → 方可确认 HTML 是基于模板生成的数据替换版本。**

**步骤 3: 数据一致性校验**

| # | 校验项 | 方式 |
|---|--------|------|
| 14 | HTML 中 FAIL 用例数 = MD 报告中 FAIL 数 | 对比 Grep `status-fail` count 与 MD 报告数据 |
| 15 | HTML 中 PASS 用例数 = MD 报告中 PASS 数 | 对比 Grep `status-pass` count 与 MD 报告数据 |

#### 自检失败处理

```
if 步骤1 任一项不通过: → 🔴 说明 HTML 不是基于模板生成的。立即重读 assets/sample-report.html 全文，复制模板为基底重新生成。
if 步骤2 不通过:     → 🔴 说明 HTML 中使用了自创类名。删除自创类名，改用模板中的标准类名。
if 步骤3 不通过:     → 🔴 HTML 与 MD 数据不一致，修正后重新生成。
if 全部通过:          → ✅ 确认通过，输出报告文件路径给用户。
```

### 截图完整性校验（若用户要求截图才执行）

> 仅在用户明确要求截图的场景下执行以下校验。

- 从阶段一执行记录中提取所有截图文件路径列表
- 使用 Glob 确认每个截图文件在磁盘上真实存在
- 检查 HTML 中每条 `<img>` 引用的截图路径均在列表中，列表中每张截图均有引用
- 校验完成后输出报告：`截图总数: N | HTML引用: N | 缺失引用: N | 无效引用: N`

### 输出文件

写入 `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.html`

---

## 3.3 输出产物清单

| 文件 | 路径 | 说明 |
|------|------|------|
| **测试执行报告**(主) | `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.md` | 五段式结构化报告，含双重验证结果 |
| **渲染版报告** | `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.html` | 交互式 HTML 报告，浏览器直接打开 |

---

## 失败处理

| 场景 | 处理 |
|------|------|
| test-case-generator 产物不存在 | 报错，提示先运行 test-case-generator skill |
| Chrome DevTools MCP 不可用 | 所有用例标记 `NOT_RUN`，报告注明"Chrome DevTools MCP 不可用" |
| 目标 URL 不可访问 | 所有用例标记 `NOT_RUN`，报告注明"目标 URL 不可访问" |

---

> 🎉 **报告生成完毕**。产物：
> - `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.md`
> - `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.html`
>
> 参考示例：[assets/sample-report.md](../assets/sample-report.md) | [assets/sample-report.html](../assets/sample-report.html)
