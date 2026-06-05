#!/usr/bin/env python3
"""
抓取各平台热点并进行交叉分析
按"点击吸引力"维度综合排名，优先选出适合写头条文章的话题。
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from difflib import SequenceMatcher

# 导入 tianapi-toutiao skill 的客户端模块
_tianapi_path = os.path.join(os.path.dirname(__file__), '..', '..', 'tianapi-toutiao', 'scripts')
sys.path.insert(0, os.path.abspath(_tianapi_path))
from tianapi_client import get_toutiao_hot as get_tianapi_hot

PLATFORMS = {
    'weibo': '微博热搜',
    'baidu': '百度热搜',
    'zhihu': '知乎热榜',
    'douyin': '抖音热点',
    'tieba': '贴吧热议',
    'toutiao': '头条热榜',
}

# 各平台对文章写作的参考价值权重
PLATFORM_WEIGHTS = {
    'zhihu': 1.2,     # 知乎讨论型内容多，利于观点文章
    'weibo': 1.1,     # 微博情绪浓度高，利于犀利文风
    'baidu': 1.0,     # 百度代表大众关注度
    'toutiao': 1.0,
    'douyin': 0.8,    # 抖音偏短视频娱乐，文章延展性弱
    'tieba': 0.8,
}

# === 点击吸引力关键词评分 ===

# 争议冲突类 — 有对立面、能站队、有讨论欲望
CONFLICT_KW = [
    '举报', '曝光', '回应', '怒斥', '炮轰', '打脸', '反转', '质疑',
    '争议', '冲突', '对峙', '怒怼', '起诉', '实名', '控诉', '发飙',
    '翻车', '打假', '造假', '伪造', '潜规则', '黑幕', '录音流出',
    '视频流出', '聊天记录', '实锤', '官方通报', '引争议', '惹众怒',
]

# 情绪推动类 — 看完会生气/震惊/心疼/拍桌子
EMOTION_KW = [
    '崩溃', '痛哭', '怒吼', '震惊', '扎心', '离谱', '可怕', '心碎',
    '咆哮', '气炸', '心疼', '悲哀', '绝望', '疯了', '受不了', '看哭',
    '毁三观', '令人发指', '触目惊心', '细思极恐', '不忍直视',
]

# 利益相关类 — 跟普通人的钱/健康/安全/子女直接相关
RELEVANCE_KW = [
    '钱', '工资', '房价', '医保', '教育', '养老', '食品安全',
    '孩子', '学校', '医院', '裁员', '公积金', '补贴', '赔偿',
    '退费', '骗', '欠薪', '放假', '扣款', '致癌', '污染',
    '涨价', '限购', '摇号', '落户',
]

# 淘汰类 — 纯快讯、无观点可写
REJECT_KW = [
    r'^(今日|明日|本周|下周).*天气',
    r'^\d+月\d+日.*',
    r'^[A-Z]{2,}.*比分',
    r'^(发布|召开|举行|开幕|闭幕|出席|会见|致辞|签约|批复)',
    r'^(最新|刚刚).*(发布|通知|公告)',
]

import platform

# newsnow CLI 路径，npm 全局安装后通过 node 直接调用
_NPM_GLOBAL = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'npm', 'node_modules', 'newsnow', 'dist', 'src', 'cli.js')
if not os.path.exists(_NPM_GLOBAL):
    # nvm 路径
    import glob as _glob
    _candidates = _glob.glob(r'C:\nvm*\nodejs\node_modules\newsnow\dist\src\cli.js')
    _NPM_GLOBAL = _candidates[0] if _candidates else None

NEWSNOW_CLI_PATH = _NPM_GLOBAL


def run_newsnow(source):
    """运行 newsnow CLI 获取数据，返回 dict"""
    if not NEWSNOW_CLI_PATH:
        print(f'[WARN] newsnow CLI not found, skipping {source}')
        return None
    try:
        result = subprocess.run(
            ['node', NEWSNOW_CLI_PATH, source, '--json', '--pretty'],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f'[WARN] {source} newsnow stderr: {result.stderr.decode("utf-8", errors="ignore")[:200]}')
            return None
        data = json.loads(result.stdout.decode('utf-8', errors='ignore'))
        return data
    except Exception as e:
        print(f'[WARN] {source} fetch failed: {e}')
        return None



def normalize_title(title):
    """标准化标题用于匹配"""
    t = title.strip()
    # 移除书名号、引号等
    t = re.sub(r'[《》「」""''『』]', '', t)
    # 移除常见后缀
    t = re.sub(r'(视频|图片|直播|组图)$', '', t)
    t = t.strip()
    return t


def title_similarity(a, b):
    """计算标题相似度"""
    return SequenceMatcher(None, a, b).ratio()


def score_clickability(title):
    """
    评估话题的"点击吸引力"——读者是否会点进去看。

    返回 (总分, 各维度分) 元组。
    维度：
      - conflict_score:   争议冲突度 (0-30)
      - emotion_score:    情绪推动力 (0-25)
      - relevance_score:  利益相关性 (0-20)
      - extend_score:     写作延展性 (0-10)
      - reject_flag:      是否应直接淘汰
    """
    conflict = 0
    emotion = 0
    relevance = 0
    reject = False

    # 淘汰检测
    for pattern in REJECT_KW:
        if re.search(pattern, title):
            reject = True
            break

    if reject:
        return -1, {'conflict': 0, 'emotion': 0, 'relevance': 0, 'extend': 0, 'reject': True}

    # 争议冲突度
    for kw in CONFLICT_KW:
        if kw in title:
            conflict += 10
            if conflict >= 30:
                conflict = 30
                break

    # 情绪推动力
    for kw in EMOTION_KW:
        if kw in title:
            emotion += 8
            if emotion >= 25:
                emotion = 25
                break

    # 利益相关性
    for kw in RELEVANCE_KW:
        if kw in title:
            relevance += 7
            if relevance >= 20:
                relevance = 20
                break

    # 写作延展性：标题存在两个以上对立信号，说明素材丰富
    extend = 10 if (conflict >= 10 and emotion >= 8) else 5 if (conflict >= 10 or emotion >= 8) else 0

    # 额外加分：标题中出现具体数字（数据感增强说服力）
    if re.search(r'\d+亿|\d+万|\d+人|\d+岁|\d+年|\d+天', title):
        extend = min(10, extend + 3)

    total = conflict + emotion + relevance + extend
    return total, {
        'conflict': conflict,
        'emotion': emotion,
        'relevance': relevance,
        'extend': extend,
        'reject': False,
    }


def classify_topic(title):
    """简单话题分类"""
    categories = {
        '社会': ['社会', '医院', '学校', '家长', '孩子', '老人', '执法人员', '司机', '乘客',
                 '派出所', '法院', '公安局', '检方', '刑拘', '行拘'],
        '时政': ['习近平', '李克强', '总理', '主席', '外交部', '商务部', '国务院', '政策',
                 '两会', '人大', '政协'],
        '娱乐': ['明星', '艺人', '导演', '电影', '电视剧', '综艺', '演唱会', '绯闻', '恋情'],
        '体育': ['NBA', 'CBA', '中超', '国足', '欧冠', '英超', '比分', '金牌', '冠军', '赛季'],
        '科技': ['AI', '人工智能', '芯片', '华为', '苹果', '特斯拉', '大模型', '机器人',
                 '自动驾驶', 'NASA', 'SpaceX'],
        '财经': ['股市', 'A股', '涨停', '跌停', '基金', '房价', '比特币', '美元', '央行'],
    }
    for cat, kws in categories.items():
        for kw in kws:
            if kw in title:
                return cat
    return '其他'


def merge_topics(platform_data, tianapi_data):
    """合并各平台数据，提取跨平台热点，加入点击吸引力评分"""
    all_titles = []
    platform_titles = defaultdict(list)

    for source, label in PLATFORMS.items():
        data = platform_data.get(source)
        if not data:
            continue
        items = data.get('items', []) if isinstance(data, dict) else []
        for idx, item in enumerate(items):
            title = item.get('title', '') if isinstance(item, dict) else str(item)
            if not title:
                continue
            norm = normalize_title(title)
            all_titles.append({
                'title': title,
                'norm': norm,
                'source': source,
                'rank': idx + 1,
            })
            platform_titles[source].append(title)

    # 按相似度聚类
    clusters = []
    used = set()

    for i, item in enumerate(all_titles):
        if i in used:
            continue
        cluster = [item]
        used.add(i)
        for j, other in enumerate(all_titles):
            if j in used:
                continue
            sim = title_similarity(item['norm'], other['norm'])
            if sim >= 0.6:
                cluster.append(other)
                used.add(j)
        clusters.append(cluster)

    # 计算每个聚类的综合得分
    topics = []
    for cluster in clusters:
        sources = set(x['source'] for x in cluster)
        best_rank = min(x['rank'] for x in cluster)
        best_title = max(cluster, key=lambda x: len(x['title']))['title']

        # TianAPI 热度指数
        hotindex = 0
        for t_item in tianapi_data:
            if title_similarity(normalize_title(best_title), normalize_title(t_item.get('word', ''))) >= 0.6:
                hotindex = t_item.get('hotindex', 0)
                break

        # 伪热度估算
        estimated_hot = 0
        if hotindex == 0:
            estimated_hot = int((len(sources) * 500000) + (100 - best_rank) * 10000)

        # 点击吸引力评分
        click_score, click_detail = score_clickability(best_title)

        # 平台权重加成
        platform_weight = sum(PLATFORM_WEIGHTS.get(s, 1.0) for s in sources) / len(sources)

        # 话题分类
        category = classify_topic(best_title)

        topics.append({
            'title': best_title,
            'sources': sorted(sources),
            'source_count': len(sources),
            'best_rank': best_rank,
            'hotindex': hotindex,
            'estimated_hot': estimated_hot,
            'total_score': hotindex + estimated_hot,
            'platform_ranks': {x['source']: x['rank'] for x in cluster},
            'click_score': click_score,
            'click_detail': click_detail,
            'platform_weight': round(platform_weight, 2),
            'category': category,
            'reject': click_detail.get('reject', False),
        })

    # 综合排序：淘汰的话题排最后，其余按点击吸引力 × 跨平台基数
    def sort_key(t):
        if t['reject']:
            return (-100, 0, 0)
        diversity = min(t['source_count'], 4)
        return (t['click_score'] * diversity, t['source_count'], t['total_score'])

    topics.sort(key=sort_key, reverse=True)
    return topics


def main():
    # Fix stdout encoding on Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print('=== 开始抓取各平台热点 ===')
    platform_data = {}
    for source in PLATFORMS:
        print(f'Fetching {source}...')
        data = run_newsnow(source)
        if data:
            platform_data[source] = data
            # 保存为 UTF-8 JSON
            with open(f'{source}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'  -> Saved {source}.json ({len(data.get("items", []))} items)')
        else:
            print(f'  -> Failed')

    print('\n=== 获取 TianAPI 热度指数 ===')
    tianapi_data = get_tianapi_hot()
    print(f'Got {len(tianapi_data)} items from TianAPI')

    # 保存 TianAPI 数据
    with open('toutiao_hot.json', 'w', encoding='utf-8') as f:
        json.dump(tianapi_data, f, ensure_ascii=False, indent=2)

    print('\n=== 交叉分析热点（按点击吸引力排序）===')
    topics = merge_topics(platform_data, tianapi_data)

    # 输出 Top 20 用于调试
    for i, t in enumerate(topics[:20], 1):
        flags = []
        if t['reject']:
            flags.append('淘汰')
        if t['click_score'] >= 40:
            flags.append('高点击')
        flag_str = f' [{"|".join(flags)}]' if flags else ''
        print(f"{i:2d}. {t['title']}{flag_str}")
        print(f"    分类: {t['category']} | 平台: {', '.join(t['sources'])} | 点击力: {t['click_score']} | 热度: {t['hotindex']:,}")

    # 保存 Top 5 结果（含详细评分）
    top5 = topics[:5]
    with open('top5_result.json', 'w', encoding='utf-8') as f:
        json.dump(top5, f, ensure_ascii=False, indent=2)
    print('\n=== Top 5 已保存到 top5_result.json ===')

    # 保存全量结果（含评分详情）
    with open('all_topics.json', 'w', encoding='utf-8') as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)
    print('=== 全量分析结果已保存到 all_topics.json ===')


if __name__ == '__main__':
    main()
