#!/usr/bin/env python3
"""
TianAPI 客户端模块
提供头条热搜榜 API 调用能力，可被其他脚本 import 使用。
"""

import os
import sys
import requests

# 导入统一配置加载器
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from config.config_loader import get_secret, get_timeout


def get_toutiao_hot(api_key=None):
    """
    获取头条热搜榜热度指数。

    Args:
        api_key: TianAPI Key，不传则从环境变量/配置文件读取。

    Returns:
        list: 热搜列表，每项包含 word（话题）和 hotindex（热度指数）。
              失败时返回空列表。
    """
    key = api_key or get_secret('tianapi_key', 'TIANAPI_KEY')
    url = get_secret('tianapi_toutiao_hot_url', 'TIANAPI_TOUTIAO_HOT_URL')
    try:
        resp = requests.get(
            f'{url}?key={key}',
            timeout=get_timeout('default'),
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
