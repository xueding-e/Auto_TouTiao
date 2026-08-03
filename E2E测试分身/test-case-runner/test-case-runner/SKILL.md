---
name: test-case-runner
description: 执行测试用例测试，生成测试报告
---

# E2E 测试执行器（渐进式）

直接读取 test-case-generator 生成的测试用例 → **按 `cases[<case_id>]` 索引读取每条用例的结构化数据**(无需在 page_structure 中盲搜) → **优先利用 yaml 中的元素线索(selector/text/role/label)加速定位,线索不足时用 take_snapshot 兜底** → 与 `ai_verification_benchmarks` **语义对比** → **双重验证**判定 PASS/FAIL → 生成结构化测试报告（md + html）。

> 📸 **截图默认关闭**。仅在用户明确要求截图时才执行 `take_screenshot`，否则全程不截图。

本 Skill 采用渐进式披露：每个阶段完成并确认后，按序打开下一阶段的文件继续执行。各阶段文件的规则约束均为强制要求，执行对应阶段时必须遵守。

---

## ⛔ 全局硬性约束

> 以下约束适用于全部阶段，任何情况下不得违反。

| # | 约束 |
|---|------|
| 🔴 | **阶段一必须亲自通过 Chrome DevTools MCP 执行操作**。严禁以"已验证"/"已有快照"/"基于已推导结果"等理由跳过执行。**你没有执行过就是没有执行过，必须现在执行。** |
| 🔴 | **全量执行，严禁挑选用例**。测试用例列出 N 条，阶段一必须对这 N 条**逐一执行、逐条判定**。严禁以"优先级低""类似功能""关键流程已覆盖""时间不足"等任何理由只执行部分用例。**少执行一条就是违规。** |
| 📸 | **截图默认关闭**。仅在用户明确要求截图时才执行 `take_screenshot`。验证通过 `take_snapshot` 输出的 a11y 树文本对比完成。 |
| 🔴 | **进入任意阶段前必须先 Read 该阶段的 reference 文件全文**。无论是正常阶段切换（阶段一 → 阶段二）、从任意位置跳转到某阶段、还是上下文丢失后恢复执行，**每次进入阶段前都必须先用 Read 工具完整读取该阶段的 reference 文件**（阶段一读 `stage-01-execute-verify.md`，阶段二读 `stage-02-generate-report.md`），确认该阶段的所有规则、约束、格式要求后再开始执行。**阶段二必须额外 Read `assets/sample-report.html` 全模板文件，不设 limit 上限（或用 limit ≥ 3000），必须读到文件最后一行（包含 `closeLightbox` 和 `Escape`）。未完整读到末尾 = 未读取 = 禁止进入 3.1。** 禁止凭记忆直接执行任何阶段。未读取 reference 文件就开始执行 = 违规执行。 |
| 🕐 | **报告生成时间必须精确**。输出报告中的「报告生成时间」必须是实际执行时刻的精确时间,严禁凭感觉估算。获取方式:在生成报告文件前通过 `RunCommand` 执行 `Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"` (PowerShell) 获取当前精确时间戳,将命令输出直接填入。若 PowerShell 不可用则用 `date` 命令。 |

---

## 🔄 上下文恢复协议

> 当对话因 Token 限制、会话中断等原因丢失上下文后恢复时，必须严格遵循以下协议。
>
> ⛔ 上下文恢复后进入任意阶段前，同样受全局硬性约束「进入任意阶段前必须先 Read 该阶段的 reference 文件全文」约束。

### 恢复步骤（按顺序执行）

1. **判断当前阶段**：根据已有产物判断执行进度（`progress.yaml` 存在 → 阶段一进行中或完成；报告文件存在 → 阶段二进行中或完成）。详细恢复流程见 `reference/context-recovery.md`
2. **重新读取阶段文件**：用 Read 工具读取当前阶段的 reference 文件全文（阶段二还需额外 Read `assets/sample-report.html`）
3. **核对已有产物**：Read `progress.yaml` 定位断点用例（`final_result == null` 的第一条），检查已有报告内容
4. **从断点继续**：基于重新读取的规则和模板继续执行

### ⛔ 上下文恢复红线

- **禁止凭记忆执行**：即使你"记得"阶段流程或模板结构，也必须重新 Read 对应文件。记忆 ≠ 已读取。
- **禁止假设产物格式**：一切以模板和规范文件为准。

---

## 📋 阶段导航

| 阶段 | 文件 | 说明 | 准入条件 |
|------|------|------|----------|
| 阶段一 | [stage-01-execute-verify.md](./reference/stage-01-execute-verify.md) | 读取用例 + 登录 + 逐条执行（snapshot 定位+uid 交互+语义验证+即时判定） | test-case-generator 产物已存在 |
| 阶段二 | [stage-02-generate-report.md](./reference/stage-02-generate-report.md) | 生成 Markdown + HTML 报告 | 所有用例已完成双重验证判定 |

> 按上表从上到下顺序执行。进入每个阶段前必须 Read 对应 reference 文件全文（全局硬性约束）。

---

## 输入输出

| 项 | 内容 |
|----|------|
| **输入** | test-case-generator 产物（`openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md` + `<模块名>.page-structure.yaml`） |
| **输出** | `openspec/sdlc-agent/E2E测试分身/ui-tests/reports/<模块名>-report.md` + `<模块名>-report.html` |
| **执行记录** | `screenshots/<模块名>-<运行编号>/progress.yaml`(进度表,小,频繁更新,阶段B 恢复主依据) + `screenshots/<模块名>-<运行编号>/execution-results.yaml`(仅 FAIL/NOT_RUN 用例详情,阶段C 报告数据源)。两个文件即使截图关闭也必须创建 |
| **截图目录** | `openspec/sdlc-agent/E2E测试分身/ui-tests/screenshots/<模块名>-<运行编号>/`(即使截图关闭也必须创建,用于存执行记录文件;用户要求截图时额外存 .png,MCP `take_screenshot` 的 filePath 必须使用绝对路径) |
| **边界** | 直接从测试用例执行测试并生成报告，不生成中间脚本，不修改原始用例 |

---

## 参考资料索引

| 文档 | 用途 | 何时加载 |
|------|------|----------|
| [assets/sample-report.md](assets/sample-report.md) | 完整示例报告-Markdown（五段式结构参考） | 阶段二生成 MD 报告时参考 |
| [assets/sample-report.html](assets/sample-report.html) | 交互式 HTML 报告模板（CSS/DOM/JS 不可改） | 阶段二生成 HTML 报告时复制基底 |

---

> 🚀 开始 → **[阶段一：读取用例 + 执行测试](./reference/stage-01-execute-verify.md)**
