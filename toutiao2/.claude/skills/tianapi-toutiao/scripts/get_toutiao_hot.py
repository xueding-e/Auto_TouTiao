#!/usr/bin/env python3
"""
头条热搜榜独立查询工具
调用 TianAPI 获取头条热搜榜数据，支持独立运行和合并 newsnow 数据。

用法：
    python get_toutiao_hot.py                # 显示 Top 10 热搜
    python get_toutiao_hot.py --json         # 输出完整 JSON
    python get_toutiao_hot.py --merge        # 合并 newsnow toutiao.json 数据
    python get_toutiao_hot.py --merge --json # 合并后输出 JSON
"""

import json
import sys
import os

# 将同目录加入 path 以便导入 tianapi_client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tianapi_client import get_toutiao_hot, hotindex_map


def merge_with_newsnow(tianapi_data, newsnow_file='toutiao.json'):
    """合并 TianAPI 热度数据和 newsnow 数据"""
    if not os.path.exists(newsnow_file):
        print(f"警告：找不到 {newsnow_file}，仅返回 TianAPI 数据")
        return tianapi_data

    try:
        with open(newsnow_file, 'r', encoding='utf-16') as f:
            newsnow_data = json.load(f)
    except Exception:
        try:
            with open(newsnow_file, 'r', encoding='utf-8') as f:
                newsnow_data = json.load(f)
        except Exception:
            print(f"警告：无法读取 {newsnow_file}，仅返回 TianAPI 数据")
            return tianapi_data

    hmap = hotindex_map(tianapi_data)

    merged_items = []
    for item in newsnow_data.get('items', []):
        title = item.get('title', '')
        merged_items.append({
            'id': item.get('id'),
            'title': title,
            'url': item.get('url'),
            'hotindex': hmap.get(title, 0),
            'extra': item.get('extra', {})
        })

    merged_items.sort(key=lambda x: x.get('hotindex', 0), reverse=True)

    return {
        'source': 'toutiao',
        'count': len(merged_items),
        'items': merged_items
    }


def main():
    print("正在获取头条热搜榜...")
    data = get_toutiao_hot()

    if not data:
        print("获取失败，请检查网络连接。")
        sys.exit(1)

    # 显示 Top 10
    print(f"\n头条热搜榜 Top 10（按热度指数排序）：\n")
    for i, item in enumerate(data[:10], 1):
        print(f"{i:2d}. {item['word']}")
        print(f"    热度指数：{item['hotindex']:,}")

    # --merge：合并 newsnow 数据
    if '--merge' in sys.argv:
        print("\n正在合并 newsnow 数据...")
        merged = merge_with_newsnow(data)
        output_file = 'toutiao_with_hotindex.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"\n合并完成，已保存到：{output_file}")

    # --json：输出完整 JSON
    if '--json' in sys.argv:
        print("\n" + json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
