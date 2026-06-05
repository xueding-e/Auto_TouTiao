# 第六步：搜索并插入配图

> **核心理念**：你的话题是网上热点，新闻报道里已经有最贴切的图片了。搜图的本质是从新闻页面或搜索引擎中找到高清大图的 HTTPS URL，直接引用即可，**不需要下载到本地**。

## 配图分辨率要求（强制）

- **最低分辨率**：宽 >= 800px 且 高 >= 600px
- **推荐分辨率**：宽 >= 1024px
- 图片 URL 中通常包含尺寸信息（如 `w1080h720`），可据此快速过滤小图
- 验证图片可访问性：对 URL 发 HEAD 请求确认 HTTP 200

## 策略链（按优先级执行）

| 优先级 | 策略 | 操作 | 适用场景 |
|--------|------|------|----------|
| 1 | **新闻页面全量提取** | WebSearch 搜相关新闻 → 请求页面提取所有 `<img>` 标签 → 按 URL 尺寸过滤 | 首选，成功率最高 |
| 2 | **og:image 提取** | 从新闻页面 `<meta property="og:image">` 提取 | 部分网站有效，但需验证图片尺寸 |
| 3 | **图片搜索引擎** | `search_topic_images(topic)` 搜百度/必应图片 | 兜底方案，API 可能不稳定 |

## 6.1 新闻页面全量提取（首选，实战验证最有效）

热点话题一定有多个新闻网站报道。直接请求新闻页面 HTML，提取**所有** `<img>` 标签的 src，然后按 URL 中的尺寸信息过滤小图。

> **为什么不用 og:image？** 实测发现新浪财经等主流站点的 og:image 经常设置为站点 Logo（如 85x85 小图标），而非文章配图。必须提取正文中的所有图片才能获得高清大图。

```python
import re, requests

def extract_article_images(url, min_size=400):
    """从新闻页面提取所有高清大图。
    通过 URL 中的尺寸标记（如 w1080h720）过滤小图。
    返回 HTTPS URL 列表。
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    r = requests.get(url, headers=headers, timeout=20)
    r.encoding = 'utf-8'

    # 提取所有 img src 和 data-src（lazy loading）
    img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', r.text, re.I)
    img_urls += re.findall(r'data-src=["\']([^"\']+)["\']', r.text, re.I)

    # 跳过明显的小图和图标
    skip_keywords = ['icon', 'logo', 'avatar', 'emoji', '1x1', 'pixel',
                     'qr_code', 'favicon', 'w85h85', 'w50h50', 'w32h32']

    results = []
    seen = set()
    for img_url in img_urls:
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        if not img_url.startswith('http'):
            continue
        if img_url in seen:
            continue
        if any(kw in img_url.lower() for kw in skip_keywords):
            continue
        # 检查 URL 中的尺寸标记（如 w1080h720）
        size_match = re.search(r'w(\d+)h(\d+)', img_url)
        if size_match:
            w, h = int(size_match.group(1)), int(size_match.group(2))
            if w < min_size or h < min_size:
                continue
        seen.add(img_url)
        results.append(img_url)

    return results

# 用法：
# 1. WebSearch 搜到 3-5 个相关新闻链接
# 2. 对每个链接调用 extract_article_images(news_url)
# 3. 合并去重后，选取前 3 张插入 Markdown
# 4. 发 HEAD 请求验证可访问性（HTTP 200）
```

**操作步骤**：
1. 用 WebSearch 搜索话题相关新闻，获取 3-5 个新闻 URL
2. 对每个 URL 调用 `extract_article_images()`，合并所有结果并去重
3. 选取前 2-3 张不同来源的高清图
4. 对每张图发 HEAD 请求确认 HTTP 200 + Content-Type 含 `image`
5. 直接插入 Markdown，不下载

## 6.2 og:image 提取（备选）

部分新闻网站的 og:image 确实是高清文章封面图。提取后**必须验证尺寸**，如果 URL 中包含 `w85h85` 等小尺寸标记则跳过。

```python
def extract_og_image(url):
    """从新闻页面提取 og:image，需额外验证尺寸"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    r = requests.get(url, headers=headers, timeout=20)
    for pattern in [
        r'<meta\s+property="og:image"\s+content="([^"]+)"',
        r'<meta\s+name="twitter:image"\s+content="([^"]+)"',
    ]:
        m = re.search(pattern, r.text, re.I)
        if m:
            img = m.group(1)
            if img.startswith('//'):
                img = 'https:' + img
            # 验证不是小图标
            if 'w85h85' in img or 'w50h50' in img:
                continue
            return img
    return None
```

## 6.3 图片搜索引擎（兜底）

如果新闻页面提取全部失败，用 `search_topic_images()` 搜百度/必应图片。

> **注意**：百度/必应图片 API 可能不稳定（JSON 解析错误、网络超时等），作为兜底方案使用。如果搜索也失败，考虑用 ImageGen 工具生成相关配图。

```python
from scripts.image_search import search_topic_images

images = search_topic_images("老人买基金亏70多万银行被判担责", count=3)
# images 中每个元素包含 'url', 'width', 'height' 字段
# 搜索结果已自动过滤低分辨率图片（< 800x600）
# 已是 HTTPS 链接，直接插入 Markdown
```

> 不要把长话题拆碎！热点话题的完整标题本身就是最好的检索词。

## 6.4 配图插入 Markdown

获取到 HTTPS 图片链接后，**直接插入 Markdown，不下载到本地**：

- 第一张（必须）：标题后作为封面图
- 第二张（必须）：文章中部关键观点后
- 第三张（可选）：文章末尾
- 全文配图数量：**2-3张**，不可少于2张
- 格式：`![描述](https://...)`
- 图片 URL 必须是完整的 `https://` 链接
- 插入后用 `verify_md_images.py` 验证全部图片可访问

> 最终 md 中所有图片都是 HTTPS URL，零本地图片引用。

## 6.5 图片相关性验证（强制）

> **核心理念**：宁可少配图，也不配无关图。一张与话题无关的图片比没有图片更糟糕——它会破坏文章的专业性和读者信任。

### 相关性格子

每张候选图片必须通过以下三项检查：

| 检查项 | 方法 | 判定标准 |
|--------|------|----------|
| **元数据匹配** | 检查图片的 `title`/`fromPageTitle`/`alt` 是否包含话题关键词 | 至少含1个话题核心词 |
| **来源页面匹配** | 检查图片来源页面标题是否与话题相关 | 来源页面标题含话题关键词 |
| **URL 语义匹配** | 检查图片 URL 路径中是否含话题相关词 | URL 路径不含无关领域词 |

### 六步验证法

执行图片筛选时，**AI 必须对每张候选图进行人工审视**：

1. **列出** 所有候选图片的元数据（title、来源页面标题、URL）
2. **提取** 话题核心关键词（人名、事件、地点、机构名等）
3. **逐张对比**：图片元数据 vs 话题关键词
4. **剔除** 不相关图片（如话题是"韦东奕"，配图却是"刘强东"或随机风景照）
5. **确认** 最终 2-3 张图均与话题直接相关
6. **记录** 剔除原因，方便后续追溯

### 常见不相关类型（必须识别并剔除）

| 类型 | 示例 | 原因 |
|------|------|------|
| 同名不同人 | 话题"韦东奕"，图片是"刘强东" | 人名部分重合但完全不同的人 |
| 泛化关键词 | 话题"银行违规"，图片是随机银行大楼 | 只有类别词匹配，无具体事件关联 |
| 跨领域 | 话题"A股暴跌"，图片是美食/风景 | 关键词拆分后搜到无关领域 |
| 通用占位图 | 话题"XXX事故"，图片是交警指挥交通 | 与具体事件完全无关的通用图 |

### 兜底方案

如果所有候选图都无法通过相关性验证：

1. **不要强行插入无关图片**
2. 使用 **ImageGen** 工具生成与话题直接相关的配图
3. 生成图也需验证：检查生成结果中的人物、场景是否与话题一致
4. 如果 ImageGen 也失败，**允许多于1张图但少于2张**，在文章中注明原因

## 实战踩坑记录

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| og:image 返回 85x85 小图标 | 新浪等站点把 og:image 设为站点 Logo | 改用全量提取 `<img>` 标签（6.1） |
| 百度图片 API 返回解析错误 | API 接口变动或反爬 | 优先用新闻页面提取，搜索作为兜底 |
| 提取到的图片全是同一张 | 只提取了第一张 `<img>` | 提取所有 `<img>` 并去重 |
| 图片 URL 缺少协议头 | 部分站点用 `//` 开头 | 自动补全 `https:` 前缀 |
| **图片与话题完全无关** | 关键词拆分后搜到泛词图（如"诈骗""银行"搜到随机大楼图）；人名混淆（如"韦东奕"搜到"刘强东"） | 必须执行 6.5 相关性验证，剔除无关图，必要时用 ImageGen 生成 |
