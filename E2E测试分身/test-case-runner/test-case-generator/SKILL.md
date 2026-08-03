---
name: test-case-generator
description: 当测试人员需要"测试用例"时使用。触发关键词:测试用例生成、design.md、proposal.md、URL探索、功能点提取、用例转换、标准用例。本 skill 支持三种输入模式:① 需求文档(design/proposal)提取功能点生成用例,内部支持两个子模式:用户提供文档与自动发现 openspec apply 完成的 change ② URL探索页面可点击功能点生成用例 ③ 已有用例转为标准格式用例。输出统一为7列表格(用例编号/等级/功能点描述/点击步骤/预期结果/AI验证基准/关联需求点)。
---

# test-case-generator Skill

> **TL;DR**: 输入(需求文档 / URL / 已有用例) → ① 识别输入模式 → ② 浏览器探索(三模式共用,模式一/三为辅助性预探索,模式二为主流程探索) → ③ 提取或探索功能点 → ④ 生成7列标准表格测试用例 → 输出 `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md`。

## 职责速览

| 项 | 内容 |
|----|------|
| **输入** | 三选一: ① `design.md`+`proposal.md` 文档(模式一内部支持两个子模式: 1A 用户直接对话提供文档获取关联 design/task/proposal/specs;1B 自动从 openspec 中寻找已完成 apply 环节的 change,多个则询问用户) ② 目标 URL ③ 已有测试用例(任意格式) |
| **输出** | `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md`(7列标准表格用例) + `.page-structure.yaml`(按用例索引的结构化数据契约,供 test-case-runner 消费) |
| **边界** | 只生成测试用例,不生成也不执行自动化脚本 |
| **执行流程** | 四步: ① 输入模式识别 ② 浏览器探索与页面结构生成 ③ 功能点提取/页面探索 ④ 用例生成 |

---

## 关键约束(红线,必须遵守)

1. **不臆造功能点**: 模式一的功能点必须来自文档原文(子模式 1A 来自用户提供的文档及关联文档;子模式 1B 来自 openspec change 的 proposal/design/tasks/specs 原文);模式二模式三的可点击点必须来自浏览器真实探索结果,不可凭文档或猜测页面结构
2. **用例编号唯一且可追溯**: 每条用例必须有 `case_id`,并能反向追溯到来源(文档章节 / 页面元素 / 原始用例)
3. **7列格式不可变**: 输出表格必须且仅包含以下7列,顺序固定: `用例编号` → `等级` → `功能点描述` → `点击步骤` → `预期结果` → `AI验证基准` → `关联需求点`
4. **等级仅用 p0/p1**: p0 = 核心主流程/冒烟级; p1 = 功能/边界/异常级。禁止使用 L1/L2/L3 或其他等级体系
5. **覆盖度达标**: 模式一必须覆盖文档中所有显式功能点(子模式 1A/1B 均需覆盖 proposal 目标 + design 页面/交互 + specs 行为 + tasks 测试要求);模式二必须覆盖页面所有可交互主功能入口;模式三必须完整转换原始用例的所有场景
6. **点击步骤可操作**: 步骤描述必须具体可执行,明确写出"点击/输入/选择"等动作及目标元素,不可使用模糊描述如"操作一下"
7. **MCP 调用超时限制(15s)**: 模式二中所有 Chrome DevTools MCP 调用(如 `navigate_page`、`take_snapshot`、`click`、`fill`、`wait_for`、`evaluate_script` 等)必须设置 `timeout: 15000`(毫秒)。超时即降级,不无限等待
8. **生成时间必须精确**: 输出产物中的 `生成时间` / `generated_at` 字段必须是实际执行时刻的精确时间,严禁凭感觉估算。获取方式:在生成文件前通过 `RunCommand` 执行 `Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"` (PowerShell) 获取当前精确时间戳,将命令输出直接填入。若 PowerShell 不可用则用 `date` 命令
9. **cases 与 .md 等价**: `.page-structure.yaml` 必须采用"用例索引为主、`page_structure` 总图为辅"的双层结构。顶级 `cases` 字段按 `case_id` 索引,每用例内联自己的 `steps[]`(每步含 element+value+post_action_wait)、`expected_results`、`ai_verification_benchmarks`、`source`。`cases` 的 key 集合必须与 `features[].cases` 的并集完全一致,且与 `.md` 表格"用例编号"列一一对应;每个 `cases[<id>]` 必须与 `.md` 表格中该用例的"点击步骤"/"预期结果"/"AI验证基准"列**逐项等价**。完整规范见 [page-structure-yaml-spec.md](./reference/page-structure-yaml-spec.md)

---

## 第一步:输入模式识别与分流

### 1.1 模式判定规则

按以下优先级自动判定输入模式(用户显式指定 > 输入特征自动判定 > 询问用户):

| 优先级 | 判定条件 | 模式 | 说明 |
|--------|---------|------|------|
| 1 | 用户显式指定模式(如"用模式一""按文档生成""探索 URL""转换已有用例") | 对应模式 | 用户意图明确,直接采用 |
| 2 | 包含"需求文档""PRD""设计文档""按 change 生成""当前 change""openspec""apply 完成"等关键词,或用户在对话中提供了文档(路径/粘贴内容/文件引用) | 模式一(document) | 文档来源 → 子模式 1A/1B 判定 → 读取文档 → 功能点 → 用例(详见 [mode1-document.md](./reference/mode1-document.md) 第2节) |
| 3 | 输入为 URL(http/https 开头),或包含"URL""页面""网址""探索页面"等关键词 | 模式二(url) | URL → 页面探索 → 用例 |
| 4 | 输入为已有用例文件(`.md`/`.txt`/`.xlsx`/`.csv`)或用例文本,或包含"已有用例""转换""转标准格式"等关键词 | 模式三(convert) | 已有用例 → 标准格式转换 |
| 5 | 输入特征不明确或多种特征混合 | 询问用户 | 用 AskUserQuestion 让用户三选一 |

> **判定要点**:
> - **优先级 1 最高**:用户显式指定时直接采用,不进行后续判定
> - **优先级 2-4 按顺序匹配**:首个命中的模式即采用,不继续判定
> - **优先级 5 兜底**:无法明确判定时必须询问,禁止默认采用某模式
> - **模式一子模式判定**: 进入模式一后,再按"用户是否直接提供文档"判定子模式 1A/1B(详见 [mode1-document.md](./reference/mode1-document.md) 第 2.1 节)
> - **混合输入处理**:若用户同时提供 URL 和已有用例,询问用户意图;若用户在模式一中额外提供 URL,该 URL 作为预探索目标

### 1.2 模式分流

| 模式 | 详细规则文件 |
|------|------------|
| 模式一(需求文档,含子模式 1A/1B) | [mode1-document.md](./reference/mode1-document.md) |
| 模式二(URL 探索) | [mode2-url.md](./reference/mode2-url.md) |
| 模式三(用例转换) | [mode3-convert.md](./reference/mode3-convert.md) |

---

## 第二步:浏览器探索与页面结构生成(三模式共用)

> 所有模式在生成用例前,必须先进行浏览器探索,捕获真实页面元素信息并生成 `.page-structure.yaml` 数据契约。

### 2.1 三模式探索角色差异

| 模式 | 探索角色 | 探索深度 | 失败后果 |
|------|---------|---------|---------|
| 模式一/三 | **辅助性**预探索 | 仅 navigate+snapshot,不深度交互 | 可降级,用例保留 `<>` 占位符仍能生成 |
| 模式二 | **主流程**探索 | navigate+snapshot → 深度交互(点击/输入触发) → 深度遍历导航 | 不可降级,探索失败 = 无用例(详见 [mode2-url.md](./reference/mode2-url.md)) |

**关键区别**: 模式一/三的功能点来自文档/已有用例,探索仅用于校准元素名;模式二的功能点来自探索本身,探索即功能点提取。

### 2.2 探索流程

```
任意模式触发
    ↓
检查用户是否提供了目标 URL?
    ├── 有 URL → 执行浏览器探索(2.3)
    └── 无 URL → 通过对话向用户索要 URL
                    ↓
              用户提供 URL 后 → 执行浏览器探索(2.3)
```

### 2.3 探索步骤

> 所有 MCP 调用必须附带 `timeout: 15000`,超时即降级。

**共用的基础探索(三模式必做)**:

1. **`navigate_page`**(timeout: 15000): 打开目标 URL
2. **`take_snapshot`**(timeout: 15000): 获取页面 a11y 树,记录以下信息:
   - 页面标题、主要区域名称
   - 所有按钮/链接/菜单的**真实文本**(如"新建智能体"、"保存"、"取消")
   - 所有输入框/选择器的 **label/placeholder 文本**(如"名称"、"类型"、"描述")
   - 对话框/弹窗的**真实标题**(如"新增知识库"、"编辑智能体")
   - 表格/列表的**真实表头字段名**(如"名称"、"类型"、"创建时间"、"操作")
   - 分页/统计文本格式(如"共 10 条"、"1/10 页")
   - 当前页面 URL 路径关键词
   - 当前页面的完整**相对路由路径**(如 `/knowledge-base/list`、`/agent/create`),作为 `features[].route` 的来源

**模式二独有的深度探索**: 详见 [mode2-url.md](./reference/mode2-url.md) 第 2 节。模式一/三在基础探索后**不进行深度交互**,直接进入功能点提取/用例转换。

### 2.4 探索降级

| 场景 | 模式一/三处理 | 模式二处理 |
|------|--------------|-----------|
| URL 不可访问(超时/404) | 降级为无探索模式,用例中保留 `<>` 占位符,并在 `.md` 顶部标注 `> ⚠️ 预探索失败: <原因>,用例中 UI 元素名使用占位符,待页面可访问后补全` | 报错,询问是否更换 URL 或提供 mock 页面 |
| Chrome DevTools MCP 不可用 | 降级为无探索模式,标注 `> ⚠️ MCP 环境不可用,未进行浏览器预探索,用例中 UI 元素名使用占位符` | 报错,提示用户检查 MCP 环境配置;或由用户手动提供页面截图/HTML 供分析,点击步骤标注"待确认" |
| 页面需要登录 | 先询问用户账号密码,或提示用户提供已登录的浏览器会话;若无法登录则降级 | 同左,若无法登录则报错 |
| snapshot 为空 | 降级为无探索模式,标注原因 | 报错,标注原因 |
| 元素无法交互(仅模式二) | — | 记录功能点但标注"无法探索",不省略用例,点击步骤标注"待确认" |
| MCP 调用超时(15s,仅模式二) | — | 该次操作降级:在功能点中标注"超时未响应",继续探索其他元素;同一元素连续 2 次超时则跳过 |

### 2.5 探索后生成产物

探索完成后,按各模式规则生成用例,并同步产出 `.page-structure.yaml`:

- **点击步骤**: 必须使用探索获取的**真实文本**(如"点击'新建智能体'按钮"而非"点击新建按钮");模式一/三降级时保留 `<>` 占位符
- **AI验证基准**: 探索获取的真实元素名直接填入(如 `"新增知识库"` 对话框而非 `<对话框名>`);模式一/三降级时保留 `<>` 占位符并标注"待页面探索确认"
- **`.page-structure.yaml`**:
  - `url` 字段填入实际使用的 URL(不再填 `null`)
  - `cases` 字段必须与 `.md` 用例表**同步生成**: 每生成一条用例,必须立即在 `cases` 顶级字段下创建以 `case_id` 为 key 的条目,内联该用例的全部 steps(每步含 element+value+post_action_wait)、expected_results、ai_verification_benchmarks、source。**禁止先生成 .md 再补 yaml,必须同步生成保持等价**(字段规范详见 [page-structure-yaml-spec.md](./reference/page-structure-yaml-spec.md))
- 探索获取的页面元素映射表作为附录写入 `.md` 文件末尾

---

## 第三步:功能点提取/用例转换

按已识别的模式执行对应规则:

- **模式一**: 读取文档,按 [mode1-document.md](./reference/mode1-document.md) 第 3-4 节提取功能点并展开为场景矩阵(模式一需先完成第 2 节子模式判定与文档获取)
- **模式二**: 基于探索结果,按 [mode2-url.md](./reference/mode2-url.md) 第 3-4 节整理功能点清单并按元素类型生成用例
- **模式三**: 解析已有用例,按 [mode3-convert.md](./reference/mode3-convert.md) 第 2-4 节做字段映射并补全场景

---

## 第四步:用例生成

### 4.1 AI 验证基准生成

按已识别的模式,套用对应模式的"场景→基准映射表"生成 AI 验证基准:
- 模式一: [mode1-document.md](./reference/mode1-document.md) 第 5 节
- 模式二: [mode2-url.md](./reference/mode2-url.md) 第 5 节
- 模式三: [mode3-convert.md](./reference/mode3-convert.md) 第 5 节

> AI 验证基准的检查项结构、判定规则、语义匹配、.md ↔ yaml 映射等共用语法规则,详见 [ai-benchmark-syntax.md](./reference/ai-benchmark-syntax.md)。

### 4.2 文件整体结构

```markdown
# <模块名> - 测试用例

> **生成模式**: <模式一/二/三>
> **子模式**: <1A 用户提供文档 / 1B openspec自动发现 / 无>(仅模式一填)
> **来源 change**: <change 名称或"用户提供的文档">(仅模式一填)
> **目标 URL**: <URL或无>
> **生成时间**: <yyyy-MM-ddTHH:mm:ss+08:00>  ← 必须用 `Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"` 精确获取,禁止估算
> **用例总数**: <N>  ← N = 测试用例表格中的行数(即所有功能点的 cases 数量之和),不是功能点数量

---

## 功能点清单

| 编号 | 功能点 | 来源 | 用例数 |
|------|--------|------|--------|
| FP-001 | <功能点> | <来源> | <N> |

---

## 测试用例

| 用例编号 | 等级 | 功能点描述 | 点击步骤 | 预期结果 | AI验证基准 | 关联需求点 |
|---------|------|-----------|---------|---------|-----------|-----------|
| TC-XXX-001 | p0 | <功能点>-<场景> | 1.xxx 2.xxx 3.xxx | xxx;xxx | 关键步骤后:snapshot中可观测的页面状态 | xxx |
| TC-XXX-002 | p1 | <功能点>-<场景> | 1.xxx 2.xxx | xxx | 关键步骤后:snapshot中可观测的页面状态 | xxx |

---

## 覆盖度说明

- 功能点覆盖: <N>/<M> (<百分比>)
- 未覆盖项及原因: <列出或"无">
- 文档来源: <列出本文档引用的源文档路径>(仅模式一)
```

### 4.3 用例编号规则

- 格式: `TC-<模块缩写>-<3位序号>`,如 `TC-AGT-001`(智能体管理第1条)
- 模块缩写从功能点清单推导(如 智能体管理→AGT,知识库→KB,人员效能看板→PED)
- 补全用例紧接原始用例编号,如原始 `TC-AGT-001`,补全为 `TC-AGT-001-A`(异常)、`TC-AGT-001-B`(边界)
- 编号在功能点清单中关联,在主表格中通过"功能点描述"隐含关联

### 4.4 关联需求点填写规则

| 模式 | 关联需求点格式 |
|------|--------------|
| 模式一(1A 用户提供文档) | `<文档名>#<章节>`(如 `design.md#3.2`、`proposal.md#目标`) 或 `<文档路径>#<章节>` |
| 模式一(1B openspec 自动发现) | `<change-name>/<文档名>#<章节>`(如 `tsg-ai-portal/design.md#3.2`) 或 `<change-name>/specs/<spec-name>/spec.md#<行为ID>` |
| 模式二 | `页面探索(<URL>)` |
| 模式三 | 原始用例的需求编号映射,无则填 `-` |

---

## 输出产物清单

| 文件 | 路径 | 说明 |
|------|------|------|
| **测试用例**(主) | `openspec/sdlc-agent/E2E测试分身/ui-tests/test-cases/<模块名>.md` | 7列标准表格用例 + 功能点清单 + 覆盖度说明 + 文档来源(模式一) |
| 页面结构描述 | `ui-tests/test-cases/<模块名>.page-structure.yaml` | **双层结构**: ① 顶级 `cases` 按用例 ID 索引,每用例内联 steps+element+value+post_action_wait+ai_verification_benchmarks(runner 主入口) ② `page_structure` 总图保留作为辅助(交叉校验、上下文恢复全局定位) |

> 若 `ui-tests/test-cases/` 目录下已有多个模块用例,更新 `README.md` 索引;若为首个模块,可省略 README。

---

## 参考文件

| 文件 | 说明 | 加载时机 |
|------|------|---------|
| [ai-benchmark-syntax.md](./reference/ai-benchmark-syntax.md) | AI 验证基准语法契约: 检查项结构、类型判定、语义匹配、.md ↔ yaml 结构化映射 | 生成 AI 验证基准时 |
| [page-structure-yaml-spec.md](./reference/page-structure-yaml-spec.md) | `.page-structure.yaml` 完整规范: 数据组织方式、cases 等价规则、yaml Schema、字段约束表、捕获要点 | 生成 yaml 时 |
| [mode1-document.md](./reference/mode1-document.md) | 模式一详细规则: 子模式 1A/1B 判定、文档获取、功能点提取、场景矩阵、AI 基准场景映射 | 模式一触发时 |
| [mode2-url.md](./reference/mode2-url.md) | 模式二详细规则: 深度探索流程、功能点清单、AI 基准场景映射、MCP 命令清单 | 模式二触发时 |
| [mode3-convert.md](./reference/mode3-convert.md) | 模式三详细规则: 已有用例解析、字段映射、转换补全、AI 基准场景映射 | 模式三触发时 |
| [examples.md](./reference/examples.md) | 三种模式完整示例 | 需要参考时 |
