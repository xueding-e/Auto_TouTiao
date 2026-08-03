# 完整示例

> 本文档为 `test-case-generator` skill 的三种模式完整示例,辅助理解规则。规则正文: [SKILL.md](../SKILL.md) | [ai-benchmark-syntax.md](./ai-benchmark-syntax.md) | [page-structure-yaml-spec.md](./page-structure-yaml-spec.md) | [mode1-document.md](./mode1-document.md) | [mode2-url.md](./mode2-url.md) | [mode3-convert.md](./mode3-convert.md)

---

## 示例一:模式一(需求文档)

**输入**: `design.md` 含章节"3.2 智能体管理 - 用户可通过表单创建智能体,名称必填,长度1-50,类型为枚举:对话型/工作流型/数字人型"

**输出(测试用例表格)**:

```markdown
# 智能体管理 - 测试用例

> **生成模式**: 模式一(需求文档) | **目标 URL**: https://example.com/agent | **生成时间**: 2026-06-19T10:00:00+08:00 | **用例总数**: 4

---

## 功能点清单

| 编号 | 功能点 | 来源 | 用例数 |
|------|--------|------|--------|
| FP-001 | 创建智能体 | design.md#3.2 | 4 |

---

## 测试用例

| 用例编号 | 等级 | 功能点描述 | 点击步骤 | 预期结果 | AI验证基准 | 关联需求点 |
|---------|------|-----------|---------|---------|-----------|-----------|
| TC-AGT-001 | p0 | 创建智能体-正常路径 | 1.点击"新建智能体"按钮 2.在"名称"输入框输入"测试智能体" 3.在"类型"下拉框选择"对话型" 4.在"描述"输入框输入"测试用" 5.点击"确认"按钮 | 智能体列表新增一条记录;提示"创建成功" | 【步骤5后】①snapshot中不再出现"新建智能体"对话框;②表格中出现含"测试智能体"的新增数据行;③表格行数比操作前增加1;④可能出现含"成功"的提示信息 | design.md#3.2 |
| TC-AGT-002 | p1 | 创建智能体-名称为空 | 1.点击"新建智能体"按钮 2.留空"名称"输入框 3.在"类型"下拉框选择"对话型" 4.点击"确认"按钮 | 提示"名称必填";未创建成功 | 【步骤4后】①snapshot中仍存在"新建智能体"对话框(未关闭);②对话框内出现含"必填"/"不能为空"的校验提示;③表格行数与操作前一致(未增加) | design.md#3.2 |
| TC-AGT-003 | p1 | 创建智能体-名称超长 | 1.点击"新建智能体"按钮 2.在"名称"输入框输入51字符名称 3.在"类型"下拉框选择"对话型" 4.点击"确认"按钮 | 提示"名称长度不能超过50";未创建成功 | 【步骤4后】①snapshot中仍存在"新建智能体"对话框(未关闭);②对话框内出现含"长度"/"不能超过"/"超出"的校验提示;③表格行数与操作前一致(未增加) | design.md#3.2 |
| TC-AGT-004 | p1 | 创建智能体-类型枚举切换 | 1.点击"新建智能体"按钮 2.在"名称"输入框输入"测试" 3.在"类型"下拉框选择"工作流型" 4.在"类型"下拉框选择"数字人型" 5.点击"确认"按钮 | 类型可切换为工作流型和数字人型;保存成功 | 【步骤4后】①snapshot中类型选择器文本变为"数字人型";②页面不出现error提示;【步骤5后】③snapshot中不再出现"新建智能体"对话框;④表格中出现含"测试"的新增行;⑤可能出现含"成功"的提示 | design.md#3.2 |

---

## 覆盖度说明

- 功能点覆盖: 1/1 (100%)
- 未覆盖项及原因: 无
```

---

## 示例二:模式二(URL 探索)

**输入**: URL `https://example.com/login`

**输出(测试用例表格)**:

```markdown
# 登录页 - 测试用例

> **生成模式**: 模式二(URL探索) | **目标 URL**: https://example.com/login | **生成时间**: 2026-06-19T11:00:00+08:00 | **用例总数**: 3

---

## 功能点清单

| 编号 | 功能点 | 来源 | 用例数 |
|------|--------|------|--------|
| FP-001 | 用户名输入 | 页面探索 | 1 |
| FP-002 | 密码输入 | 页面探索 | 1 |
| FP-003 | 登录按钮 | 页面探索 | 1 |

---

## 测试用例

| 用例编号 | 等级 | 功能点描述 | 点击步骤 | 预期结果 | AI验证基准 | 关联需求点 |
|---------|------|-----------|---------|---------|-----------|-----------|
| TC-LOGIN-001 | p0 | 登录-正常路径 | 1.输入用户名"admin" 2.输入密码"123456" 3.点击登录按钮 | 跳转首页;右上角显示admin | 【步骤3后】①snapshot中URL已从/login变为首页地址;②snapshot中出现"admin"用户标识;③页面不再出现登录表单;④页面不出现error提示 | 页面探索(https://example.com/login) |
| TC-LOGIN-002 | p1 | 登录-用户名为空 | 1.留空用户名 2.输入密码"123456" 3.点击登录按钮 | 提示"用户名必填";未跳转 | 【步骤3后】①snapshot中仍存在登录表单(未跳转);②页面出现含"必填"/"不能为空"/"请输入"的校验提示;③URL仍为/login | 页面探索(https://example.com/login) |
| TC-LOGIN-003 | p1 | 登录-密码为空 | 1.输入用户名"admin" 2.留空密码 3.点击登录按钮 | 提示"密码必填";未跳转 | 【步骤3后】①snapshot中仍存在登录表单(未跳转);②页面出现含"必填"/"不能为空"/"请输入"的校验提示;③URL仍为/login | 页面探索(https://example.com/login) |

---

## 覆盖度说明

- 可点击点覆盖: 3/3 (100%)
- 未覆盖项及原因: 无
```

---

## 示例三:模式三(已有用例转换)

**输入**: 已有用例(自然语言格式):
```
用例1: 登录功能测试
步骤: 输入用户名admin,输入密码123456,点击登录
预期: 跳转首页
优先级: 高

用例2: 搜索功能测试
步骤: 在搜索框输入"智能体",点击搜索按钮
预期: 列表显示包含"智能体"的记录
```

**输出(测试用例表格)**:

```markdown
# 功能测试 - 测试用例

> **生成模式**: 模式三(用例转换) | **目标 URL**: https://example.com | **生成时间**: 2026-06-19T12:00:00+08:00 | **用例总数**: 3

---

## 功能点清单

| 编号 | 功能点 | 来源 | 用例数 |
|------|--------|------|--------|
| FP-001 | 登录功能 | 原始用例 | 2 |
| FP-002 | 搜索功能 | 原始用例 | 1 |

---

## 测试用例

| 用例编号 | 等级 | 功能点描述 | 点击步骤 | 预期结果 | AI验证基准 | 关联需求点 |
|---------|------|-----------|---------|---------|-----------|-----------|
| TC-LOGIN-001 | p0 | 登录-正常路径 | 1.在"用户名"输入框输入"admin" 2.在"密码"输入框输入"123456" 3.点击"登录"按钮 | 跳转首页 | 【步骤3后】①snapshot中URL已从/login变为首页地址;②页面不再出现登录表单;③页面不出现error提示 | - |
| TC-LOGIN-002 | p1 | 登录-用户名为空(补全) | 1.留空"用户名"输入框 2.在"密码"输入框输入"123456" 3.点击"登录"按钮 | 提示用户名必填;未跳转 | 【步骤3后】①snapshot中仍存在登录表单(未跳转);②页面出现含"必填"/"不能为空"/"请输入"的校验提示;③URL仍为/login | - (补全) |
| TC-SEARCH-001 | p0 | 搜索-正常搜索 | 1.在"搜索"输入框输入"智能体" 2.点击"搜索"按钮 | 列表显示包含"智能体"的记录 | 【步骤2后】①snapshot中表格/列表刷新;②所有可见行均包含"智能体"关键字;③底部"共N条"中N值≥1 | -|

---

## 覆盖度说明

- 原始用例转换: 2/2 (100%)
- 补全用例: 1条(登录-用户名为空)
- 未覆盖项及原因: 无
```

---

## 示例四:完整 `.page-structure.yaml` (含 cases 索引)

> 本示例展示按用例索引的完整 yaml 结构。以示例一(智能体管理)为例,展示 `cases` 顶级字段如何按 `case_id` 内联每条用例的 steps/element/value/post_action_wait/ai_verification_benchmarks,与 .md 表格逐项等价。yaml 字段完整规范见 [page-structure-yaml-spec.md](./page-structure-yaml-spec.md)。

```yaml
module: 智能体管理
source_type: document
url: https://example.com/agent
generated_at: 2026-07-07T10:30:00+08:00

features:
  - id: FP-001
    name: 创建智能体
    source: design.md#3.2
    cases: [TC-AGT-001, TC-AGT-002, TC-AGT-003, TC-AGT-004]
    route: /agent/list

cases:                                    # 按用例 ID 索引(runner 主入口)
  TC-AGT-001:
    feature_id: FP-001
    feature_name: 创建智能体
    priority: p0
    description: 创建智能体-正常路径
    route: /agent/list
    preconditions: null
    steps:
      - seq: 1
        action: click
        target: 新建智能体按钮
        element:
          role: button
          text: 新建智能体
          label: null
          selector: null
          region: 工具栏
          dialog: null
        interaction: click
        value: null
        post_action_wait:
          type: dialog
          indicator: 新建智能体
          timeout: 10000
      - seq: 2
        action: fill
        target: 名称输入框
        element:
          role: textbox
          text: null
          label: 名称
          selector: null
          region: null
          dialog: 新建智能体
        interaction: fill
        value: 测试智能体_0707
        post_action_wait:
          type: none
          indicator: null
          timeout: 10000
      - seq: 3
        action: select_option
        target: 类型下拉框
        element:
          role: combobox
          text: null
          label: 类型
          selector: null
          region: null
          dialog: 新建智能体
        interaction: select_option
        value: 对话型
        post_action_wait:
          type: none
          indicator: null
          timeout: 10000
      - seq: 4
        action: fill
        target: 描述输入框
        element:
          role: textbox
          text: null
          label: 描述
          selector: null
          region: null
          dialog: 新建智能体
        interaction: fill
        value: 测试用
        post_action_wait:
          type: none
          indicator: null
          timeout: 10000
      - seq: 5
        action: click
        target: 确认按钮
        element:
          role: button
          text: 确认
          label: null
          selector: null
          region: null
          dialog: 新建智能体
        interaction: click
        value: null
        post_action_wait:
          type: toast
          indicator: 成功
          timeout: 10000
    expected_results:
      - 智能体列表新增一条记录
      - 提示"创建成功"
    ai_verification_benchmarks:
      - step_ref: 5
        checks:
          - type: core
            assertion: not_appear
            target: 新建智能体
            options: []
            compare: null
          - type: core
            assertion: appear
            target: 测试智能体
            options: []
            compare: null
          - type: core
            assertion: quant_compare
            target: null
            options: []
            compare: 增加1
          - type: weak
            assertion: match_any
            target: 成功
            options: [成功, 创建成功, 保存成功, 操作成功]
            compare: null
    source: design.md#3.2

  TC-AGT-002:
    feature_id: FP-001
    feature_name: 创建智能体
    priority: p1
    description: 创建智能体-名称为空
    route: /agent/list
    preconditions: null
    steps:
      - seq: 1
        action: click
        target: 新建智能体按钮
        element: { role: button, text: 新建智能体, label: null, selector: null, region: 工具栏, dialog: null }
        interaction: click
        value: null
        post_action_wait: { type: dialog, indicator: 新建智能体, timeout: 10000 }
      - seq: 2
        action: fill
        target: 名称输入框(留空)
        element: { role: textbox, text: null, label: 名称, selector: null, region: null, dialog: 新建智能体 }
        interaction: fill
        value: ""
        post_action_wait: { type: none, indicator: null, timeout: 10000 }
      - seq: 3
        action: select_option
        target: 类型下拉框
        element: { role: combobox, text: null, label: 类型, selector: null, region: null, dialog: 新建智能体 }
        interaction: select_option
        value: 对话型
        post_action_wait: { type: none, indicator: null, timeout: 10000 }
      - seq: 4
        action: click
        target: 确认按钮
        element: { role: button, text: 确认, label: null, selector: null, region: null, dialog: 新建智能体 }
        interaction: click
        value: null
        post_action_wait: { type: none, indicator: null, timeout: 10000 }
    expected_results:
      - 提示"名称必填"
      - 未创建成功
    ai_verification_benchmarks:
      - step_ref: 4
        checks:
          - type: core
            assertion: appear
            target: 新建智能体
            options: []
            compare: null
          - type: core
            assertion: match_any
            target: 必填
            options: [必填, 不能为空, 请输入]
            compare: null
          - type: core
            assertion: consistent
            target: null
            options: []
            compare: 与操作前一致
    source: design.md#3.2

  # TC-AGT-003、TC-AGT-004 同结构,略

page_structure:                           # 辅助总图(交叉校验、上下文恢复全局定位)
  main_page:
    regions:
      - name: 页面标题区
        description: 显示"智能体管理"标题
        elements: []
      - name: 工具栏
        description: 包含新建按钮、批量操作等
        elements:
          - role: button
            text: 新建智能体
            label: null
            selector: null
            interaction: click
            sample_value: null
            post_action_wait: { type: dialog, indicator: 新建智能体, timeout: 10000 }
            description: 点击打开"新建智能体"对话框
            required: false
            default_value: null
            extra: null
      - name: 卡片列表区
        description: 智能体卡片网格
        elements: []
      - name: 分页区
        description: 底部分页
        elements: []
    stats:
      total_items: 共 0 条
      total_pages: 0
      items_per_page: 12
  dialogs:
    新建智能体:
      trigger: 点击工具栏"新建智能体"按钮
      fields:
        - role: textbox
          label: 名称
          selector: null
          interaction: fill
          sample_value: 测试智能体_0707
          post_action_wait: { type: none, indicator: null, timeout: 10000 }
          required: true
          default_value: null
          extra: 长度1-50
        - role: combobox
          label: 类型
          selector: null
          interaction: select_option
          sample_value: 对话型
          post_action_wait: { type: none, indicator: null, timeout: 10000 }
          required: true
          default_value: null
          extra: 枚举:对话型/工作流型/数字人型
        - role: textbox
          label: 描述
          selector: null
          interaction: fill
          sample_value: 测试用
          post_action_wait: { type: none, indicator: null, timeout: 10000 }
          required: false
          default_value: null
          extra: null
      buttons:
        - role: button
          text: 确认
          selector: null
          interaction: click
          post_action_wait: { type: toast, indicator: 成功, timeout: 10000 }
          description: 提交表单
        - role: button
          text: 取消
          selector: null
          interaction: click
          post_action_wait: { type: none, indicator: null, timeout: 10000 }
          description: 关闭对话框
```

**关键说明**:
- `cases[TC-AGT-001].steps[1].element` 与 `page_structure.main_page.regions[工具栏].elements[0]` 描述同一个"新建智能体"按钮,但 cases 内联了该用例所需的全部上下文(value/post_action_wait),runner 无需回查总图
- `cases[TC-AGT-001].ai_verification_benchmarks` 与 .md 表格中 TC-AGT-001 的"AI验证基准"列逐项等价(映射规则见 [ai-benchmark-syntax.md](./ai-benchmark-syntax.md) 第六节)
- `cases[TC-AGT-001].steps[2].value = "测试智能体_0707"` 优先级高于 `page_structure.dialogs[新建智能体].fields[名称].sample_value`
- `page_structure` 总图保留: 用于交叉校验 cases 是否覆盖所有功能点、上下文恢复时全局定位、覆盖度统计
