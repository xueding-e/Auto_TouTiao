---
name: brain
description: 头条文章发布记忆系统。从 Obsidian 加载历史发布记录，在内存中维护已发布话题集合，提供去重过滤和发布记录功能。可被 auto-daily-publish 等 skill 调用。当用户提到"加载记忆"、"过滤重复"、"记录发布"、"brain"、"去重选题"等时触发。
---

# Brain 记忆系统

头条文章发布的记忆层。启动时从 Obsidian 加载历史记录，运行时提供去重判断，发布后同步写回 Obsidian。

## 架构

```
auto-daily-publish → brain → Obsidian 存储
```

- **Obsidian**: 持久化存储（只读/写入文件）
- **brain**: 内存记忆（加载、去重、决策）

## 文件路径

| 项目 | 路径 |
|------|------|
| Obsidian Vault | `/Users/wangc/IdeaProjects/obsidian/knowledge-base/` |
| 发布记录文件 | `/Users/wangc/IdeaProjects/obsidian/knowledge-base/03-热点新闻/发布记录.md` |

## 记忆数据结构

brain 在内存中维护以下数据：

```
memory.published_titles = set()     # 已发布标题集合（去重用）
memory.publish_log = []              # 发布日志 [{"title": "xx", "date": "2026-06-08"}]
memory.last_sync = ""                # 最后从 Obsidian 同步的时间
```

## 操作流程

### 操作 1：load() — 加载记忆

每次开始选题前，先从 Obsidian 加载最新发布记录。

1. **读取 Obsidian 发布记录文件**（`Read` 工具）
2. **解析内容**：
   - 按行分割
   - 提取所有 `- ` 开头的列表项（标题）
   - 提取 `## YYYY-MM-DD` 日期标题
   - 构建 `published_titles` 集合和 `publish_log` 列表
3. **更新 `last_sync`** 为当前时间

**文件不存在时**：
- `published_titles` 设为空集合
- `publish_log` 设为空列表
- 告知用户"首次运行，无历史发布记录"

### 操作 2：is_published(title) — 判断是否已发布

1. 检查 `title` 是否在 `memory.published_titles` 集合中（完全匹配）
2. 返回 `True`（已发布）或 `False`（未发布）

### 操作 3：filter(candidates) — 过滤重复候选话题

给定候选话题列表，返回未发布过的话题。

1. **确保记忆已加载**：如果 `last_sync` 为空，先执行 `load()`
2. **过滤**：对每个候选标题，检查是否在 `memory.published_titles` 中
3. **返回结果**：
   ```
   候选话题共 N 个：
   - 已过滤（已发布）：X 个
   - 未发布（可用）：Y 个
   
   可用话题：
   1. 话题A
   2. 话题B
   ```
4. 如果可用话题为 0，告知调用方"所有候选话题都已发布过"

### 操作 4：record(title, date) — 记录新发布

发布成功后，将文章标题记录到记忆中并写回 Obsidian。

1. **检查是否已存在**：
   - 如果 `title` 已在 `memory.published_titles` 中，跳过（避免重复）
2. **更新内存**：
   - 将 `title` 加入 `memory.published_titles`
   - 将 `{"title": title, "date": date}` 加入 `memory.publish_log`
3. **写回 Obsidian**：
   - 读取发布记录文件（如不存在则创建）
   - 检查 `date` 对应的日期段是否存在
   - **日期段存在**：在该日期段末尾追加 `- title`
   - **日期段不存在**：在文件开头插入新的 `## date` 段和标题
   - 用 `Write` 工具保存文件

### 操作 5：stats() — 记忆统计

返回记忆系统的统计信息：
- 总发布文章数
- 最后发布日期
- 各话题的发布频次（如有需要）

## 被 auto-daily-publish 调用

### Phase 2.2（选题阶段）

```
1. 获取 Top 5 候选话题
2. 调用 brain.load()           # 确保记忆最新
3. 调用 brain.filter(candidates) # 过滤已发布话题
4. 从过滤结果中取前 3 个生成文章
5. 如不足 3 个，告知用户
```

### Phase 4（发布后）

```
1. 发布成功
2. 从 .md 文件提取标题（第一个 # 后的文本）
3. 调用 brain.record(title, date)  # 记录到记忆 + 写回 Obsidian
4. 删除本地 .md 文件
```

## 边界情况

| 场景 | 处理 |
|------|------|
| 发布记录文件首次不存在 | load() 返回空集合，record() 时自动创建 |
| 候选话题全部已发布 | filter() 返回空列表，告知调用方顺延或停止 |
| 同一天多次发布 | record() 追加到同一日期段下 |
| 标题含特殊字符 | 原样记录和匹配，不做转义 |
| 记忆未加载时调用 filter | 自动先执行 load() |
