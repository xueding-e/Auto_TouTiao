# 第一步：搜集热点

运行自动化脚本，一键抓取 6 个平台热点 + 头条热度指数（via tianapi-toutiao skill）+ 交叉分析：

```bash
python ./scripts/fetch_and_analyze.py
```

## 脚本自动完成的事项

- 并行抓取微博、百度、知乎、抖音、贴吧、头条 6 个平台的热搜
- 调用 tianapi-toutiao skill 获取头条热度指数
- 跨平台标题聚类匹配（相似度 ≥ 0.6 视为同一话题）
- **五维点击吸引力评分**（争议冲突度 / 情绪推动力 / 利益相关性 / 写作延展性 / 跨平台验证）
- 输出 `top5_result.json` 和 `all_topics.json` 到当前目录

## 容错

如果 newsnow 某个源拉取失败（如被 Cloudflare 拦截），跳过该源继续，不影响整体流程。
