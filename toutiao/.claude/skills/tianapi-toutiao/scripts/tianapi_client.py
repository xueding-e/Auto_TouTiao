#!/usr/bin/env python3
"""
TianAPI 客户端模块
提供头条热搜榜 API 调用能力，可被其他脚本 import 使用。
"""

import requests

TIANAPI_KEY = 'b723b22584391c9488e31694b9cc711f'
TIANAPI_TOUTIAO_HOT_URL = 'https://apis.tianapi.com/toutiaohot/index'


def get_toutiao_hot(api_key=None):
    """
    获取头条热搜榜热度指数。

    Args:
        api_key: TianAPI Key，不传则使用内置 Key。

    Returns:
        list: 热搜列表，每项包含 word（话题）和 hotindex（热度指数）。
              失败时返回空列表。
    """
    key = api_key or TIANAPI_KEY
    try:
        resp = requests.get(
            f'{TIANAPI_TOUTIAO_HOT_URL}?key={key}',
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') != 200:
            print(f'[WARN] TianAPI error: {data.get("msg")}')
            return []
        return data['result']['list']
    except Exception as e:
        print(f'[WARN] TianAPI request failed: {e}')
        return []


def hotindex_map(tianapi_data):
    """
    从天搜数据构建 标题 -> 热度指数 的映射。

    Args:
        tianapi_data: get_toutiao_hot() 返回的列表。

    Returns:
        dict: {word: hotindex}
    """
    return {item['word']: item['hotindex'] for item in tianapi_data if 'word' in item}
