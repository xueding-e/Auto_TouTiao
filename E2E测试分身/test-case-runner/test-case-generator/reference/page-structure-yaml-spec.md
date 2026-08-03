# .page-structure.yaml 规范(统一,三模式共用)

> 本规范为 `test-case-generator` skill 的强制数据契约。`.page-structure.yaml` 是 generator 与下游 `test-case-runner` 之间的桥梁。主文件: [SKILL.md](../SKILL.md) | AI 验证基准语法见: [ai-benchmark-syntax.md](./ai-benchmark-syntax.md)

---

## 一、数据组织方式

采用"用例索引为主、`page_structure` 总图为辅"的双层结构:

- **顶级 `cases` 字段**(runner 执行主入口): 按用例 ID 索引,每个用例必须内联自己执行所需的全部数据(steps + element + value + post_action_wait + ai_verification_benchmarks),字段不得省略或留空待 runner 补全
- **`page_structure` 总图**(辅助): 用于交叉校验、覆盖度检查、上下文恢复全局定位,字段可简化

runner 执行用例时直接读 `cases[<case_id>]`,无需扫描 `page_structure`。

---

## 二、cases 与 .md 等价规则(硬性约束)

1. **`cases` 的 key 集合**必须与 `features[].cases` 的并集**完全一致**,且与 `.md` 表格"用例编号"列**一一对应**
2. **每个 `cases[<id>]`** 必须与 `.md` 表格中该用例的"点击步骤"/"预期结果"/"AI验证基准"列**逐项等价**,不得遗漏、新增或矛盾
3. **`cases[].steps[]`**: 每步含 `element`(role/text/label/selector/region/dialog)+ `interaction` + `value` + `post_action_wait`,与 `.md`"点击步骤"列的"1.xxx 2.xxx"序号一致
4. **`cases[].expected_results`**: 与 `.md`"预期结果"列一致(面向人的业务语言)
5. **`cases[].ai_verification_benchmarks`**: 与 `.md`"AI验证基准"列对应的结构化版本,`core`/`weak` 标记和 `step_ref` 必须与 `.md` 文本中的 `①`~`⑨`/`可能出现`/`【步骤N后】` 标记对齐(映射规则见 [ai-benchmark-syntax.md](./ai-benchmark-syntax.md) 第六节)
6. **同步生成**: 禁止先生成 `.md` 再补 yaml,必须同步生成保持等价

---

## 三、完整 yaml Schema

```yaml
module: <模块名>
source_type: document | url | convert   # 对应模式一/二/三
url: <目标URL>                            # 必填(模式一/三预探索后填入,模式二必填)
generated_at: <yyyy-MM-ddTHH:mm:ss+08:00>  # 必须用 Get-Date 精确获取,禁止估算
features:                                 # 必填,功能点清单(与 .md 功能点清单一致)
  - id: FP-001                            # 统一 FP-XXX 编号
    name: <功能点名称>
    source: <来源>                         # 文档章节 / 页面探索 / 原始用例
    cases: [TC-XXX-001, TC-XXX-002]       # 关联用例编号列表
    route: <子路由路径>                     # 推荐: 该功能点所在页面的相对路由路径,runner 可直接 navigate_page 到达而非逐层点击导航

cases:                                    # 必填,按用例 ID 索引(runner 执行主入口)
  TC-XXX-001:                             # 用例编号作为 key,与 .md 表格"用例编号"列一一对应
    feature_id: FP-001                    # 关联功能点 ID
    feature_name: <功能点名称>              # 冗余字段,runner 报告与日志直接引用,避免回查 features
    priority: p0 | p1                     # 与 .md 表格"等级"列一致
    description: <功能点描述-场景>           # 与 .md 表格"功能点描述"列一致
    route: <子路由路径或null>               # 推荐: 该用例起始路由,runner 可直接 navigate_page 跳过逐层导航;null 表示沿用当前页
    preconditions: <前置条件或null>         # 如"需登录""需有至少1条数据""需先执行TC-XXX-001"
    steps:                                # 步骤序列,每步内联该步骤涉及的元素(从 .md"点击步骤"列结构化)
      - seq: 1                            # 步骤序号,与 .md"点击步骤"列的"1.xxx 2.xxx"序号一致
        action: click | fill | select_option | type_text | press_key | hover | observe  # 动作类型,observe 表示仅 snapshot 验证不交互
        target: <目标元素语义描述>           # 给人看的描述,如"新建智能体按钮""名称输入框"
        element:                          # 该步骤目标元素的内联结构(与 page_structure.elements 同构,跨会话稳定锚点)
          role: button | textbox | combobox | radio | link | heading | statictext | ...  # 主锚点1: a11y 树原生,跨会话稳定
          text: <元素文本或null>            # 主锚点2: 元素显示文本(button/link 的文本);非文本元素填 null
          label: <label文本或null>          # 主锚点3: 输入框/选择器的 label/placeholder;非输入元素填 null
          selector: <CSS选择器或null>       # 辅助消歧: 仅当 role+text/label 歧义(同文本多元素)且能查到 data-testid/id 时填写;默认 null
          region: <区域名称或null>          # 该元素在 page_structure.main_page.regions 中的区域名,用于总图回查;对话框内元素填 null
          dialog: <对话框标题或null>        # 该元素所在对话框标题(对应 page_structure.dialogs 的 key);主页元素填 null
        interaction: click | fill | select_option | type_text | press_key | hover | null  # 显式交互方式;null=由 runner 按 role 推断
        value: <输入值或null>              # 输入类动作的填值(优先级高于 element.sample_value);非输入动作填 null
        post_action_wait:                  # 该步骤交互后的等待条件
          type: dialog | toast | navigation | reload | none  # 等待类型;none=无需等待直接 snapshot
          indicator: <等待文本或null>        # 等待目标文本(如对话框标题 / "成功" toast);type=none 时为 null
          timeout: <毫秒,默认10000>          # 最大等待时间,默认 10000ms
      - seq: 2                            # 后续步骤同结构
        action: ...
        element: { role: ..., text: ..., label: ..., selector: null, region: ..., dialog: null }
        interaction: ...
        value: ...
        post_action_wait: { type: none, indicator: null, timeout: 10000 }
    expected_results:                      # 与 .md 表格"预期结果"列一致(面向人的业务语言)
      - <预期1>
      - <预期2>
    ai_verification_benchmarks:            # 与 .md 表格"AI验证基准"列对应的结构化版本(面向 AI 的可观测语言)
      - step_ref: 5                        # 关联步骤序号(如 .md 中"【步骤5后】"对应 step_ref=5)
        checks:                            # 检查项列表(对应 .md 中 `;` 分隔的检查项)
          - type: core | weak              # core=核心条件(必须满足,FAIL 影响),weak=弱条件(可能出现,不影响)
            assertion: not_appear | appear | match_any | quant_compare | consistent | no_error | url_contains  # 断言类型(对应 .md 检查项类型)
            target: <断言目标文本或null>     # 断言目标;not_appear/appear 时为待搜索文本;match_any 时填第一个选项
            options: [<可选1>, <可选2>, ...] # 仅 match_any 使用(对应 .md 中 `含"A"/"B"/"C"`);其他类型填 []
            compare: <对比描述或null>        # 仅 quant_compare/consistent 使用(如 "增加1" / "与操作前一致")
          - type: weak
            assertion: match_any
            target: 成功
            options: [成功, 创建成功, 保存成功, 操作成功]
            compare: null
    source: <关联需求点或null>              # 与 .md 表格"关联需求点"列一致

page_structure:                           # 保留,页面结构总图(辅助: 交叉校验、上下文恢复全局定位、覆盖度检查)
  main_page:                              # 主页面结构
    regions:                              # 页面区域划分
      - name: <区域名称>                    # 如"页面标题区""工具栏""卡片列表区""分页区"
        description: <区域说明>
        elements:                         # 区域内可交互元素
          - role: button | textbox | combobox | radio | link | heading | statictext | ...  # 主锚点1: a11y 树原生,跨会话稳定,generator 100% 可捕获
            text: <元素文本>               # 主锚点2: 元素显示文本(按钮名/标签名/标题等),与 role 组合即可跨会话定位
            label: <label文本>             # 主锚点3: 输入框/选择器的 label 或 placeholder(无则 null),a11y 树原生字段
            selector: <CSS选择器或null>     # 可选辅助: 仅当需消歧(同文本多元素)且能用 evaluate_script(uid) 查到 data-testid/id 时填写;默认 null。a11y 快照不暴露 HTML 属性
            interaction: click | fill | select_option | type_text | press_key | hover | null  # 推荐: 显式交互方式,仅当需要覆盖 role 默认推断时填写;null=由 runner 自行推断
            sample_value: <示例填值>        # 推荐: runner 执行时填入的具体测试数据(仅 textbox/combobox 等输入类元素,非输入元素填 null)
            post_action_wait:              # 推荐: 交互后的等待条件,指导 runner 在 snapshot 前等待目标状态
              type: dialog | toast | navigation | reload | none  # 等待类型
              indicator: <等待出现的文本>     # 等待目标文本出现(如"新增"对话框标题 / "成功"toast),type=none 时可为 null
              timeout: <毫秒,默认10000>      # 最大等待时间,默认 10000ms
            description: <元素用途说明>     # 给 runner 的提示,如"需按Enter触发搜索"
            required: true | false        # 仅表单字段,是否必填
            default_value: <默认值>        # 仅选择器/单选,默认选中值(无则 null)
            extra: <附加信息>              # 如"下方显示 0/500 字数统计"
    stats:                                # 页面统计数据(探索时观察到的基准值)
      total_items: <"共 N 条"格式文本>      # 如"共 58 条"
      total_pages: <总页数>                # 如 7
      items_per_page: <每页条数>           # 如 8
  dialogs:                                # 对话框/弹窗结构(可选,无弹窗则省略此键)
    <对话框标题>:                           # 如"新增MCP",用真实标题作为 key
      trigger: <触发方式描述>               # 如 点击"创建MCP"按钮
      fields:                             # 对话框内表单字段
        - role: textbox | combobox | radio | checkbox | ...  # 主锚点1
          label: <字段label文本>           # 主锚点2: 与 role 组合即可跨会话定位
          selector: <CSS选择器或null>       # 可选辅助: 默认 null,仅消歧时填
          interaction: click | fill | select_option | null  # 推荐
          sample_value: <示例填值>          # 推荐
          post_action_wait:
            type: dialog | toast | navigation | reload | none
            indicator: <等待出现的文本>
            timeout: <毫秒,默认10000>
          required: true | false
          default_value: <默认值>
          extra: <附加信息>
      buttons:                            # 对话框内按钮
        - role: button                    # 主锚点1
          text: <按钮文本>                 # 主锚点2: 与 role 组合即可跨会话定位
          selector: <CSS选择器或null>       # 可选辅助: 默认 null,仅消歧时填
          interaction: click | null        # 推荐
          post_action_wait:
            type: dialog | toast | navigation | reload | none
            indicator: <等待出现的文本>
            timeout: <毫秒,默认10000>
          description: <按钮用途>
```

---

## 四、字段约束

| 字段 | 必填 | 说明 |
|------|------|------|
| `features[].id` | 是 | 统一 `FP-XXX`,与 `.md` 功能点清单一一对应 |
| `features[].name` | 是 | 与 `.md` 功能点清单的"功能点"列一致 |
| `features[].source` | 是 | 模式一填文档章节;模式二填 `页面探索(<URL>)`;模式三填 `原始用例` |
| `features[].cases` | 是 | 关联用例编号列表,必须与 `.md` 用例表一一对应,数量一致。同时必须与 `cases` 顶级 key 一一对应 |
| `features[].route` | 推荐 | 该功能点所在页面的相对路由路径(如 `/knowledge-base/list`),runner 可直接 `navigate_page` 到达,避免逐层点击导航 |
| **`cases`** | 是 | **按用例 ID 索引的顶级字段(runner 主入口)**。每个 `case_id` 下内联该用例执行所需的全部数据(steps + element + value + post_action_wait + ai_verification_benchmarks) |
| `cases[<id>].feature_id` | 是 | 关联功能点 ID,与 `features[].id` 对应 |
| `cases[<id>].feature_name` | 是 | 冗余字段,runner 报告与日志直接引用,避免回查 `features` |
| `cases[<id>].priority` | 是 | 与 `.md` 表格"等级"列一致,仅 `p0`/`p1` |
| `cases[<id>].description` | 是 | 与 `.md` 表格"功能点描述"列一致 |
| `cases[<id>].route` | 推荐 | 该用例起始路由;`null` 表示沿用当前页 |
| `cases[<id>].preconditions` | 可选 | 前置条件描述,如"需登录""需先执行 TC-XXX-001" |
| `cases[<id>].steps[]` | 是 | **步骤序列**,与 `.md`"点击步骤"列序号一致。每步内联 `element`(role/text/label/selector/region/dialog)、`interaction`、`value`、`post_action_wait` |
| `cases[<id>].steps[].seq` | 是 | 步骤序号,从 1 开始 |
| `cases[<id>].steps[].action` | 是 | 动作类型:`click`/`fill`/`select_option`/`type_text`/`press_key`/`hover`/`observe`。`observe` 表示仅 snapshot 验证不交互 |
| `cases[<id>].steps[].target` | 是 | 目标元素语义描述(给人看),如"新建智能体按钮" |
| `cases[<id>].steps[].element.role` + `text`/`label` | 主锚点 是 | **跨会话稳定定位的首选标识**,a11y 树原生字段,generator 100% 可捕获。runner 在新会话 `take_snapshot` 后按 role+name/label 组合搜索当前 uid。uid 不可写入 yaml |
| `cases[<id>].steps[].element.selector` | 可选辅助 | CSS 选择器,优先级 `data-testid` > `data-cy` > `aria-label` > `id` > `name`。a11y 快照不暴露 HTML 属性,默认 `null`;仅当需消歧且能用 `evaluate_script(uid)` 主动查询到时填写。**null 是正常值,不要为了填而填** |
| `cases[<id>].steps[].element.region` | 可选 | 该元素在 `page_structure.main_page.regions` 中的区域名,用于总图回查;对话框内元素填 `null` |
| `cases[<id>].steps[].element.dialog` | 可选 | 该元素所在对话框标题(对应 `page_structure.dialogs` 的 key);主页元素填 `null` |
| `cases[<id>].steps[].interaction` | 推荐 | 显式指定交互方式;`null` 表示由 runner 按 role 推断(button→click, textbox→fill, combobox→select_option) |
| `cases[<id>].steps[].value` | 输入类必填 | 该步骤的具体填值,**优先级高于 page_structure 中的 `sample_value`**。非输入动作填 `null`。值应真实可用(如名称用 `"测试模块X_0823"` 而非 `<名称>`) |
| `cases[<id>].steps[].post_action_wait` | 推荐 | 该步骤交互后的等待条件。包含 `type`(dialog/toast/navigation/reload/none)、`indicator`(等待的目标文本)、`timeout`(超时,默认 10000ms)。`type=none` 表示无需等待,可直接 snapshot |
| `cases[<id>].expected_results[]` | 是 | 与 `.md` 表格"预期结果"列一致(面向人的业务语言) |
| `cases[<id>].ai_verification_benchmarks[]` | 是 | **与 `.md` 表格"AI验证基准"列对应的结构化版本**。每个元素含 `step_ref`(关联步骤序号)和 `checks[]`(检查项列表)。结构见 [ai-benchmark-syntax.md](./ai-benchmark-syntax.md) 第六节 |
| `cases[<id>].source` | 是 | 与 `.md` 表格"关联需求点"列一致 |
| `page_structure` | 是 | 页面结构总图(辅助): 交叉校验、上下文恢复全局定位、覆盖度检查。runner 不再以此为执行主入口 |
| `page_structure.main_page.regions[]` | 是 | 页面区域划分,至少包含 1 个区域。供 `cases[].steps[].element.region` 回查 |
| `page_structure.main_page.regions[].elements[]` | 是 | 区域内可交互元素总清单。每个元素至少含 `role` 和 `text` |
| `page_structure.main_page.stats` | 模式二必填;模式一/三预探索后填入 | 页面统计数据(探索时观察到的基准值),供 `quant_compare`/`consistent` 类断言引用基准值 |
| `page_structure.dialogs` | 有弹窗时必填 | 以对话框真实标题为 key,描述内部字段和按钮总清单。供 `cases[].steps[].element.dialog` 回查 |

---

## 五、捕获要点(生成侧)

> 本节说明 generator 在浏览器探索阶段应捕获哪些信息填入 yaml,完整探索流程见 [SKILL.md](../SKILL.md) 第二步。

- **跨会话稳定锚点优先**: `role` + `text`/`label` 是 a11y 树原生字段,跨会话稳定,作为元素定位主路径。uid 不可写入 yaml(每次 take_snapshot 都可能变),仅 generator 在当前会话内交互时使用
- **selector 谨慎填写**: a11y 快照不暴露 HTML 属性,默认 `null`;仅当同文本多元素歧义且能用 `evaluate_script(uid)` 查到 `data-testid`/`id` 时填写。优先级 `data-testid` > `data-cy` > `aria-label` > `id` > `name`
- **value 与 sample_value 两级模型**:
  - `cases[].steps[].value`: **用例级填值**(必填),generator 探索时推断的具体测试数据,如 `"测试智能体_0823"`。runner 优先使用此值
  - `page_structure.elements[].sample_value`: **页面级示例值**(可选),作为 cases.value 缺失时的回退。对输入框/选择器结合上下文推断合理填值(如名称用 `"测试<模块名>_<随机后缀>"`,日期选今天,下拉选非默认的第一项);对按钮等非输入元素记为 `null`
- **post_action_wait 推断**: 观察交互后页面变化推断等待条件:
  - 点击按钮→打开对话框: `{type: "dialog", indicator: "<对话框标题>"}`
  - 提交表单→出现 toast/列表变化: `{type: "toast", indicator: "成功"}`
  - 点击链接→页面跳转: `{type: "navigation", indicator: "<新页面标题>"}`
  - 无明显变化: `{type: "none"}`
- **route 提取**: 从当前导航 URL 提取相对路径,填入 `features[].route` 和 `cases[].route`;若多个功能点共用一个子页面,route 值相同
- **interaction 推断**: 根据元素 role 推断默认交互方式(button/link/radio→`click`, textbox→`fill`, combobox→`select_option`, checkbox→`click`);若 role 不足以推断,记为 `null` 交由 runner 自行判断

---

## 六、职责边界

本规范只负责**生成** `.page-structure.yaml` 数据契约,不描述 runner 如何消费这些数据。runner 的执行流程、元素定位策略、等待策略、降级兜底等使用方式见 `test-case-runner/reference/stage-01-execute-verify.md`,此处不重复。
