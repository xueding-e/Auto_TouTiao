# 模式二: URL → 页面探索 → 测试用例

> 本文档为 `test-case-generator` skill 的模式二详细规则,只描述模式二独有的内容。共用部分见: [SKILL.md](../SKILL.md)(整体流程与基础探索) | [ai-benchmark-syntax.md](./ai-benchmark-syntax.md)(AI 验证基准语法) | [page-structure-yaml-spec.md](./page-structure-yaml-spec.md)(yaml 规范)

---

## 1. 模式说明与输入特征

- **输入**: 目标 URL(http/https 开头)
- **功能点来源**: 浏览器探索本身(探索即功能点提取)
- **浏览器探索角色**: **主流程探索**(不可降级),包括基础探索 + 深度交互 + 深度遍历导航
- **失败后果**: 探索失败 = 无用例

> 基础探索(navigate+snapshot)的完整流程见 [SKILL.md](../SKILL.md) 第二步。本节描述模式二在基础探索之上**独有的深度探索**。

---

## 2. 深度探索流程

> 所有 MCP 调用必须附带 `timeout: 15000`,超时即降级。

**Chrome DevTools MCP 探索流程**:

1. `navigate_page`(timeout: 15000) 打开目标 URL
2. `take_snapshot`(timeout: 15000) 获取 a11y 树(含 uid)
3. 遍历快照,识别可交互元素:
   - `role: button/link/menuitem/tab` → 点击类功能点
   - `role: textbox/combobox/checkbox/radio` → 输入/选择类功能点
   - `role: navigation/dialog/alert` → 导航/弹窗类功能点
4. 对每个主功能入口触发交互(每次调用 timeout: 15000),观察:
   - 页面跳转(URL 变化)
   - DOM 变化(弹窗出现/列表加载)
   - 交互后 `take_snapshot`(timeout: 15000) 记录状态
5. 深度探索: 对导航菜单逐项展开,记录二级/三级功能入口(每次操作 timeout: 15000)
6. 遇到登录页时,先 `fill`(timeout: 15000) 账号密码 → `click`(timeout: 15000) 登录按钮,完成登录后再探索
7. 任何 MCP 调用超过 15s 未返回视为超时: 该操作降级,标记"超时未响应",继续探索下一个元素;同一元素连续 2 次超时则跳过

---

## 3. 功能点清单与页面结构提取

> `features[]` 为功能点清单(与 `.md` 一致),`page_structure` 为页面结构描述(runner 执行时的"地图")。探索时需同时提取功能点和页面结构信息,字段规范详见 [page-structure-yaml-spec.md](./page-structure-yaml-spec.md)。

```yaml
module: 登录页
source_type: url
url: https://example.com
generated_at: 2026-06-19T10:00:00Z
features:
  - id: FP-001
    name: 登录
    source: 页面探索(https://example.com)
    cases: [TC-LOG-001]
  - id: FP-002
    name: 智能体管理
    source: 页面探索(https://example.com)
    cases: [TC-AGT-001]
page_structure:
  main_page:
    regions:
      - name: 登录表单区
        description: 页面中央登录表单
        elements:
          - role: textbox
            text: null
            label: "用户名"
            description: 用户名输入框
            required: true
          - role: textbox
            text: null
            label: "密码"
            description: 密码输入框
            required: true
          - role: button
            text: "登录"
            description: 提交登录表单
    stats:
      total_items: null
      total_pages: null
  dialogs: {}
```

---

## 4. 功能点 → 测试用例

对每个可点击功能点生成至少一条"正常点击"用例;对输入类元素补充"输入校验"用例:

| 功能点类型 | 生成的用例 | 等级 |
|-----------|-----------|------|
| 点击类(按钮/链接/菜单) | 正常点击 → 验证跳转/弹窗/状态变化 | p0(主入口) / p1(次级) |
| 输入类(文本框) | 正常输入 + 空值校验 + 边界值 | p0(正常) / p1(校验) |
| 选择类(下拉/单选/多选) | 正常选择 + 各选项切换 | p0(正常) / p1(切换) |
| 勾选类(复选框/开关) | 勾选 + 取消勾选 | p1 |

---

## 5. AI 验证基准生成(模式二场景映射表)

> 共用语法规则(检查项结构、类型判定、语义匹配、.md ↔ yaml 映射)见 [ai-benchmark-syntax.md](./ai-benchmark-syntax.md)。本节仅列出模式二的"探索数据→基准映射"和生成规则。

模式二的 AI验证基准基于**探索过程中观察到的真实页面状态**编写,具有最高精度。利用探索时获取的真实数据填充模板占位符。

### 5.1 探索数据→基准映射

| 信息来源 | 探索时获取的内容 | AI验证基准中的应用 |
|---------|----------------|-------------------|
| `take_snapshot` 输出 | 页面元素文本、结构、角色、uid | 直接引用**真实元素文本**作为锚点(如对话框标题、按钮文字、表格表头) |
| 交互后状态变化 | URL 跳转、弹窗出现/消失、列表加载 | 描述交互后 snapshot 应显示的状态,**必须包含正向+反向断言** |
| `post_action` 字段 | 功能点的交互后行为 | 转为量化可观测描述(如"N值比操作前增加1") |
| `evaluate_script` 结果 | 列表行数、选中状态、元素属性 | 用于量化验证(如"表格行数从5变为6") |
| `list_console_messages` | 控制台错误/警告 | 补充反向断言:"页面不出现error提示" |

### 5.2 生成规则

1. 探索时已见过真实页面,**验证基准必须填入真实元素文本**,不得使用 `<>` 占位符
2. 套用对应场景的编写模板,将模板中的占位符替换为探索观察到的真实文本
3. 正常路径:必须包含正向断言(出现什么)+反向断言(不再出现什么)+量化变化(数量增减)
4. 校验场景:使用 `含"A"/"B"` 格式列出探索时观察到的**真实校验提示文本**,同时保留近义词汇兜底
5. 跳转场景:必须描述 URL 变化(包含真实路径关键词)和**至少2个**目标页面特征元素
6. 列表展示场景:必须列出探索时观察到的**真实表头字段名**(至少4个),不用模糊描述
7. 每条基准以 `【步骤N后】` 开头,多个验证点用 `;` 分隔,推荐用 `①②③④` 编号

### 5.3 示例

- 探索观察到登录后跳转首页,侧边栏含"人员效能看板"等菜单,URL 从 `/login` 变为 `/dashboard`
- AI验证基准: `【步骤3后】①snapshot中URL从/login变为/dashboard;②snapshot中包含"人员效能看板""团队效能看板"菜单文本;③页面不再出现登录表单;④页面不出现error提示`

- 探索观察到创建对话框标题为"新增知识库",确认按钮名为"确认"
- AI验证基准: `【步骤5后】①snapshot中不再出现"新增知识库"对话框;②知识库卡片列表中出现含"测试知识库"的卡片;③底部"共N条"中N值比操作前增加1;④可能出现含"成功"的提示信息`

---

## 6. 输出特点

模式二**必须进行浏览器探索**,因此:
- "点击步骤"列基于真实页面交互填写,步骤中的目标元素名称来自探索结果
- "AI验证基准"列基于探索时 `take_snapshot` 观察到的真实页面状态编写,精度高
- "关联需求点"列填写 `页面探索(<URL>)`
- 用例覆盖页面所有可交互主功能入口
- `.page-structure.yaml` 包含完整的页面区域划分、元素清单、对话框字段表和页面统计数据,runner 可据此在 snapshot 中按区域+role+label 精准定位元素

---

## 7. 失败处理

| 场景 | 处理 |
|------|------|
| MCP 调用超时(15s) | 该次操作降级:在功能点中标注"超时未响应",继续探索其他元素;同一元素连续2次超时则跳过并标记"无法探索" |
| 目标 URL 不可访问 | 报错,询问是否更换 URL 或提供 mock 页面 |
| Chrome DevTools MCP 不可用 | 报错,提示用户检查 MCP 环境配置;或由用户手动提供页面截图/HTML 供分析,点击步骤标注"待确认" |
| 元素无法交互 | 记录功能点但标注"无法探索",不省略用例,点击步骤标注"待确认" |
| 登录失败 | 询问账号密码,或提示用户提供已登录的浏览器会话;若无法登录则报错 |

---

## 8. 速查:浏览器探索命令清单

> **所有命令统一超时**: `timeout: 15000`(15秒),超时即降级,不阻塞后续探索。

| MCP 命令 | 用途 | 超时参数 |
|---------|------|---------|
| `navigate_page` | 打开 URL / 前进 / 后退 / 刷新 | `timeout: 15000` |
| `take_snapshot` | 获取 a11y 树(含 uid),识别可交互元素 | `timeout: 15000` |
| `click` | 点击元素(验证功能点) | `timeout: 15000` |
| `fill` | 填充输入框(验证输入类功能点) | `timeout: 15000` |
| `wait_for` | 等待元素出现/文本变化 | `timeout: 15000` |
| `evaluate_script` | 执行 JS(获取元素属性/列表) | `timeout: 15000` |
| `list_console_messages` | 查看控制台(排查异常) | `timeout: 15000` |
