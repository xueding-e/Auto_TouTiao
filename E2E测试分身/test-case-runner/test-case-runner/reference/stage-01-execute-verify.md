# 阶段一：读取用例 + 执行测试 + 语义验证

> ⛔ **进入本阶段前，必须已用 Read 工具完整读取本文件全文**。这是全局硬性约束，不可跳过。凭记忆执行 = 违规执行。
>
> 🔴 **准入条件**：test-case-generator 产物已存在（`openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md` + `<模块名>.page-structure.yaml`）。MCP 不可用时自动降级为 NOT_RUN。
>
> 🔴 **本阶段为核心执行阶段**。必须亲自通过 Chrome DevTools MCP 在浏览器中执行操作。严禁以"已验证"/"已有快照"/"基于已推导结果"等理由跳过执行。
>
> 🔴 **全量执行**：测试用例列出 N 条，必须对这 N 条**逐一执行、逐条判定**。严禁以任何理由只执行部分用例。
>
> 本阶段完成后，继续 **[阶段二：报告生成](./stage-02-generate-report.md)**。

---

## ⛔ 阶段一硬性约束

| # | 约束 | 说明 |
|---|------|------|
| 🔴1 | **即时判定** | 每条用例执行完毕后立即给出 `final_result`（PASS/FAIL/NOT_RUN），禁止延迟判定 |
| 🔴2 | **内容验证** | 内容验证通过 `evaluate_script`（首选）或 `take_snapshot`（复杂结构）做 AI 语义对比，截图仅作证据不用于分析 |
| 🔴3 | **进度追踪** | 执行开始前初始化 `progress.yaml`(每条用例 `final_result: null`);用例完成时直接写入 `final_result`(PASS/FAIL/NOT_RUN);**仅 FAIL/NOT_RUN 时**追加 `execution-results.yaml` 条目(PASS 不记录,避免冗余)。上下文恢复时以 `progress.yaml` 为唯一断点依据 |
| 🔴4 | **SSL 证书错误** | 导航后必须先 `take_snapshot` 确认页面内容。若 snapshot 中出现"您的连接不是私密连接"/"隐私设置错误"/"不安全"等证书警告提示 → 必须依次：① 从 snapshot 中找到"高级"按钮的 uid，`click` 该 uid → ② 再次 `take_snapshot`，找到"继续前往"链接的 uid，`click` 该 uid 绕过证书警告。严禁跳过"高级"直接点"继续前往" |

---

## 2.0 准入前校验

> ⛔ 在执行任何用例之前，必须完成以下校验。任一项不通过，禁止进入 2.1。

| # | 校验项 | 校验方式 | 通过标准 |
|---|--------|---------|---------|
| 1 | test-case-generator 产物存在 | Glob 搜索 `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/*.md` | 至少 1 个 `.md` 文件存在 |
| 2 | `.page-structure.yaml` 存在 | Glob 搜索 `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/*.page-structure.yaml` | 至少 1 个 `.yaml` 文件存在 |
| 3 | **`cases` 顶级字段存在** | Read `.page-structure.yaml` 后检查是否含 `cases` 顶级字段 | `cases` 字段存在且至少含 1 个 `case_id` key;若缺失,降级为旧路径(按 `page_structure` 盲搜)并在报告中标注 |
| 4 | Chrome DevTools MCP 可用 | 调用 `list_pages` | 正常返回页面列表，无错误 |
| 5 | 运行目录就绪 | 在项目根目录下创建 `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/`(即使截图关闭也必须创建,用于存 `progress.yaml` 和 `execution-results.yaml`) | 目录存在且可写 |
| 6 | **初始化执行记录文件** | 在运行目录下创建 `progress.yaml`(若不存在)和 `execution-results.yaml`(若不存在) | 两个文件存在且 `progress.yaml` 含所有用例的 `final_result: null` 初始条目 |

### 确定项目根目录（workspace_root）

> ⛔ 截图必须存放在**项目根目录**的 `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/` 下，不得使用 MCP 默认路径（如 `C:\Users\xxx\tests`）。

```
项目根目录 = 当前 workspace 的根路径（如 c:\work\sdd\cmb-js-aispec-sdlc-repository）
所有截图 filePath 必须拼接: <项目根目录>\openspec\sdlc-agent\E2E测试分身\ui-tests\screenshots\<模块名>-<运行编号>\<文件名>.png
执行记录文件路径: <项目根目录>\openspec\sdlc-agent\E2E测试分身\ui-tests\screenshots\<模块名>-<运行编号>\progress.yaml
                  <项目根目录>\openspec\sdlc-agent\E2E测试分身\ui-tests\screenshots\<模块名>-<运行编号>\execution-results.yaml
```

> ⛔ 截图与执行记录文件必须在同一目录下，便于上下文恢复与报告生成时统一检索。

### 确定运行编号

```
运行编号规则：<项目根目录>\openspec\sdlc-agent\E2E测试分身\ui-tests\screenshots\ 下已有 <模块名>-NN 子目录的最大编号 + 1，首次运行为 01
格式：两位数，如 01、02、03
```

### 2.0.5 初始化执行记录文件

> ⛔ 校验6 的具体执行步骤。两个文件即使截图关闭也必须创建,它们是阶段B 恢复和阶段C 报告的持久化数据源。

#### progress.yaml 结构（进度表,小文件,频繁更新）

> **二态模型**: `final_result` 直接表达进度。`null` = 未完成(断点);`PASS`/`FAIL`/`NOT_RUN` = 已完成。砍掉冗余的 status 字段和 IN_PROGRESS 状态(单条用例执行非原子,恢复后仍需重跑,IN_PROGRESS 无意义)。

```yaml
module: <模块名>
run_id: <运行编号,如 01>
url: <目标URL>
started_at: <ISO8601 开始时间>
last_updated: <ISO8601 最后更新时间>

cases:                                # 用 case_id 作为 key,值为 final_result
  TC-XXX-001: null                    # 未完成(断点候选)
  TC-XXX-002: null                    # 未完成
  # 执行后:
  # TC-XXX-001: PASS                  # 已完成
  # TC-XXX-002: FAIL                  # 已完成
  # TC-XXX-003: NOT_RUN               # 已完成
  # ... 每条用例一个条目
```

#### execution-results.yaml 结构（仅记录 FAIL/NOT_RUN 用例）

```yaml
# 初始状态(刚创建时):
results: {}                           # 空对象,无任何用例条目

# 执行后状态(仅 FAIL/NOT_RUN 用例追加条目;PASS 不记录):
# results:
#   TC-XXX-012:                       # case_id 作为 key(仅 FAIL/NOT_RUN)
#     completed_at: <ISO8601>         # 完成时间
#     result: FAIL                    # FAIL 或 NOT_RUN
#     failed_step: "step-3"           # FAIL 时填失败步骤 seq,NOT_RUN 时 null
#     failed_action: "click"          # 失败动作简述(如"点击查询按钮""元素定位")
#     error: "删除确认后..."          # 失败现象简述(如"元素未找到""snapshot 显示表格未清空")
#     not_run_reason: null            # NOT_RUN 技术性原因(MCP 断连/页面崩溃等)
#     screenshot_path: null           # 截图绝对路径,未截图时 null
#     defect:                         # 缺陷信息(仅 FAIL 时填)
#       description: "..."            # 缺陷描述(对应报告"缺陷描述"列)
#       expected_vs_actual: "..."     # 预期 vs 实际对比(对应报告"差异说明")
#       severity: "HIGH"              # 严重程度: 高/中/低
#       failure_type: "功能缺陷"      # 失败类型: 执行失败/内容不一致
```

> 💡 **设计原则**: PASS 用例不写入 `execution-results.yaml`,避免大量 null 冗余。PASS 用例的状态由 `progress.yaml` 的 `PASS` 值即可表达,报告生成时 PASS 用例的"snapshot 实际内容"填"与预期一致"。

#### 初始化时机

- 首次进入阶段B(校验1-5 通过后):创建两个文件,`progress.yaml` 含所有用例 `final_result: null` 条目,`execution-results.yaml` 含空 `results: {}`
- 上下文恢复时(已有 `progress.yaml`):**禁止重新初始化**,直接读取现有进度继续

### 校验不通过处理

```
if 校验1或2不通过: → 🔴 报错退出，提示先运行 test-case-generator skill
if 校验3不通过:     → ⚠️ 降级为旧路径(按 page_structure 盲搜),报告中标注"cases 索引缺失,使用 page_structure 兜底",继续执行
if 校验4不通过:     → 🔴 报错退出，提示执行阶段一确认 Chrome DevTools MCP 连接
if 校验5不通过:     → 创建运行目录后继续
if 校验6不通过:     → 若 progress.yaml 不存在则初始化创建;若已存在则保留(上下文恢复场景)
```

---

## 2.1 读取测试用例产物

### 2.1.1 定位产物文件

```powershell
dir openspec\sdlc-agent\E2E测试分身\ui-tests\test-cases\
```

确定本次执行的模块名（从文件名提取，如 `人员效能看板.md` → 模块名 = `人员效能看板`）。

### 2.1.2 读取页面结构描述（.page-structure.yaml）

使用 Read 工具完整读取 `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.page-structure.yaml`。提取：

**元信息字段(执行前一次性读取)**:

| 字段 | 用途 |
|------|------|
| `module` | 模块名 |
| `url` | 目标 URL（若 `null` 则从用例上下文推断） |
| `features[].id` | 功能点 ID |
| `features[].name` | 功能点名称 |
| `features[].cases` | 关联用例编号列表 |
|`features[].route`| ☆ 该功能点的相对路由路径,可直接 `navigate_page` 到达 |

**主入口字段(按用例索引)**:

| 字段 | 用途 |
|------|------|
| **`cases`** | ★★★ **runner 执行主入口**,以 `case_id` 为 key。执行用例 TC-XXX-001 时直接读 `cases[TC-XXX-001]`,拿到该用例的 steps/expected_results/ai_verification_benchmarks 全部数据,**无需在 page_structure 中盲搜** |
| `cases[<id>].feature_id` / `feature_name` | 关联功能点,用于报告 |
| `cases[<id>].priority` | 用例等级 |
| `cases[<id>].description` | 用例描述 |
| `cases[<id>].route` | 该用例起始路由,优先 `navigate_page` 跳转 |
| `cases[<id>].preconditions` | 前置条件,执行前检查 |
| `cases[<id>].steps[]` | ★ 步骤序列,每步内联 element/interaction/value/post_action_wait |
| `cases[<id>].steps[].element.role` + `text`/`label` | ★ 主锚点: a11y 树原生字段,跨会话稳定,runner 定位元素的**主路径** |
| `cases[<id>].steps[].element.selector` | ☆ 辅助消歧: CSS 选择器,仅当主路径歧义时使用;大多数为 null 是正常现象 |
| `cases[<id>].steps[].element.region` / `dialog` | ☆ 元素所在区域/对话框,需要回查总图时使用 |
| `cases[<id>].steps[].interaction` | ☆ 显式交互方式 |
| `cases[<id>].steps[].value` | ★ 输入类动作的填值,优先级高于 page_structure 中的 sample_value |
| `cases[<id>].steps[].post_action_wait` | ☆ 交互后等待条件 |
| `cases[<id>].expected_results[]` | 预期结果(面向人) |
| `cases[<id>].ai_verification_benchmarks[]` | ★★★ AI 验证基准结构化版本,含 step_ref + checks[] |
| `cases[<id>].source` | 关联需求点 |

**辅助字段(page_structure 总图,交叉校验与上下文恢复时使用)**:

| 字段 | 用途 |
|------|------|
| `page_structure.main_page.regions[]` | 页面区域划分和元素总清单 — 辅助交叉校验、上下文恢复全局定位 |
| `page_structure.main_page.stats` | 页面统计数据(总条数、总页数等基准值),供 quant_compare/consistent 类断言引用基准 |
| `page_structure.dialogs` | 对话框/弹窗结构(字段、按钮清单),供 cases[].steps[].element.dialog 回查 |

### 2.1.3 交叉校验

逐条对比 `.md` 中的用例编号与 `.page-structure.yaml` 中的索引：

```
.md 用例数 = N
.yaml features[].cases 并集（去重）= M
.yaml cases 顶级 key 集合（去重）= K
if N ≠ M: → ⚠️ 警告：features 与 .md 不一致，以 .md 为准执行，报告中注明差异
if N ≠ K: → ⚠️ 警告：cases 索引与 .md 不一致，以 .md 为准执行，缺失的 case_id 走 page_structure 兜底，报告中注明差异
if N = M = K: → ✅ 数据一致
```

---

## 2.2 登录与页面初始化

1. `navigate_page`(timeout: 15000) 打开目标 URL
2. 确认页面加载完成（优先用 `evaluate_script` 检查关键元素存在，如 `() => document.body.textContent.includes('MCP广场')`；SSL 证书场景必须用 `take_snapshot`）

若页面未加载完成，标记所有用例为 NOT_RUN 并退出。

---

## 2.3 逐用例执行（核心流程）

> 🔴 按测试用例表格顺序，逐条执行。执行前确认 `progress.yaml` 已初始化(所有用例 `final_result: null`)。
>
> **进度持久化**: 每条用例**执行完成并即时判定后**,直接将 `final_result`(PASS/FAIL/NOT_RUN) 写入 `progress.yaml` 的 `cases[<id>]`;**仅当结果为 FAIL 或 NOT_RUN 时**,才追加 `execution-results.yaml` 的 `results[<case_id>]` 条目(PASS 不记录,避免冗余)。无需 IN_PROGRESS 中间态(单条用例执行非原子,恢复后仍需重跑,中间态无意义)。
>
> **数据来源**: 每条用例的 steps/element/value/post_action_wait/ai_verification_benchmarks 直接从 `cases[<case_id>]` 读取,**无需从 .md 表格解析、无需在 page_structure 中盲搜**。`page_structure` 仅在 cases 缺失或需回查总图时使用。

---

### 2.3.0 YAML 参考定位

> ⚡ **核心原则**: `page-structure.yaml` 是**参考文档**,提供元素线索(text/label/role/selector)帮助 AI 快速定位,**不是必须逐字段执行的脚本**。AI 应优先利用 yaml 中的元素信息加速定位,但保留根据实际情况选择最优 MCP 工具的灵活性。

#### 元素定位建议优先级（参考,非强制）

对每条 step,建议按以下优先级尝试定位元素:

| 优先级 | 数据来源 | 定位方式 | 适用场景 |
|--------|---------|---------|---------|
| **P1** | `step.element.selector` | `evaluate_script` 用 CSS selector 直接查询 | yaml 中提供了 selector 时,最快捷 |
| **P2** | `step.element.text` + `step.element.role` | `evaluate_script` 按 a11y 角色+文本组合查询 | 有明确角色和文本的按钮/链接 |
| **P3** | `step.element.text` 或 `step.element.label` | `evaluate_script` 按文本/标签模糊查询 | 文本唯一性较高的场景 |
| **P4** | `take_snapshot` + uid | snapshot 获取 a11y 树,按 yaml 中的 text/role 匹配 uid,再 click/fill | yaml 信息不足或 P1-P3 失效时 |

> 💡 **使用建议**: yaml 数据是加速器,不是约束。优先用 yaml 线索走 P1-P3 快速定位;线索不足或定位失败时,用 `take_snapshot` 兜底是正常路径,不是违规。

#### 步骤执行流程

对 `cases[<id>].steps[]` 中的每条 step:

```
1. 从 yaml 提取元素线索: selector/text/label/role + action/value/post_action_wait
2. 参考优先级 P1→P2→P3 尝试用 evaluate_script 定位元素
3. 若 P1-P3 成功 → 直接执行交互(click/fill/select/press_key/navigate)
4. 若 P1-P3 失败或 yaml 线索不足 → take_snapshot 获取 uid → 用 click(uid)/fill(uid,value) 交互
5. 按 post_action_wait 等待(dialog/toast/navigation/reload/none)
```

#### 验证流程

所有步骤执行完毕后,按 `cases[<id>].ai_verification_benchmarks` 逐条验证:

- 简单验证(文本存在/URL/元素存在/数字对比)→ 优先用 `evaluate_script` 返回简短结果
- 复杂结构验证(dialog 整体结构/table 层级/a11y 属性)→ 用 `take_snapshot`
- 按 `cases[<id>].ai_verification_benchmarks` 逐条判定,所有 core 项满足 → PASS;任一 core 项不满足 → FAIL
- **语义匹配不是关键字匹配**: "名称必填"≈"请输入名称"≈"名称不能为空" 均视为通过

> ⚠️ **控制台/接口报错即 FAIL**: 验证过程中若发现页面表现与预期不符,必须检查控制台和网络请求:
> - `list_console_messages` → 若存在 error 级别日志(如 JS 异常、未捕获错误) → **直接判定 FAIL**,失败类型为"执行失败",error 内容记入 `execution-results.yaml` 的 `error` 字段
> - `list_network_requests` → 若存在 4xx/5xx 响应(如接口 500、404、403) → **直接判定 FAIL**,失败类型为"执行失败",接口 URL + 状态码记入 `error` 字段
> - 仅在"表现与预期不符"时触发检查;预期内的小问题(如 console.warn、图片 404)不触发 FAIL
>
> ⚠️ **控制台错误归属判定（防止前序用例错误污染）**:
> - `list_console_messages` 返回的是浏览器会话的**全量累积日志**,前序用例产生的 error 不会被自动清除
> - 当验证阶段调用 `list_console_messages` 发现 error 时,必须通过 `msgid` 判断是否为本用例执行期间新增:
>   - **方式一（推荐）**: 若本用例步骤执行前未调用过 `list_console_messages`,立即调用一次获取当前全量 error 的 `msgid` 作为基线,再次调用后只关注新增 `msgid`;若两次调用间无新 error,说明均为前序遗留,忽略不判
>   - **方式二**: 若 error 的 `msgid` 连续且最小者明显早于本用例执行时机(如前序用例已记录过该错误),视为前序遗留,忽略不判
> - 若 `navigate_page` 触发了页面重载(URL 发生变化),日志已重置,当前 error 均视为本用例产生
> - 同理,`list_network_requests` 也按此原则判断请求归属

---

### 2.3.1 执行主循环

**每条用例执行标准流程**（所有 MCP 调用统一 timeout: 15000，超时重试 1 次）：

1. **读取用例数据**: 直接读 `cases[<当前用例_id>]`,拿到 `steps[]`/`expected_results`/`ai_verification_benchmarks`/`route`/`preconditions`
2. **路由直达**: 若 `cases[<id>].route` 非空且当前 URL 不匹配,`navigate_page(route)` 跳转
3. **前置条件检查**: 若 `preconditions` 非空,确认前置条件满足(如需登录则先登录,需有数据则先确认数据存在)
4. **逐步骤执行**: 按 [2.3.0 YAML 参考定位](#230-yaml-参考定位) 的流程,遍历 `cases[<id>].steps[]` 逐条执行
5. **验证**: 按 [2.3.0 验证流程](#验证流程) 逐条检查 `ai_verification_benchmarks`;若需检查控制台错误,按上述"控制台错误归属判定"规则区分前序遗留与本用例新增

> 📸 **截图默认关闭**。仅在用户明确要求截图时，才在核心验证步骤后执行 `take_screenshot`(filePath: `<项目根目录>\tests\screenshots\<模块名>-<运行编号>\<用例编号>_<场景>.png`)，filePath 必须使用绝对路径。

### 即时判定

每条用例执行完立即给结果：

| MCP 操作 | snapshot 语义 | 结果 | 失败类型 |
|----------|-------------|------|---------|
| ✅ 成功 | ✅ 一致 | ✅ PASS | — |
| ✅ 成功 | ❌ 不符 | ❌ FAIL | 内容不一致 |
| ❌ 失败 | — | ❌ FAIL | 执行失败 |
| 环境崩溃 | — | ⬜ NOT_RUN | — |

> NOT_RUN 仅限浏览器断连/页面崩溃/登录态丢失等技术性原因，严禁"优先级低""时间不足"等理由。

### 2.3.x 更新执行记录文件（每条用例判定后立即执行）

> ⛔ 即时判定给出 `final_result` 后,必须立即更新持久化文件。`progress.yaml` 每条都更新;`execution-results.yaml` 仅 FAIL/NOT_RUN 时追加。严禁延迟批量更新。

#### 步骤 A: 更新 progress.yaml（每条用例都执行）

```yaml
# 更新该用例条目(直接将 null 改为 final_result):
cases[<当前用例_id>]: <PASS | FAIL | NOT_RUN>

# 更新时间戳:
last_updated: <当前 ISO8601 时间>
```

> **说明**: 不再维护 summary 统计字段。统计信息在阶段C 报告生成或阶段B 完成判定时从 `cases` 实时计算。

#### 步骤 B: 追加 execution-results.yaml（仅 FAIL/NOT_RUN 时执行）

> 💡 PASS 用例**跳过此步骤**,不写入 `execution-results.yaml`。仅当 `final_result` 为 FAIL 或 NOT_RUN 时才追加。

```yaml
results:
  <当前用例_id>:
    completed_at: <当前 ISO8601 时间>
    result: <FAIL | NOT_RUN>
    failed_step: <FAIL 时填失败步骤 seq,NOT_RUN 时 null>
    failed_action: <FAIL 时填失败动作简述,NOT_RUN 时 null>
    error: <FAIL 时填失败现象简述,NOT_RUN 时 null>
    not_run_reason: <NOT_RUN 时填技术性原因,FAIL 时 null>
    screenshot_path: <截图绝对路径或 null>
    defect:                         # 仅 FAIL 时填,NOT_RUN 时各字段 null
      description: <缺陷描述>
      expected_vs_actual: <预期 vs 实际对比>
      severity: <高/中/低>
      failure_type: <执行失败/内容不一致/功能缺陷>
```

### 阶段B 完成判定

```
读取 progress.yaml
遍历 cases,统计 value == null 的用例数(未完成数)
if 未完成数 == 0:
    → ✅ 阶段B 完成,所有用例 final_result 非 null,进入阶段C
else:
    → 🔴 仍有 final_result == null 的用例,继续执行
```

> ⛔ 上下文恢复时,以 `progress.yaml` 中 `cases` 是否还有 `value == null` 作为阶段B 完成的唯一判定标准,不依赖对话记忆。

---

## 2.4 工具速查

> **所有命令统一超时**: `timeout: 15000`(15秒)，超时即重试，2 次失败则降级。

| MCP 工具 | 用途 | 关键参数 |
|---------|------|---------|
| `navigate_page` | 打开 URL / 刷新 / 前进后退 | `type: "url"`, `url`, `timeout: 15000` |
| `take_snapshot` | 获取 a11y 树（含 uid），定位元素和验证内容 | `timeout: 15000`, `verbose: true`(详细模式) |
| `take_screenshot` | 截图存证（可选，默认关闭） | `filePath`, `fullPage: true`(全页), `timeout: 15000` |
| `click` | 点击元素 | `uid`(来自 snapshot), `timeout: 15000` |
| `fill` | 填充输入框 / 原生 `<select>` 选择 | `uid`, `value`, `timeout: 15000`<br/>⚠️ **不适用于 combobox 下拉选择**（见 2.3 交互方式） |
| `press_key` | 按键（Enter/Escape/Tab 等） | `key`, `timeout: 15000` |
| `hover` | 悬停元素 | `uid`, `timeout: 15000` |
| `type_text` | 逐字输入（搜索建议等场景） | `text`, `submitKey`(可选), `timeout: 15000` |
| `wait_for` | 等待指定文本出现 | `text: ["文本1","文本2"]`, `timeout: 15000` |
| `evaluate_script` | 执行 JS（查 iframe/元素属性等） | `function`, `timeout: 15000` |
| `handle_dialog` | 处理浏览器弹窗 | `action: "accept"/"dismiss"`, `timeout: 15000` |
| `list_pages` | 查看所有页面 | `timeout: 15000` |
| `select_page` | 切换到指定页面 | `pageId`, `timeout: 15000` |

---

## 2.5 异常处理

| 场景 | 处理 |
|------|------|
| evaluate_script 返回 not_found | 降级到 `take_snapshot` + uid 定位，重试 1 次 |
| 元素未出现 | `wait_for` 等待目标文本，超时重试 1 次 |
| 浏览器断连 | 重新连接 MCP，恢复会话，失败则 NOT_RUN |
| 页面崩溃/白屏 | `navigate_page(type: "reload")` 刷新，2 次失败则 NOT_RUN |
| 登录态丢失 | 重新登录，当前用例重跑 |
| 目标 URL 不可访问 | 全部用例 NOT_RUN，直接进入阶段二 |
| MCP 连接断开 | 重新连接 Chrome DevTools MCP，恢复后继续 |

---

## 2.6 完成标准

- [ ] `progress.yaml` 中所有用例 `final_result` 非 null(即 `cases` 中无 `value == null` 的条目)
- [ ] 每条用例有 `final_result`（PASS/FAIL/NOT_RUN）
- [ ] 已执行用例（PASS+FAIL）的判定结果均有对应的验证记录（evaluate_script 或 snapshot）
- [ ] 若用户要求截图，截图文件已按命名规则存放至截图目录
- [ ] NOT_RUN 用例均有技术性原因说明，无违规理由

> ✅ 全部满足 → 继续 **[阶段二：报告生成](./stage-02-generate-report.md)**
