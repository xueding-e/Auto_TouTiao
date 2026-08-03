# 测试分身 - 上下文恢复索引

> 本文件是**测试分身编排者**在上下文丢失/压缩/会话中断后恢复执行的**唯一入口**。
>
> ⛔ 恢复时必须严格按本文件流程：**先按 §1 yaml 规则识别当前阶段 → 再按 §2 yaml 索引读取必需文件 → 最后按 §3 md 步骤从断点继续**。禁止凭记忆执行。
>
> 本文件仅覆盖 **UI 测试（E2E）** 流程；接口测试、单元测试由 `test-api-runner` / `test-unit-runner` 技能内部自管理恢复，不在此索引范围内。

---

## §1 阶段识别规则（yaml 字段化）

> AI 直接按 `checks` 顺序执行 Glob 检查，第一个 `hit: true` 的规则即为当前阶段。

```yaml
# 阶段识别：按顺序检查，首个命中即停止
stage_detection:
  - id: C_done
    description: 阶段C 完成（流程已结束）
    check:
      tool: glob
      pattern: "openspec/sdlc-agent/E2E测试分身/ui-tests/reports/*-report.html"
      condition: exists
    on_hit:
      stage: C
      status: done
      next_action: 告知用户报告路径，流程结束

  - id: C_in_progress
    description: 阶段C 进行中（MD 报告已生成，HTML 未生成或自检未过）
    check:
      tool: glob
      pattern: "openspec/sdlc-agent/E2E测试分身/ui-tests/reports/*-report.md"
      condition: exists
    on_hit:
      stage: C
      status: in_progress
      next_action: 进入 §3 阶段C 恢复步骤

  - id: B_in_progress
    description: 阶段B 进行中（progress.yaml 存在且未全部 COMPLETE）
    check:
      tool: glob
      pattern: "openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-*/progress.yaml"
      condition: exists
    on_hit:
      stage: B
      status: in_progress
      next_action: 进入 §3 阶段B 恢复步骤（Read progress.yaml 做断点定位）

  - id: A_done
    description: 阶段A 完成（yaml 已生成，准备进入阶段B）
    check:
      tool: glob
      pattern: "openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/*.page-structure.yaml"
      condition: exists
    on_hit:
      stage: A
      status: done
      next_action: 询问用户确认测试用例 → 进入 §3 阶段B 恢复步骤

  - id: A_in_progress
    description: 阶段A 进行中（.md 已生成，yaml 未生成）
    check:
      tool: glob
      pattern: "openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/*.md"
      condition: exists
    on_hit:
      stage: A
      status: in_progress
      next_action: 进入 §3 阶段A 恢复步骤（续生成 yaml）

  - id: A_not_started
    description: 阶段A 未开始（无任何产物）
    check:
      tool: glob
      pattern: "openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/*.md"
      condition: not_exists
    on_hit:
      stage: A
      status: not_started
      next_action: 询问用户输入源 → 从头开始阶段A

# 阶段B 内部断点定位（仅 stage=B 时执行）
breakpoint_detection:
  primary_source:
    file: "openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/progress.yaml"
    description: Read progress.yaml,遍历 cases 找第一个 value == null 的用例(即 final_result 未判定)
    authority: 唯一持久化依据
    note: |
      - 截图默认关闭时无截图文件,不作为恢复依据
      - progress.yaml 是阶段B 唯一可靠的断点定位源
      - 二态模型: null = 未完成(断点);PASS/FAIL/NOT_RUN = 已完成
  fallback_source:
    file: "screenshots/<模块名>-<运行编号>/ 下的截图文件名"
    description: 仅当 progress.yaml 不存在时,列出截图文件名推断已执行用例
    authority: 兜底
    note: progress.yaml 不存在 = 阶段B 未正确初始化,应回阶段A 确认或重新初始化
  conflict_resolution: "无冲突场景 - progress.yaml 是唯一持久化源"
```

---

## §2 文件索引清单（yaml 字段化）

> AI 按 `stage_required` 标记读取对应阶段的文件。`必读` = 必须完整 Read；`按需` = 仅在特定情况下读取；`强制` = 有特殊 Read 要求（如 limit 下限）。

```yaml
# 编排者指令（全阶段必读）
orchestrator_files:
  - path: "测试分身.md"
    stage_required: [A, B, C]
    read_level: 必读
    purpose: 编排者主指令：测试类型判定、流程顺序、用户确认机制
  - path: ".trae/skills/test-case-runner/reference/context-recovery.md"
    stage_required: [A, B, C]
    read_level: 必读
    purpose: 本文件：阶段识别 + 文件索引

# test-case-generator skill 文件（阶段A 必读）
generator_files:
  - path: ".trae/skills/test-case-generator/SKILL.md"
    stage_required: [A]
    read_level: 必读
    purpose: skill 主文件：输入模式、关键约束、yaml 规范、ai_verification_benchmarks 语法
  - path: ".trae/skills/test-case-generator/reference/mode1-document.md"
    stage_required: [A]
    read_level: 按需
    condition: "输入模式为 document"
    purpose: 文档解析、功能点提取规则
  - path: ".trae/skills/test-case-generator/reference/mode2-url.md"
    stage_required: [A]
    read_level: 按需
    condition: "输入模式为 url"
    purpose: 浏览器探索流程、MCP 命令清单、可点击点提取
  - path: ".trae/skills/test-case-generator/reference/mode3-convert.md"
    stage_required: [A]
    read_level: 按需
    condition: "输入模式为 convert"
    purpose: 已有用例解析、字段映射、转换补全
  - path: ".trae/skills/test-case-generator/reference/examples.md"
    stage_required: [A]
    read_level: 按需
    condition: "不确定输出格式时"
    purpose: 三种模式的完整输出示例 + yaml 完整结构示例

# test-case-runner skill 文件（阶段B/C 必读）
runner_files:
  - path: ".trae/skills/test-case-runner/SKILL.md"
    stage_required: [B, C]
    read_level: 必读
    purpose: skill 主文件：全局硬约束、阶段导航、输入输出
  - path: ".trae/skills/test-case-runner/reference/stage-01-execute-verify.md"
    stage_required: [B]
    read_level: 必读
    purpose: 阶段一：准入校验、读取用例、登录初始化、逐用例执行、即时判定
  - path: ".trae/skills/test-case-runner/reference/stage-02-generate-report.md"
    stage_required: [C]
    read_level: 必读
    purpose: 阶段二：报告生成、计算公式、字段映射、自检清单
  - path: ".trae/skills/test-case-runner/assets/sample-report.md"
    stage_required: [C]
    read_level: 按需
    purpose: MD 报告格式参考（五段式结构），不复制内容
  - path: ".trae/skills/test-case-runner/assets/sample-report.html"
    stage_required: [C]
    read_level: 强制
    constraints:
      - "limit ≥ 3000"
      - "必须读到文件末尾（含 function openLightbox / closeLightbox / Escape）"
      - "必须确认结构完整（含 :root{ CSS 变量 / .case-panel / .defect-card / .artifact-index / <script>）"
    purpose: HTML 报告模板（强制完整 Read）

# 数据产物（阶段B/C 必读）
data_artifacts:
  - path: "openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md"
    stage_required: [B, C]
    read_level: 必读
    purpose: 7 列标准表格用例（人可读）
  - path: "openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.page-structure.yaml"
    stage_required: [B, C]
    read_level: 必读
    purpose: 按用例索引的结构化数据契约（runner 主入口）
    key_field: "cases[<case_id>] 为执行主入口"
  - path: "openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/progress.yaml"
    stage_required: [B, C]
    read_level: 必读
    purpose: "进度表(小文件):阶段B 恢复断点定位 + 阶段C 报告头统计"
    key_field: "cases[<case_id>] 值(null/PASS/FAIL/NOT_RUN)"
    note: "阶段B 唯一持久化断点依据"
  - path: "openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/execution-results.yaml"
    stage_required: [C]
    read_level: 必读
    purpose: "用例详情索引(大文件):阶段C 报告的失败用例详情/缺陷/截图路径数据源"
    key_field: "results[<case_id>].defect/error/screenshot_path"
    note: "阶段B 恢复时无需读取(只需 progress.yaml)"
  - path: "openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/"
    stage_required: [C]
    read_level: 按需
    condition: "用户要求截图时"
    purpose: 执行证据(截图 .png 文件)，HTML 报告需 <img> 引用
  - path: "openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.md"
    stage_required: [C]
    read_level: 按需
    condition: "已生成 MD 报告时"
    purpose: 供 HTML 生成参考
  - path: "openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.html"
    stage_required: [C]
    read_level: 按需
    condition: "已生成 HTML 报告时"
    purpose: 供 HTML 自检
```

---

## §3 各阶段恢复步骤（md 叙述）

### 阶段A 恢复（test-case-generator）

**适用判定**: §1 命中 `A_in_progress` 或 `A_not_started`。

**恢复步骤**:

1. **Read 编排者指令**（按 §2 `orchestrator_files`）:
   - `测试分身.md`（确认测试类型与流程顺序）
   - 本文件（已完成）

2. **Read skill 主文件**（按 §2 `generator_files`）:
   - `.trae/skills/test-case-generator/SKILL.md`（**全文必读**，含关键约束、yaml 规范、ai_verification_benchmarks 语法）

3. **识别输入模式**:
   - 若已有部分 .md 产物 → Read 该 .md 头部确定已识别的 `生成模式` 字段（document/url/convert）
   - 若无产物 → 向用户询问输入源（需求文档路径 / URL / 已有用例），按 `测试分身.md` 模式判定规则确定

4. **Read 模式专属 reference**（按已识别模式选一，§2 `generator_files` 中 `read_level: 按需` 的三个 mode 文件）:
   - 模式一(document): `reference/mode1-document.md`
   - 模式二(url): `reference/mode2-url.md`
   - 模式三(convert): `reference/mode3-convert.md`

5. **按需 Read 示例**:
   - `reference/examples.md`（仅在不确定输出格式时读取）

6. **从断点继续**:
   - 若无 .md → 从"功能点提取/页面探索"重新开始
   - 若有 .md 无 .yaml → 从"yaml 生成"继续，需补齐 `cases` 顶级字段
   - 生成完毕后**必须获得用户明确确认**才能进入阶段B

---

### 阶段B 恢复（test-case-runner 阶段一：执行测试）

**适用判定**: §1 命中 `B_in_progress` 或 `A_done`。

**恢复步骤**:

1. **Read 编排者指令**（按 §2 `orchestrator_files`）:
   - `测试分身.md`
   - 本文件

2. **Read skill 主文件 + 阶段文件**（按 §2 `runner_files`，**全文必读，不可跳过**）:
   - `.trae/skills/test-case-runner/SKILL.md`
   - `.trae/skills/test-case-runner/reference/stage-01-execute-verify.md`

3. **定位模块名 + 运行编号**:
   - Glob `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/*.md` → 从文件名提取模块名
   - Glob `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-*/` → 取最大运行编号

4. **Read 数据产物**（按 §2 `data_artifacts`）:
   - `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md`（**全文**）
   - `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.page-structure.yaml`（**全文**，重点提取 `cases[<case_id>]` 索引）
   - `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/progress.yaml`（**全文**，断点定位主依据）
   - ⚠️ **不需要读 execution-results.yaml**（阶段B 恢复只需 progress.yaml 定位断点）

5. **执行阶段一准入校验**（见 stage-01-execute-verify.md 第 2.0 节）:
   - 校验 1-2: 产物存在
   - 校验 3: `cases` 顶级字段存在（缺失则降级为 page_structure 兜底）
   - 校验 4: Chrome DevTools MCP 可用（`list_pages`）
   - 校验 5: 运行目录就绪
   - 校验 6: progress.yaml 已存在（上下文恢复场景下应已存在，**禁止重新初始化**）

6. **定位执行断点**（按 §1 `breakpoint_detection`）:
   - Read `progress.yaml`，遍历 `cases` 找第一个 `value == null` 的用例（即 final_result 未判定）
   - 该用例即为断点用例，从它开始继续执行
   - 若所有用例 `value != null`（PASS/FAIL/NOT_RUN）→ 阶段B 已完成，直接进入阶段C
   - ⚠️ 禁止用截图文件名定位断点（截图可能未开启）

7. **从断点用例继续**:
   - 直接读 `cases[<断点 case_id>]` 拿到该用例的 steps/expected_results/ai_verification_benchmarks
   - 按 stage-01-execute-verify.md 第 2.3 节"逐用例执行标准流程"执行
   - 每条用例判定后立即更新 `progress.yaml`（cases[<id>] 值从 null 改为 final_result）和 `execution-results.yaml`（追加 results 条目）
   - ⚡ **连续执行优化**（单次会话内，未发生上下文压缩时适用）：新增）:
     - 已读取的文件（SKILL.md、stage-01、.md、.yaml）无需重复读取，直接从对话上下文获取
     - 每个用例的 steps/expected_results/ai_verification_benchmarks 从已读的 page-structure.yaml 上下文中获取，不重新 Read
     - `progress.yaml` 更新使用 Edit 精确修改 `cases[<id>]` 值，无需先 Read（已知当前值）
     - `execution-results.yaml` 追加使用 Edit，仅在不确定文件结构时才 Read
     - 详见 §6 上下文管理优化

8. **阶段B 完成判定**（2026-07-07 修订）:
   - Read `progress.yaml`,遍历 `cases` 统计 `value == null` 的用例数
   - 未完成数 == 0 → ✅ 阶段B 完成，进入阶段C
   - 否则 → 继续执行剩余 `value == null` 的用例
   - ⛔ 不依赖对话记忆判定完成

---

### 阶段C 恢复（test-case-runner 阶段二：生成报告）

**适用判定**: §1 命中 `C_in_progress`。

**恢复步骤**:

1. **Read 编排者指令**（按 §2 `orchestrator_files`）:
   - `测试分身.md`
   - 本文件

2. **Read skill 主文件 + 阶段文件**（按 §2 `runner_files`，**全文必读，不可跳过**）:
   - `.trae/skills/test-case-runner/SKILL.md`
   - `.trae/skills/test-case-runner/reference/stage-02-generate-report.md`

3. **Read 报告模板**（按 §2 `runner_files` 中 `read_level: 强制` 的约束）:
   - `.trae/skills/test-case-runner/assets/sample-report.html`
     - ⛔ 必须确认读到末尾（含 `function openLightbox`、`closeLightbox`、`Escape`）
     - ⛔ 必须确认结构完整（含 `:root{` CSS 变量、`.case-panel`、`.defect-card`、`.artifact-index`、`<script>`）
   - `.trae/skills/test-case-runner/assets/sample-report.md`（格式参考，不复制内容）

4. **Read 数据产物**（按 §2 `data_artifacts`，2026-07-07 修订）:
   - `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md`（用例总数、功能点）
   - `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.page-structure.yaml`（cases 索引、features）
   - `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/progress.yaml`（**全文**，报告头统计 + 每条用例 final_result）
   - `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/execution-results.yaml`（**全文**，失败用例详情/缺陷/截图路径）
   - ⛔ 不依赖对话记忆，所有执行数据从这两个 yaml 读取

5. **定位报告生成断点**:
   - Glob 检查 `reports/<模块名>-report.md` 是否存在
     - 不存在 → 从 3.1 Markdown 报告生成开始
     - 存在 → Read 该 md 报告内容，跳到步骤 6
   - Glob 检查 `reports/<模块名>-report.html` 是否存在
     - 不存在 → 从 3.2 HTML 报告生成开始
     - 存在 → 执行 HTML 自检（见步骤 7）

6. **MD 报告生成/续写**:
   - 按 stage-02-generate-report.md 第 3.1 节五段式结构生成
   - 数据来源(2026-07-07 修订): `progress.yaml` 的 cases[] 值(实时计算统计) + `execution-results.yaml` 的 results[<id>] 详情
   - 输出: `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.md`

7. **HTML 报告生成/续写 + 自检**:
   - 复制 `assets/sample-report.html` 为基底（**严禁从零写 HTML**）
   - 按 stage-02-generate-report.md 第 3.2 节字段映射填充数据
   - 执行 HTML 生成后自检（8 项检查，见 stage-02 第"HTML 生成后自检"节）
   - 自检失败 → 重读 sample-report.html 全文，重新生成
   - 输出: `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.html`

8. **阶段C 完成判定**: MD + HTML 报告均存在且 HTML 自检全部通过 → 流程结束，向用户输出报告路径

---

## §4 恢复红线

> ⛔ 以下红线适用于所有阶段恢复，违反即视为违规执行。

| # | 红线 | 说明 |
|---|------|------|
| 🔴1 | **禁止凭记忆执行（压缩后恢复场景）** | 上下文压缩/会话中断后恢复时，必须重新 Read 对应文件。单次会话内连续执行时，已 Read 的文件无需重复读取（详见 §6） |
| 🔴2 | **禁止假设产物格式** | 一切以模板和规范文件为准，禁止凭记忆推断产物结构 |
| 🔴3 | **禁止跳过阶段文件 Read（首次进入或压缩后恢复）** | 首次进入任意阶段或压缩后恢复时必须 Read 该阶段 reference 文件全文。连续执行时已读文件不重复读（详见 §6） |
| 🔴4 | **HTML 模板必须完整 Read** | 阶段C 必须读到 `sample-report.html` 末尾（含 JS 交互代码），limit < 3000 或未读到末尾 = 未读取 |
| 🔴5 | **断点定位以 progress.yaml 为准(2026-07-07 修订)** | 截图默认关闭时无截图文件,对话记忆上下文丢失即失效。阶段B 断点定位**唯一**依据是 `progress.yaml` |
| 🔴6 | **阶段切换需用户确认** | 阶段A → 阶段B 必须获得用户对测试用例的明确确认；阶段B → 阶段C 自动衔接（progress.yaml 中 completed == total_cases 即可） |
| 🔴7 | **cases 索引优先** | 阶段B 恢复后执行用例时优先读 `cases[<case_id>]`，仅在缺失时回退 page_structure 兜底 |
| 🔴8 | **执行记录即时写入(2026-07-07 新增)** | 每条用例判定后必须立即更新 `progress.yaml` + `execution-results.yaml`,严禁延迟批量更新。中途崩溃也要保证已执行用例的记录已持久化 |

---

## §5 快速恢复决策树

```
上下文丢失
   │
   ├─ Glob reports/*-report.html 存在?
   │     ├─ 是 → 阶段C 完成，告知用户报告路径
   │     └─ 否 ↓
   ├─ Glob reports/*-report.md 存在?
   │     ├─ 是 → 阶段C 进行中 → 读 stage-02 + sample-report.html + progress.yaml + execution-results.yaml → 续写 HTML
   │     └─ 否 ↓
   ├─ Glob screenshots/<模块名>-*/progress.yaml 存在?
   │     ├─ 是 → 阶段B 进行中 → 读 stage-01 + .md + .yaml + progress.yaml → 定位断点用例(value==null) → 续执行
   │     └─ 否 ↓
   ├─ Glob test-cases/*.page-structure.yaml 存在?
   │     ├─ 是 → 阶段A 完成 → 询问用户确认 → 进入阶段B(初始化 progress.yaml + execution-results.yaml)
   │     └─ 否 ↓
   ├─ Glob test-cases/*.md 存在?
   │     ├─ 是 → 阶段A 进行中 → 读 generator SKILL + 对应 mode reference → 续生成 yaml
   │     └─ 否 → 阶段A 未开始 → 询问用户输入源 → 从头开始
```

---

## §6 上下文管理优化（减少压缩频率，2026-07-07 新增）

> 测试用例数量较多（≥10）时，对话历史会快速累积导致频繁压缩。以下策略区分**压缩后恢复**与**连续执行**两种场景，在保证可靠性的前提下最小化 token 消耗。

### 6.1 两种执行场景

| 场景 | 触发条件 | 文件读取策略 |
|------|----------|-------------|
| **压缩后恢复** | 上下文压缩/会话中断后首次执行 | 按 §2/§3 完整 Read 所有必读文件（全量加载） |
| **连续执行** | 单次会话内，已完成 ≥1 个用例且未发生压缩 | 从对话上下文获取已读文件内容，不重复 Read |

### 6.2 文件读取最小化（连续执行场景）

| 文件 | 首次进入阶段B | 连续执行时 | 压缩后恢复时 |
|------|-------------|-----------|-------------|
| `SKILL.md` | ✅ 全文 Read | ⛔ 不重复读 | ✅ 重新 Read |
| `stage-01-execute-verify.md` | ✅ 全文 Read | ⛔ 不重复读 | ✅ 重新 Read |
| `<模块名>.md` | ✅ 全文 Read | ⛔ 不重复读 | ✅ 重新 Read |
| `<模块名>.page-structure.yaml` | ✅ 全文 Read | ⛔ 不重复读，从上下文取 `cases[<id>]` | ✅ 重新 Read |
| `progress.yaml` | ✅ 全文 Read | ⚡ 用 Edit 改值，不先 Read | ✅ 重新 Read |
| `execution-results.yaml` | ⛔ 不读（阶段B 恢复不需要） | ⚡ 用 Edit 追加，不先 Read | ✅ 重新 Read（仅阶段C 需要） |

此时依赖 §1-§5 的恢复机制确保执行连续性即可。
