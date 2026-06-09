#!/usr/bin/env python3
"""
图片搜索模块 - 为头条文章搜索并插入相关图片

搜图策略（按优先级）：
1. 新闻原图提取：从新闻页面的 og:image / 首图提取
2. 全话题名搜索：用完整话题名搜索 Baidu/Bing 图片（热点话题的新闻图已在索引中）
3. 关键词拆分搜索：兜底方案，用短词搜索通用配图

使用方法：
>>> from scripts.image_search import search_images, download_image, search_topic_images
>>> images = search_topic_images("准女婿涉嫌诈骗7亿丈母娘拒腾房被拘", count=3)
"""

import os
import re
import sys
import json
import struct
import urllib.parse
from io import BytesIO

try:
    import requests
except ImportError:
    print("[ERROR] requests 未安装。请执行: pip install requests")
    raise

# 导入统一配置加载器
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from config.config_loader import get_http, get_user_agent, get_timeout, get_min_image_size

# --- 从配置文件加载 ---
_http_cfg = get_http()
MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT = get_min_image_size()
_SKIP_KEYWORDS = _http_cfg.get('skip_keywords', [])
_STOP_WORDS = set(_http_cfg.get('stop_words', []))
_FETCH_MULTIPLIER = _http_cfg.get('fetch_multiplier', 4)


# ============ 图片分辨率检测 ============

def check_image_resolution(url, timeout=10):
    """
    通过下载图片头部数据检测图片实际分辨率。
    优先从 Content-Length 和尺寸信息判断，必要时下载前几 KB 解析头部。

    Returns:
        tuple: (width, height)，检测失败返回 (0, 0)
    """
    headers = {
        'User-Agent': get_user_agent(),
    }
    try:
        # 下载前 32KB 用于解析图片头部
        resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
        resp.raise_for_status()
        data = b''
        for chunk in resp.iter_content(chunk_size=8192):
            data += chunk
            if len(data) >= 32768:
                break
        resp.close()

        if len(data) < 24:
            return 0, 0

        # PNG: 前8字节签名，IHDR块包含宽高
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', data[16:24])
            return int(w), int(h)

        # JPEG: 从 SOF 标记读取
        if data[:2] == b'\xff\xd8':
            i = 2
            while i < len(data) - 9:
                if data[i] == 0xFF:
                    marker = data[i + 1]
                    # SOF0-SOF3 标记
                    if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                        h = struct.unpack('>H', data[i+5:i+7])[0]
                        w = struct.unpack('>H', data[i+7:i+9])[0]
                        return int(w), int(h)
                    # 跳过非 SOF 段
                    if marker not in (0xD8, 0xD9, 0x00, 0x01) and not (0xD0 <= marker <= 0xD7):
                        seg_len = struct.unpack('>H', data[i+2:i+4])[0]
                        i += 2 + seg_len
                        continue
                i += 1

        # GIF: 逻辑屏幕描述符
        if data[:6] in (b'GIF87a', b'GIF89a'):
            w, h = struct.unpack('<HH', data[6:10])
            return int(w), int(h)

        # WebP: RIFF 容器
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            if data[12:16] == b'VP8 ' and len(data) > 30:
                w = struct.unpack('<H', data[26:28])[0] & 0x3FFF
                h = struct.unpack('<H', data[28:30])[0] & 0x3FFF
                return int(w), int(h)
            if data[12:16] == b'VP8L' and len(data) > 25:
                bits = struct.unpack('<I', data[21:25])[0]
                w = (bits & 0x3FFF) + 1
                h = ((bits >> 14) & 0x3FFF) + 1
                return int(w), int(h)

        return 0, 0
    except Exception as e:
        print(f"[WARN] 图片分辨率检测失败 {url[:60]}...: {e}")
        return 0, 0


def is_high_resolution(url, width=0, height=0):
    """
    判断图片是否为高分辨率。
    优先使用 API 返回的宽高，如果为 0 则实际检测。

    Returns:
        bool: True 表示满足高分辨率要求
    """
    if width > 0 and height > 0:
        return width >= MIN_IMAGE_WIDTH and height >= MIN_IMAGE_HEIGHT

    # API 没返回尺寸信息，实际检测
    w, h = check_image_resolution(url)
    if w > 0 and h > 0:
        return w >= MIN_IMAGE_WIDTH and h >= MIN_IMAGE_HEIGHT

    # 检测失败时视为不合格
    return False


# ============ 新闻原图提取 ============

def extract_article_images(url, min_size=400):
    """
    从新闻页面提取所有高清大图（实战验证最有效的方法）。

    原理：请求新闻页面 HTML，提取所有 <img> 标签的 src 和 data-src，
    通过 URL 中的尺寸标记（如 w1080h720）过滤小图。

    比 og:image 更可靠——实测新浪财经等站点的 og:image 经常是 85x85 站点 Logo，
    而正文中的 <img> 标签才包含真正的高清新闻配图。

    Args:
        url: 新闻页面 URL
        min_size: URL 中标记的最小宽度/高度（像素）

    Returns:
        list[dict]: [{'url': ..., 'source': 'article_img'}, ...]
    """
    headers = {
        'User-Agent': get_user_agent(),
    }
    results = []
    try:
        resp = requests.get(url, headers=headers, timeout=get_timeout('article'))
        resp.encoding = 'utf-8'
        html = resp.text

        # 提取所有 img src 和 data-src（lazy loading）
        img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I)
        img_urls += re.findall(r'data-src=["\']([^"\']+)["\']', html, re.I)

        # 跳过明显的小图和图标（从配置读取）
        skip_keywords = _SKIP_KEYWORDS

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
            results.append({
                'url': img_url,
                'source': 'article_img',
                'from_url': url,
            })
    except Exception as e:
        print(f"[WARN] 新闻页面图片提取失败 {url[:60]}...: {e}")

    return results


def extract_og_image_from_html(html_text):
    """
    从 HTML 中提取 og:image 元标签中的图片 URL。
    这是新闻报道的标配——几乎每条新闻都设置了 og:image。

    Returns:
        str or None: og:image URL
    """
    if not html_text:
        return None

    # 匹配 <meta property="og:image" content="URL">
    match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html_text, re.IGNORECASE)
    if match:
        return match.group(1)

    # 匹配 <meta name="twitter:image" content="URL">
    match = re.search(r'<meta\s+name="twitter:image"\s+content="([^"]+)"', html_text, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def extract_images_from_html(html_text, max_images=3):
    """
    从 HTML 中提取候选图片 URL。
    按优先级：og:image → twitter:image → <img> 标签中的大图

    Returns:
        list[dict]: [{'url': ..., 'source': 'og:image'}, ...]
    """
    results = []

    # 1. og:image（最优先，就是新闻封面图）
    og = extract_og_image_from_html(html_text)
    if og and og.startswith('http'):
        results.append({'url': og, 'source': 'og:image'})

    # 2. <img> 标签中尺寸较大的图
    img_pattern = re.compile(
        r'<img[^>]+src="(https?://[^"]+)"[^>]*>',
        re.IGNORECASE
    )
    for match in img_pattern.finditer(html_text):
        url = match.group(1)
        # 跳过明显的小图、图标、logo（从配置读取）
        if any(x in url.lower() for x in _SKIP_KEYWORDS):
            continue
        if url.startswith('http'):
            results.append({'url': url, 'source': 'img_tag'})
            if len(results) >= max_images:
                break

    return results[:max_images]


# ============ 图片搜索引擎 ============

def search_baidu_images(keyword, count=3):
    """百度图片搜索，优先获取高分辨率原图"""
    results = []
    try:
        encoded_keyword = urllib.parse.quote(keyword)
        # 从配置读取搜索参数
        _baidu_cfg = _http_cfg.get('baidu_image', {})
        _baidu_url = _baidu_cfg.get('url', 'https://image.baidu.com/search/acjson')
        _baidu_params = _baidu_cfg.get('params', {})
        fetch_count = count * _FETCH_MULTIPLIER
        url = (
            f"{_baidu_url}?"
            f"tn={_baidu_params.get('tn', 'resultjson_com')}&ipn={_baidu_params.get('ipn', 'rj')}"
            f"&ct={_baidu_params.get('ct', 201326592)}&is=&fp=result"
            f"&queryWord={encoded_keyword}&cl=2&lm=-1&ie=utf-8&oe=utf-8"
            f"&adpicid=&st=-1&z=&ic=0&hd={_baidu_params.get('hd', 1)}&latest={_baidu_params.get('latest', 1)}&copyright=0"
            f"&word={encoded_keyword}&s=&se=&tab=&width={_baidu_params.get('width', 1024)}&height={_baidu_params.get('height', 768)}"
            f"&face=0&istype=2&qc=&nc=1&fr=&expermode=&nojc=1"
            f"&pn=0&rn={fetch_count}"
        )
        headers = {
            'User-Agent': get_user_agent(),
            'Referer': _baidu_cfg.get('referer', 'https://image.baidu.com/'),
        }
        resp = requests.get(url, headers=headers, timeout=get_timeout('default'))
        resp.encoding = 'utf-8'
        content = resp.text
        if content.startswith('baidu'):
            content = content[5:]
        data = json.loads(content)
        for item in data.get('data', []):
            if len(results) >= count:
                break
            # 优先使用 objURL（原始高清大图），其次 hoverURL，最后 middleURL
            img_url = item.get('objURL') or item.get('hoverURL') or item.get('middleURL')
            if not img_url or not img_url.startswith('http'):
                continue
            w = int(item.get('width', 0) or 0)
            h = int(item.get('height', 0) or 0)
            # 分辨率过滤：优先使用 API 返回的宽高
            if w > 0 and h > 0:
                if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
                    continue
            results.append({
                'url': img_url,
                'width': w,
                'height': h,
                'title': item.get('fromPageTitle', '').replace('<strong>', '').replace('</strong>', ''),
                'source': 'baidu_image',
            })
    except Exception as e:
        print(f"[WARN] 百度图片搜索失败: {e}")
    return results


def search_bing_images(keyword, count=3):
    """必应图片搜索，过滤小图只保留大图"""
    results = []
    try:
        encoded_keyword = urllib.parse.quote(keyword)
        # 从配置读取搜索参数
        _bing_cfg = _http_cfg.get('bing_image', {})
        _bing_url = _bing_cfg.get('url', 'https://www.bing.com/images/async')
        fetch_count = count * 3
        url = (
            f"{_bing_url}?q={encoded_keyword}"
            f"+filterui%3aimagesize-large"
            f"&first=0&count={fetch_count}&cw=1920&ch=1080&relp=35"
            f"&tsc=ImageBasicHover&datsrc=I&layout=RowBased_Landscape&mmasync=1"
        )
        headers = {
            'User-Agent': get_user_agent(),
            'Referer': _bing_cfg.get('referer', 'https://www.bing.com/images/'),
        }
        resp = requests.get(url, headers=headers, timeout=get_timeout('default'))
        data = resp.json()
        for item in data.get('items', []):
            if len(results) >= count:
                break
            img_url = item.get('mediaUrl')
            if not img_url or not img_url.startswith('http'):
                continue
            w = int(item.get('width', 0) or 0)
            h = int(item.get('height', 0) or 0)
            if w > 0 and h > 0:
                if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
                    continue
            results.append({
                'url': img_url,
                'width': w,
                'height': h,
                'title': item.get('title', ''),
                'source': 'bing_image',
            })
    except Exception as e:
        print(f"[WARN] 必应图片搜索失败: {e}")
    return results


# ============ 图片相关性检查 ============

def extract_topic_keywords(topic):
    """
    从话题中提取核心关键词（人名、事件、地点、机构名等）。
    去除通用连接词，保留有辨识度的专有名词。
    """
    # 从配置文件加载停用词
    stop_words = _STOP_WORDS
    keywords = []
    for word in re.findall(r'[\u4e00-\u9fff]{2,}', topic):
        if word not in stop_words and len(word) >= 2:
            keywords.append(word)
    return keywords


def check_image_relevance(image_info, topic_keywords):
    """
    检查单张图片是否与话题相关。

    Args:
        image_info: dict，包含 'url', 'title', 可能还有 'from_url'
        topic_keywords: list[str]，话题关键词

    Returns:
        dict: {
            'pass': bool,
            'score': int (0-3),
            'matched': list[str] (匹配到的关键词),
            'reason': str (不通过时的原因)
        }
    """
    score = 0
    matched = []

    # 收集所有可用的文本信息
    texts = []
    title = image_info.get('title', '')
    from_url = image_info.get('from_url', '')
    url = image_info.get('url', '')

    if title:
        texts.append(title.lower())
    if from_url:
        texts.append(from_url.lower())

    combined = ' '.join(texts)

    # 检查每个关键词是否在元数据中出现
    for kw in topic_keywords:
        kw_lower = kw.lower()
        if kw_lower in combined:
            score += 1
            matched.append(kw)

    # 额外检查：如果至少1个核心关键词匹配，视为通过
    # 2个以上匹配为强相关
    if score >= 1:
        return {
            'pass': True,
            'score': score,
            'matched': matched,
            'reason': ''
        }
    else:
        return {
            'pass': False,
            'score': 0,
            'matched': [],
            'reason': f'元数据中未匹配到话题关键词 {topic_keywords[:5]}'
        }


def filter_relevant_images(images, topic, min_score=1):
    """
    从候选图片中过滤出与话题相关的图片。

    Args:
        images: list[dict]，候选图片列表
        topic: str，话题文本
        min_score: int，最低相关分数（默认1即至少1个关键词匹配）

    Returns:
        tuple: (relevant_images, rejected_images)
    """
    keywords = extract_topic_keywords(topic)
    if not keywords:
        print(f"  [相关性] 未能从话题中提取关键词，保留全部图片")
        return images, []

    print(f"  [相关性] 话题关键词: {keywords[:8]}")

    relevant = []
    rejected = []
    for img in images:
        result = check_image_relevance(img, keywords)
        if result['pass'] and result['score'] >= min_score:
            img['relevance_score'] = result['score']
            img['relevance_matched'] = result['matched']
            relevant.append(img)
        else:
            rejected.append({
                'url': img.get('url', '')[:80],
                'title': img.get('title', '')[:40],
                'reason': result['reason']
            })

    if rejected:
        print(f"  [相关性] 剔除 {len(rejected)} 张不相关图片:")
        for r in rejected[:3]:
            print(f"    - {r['url']} ... [{r['reason']}]")

    # 按相关分数降序排列
    relevant.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    return relevant, rejected

def search_images(keyword, count=3):
    """综合搜索图片，百度优先，必应兜底"""
    print(f"  搜索图片: {keyword}")
    results = search_baidu_images(keyword, count)
    if len(results) < count:
        results += search_bing_images(keyword, count - len(results))
    return results[:count]


def split_topic_keywords(topic, max_len=15):
    """将长话题拆分为短关键词（兜底用）"""
    # 按空格和标点拆分
    parts = re.split(r'[，。！？；、\s]+', topic)
    keywords = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_len:
            keywords.append(part)
        else:
            # 长片段再拆分
            for i in range(0, len(part), max_len):
                chunk = part[i:i+max_len].strip()
                if chunk and len(chunk) >= 2:
                    keywords.append(chunk)
    return keywords


def search_topic_images(topic, count=3, check_relevance=True):
    """
    为话题搜索最贴切的配图。

    策略（按优先级）：
    1. 用完整话题名搜索（热点话题的新闻图已在图片索引中）
    2. 用话题前 20 字搜索（截短但保持语义）
    3. 兜底：拆分成短关键词搜索

    搜索后默认执行相关性过滤，剔除与话题无关的图片。

    Args:
        topic: 话题文本
        count: 需要的图片数量
        check_relevance: 是否执行相关性过滤（默认 True）

    Returns:
        list[dict]: 图片信息列表（已过滤无关图）
    """
    all_results = []

    # 策略 1：完整话题名
    print(f"  [策略1] 完整话题名搜索")
    results = search_images(topic, count * 2)  # 多搜一些，为相关性过滤留余量
    all_results.extend(results)

    # 策略 2：如果结果不够，用话题前 N 字
    if len(all_results) < count * 2 and len(topic) > 20:
        short_topic = topic[:20]
        if short_topic != topic:
            print(f"  [策略2] 截短话题搜索: {short_topic}")
            results = search_images(short_topic, count * 2 - len(all_results))
            for r in results:
                if not any(a['url'] == r['url'] for a in all_results):
                    all_results.append(r)

    # 策略 3：拆分关键词兜底（仅在结果极少时使用）
    if len(all_results) < count:
        keywords = split_topic_keywords(topic)
        for kw in keywords[:5]:
            if len(all_results) >= count:
                break
            print(f"  [策略3] 关键词兜底: {kw}")
            results = search_images(kw, 1)
            for r in results:
                if not any(a['url'] == r['url'] for a in all_results):
                    all_results.append(r)
                    break

    # 相关性过滤
    if check_relevance and all_results:
        relevant, _ = filter_relevant_images(all_results, topic, min_score=1)
        if relevant:
            all_results = relevant
            print(f"  [相关性] 通过过滤 {len(relevant)} 张相关图片")
        else:
            print(f"  [相关性] 无图片通过相关性过滤！请考虑使用 ImageGen 生成相关配图")
            all_results = []

    return all_results[:count]


# ============ Markdown 操作 ============

def insert_images_into_md(md_text, topic, max_images=3):
    """
    在 Markdown 文章中插入图片。
    优先使用完整话题名搜索，确保匹配新闻原图。
    """
    print(f"\n=== 为话题配图: {topic} ===")
    images = search_topic_images(topic, max_images)

    if not images:
        print("[WARN] 未能找到相关图片")
        return md_text, []

    print(f"最终获得 {len(images)} 张图片")

    lines = md_text.split('\n')
    result_lines = []
    image_idx = 0

    for i, line in enumerate(lines):
        result_lines.append(line)

        # 封面图：标题后
        if image_idx == 0 and line.startswith('# ') and i + 1 < len(lines):
            result_lines.append('')
            result_lines.append(f'![{topic}]({images[image_idx]["url"]})')
            result_lines.append('')
            image_idx += 1

        # 正文配图：每隔几段插入
        elif image_idx < len(images):
            if line.strip() and i > 0 and i % 4 == 0:
                if i + 1 < len(lines) and lines[i + 1].strip() == '':
                    desc = images[image_idx].get('title', '配图')[:20] or '配图'
                    result_lines.append(f'![{desc}]({images[image_idx]["url"]})')
                    image_idx += 1

    # 剩余图片追加到末尾
    while image_idx < len(images):
        result_lines.append('')
        desc = images[image_idx].get('title', '相关图片')[:20] or '相关图片'
        result_lines.append(f'![{desc}]({images[image_idx]["url"]})')
        image_idx += 1

    new_md = '\n'.join(result_lines)
    return new_md, images


def download_image(url):
    """验证图片 URL 是否可访问，返回 bytes"""
    try:
        headers = {
            'User-Agent': get_user_agent(),
        }
        resp = requests.get(url, headers=headers, timeout=get_timeout('default'))
        resp.raise_for_status()
        return BytesIO(resp.content)
    except Exception as e:
        print(f"[WARN] 图片无法下载 {url[:60]}...: {e}")
        return None


# ============ 测试入口 ============

if __name__ == '__main__':
    topic = "准女婿涉嫌诈骗7亿丈母娘拒腾房被拘"
    print(f"测试话题: {topic}")
    images = search_topic_images(topic, count=3)
    print(f"\n=== 搜索到的图片 ===")
    for i, img in enumerate(images):
        w = img.get('width', 0)
        h = img.get('height', 0)
        res = f"{w}x{h}" if w and h else "未知"
        print(f"{i+1}. {img.get('source', 'unknown'):>12} | {res:>10} | {img['url'][:80]}")
