#!/usr/bin/env python3
"""
Markdown 图片完整性验证脚本

用法:
  python verify_md_images.py <markdown文件路径>

功能:
  - 提取 md 文件中所有 ![描述](URL) 图片引用
  - 对每个 URL 发送请求验证是否可访问
  - 输出验证报告：总图片数、有效数、失效数及失效 URL 列表
  - 退出码: 0 = 全部通过, 1 = 存在失效图片
"""

import re
import sys
import os
import argparse

# 修复 Windows 终端 GBK 编码不支持 emoji 的问题
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import requests
except ImportError:
    print("[ERROR] requests 未安装。请执行: pip install requests")
    raise

# 导入统一配置加载器
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from config.config_loader import get_user_agent, get_timeout


def extract_images(md_text):
    """从 Markdown 文本中提取所有图片引用，返回 [(描述, URL, 行号), ...]"""
    images = []
    for i, line in enumerate(md_text.split('\n'), 1):
        for match in re.finditer(r'!\[(.*?)\]\((.*?)\)', line):
            desc = match.group(1).strip()
            url = match.group(2).strip()
            images.append((desc, url, i))
    return images


def verify_image_url(url, timeout=10):
    """
    验证图片 URL 是否可访问。
    先用 HEAD 请求检查，失败则降级为 GET 请求。
    返回 (is_valid, status_code_or_error)
    """
    headers = {
        'User-Agent': get_user_agent(),
        'Referer': 'https://image.baidu.com/',
    }

    # 先尝试 HEAD 请求（轻量级）
    try:
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return True, 200
        # 有些服务器不支持 HEAD，降级为 GET
    except requests.exceptions.RequestException:
        pass

    # 降级为 GET 请求
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)
        if resp.status_code == 200:
            # 检查 Content-Type 是否为图片
            content_type = resp.headers.get('Content-Type', '')
            if 'image' in content_type or 'octet-stream' in content_type:
                return True, 200
            # Content-Type 不包含 image 但状态码 200，仍视为有效（某些 CDN 不设置正确类型）
            return True, 200
        return False, resp.status_code
    except requests.exceptions.Timeout:
        return False, 'timeout'
    except requests.exceptions.ConnectionError:
        return False, 'connection_error'
    except requests.exceptions.RequestException as e:
        return False, str(type(e).__name__)


def verify_md_images(md_path):
    """验证 Markdown 文件中所有图片的完整性"""
    if not os.path.exists(md_path):
        print(f"[ERROR] 文件不存在: {md_path}")
        return False

    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    images = extract_images(md_text)

    if not images:
        print(f"[INFO] {md_path} 中没有找到图片引用")
        return True

    print(f"📋 图片验证报告: {md_path}")
    print(f"{'='*60}")
    print(f"共找到 {len(images)} 张图片引用\n")

    valid_count = 0
    invalid_list = []

    for idx, (desc, url, line_no) in enumerate(images, 1):
        short_url = url[:80] + '...' if len(url) > 80 else url
        print(f"  [{idx}/{len(images)}] 第{line_no}行: {desc or '(无描述)'} -> {short_url}")

        is_valid, status = verify_image_url(url)

        if is_valid:
            print(f"         ✅ 有效 (HTTP {status})")
            valid_count += 1
        else:
            print(f"         ❌ 失效 (状态: {status})")
            invalid_list.append({
                'desc': desc,
                'url': url,
                'line': line_no,
                'error': status,
            })

    print(f"\n{'='*60}")
    print(f"验证结果: {valid_count}/{len(images)} 有效")

    if invalid_list:
        print(f"\n❌ 失效图片列表 ({len(invalid_list)} 张):")
        for item in invalid_list:
            print(f"  - 第{item['line']}行 [{item['desc']}] {item['url']} (错误: {item['error']})")
        print(f"\n⚠️  请替换失效图片后重新验证")
        return False
    else:
        print(f"\n✅ 所有图片验证通过!")
        return True


def main():
    parser = argparse.ArgumentParser(description="Markdown 图片完整性验证")
    parser.add_argument("input", help="要验证的 Markdown 文件路径")
    args = parser.parse_args()

    success = verify_md_images(args.input)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
