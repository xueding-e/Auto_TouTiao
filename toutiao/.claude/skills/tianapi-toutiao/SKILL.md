---
name: tianapi-toutiao
description: 通过 TianAPI 获取今日头条热搜榜数据，包含热度指数。可独立查询，也可被 daily-hot-article 等 skill 调用以获取热度参照。当用户提到"头条热搜"、"头条热度"、"toutiao hot"、"天API热搜"等时触发。
---

# TianAPI 头条热搜

通过 TianAPI 获取今日头条热搜榜数据，包含热度指数。可独立使用，也可被其他 skill 调用。

## 前置依赖

- **Python 依赖**：`pip install requests`
- **TianAPI Key**：已内置，无需额外配置

## 功能说明

### 1. 独立查询头条热搜

直接运行 CLI 工具，获取当前头条热搜榜：

```bash
# 显示 Top 10 热搜
python ./scripts/get_toutiao_hot.py

# 输出完整 JSON
python ./scripts/get_toutiao_hot.py --json

# 合并 newsnow toutiao.json 数据（需要先在当前目录有 toutiao.json）
python ./scripts/get_toutiao_hot.py --merge

# 合并后输出 JSON
python ./scripts/get_toutiao_hot.py --merge --json
```

### 2. 作为模块被其他 skill 调用

在 Python 脚本中导入 `tianapi_client` 模块：

```python
import sys
import os

# 添加 tianapi-toutiao skill 的 scripts 目录到 path
_tianapi_path = os.path.join(os.path.dirname(__file__), '..', '..', 'tianapi-toutiao', 'scripts')
sys.path.insert(0, os.path.abspath(_tianapi_path))

from tianapi_client import get_toutiao_hot, hotindex_map

# 获取热搜数据
data = get_toutiao_hot()  # 返回 list[dict]，每项含 word 和 hotindex

# 构建标题 -> 热度映射
hmap = hotindex_map(data)
hotindex = hmap.get('某个话题', 0)
```

### API 返回数据格式

```json
[
  {
    "word": "话题名称",
    "hotindex": 5036779
  },
  ...
]
```

## 文件结构

```
tianapi-toutiao/
├── SKILL.md                    <- 你正在读的文件
└── scripts/
    ├── tianapi_client.py       <- 核心客户端模块（可被其他 skill import）
    └── get_toutiao_hot.py      <- 独立 CLI 查询工具
```

## 被 daily-hot-article 调用

`daily-hot-article` skill 的 `fetch_and_analyze.py` 通过 import `tianapi_client` 模块获取头条热度指数，用于跨平台热点排名。调用路径：

```
daily-hot-article/scripts/fetch_and_analyze.py
  → import tianapi-toutiao/scripts/tianapi_client.py
    → get_toutiao_hot()  # 获取热搜列表
    → hotindex_map()     # 构建热度映射
```

## 注意事项

- API Key 已内置在 `tianapi_client.py` 中，开箱即用
- API 调用超时设置为 15 秒，失败时返回空列表不会中断流程
- 热度指数数值越大表示话题越热
