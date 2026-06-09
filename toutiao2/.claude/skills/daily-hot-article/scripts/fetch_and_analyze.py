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

# 导入统一配置加载器
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from config.config_loader import (
    get_scoring, get_platforms, get_scoring_keywords, get_reject_patterns,
    get_max_score, get_per_keyword_point, get_platform_weights as _get_pw,
    get_platform_names as _get_pn,
)

# 导入 tianapi-toutiao skill 的客户端模块
_tianapi_path = os.path.join(os.path.dirname(__file__), '..', '..', 'tianapi-toutiao', 'scripts')
sys.path.insert(0, os.path.abspath(_tianapi_path))
from tianapi_client import get_toutiao_hot as get_tianapi_hot

# --- 从配置文件加载 ---

PLATFORMS = _get_pn()
PLATFORM_WEIGHTS = _get_pw()

# 评分配置
_scoring_cfg = get_scoring()
SIMILARITY_THRESHOLD = _scoring_cfg.get('similarity_threshold', 0.6)
TOPIC_CATEGORIES = _scoring_cfg.get('topic_categories', {})

# 关键词列表
CONFLICT_KW = get_scoring_keywords('conflict')
EMOTION_KW = get_scoring_keywords('emotion')
RELEVANCE_KW = get_scoring_keywords('relevance')
INFO_GAP_KW = get_scoring_keywords('info_gap')
REJECT_KW = get_reject_patterns()

import platform

# newsnow CLI 路径，npm 全局安装后通过 node 直接调用
def _find_newsnow_cli():
    """跨平台查找 newsnow CLI 路径（支持 nvm/fnm/brew/npm global）"""
    import shutil
    import glob as _glob

    home = os.path.expanduser('~')

    # 方法 1: shutil.which（最可靠，自动搜索 PATH）
    which_path = shutil.which('newsnow')
    if which_path:
        real = os.path.realpath(which_path)
        # 如果 realpath 直接指向 cli.js，直接返回
        if real.endswith('cli.js') and os.path.exists(real):
            return real
        # 否则从 real 向上查找 cli.js
        search_dir = os.path.dirname(real)
        for _ in range(6):
            cli_js = os.path.join(search_dir, 'dist', 'src', 'cli.js')
            if os.path.exists(cli_js):
                return cli_js
            cli_js2 = os.path.join(search_dir, 'lib', 'node_modules', 'newsnow', 'dist', 'src', 'cli.js')
            if os.path.exists(cli_js2):
                return cli_js2
            search_dir = os.path.dirname(search_dir)
            if search_dir == os.path.dirname(search_dir):
                break

    # 方法 2: 从配置文件读取搜索路径
    platforms_cfg = get_platforms()
    search_patterns = platforms_cfg.get('newsnow_search_patterns', [])
    for pattern in search_patterns:
        expanded = os.path.expanduser(pattern)
        matches = _glob.glob(expanded)
        if matches:
            return matches[0]

    return None

NEWSNOW_CLI_PATH = _find_newsnow_cli()


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
    维度（满分 100）：
      - conflict_score:   争议冲突度 (0-30)
      - emotion_score:    情绪推动力 (0-25)
      - relevance_score:  利益相关性 (0-20)
      - info_gap_score:   信息差 (0-15)
      - extend_score:     写作延展性 (0-10)
      - reject_flag:      是否应直接淘汰
    """
    conflict = 0
    emotion = 0
    relevance = 0
    info_gap = 0
    reject = False

    # 淘汰检测
    for pattern in REJECT_KW:
        if re.search(pattern, title):
            reject = True
            break

    if reject:
        return -1, {'conflict': 0, 'emotion': 0, 'relevance': 0, 'info_gap': 0, 'extend': 0, 'reject': True}

    # 从配置读取每关键词分值和满分
    conflict_pt = get_per_keyword_point('conflict')
    emotion_pt = get_per_keyword_point('emotion')
    relevance_pt = get_per_keyword_point('relevance')
    info_gap_pt = get_per_keyword_point('info_gap')
    conflict_max = get_max_score('conflict')
    emotion_max = get_max_score('emotion')
    relevance_max = get_max_score('relevance')
    info_gap_max = get_max_score('info_gap')
    extend_max = get_max_score('extend')

    # 争议冲突度
    for kw in CONFLICT_KW:
        if kw in title:
            conflict += conflict_pt
            if conflict >= conflict_max:
                conflict = conflict_max
                break

    # 情绪推动力
    for kw in EMOTION_KW:
        if kw in title:
            emotion += emotion_pt
            if emotion >= emotion_max:
                emotion = emotion_max
                break

    # 利益相关性
    for kw in RELEVANCE_KW:
        if kw in title:
            relevance += relevance_pt
            if relevance >= relevance_max:
                relevance = relevance_max
                break

    # 信息差：揭露大多数人不知道的事
    for kw in INFO_GAP_KW:
        if kw in title:
            info_gap += info_gap_pt
            if info_gap >= info_gap_max:
                info_gap = info_gap_max
                break

    # 写作延展性：标题存在两个以上对立信号，说明素材丰富
    extend = extend_max if (conflict >= conflict_pt and emotion >= emotion_pt) else extend_max // 2 if (conflict >= conflict_pt or emotion >= emotion_pt) else 0

    # 额外加分：标题中出现具体数字（数据感增强说服力）
    if re.search(r'\d+亿|\d+万|\d+人|\d+岁|\d+年|\d+天', title):
        extend = min(10, extend + 3)

    total = conflict + emotion + relevance + info_gap + extend
    return total, {
        'conflict': conflict,
        'emotion': emotion,
        'relevance': relevance,
        'info_gap': info_gap,
        'extend': extend,
        'reject': False,
    }


def classify_topic(title):
    """简单话题分类（从 config/scoring.yaml 读取分类关键词）"""
    for cat, kws in TOPIC_CATEGORIES.items():
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
            if sim >= SIMILARITY_THRESHOLD:
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
            if title_similarity(normalize_title(best_title), normalize_title(t_item.get('word', ''))) >= SIMILARITY_THRESHOLD:
                hotindex = t_item.get('hotindex', 0)
                break

        # 伪热度估算
        estimated_hot = 0
        if hotindex == 0:
            _est = _scoring_cfg.get('hot_estimation', {})
            source_base = _est.get('source_base', 500000)
            rank_base = _est.get('rank_base', 10000)
            estimated_hot = int((len(sources) * source_base) + (100 - best_rank) * rank_base)

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
        detail = t['click_detail']
        detail_str = f"争议:{detail.get('conflict',0)} 情绪:{detail.get('emotion',0)} 利益:{detail.get('relevance',0)} 信息差:{detail.get('info_gap',0)} 延展:{detail.get('extend',0)}"
        print(f"    分类: {t['category']} | 平台: {', '.join(t['sources'])} | 点击力: {t['click_score']} | {detail_str} | 热度: {t['hotindex']:,}")

    # 保存 Top 5 结果（含详细评分）
    _platforms_cfg = get_platforms()
    _output_fn = _platforms_cfg.get('output_filenames', {})
    top5_fn = _output_fn.get('top5', 'top5_result.json')
    all_fn = _output_fn.get('all_topics', 'all_topics.json')

    top5 = topics[:5]
    with open(top5_fn, 'w', encoding='utf-8') as f:
        json.dump(top5, f, ensure_ascii=False, indent=2)
    print(f'\n=== Top 5 已保存到 {top5_fn} ===')

    # 保存全量结果（含评分详情）
    with open(all_fn, 'w', encoding='utf-8') as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)
    print(f'=== 全量分析结果已保存到 {all_fn} ===')


if __name__ == '__main__':
    main()
