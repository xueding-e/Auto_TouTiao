---
name: toutiao-publisher
description: 使用Chrome DevTools MCP自动将本地Markdown文章发布到头条号。当用户提到"发布头条"、"头条发布"、"toutiao publish"、"发布文章到头条"、"自动发布头条"时触发。
---

# 头条号文章自动发布

使用Chrome DevTools MCP操控浏览器，将本地Markdown文章自动填写到头条号发布页面并完成发布。

## 前置条件

- Chrome DevTools MCP已配置并可用
- 用户已在浏览器中登录头条号(mp.toutiao.com)
- 本地指定文件夹下存在 `.md` 文件

## 超时控制

**整个发布流程（从导航到发布页开始）必须在 10 分钟内完成。**

- 开始发布前记录起始时间
- 每个关键步骤（标题填写、正文粘贴、配图插入、点击发布）完成后检查耗时
- **如果超过 10 分钟仍未发布成功**：
  1. 记录失败原因到 Obsidian（见下方"错误记录到 Obsidian"）
  2. 删除当前待发布的 `.md` 文件
  3. 取下一篇继续发布（如果是批量发布流程）
  4. 向用户汇报超时情况

## 发布流程

### 第一步：加载MCP工具

加载 `chrome-devtools` MCP server的所有工具，确保后续步骤可用。

### 第二步：导航到发布页面

使用 `navigate_page` 打开发布页面（URL 从 `config/platforms.yaml` 的 `publish_url` 读取）：
```
# 默认值，如有变更请修改 config/platforms.yaml
https://mp.toutiao.com/profile_v4/graphic/publish?from=toutiao_pc
```

**登录检查**：
- 等待页面加载（用 `wait_for` 检测页面特征文本如"发布"或"图文"）
- 如果页面跳转到了登录页，**停止操作并告知用户需要先登录**

### 第三步：扫描本地文章

扫描用户指定的文章文件夹（默认从 `config/platforms.yaml` 的 `output_dir` 读取），找到所有 `.md` 文件：

- 如果有多个 `.md` 文件，按**修改时间排序**，取最新的一个
- 如果文件夹下没有 `.md` 文件，告知用户并停止

### 第四步：解析Markdown内容

读取选中的 `.md` 文件并解析为**标题**和**正文**。

**标题提取规则**（按优先级）：
1. 文件内第一个 `# ` 一级标题 → 去除 `# ` 后作为标题
2. 若不匹配，使用文件名（去掉 `.md` 后缀）作为标题

**正文提取规则**：
- 去掉标题行（第一个 `# ` 行）
- 保留其余所有内容（包括二级及以下标题、列表等）
- 若文件没有一级标题，则全文作为正文
- **注意**：.md 文件中不含图片，无需解析图片

**结构化输出**：解析完成后应得到以下两个对象：
```
title:      标题字符串
bodyLines:  正文行数组（每行为一段）
```

### 第五步：定位页面元素

使用 `take_snapshot` 获取页面的a11y树，识别以下元素：

| 元素 | 常见特征 |
|------|---------|
| 标题输入框 | placeholder含"标题"或"请输入标题" |
| 正文编辑区 | contenteditable="true" 的div，或富文本编辑器区域 |
| 预览并发布按钮 | 文案为"预览并发布" |

**兜底策略**：如果a11y树无法精确定位，使用 `evaluate_script` 通过DOM选择器查找：
```javascript
// 标题输入框（textarea，非 input）
document.querySelector('textarea[placeholder*="标题"]') ||
document.querySelector('textarea[maxlength]') ||
document.querySelector('textarea')

// 正文编辑区
document.querySelector('[contenteditable="true"]') ||
document.querySelector('.ProseMirror') ||
document.querySelector('div[role="textbox"]')
```

### 第六步：填写标题

标题输入框是一个 `textarea` 元素（非 `input`）。使用 `click` 聚焦后用 `type_text` 输入标题。

**重要：不要使用 `fill` 工具填写标题**，`fill` 会丢失最后一个字符。也不要使用 `evaluate_script` + `nativeInputValueSetter` 方式设置标题，会导致后续页面状态异常。

```
1. click(uid="<标题输入框uid>")   // 聚焦
2. type_text(text="<标题文本>")   // 逐字输入，不会截断
```

**注意**：
- 标题长度应在2-30字之间，超长时截断并提示用户
- 填写后通过 `take_snapshot` 确认标题完整显示

### 第七步：填写正文文本（使用剪贴板粘贴方式）

**重要：头条号编辑器使用 ProseMirror 富文本引擎，直接操作 `editor.innerHTML` 会破坏其内部状态管理，导致 `contenteditable` 变为 `"false"` 等异常。必须使用剪贴板粘贴（ClipboardEvent）方式插入内容。**

#### 7.1 构建 HTML 内容

将正文 Markdown 转为 HTML：

- 加粗标记 `**text**` → `<strong>text</strong>`
- `# ` / `## ` 标题 → `<h1>` / `<h2>`
- 列表项 `- text` → `<li>text</li>`
- 正文段落 → `<p>段落文本</p>`
- 正文中**不含图片**，无需处理 Markdown 图片语法

#### 7.2 通过剪贴板粘贴插入内容

使用 `evaluate_script` 模拟粘贴事件，将 HTML 内容插入编辑器：

```javascript
const editor = document.querySelector('.ProseMirror');
if (editor) {
  editor.click(); // 确保编辑器获得焦点

  // 构建完整的 HTML 内容（不含图片，图片在第八步上传）
  const htmlContent = `
    <h2>小标题</h2>
    <p>第一段正文...</p>
    <p>第二段正文...</p>
    <p><strong>加粗文本</strong></p>
  `.trim();

  // 通过 ClipboardEvent 模拟粘贴
  const clipboardData = new DataTransfer();
  clipboardData.setData('text/html', htmlContent);
  clipboardData.setData('text/plain', '纯文本备用内容...');

  const pasteEvent = new ClipboardEvent('paste', {
    bubbles: true,
    cancelable: true,
    clipboardData: clipboardData
  });

  editor.dispatchEvent(pasteEvent);
}
```

#### 7.3 验证粘贴结果

粘贴后需验证编辑器状态：

```javascript
const editor = document.querySelector('.ProseMirror');
// 检查 contenteditable 是否仍为 true
const editable = editor.getAttribute('contenteditable');
// 应显示 "true"
// 检查段落数量
const childCount = editor.children.length;
// 此时应无图片（图片在第八步上传）
const imgCount = editor.querySelectorAll('img').length;
```

**注意**：
- 加粗标记 `**text**` 需转换为 `<strong>text</strong>`
- 正文中**不含图片**，粘贴后编辑器内应无 `<img>` 元素

### 第八步：搜索并插入新闻配图

正文粘贴完成后，为文章搜索并插入 **2-3 张**与话题相关的配图。

> **核心理念**：文章话题是网上热点，新闻报道里已经有最贴切的图片。优先从相关新闻页面提取高清大图，搜不到再用 ImageGen 生成。

#### 8.1 确定搜索关键词

从文章标题中提取核心话题作为搜索关键词。标题完整文本通常就是最佳检索词。

#### 8.2 搜索新闻配图（策略链）

| 优先级 | 策略 | 操作 |
|--------|------|------|
| 1 | **新闻页面提取** | WebSearch 搜相关新闻 → WebFetch 获取页面 → 提取 `<img>` 标签 → 过滤高清大图 |
| 2 | **ImageGen 生成** | 搜不到相关图片时，用 ImageGen 生成与话题相关的配图 |

**策略 1 详述：**

1. 用 **WebSearch** 搜索话题关键词，获取 3-5 个新闻链接
2. 对每个链接用 **WebFetch** 获取 HTML
3. 提取 `<img>` 标签 src，跳过小图（URL 含 `icon`/`logo`/`avatar`/`favicon`/`w50h50` 等）
4. 通过 URL 尺寸标记（如 `w800h600`）过滤低分辨率图
5. **相关性过滤**：只保留图片 URL 或来源标题含话题关键词的图片
6. 选取 2-3 张不同来源的高清图

**策略 2 详述：**

如果新闻页面完全搜不到相关图片，用 ImageGen 生成。ImageGen 输出本地文件，需先读取为 base64 Data URI，再通过剪贴板粘贴插入：

1. `ImageGen(name="<话题简称>", prompt="<描述话题场景>", size="1024x768")`
2. 用 `Read` 工具读取生成图片（返回 base64），构造 data URI：`data:image/png;base64,...`
3. 将 data URI 作为 `<img src>` 通过剪贴板粘贴插入

#### 8.3 通过剪贴板粘贴插入图片

**所有图片（HTTPS URL 和本地文件）统一使用剪贴板粘贴方式**，工具栏上传不可靠。

图片在正文段落的**合适位置**插入：第 1 张在文章开头，第 2 张在中间，第 3 张在末尾。

```javascript
const editor = document.querySelector('.ProseMirror');
let paragraphs = Array.from(editor.querySelectorAll('p'));

// 要插入的图片 URL 或 data URI 列表
const imageUrls = [
  'https://example.com/news/image1.jpg',
  'https://example.com/news/image2.jpg',
];

// 目标位置（段落索引）
const positions = [0, Math.max(1, Math.floor(paragraphs.length / 2))];

imageUrls.forEach((url, i) => {
  const target = paragraphs[positions[i]];
  if (!target) return;

  // 在目标段落后设置光标
  const range = document.createRange();
  range.setStartAfter(target);
  range.collapse(true);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);

  // 通过剪贴板粘贴图片（与第七步同模式）
  const clipboardData = new DataTransfer();
  clipboardData.setData('text/html', `<p><img src="${url}" alt="配图"></p>`);
  clipboardData.setData('text/plain', '');

  editor.dispatchEvent(new ClipboardEvent('paste', {
    bubbles: true, cancelable: true, clipboardData: clipboardData
  }));

  // 重新获取段落列表（DOM 已变化）
  paragraphs = Array.from(editor.querySelectorAll('p'));
});
```

#### 8.4 配图验证与去重

插入完成后验证：
1. `editor.querySelectorAll('img').length` >= 2（至少 2 张）
2. 每张图 naturalWidth > 0（成功加载）

然后检测并清理重复图片。剪贴板粘贴每张图时可能产生重复（同一图片出现两次）：

```javascript
const editor = document.querySelector('.ProseMirror');
const imgs = Array.from(editor.querySelectorAll('img'));

const srcMap = {};
imgs.forEach((img) => {
  const src = img.src || img.getAttribute('src') || '';
  if (!srcMap[src]) srcMap[src] = [];
  srcMap[src].push(img);
});

const hasDuplicates = Object.values(srcMap).some(group => group.length > 1);
if (hasDuplicates) {
  Object.values(srcMap).forEach(group => {
    if (group.length > 1) {
      for (let i = 1; i < group.length; i++) {
        const parent = group[i].closest('p') || group[i].parentElement;
        if (parent) parent.remove();
      }
    }
  });
}
```

**重要**：不要在没有检测的情况下直接按奇偶索引删除图片。

### 发布前检查（第八步之后、第九步之前）

在点击"预览并发布"之前，必须完成以下检查：

1. **标题检查**：
   - 使用 `take_snapshot` + `evaluate_script` 读取标题 `textarea` 的 `value`
   - 确认标题非空、长度 2-30 字符
   - 标题应与 `.md` 文件中的一级标题一致
   - 如果为空或不一致，重新填写

2. **正文检查**：
   - 使用 `evaluate_script` 检查 `.ProseMirror` 的内容
   - `editor.children.length` 应 > 0（有正文内容）
   - `editor.innerText.trim()` 长度应 > 50 字符（排除空文章）
   - 确认正文包含文本内容（不只是图片）

3. **配图检查**：
   - `editor.querySelectorAll('img').length` 应 >= 2
   - **如果 < 2 张配图且所有搜索策略都未能获取到图片**：
     1. 记录失败原因到 Obsidian
     2. 删除当前 `.md` 文件
     3. 取下一篇继续发布
     4. 停止当前发布流程

4. 任何一项检查不通过，修复后重新检查，再进入第九步

### 第九步：点击预览并发布

点击"预览并发布"按钮（通过 `take_snapshot` 找到按钮的 uid 后 `click`）。

**封面图处理**：
- 如果弹出封面图选择面板并提示"图片尺寸过小"，说明正文中的图片不满足封面图尺寸要求（最小 452×352）
- 此时应点击"无封面"选项跳过封面图要求
- 使用 `evaluate_script` 定位并点击"无封面"的 LabelText 元素：
```javascript
const labels = document.querySelectorAll('label.byte-radio');
for (const label of labels) {
  if (label.textContent.trim() === '无封面') {
    label.click();
    break;
  }
}
```
- 选中"无封面"后，关闭封面图面板（点击面板关闭按钮），再重新点击"预览并发布"

### 第十步：验证发布结果

点击"预览并发布"后，**通过检查网络接口返回确认发布结果**，不依赖页面 UI 提示（头条有显示 bug，"提交成功"文字可能不显示或短暂消失）。

**验证方法**：

1. 使用 `list_network_requests` 获取发布后的网络请求，过滤 `resourceTypes` 为 `["fetch", "xhr"]`
2. 找到最新的 `POST https://mp.toutiao.com/mp/agw/article/publish` 请求（取最后一条）
3. 使用 `get_network_request` 获取该请求的响应

**成功标志**：

响应 body 中同时满足：
- `"code": 0`
- `"message": "提交成功"`
- `"data.pgc_id"` 存在（文章 ID，如 `"7647812053961245219"`）

**失败标志**：
- `"code": 7050` → `"保存失败"`（通常是图片尺寸不满足封面要求）
- 其他非 0 的 code → 读取 `"message"` 和 `"reason"` 字段告知用户

**发布成功后**：
1. 使用 `close_page` 关闭当前浏览器页面标签
2. 向用户汇报发布结果（标题、文章 ID）

**注意**：头条 UI 的"提交成功"提示可能不显示或短暂消失，`take_snapshot` 无法稳定捕获。**必须以接口返回为准。**

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| Chrome DevTools 返回 "The browser is already running" | 存在未被 MCP 管理的 Chrome 实例占用了 user data directory。**杀掉所有 Chrome 进程，等待 3 秒后重试**。macOS 用 `killall Google\ Chrome`，Windows 用 `taskkill /F /IM chrome.exe` |
| 未登录 | 停止，提示用户先登录 |
| 无.md文件 | 停止，提示用户检查文件夹 |
| 标题/正文为空 | 停止，提示用户检查文件内容 |
| 页面元素找不到 | 用 `take_snapshot` 截图，告知用户页面结构变化 |
| 发布按钮不可点击 | 检查是否有必填项未填（如封面图、分类），补充后再试 |
| 发布失败有提示 | 读取错误提示内容，告知用户具体原因；记录到 Obsidian |
| 图片加载失败 | 跳过该图片，完成后告知用户哪些图片未能加载 |
| 图片搜索无结果 | 使用 ImageGen 生成，读取为 base64 Data URI，通过剪贴板粘贴（第八步策略2） |
| **所有策略均未能获取 >= 2 张配图** | **记录到 Obsidian，删除当前 .md 文件，取下一篇继续** |
| **发布耗时超过 10 分钟** | **记录到 Obsidian，删除当前 .md 文件，取下一篇继续** |

## 错误记录到 Obsidian

**所有发布失败或异常（含超时、配图失败、接口错误等）必须记录到 Obsidian 笔记**，供后续 gbrain 提炼记忆、分析模式、避免重复出错。

### 记录格式

在 Obsidian 中创建/追加笔记，每条记录包含：

```markdown
---
date: {{YYYY-MM-DD HH:mm}}
article: {{文件名}}
title: {{文章标题}}
error_type: {{timeout|no_images|publish_failed|login_expired|element_not_found|browser_stuck|other}}
---

## 失败详情

- **耗时**：X 分钟
- **失败步骤**：{{具体步骤描述}}
- **错误信息**：{{接口返回的 code/message 或页面提示}}
- **已尝试的修复**：{{做了什么尝试}}
- **配图情况**：{{搜索了哪些关键词，找到/未找到几张}}

## 上下文

- 文章目录：{{output_dir 路径}}
- 浏览器状态：{{页面 URL、是否异常}}
```

### 记录位置

- 默认写入 Obsidian vault 下的 `Toutiao Publish Log/{{YYYY-MM-DD}}.md`
- 如果当天文件已存在，追加到末尾
- 使用 `evaluate_script` + `navigator.clipboard` 或本地文件写入（取决于 Obsidian 是否开放 API）

### 后续利用

- gbrain 定期从 Obsidian 笔记中提取失败模式
- 形成记忆反馈到本 skill 的"已知问题与踩坑记录"表
- 避免重复犯同样的错误

## 注意事项

- 头条号发布页是动态渲染的，元素加载可能需要1-3秒，关键步骤间使用 `wait_for` 等待
- **标题填写必须使用 `click` + `type_text`**，不要用 `fill`（会丢字）或 JS 方式（会破坏页面状态）
- **正文内容插入必须使用 ClipboardEvent 剪贴板粘贴方式**（见第七步），不要用 `editor.innerHTML` 直接操作
- **编辑器选择器**：使用 `.ProseMirror` 定位编辑器
- **配图**：正文粘贴后，通过第八步搜索新闻配图并以剪贴板粘贴插入（目标 2-3 张）。优先新闻原图，无结果时用 ImageGen 生成
- **封面图**：如果正文图片尺寸不满足封面要求（最小 452×352），选择"无封面"选项
- 发布前若需要选择文章分类或添加标签，根据页面提示补充
- 操作完成后向用户汇报：发布状态、使用的文章文件名、标题、图片插入情况
- **超时控制**：发布流程超过 10 分钟时停止，记录失败到 Obsidian，删除当前文章，下一篇继续
- **配图底线**：所有策略均未能获取 >= 2 张配图时不发布，记录失败到 Obsidian，删除当前文章
- **错误记录**：所有发布失败必须记录到 Obsidian，供 gbrain 提炼记忆、持续进化

## 已知问题与踩坑记录

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 剪贴板粘贴后可能出现重复图片 | 粘贴事件有时被编辑器处理两次，导致同一 src 的图片出现多次 | 先按 src 属性检测是否真的存在重复，确认重复后再清理（保留每组第一张），见第8.4步。无重复时不做任何操作 |
| 粘贴后首段出现"编辑搜图"文字 | 这是图片 hover 时显示的覆盖层文本，不是实际正文内容 | 无需处理，这只是 a11y 树中的 UI 控件文本 |
| 点击"预览并发布"后弹出封面图面板 | 默认"单图"模式下正文图片尺寸不满足封面要求 | 选择"无封面"，关闭面板，再次点击"预览并发布" |
| `fill` 工具填写标题丢失最后一个字符 | 头条号标题 `textarea` 与 `fill` 工具的交互兼容性问题 | 使用 `click` 聚焦后 `type_text` 逐字输入 |
| `evaluate_script` + nativeInputValueSetter 设置标题后页面状态异常 | 直接修改 textarea value 可能破坏 React 状态管理 | 不要用 JS 方式设置标题，只用 `type_text` |
| `wait_for` 等待"提交成功"超时 / `take_snapshot` 找不到"提交成功" | 头条 UI 有显示 bug，"提交成功"文字可能不显示或短暂消失 | 不依赖 UI 提示，通过 `list_network_requests` + `get_network_request` 检查 `POST /mp/agw/article/publish` 接口返回的 `code:0` 和 `message:"提交成功"` 确认发布成功 |
| 发布流程超过 10 分钟未完成 | 头条页面响应慢或图片上传耗时过长 | 超时后停止，记录失败到 Obsidian，删除当前文章，下一篇继续 |
| 所有配图策略均失败（新闻原图 + ImageGen 均无可用图片） | 热点话题在某些时段确实没有可用图片资源 | 不发布，记录到 Obsidian，删除当前 .md 文件，下一篇继续 |
| 所有 Chrome DevTools MCP 调用返回 "The browser is already running" | 存在未被 MCP 管理的 Chrome 实例占用了 user data directory | 用 `killall Google\ Chrome`（macOS）或 `taskkill /F /IM chrome.exe`（Windows）杀掉 Chrome 进程，等待 3 秒后重试 |
