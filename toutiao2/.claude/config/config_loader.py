#!/usr/bin/env python3
"""
统一配置加载器

用法:
    from config.config_loader import load_config, get_secret, get_scoring, get_platforms, get_http

所有配置文件位于 今日头条/config/ 目录:
    - secrets.yaml   — API 密钥（优先读环境变量）
    - scoring.yaml   — 评分参数、关键词列表
    - platforms.yaml — 平台名称、权重、搜索路径
    - http.yaml      — HTTP 请求配置、图片搜索参数
"""

import os
import yaml

# --- 路径定位 ---

def _find_config_dir():
    """自动定位 config/ 目录（支持从任意深度的脚本调用）"""
    # config_loader.py 自身在 config/ 下
    own_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(own_dir) == 'config':
        return own_dir

    # 否则从项目根目录找
    project_root = os.path.join(own_dir, '..')
    candidate = os.path.join(project_root, 'config')
    if os.path.isdir(candidate):
        return os.path.abspath(candidate)

    # 兜底：从调用者文件位置向上查找
    import inspect
    frame = inspect.stack()[2]
    caller_dir = os.path.dirname(os.path.abspath(frame.filename))
    for _ in range(6):
        candidate = os.path.join(caller_dir, 'config')
        if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, 'scoring.yaml')):
            return candidate
        caller_dir = os.path.dirname(caller_dir)

    raise FileNotFoundError("无法定位 config/ 目录，请确认项目结构")


# --- 缓存 ---

_config_cache = {}
_config_dir = None


def _load_yaml(filename):
    """加载并缓存 YAML 文件"""
    global _config_dir
    if _config_dir is None:
        _config_dir = _find_config_dir()

    if filename not in _config_cache:
        filepath = os.path.join(_config_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            _config_cache[filename] = yaml.safe_load(f) or {}
    return _config_cache[filename]


# --- 公开接口 ---

def load_config(filename):
    """加载指定 YAML 配置文件，返回 dict"""
    return _load_yaml(filename)


def get_secret(key, env_var=None):
    """
    获取密钥值。
    优先从环境变量读取，fallback 到 secrets.yaml。

    Args:
        key: secrets.yaml 中的键名
        env_var: 环境变量名（可选，默认自动推导大写形式）

    Returns:
        str: 密钥值
    """
    if env_var is None:
        env_var = key.upper()
    val = os.environ.get(env_var)
    if val:
        return val
    cfg = _load_yaml('secrets.yaml')
    return cfg.get(key, '')


def get_scoring():
    """获取评分配置（关键词列表、参数、淘汰规则）"""
    return _load_yaml('scoring.yaml')


def get_platforms():
    """获取平台配置（名称映射、权重、搜索路径）"""
    return _load_yaml('platforms.yaml')


def get_http():
    """获取 HTTP 配置（User-Agent、超时、图片搜索参数）"""
    return _load_yaml('http.yaml')


# --- 便捷函数 ---

def get_scoring_keywords(dimension):
    """
    获取指定维度的关键词列表。

    Args:
        dimension: 'conflict', 'emotion', 'relevance', 'info_gap'

    Returns:
        list[str]: 关键词列表
    """
    cfg = get_scoring()
    key = f'{dimension}_keywords'
    return cfg.get(key, [])


def get_reject_patterns():
    """获取淘汰类正则模式列表"""
    cfg = get_scoring()
    return cfg.get('reject_patterns', [])


def get_max_score(dimension):
    """获取指定维度的满分值"""
    cfg = get_scoring()
    return cfg.get('max_scores', {}).get(dimension, 0)


def get_per_keyword_point(dimension):
    """获取指定维度每命中一个关键词的分值"""
    cfg = get_scoring()
    return cfg.get('per_keyword_points', {}).get(dimension, 0)


def get_platform_weights():
    """获取平台权重字典"""
    cfg = get_platforms()
    return cfg.get('platform_weights', {})


def get_platform_names():
    """获取平台名称映射字典"""
    cfg = get_platforms()
    return cfg.get('platforms', {})


def get_user_agent():
    """获取通用 User-Agent 字符串"""
    cfg = get_http()
    return cfg.get('user_agent', 'Mozilla/5.0')


def get_timeout(kind='default'):
    """
    获取超时值（秒）。

    Args:
        kind: 'default', 'image', 'article'
    """
    cfg = get_http()
    key = f'{kind}_timeout'
    return cfg.get(key, cfg.get('default_timeout', 15))


def get_min_image_size():
    """获取图片最小分辨率 (width, height)"""
    cfg = get_http()
    return cfg.get('min_image_width', 800), cfg.get('min_image_height', 600)
