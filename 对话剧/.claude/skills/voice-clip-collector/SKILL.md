---
name: voice-clip-collector
description: 从B站搜索并下载指定影视角色的语音剪辑，按静音分割为独立片段，提取目标角色的纯音频。当用户提到"收集语音"、"收集角色语音"、"下载台词音频"、"收集xxx的语音"、"语音clip"时触发。
---

# 影视角色语音收集

搜索B站已有的角色名场面/台词剪辑，下载后按静音段分割，逐段确认角色，提取目标人物的纯音频。

## 流程

### 第一步：确定搜索目标

用户指定：**作品名** + **角色名** + （可选）**数量/时长目标**

例如：「潜伏，吴敬中，50秒」

### 第二步：搜索角色语音剪辑

用 **WebSearch** 在 **B站 (bilibili.com)** 搜索：

| 搜索词组合 | 说明 |
|-----------|------|
| `site:bilibili.com 潜伏 吴敬中 名场面` | 精确匹配B站 |
| `site:bilibili.com 潜伏 吴敬中 台词合集` | 找合集/汇编类 |
| `site:bilibili.com 潜伏 吴敬中 经典台词` | 找单段名场面 |
| `site:bilibili.com 潜伏 吴敬中 纯享` | 找无BGM纯净版 |

**目标**：找到包含该角色台词/语音的B站视频链接，优先选择：
- 台词合集/混剪（内容长）
- 单段长台词（如演讲、独白）
- 音质清晰、无背景音乐

### 第三步：下载视频

用 `yt-dlp` 下载B站视频到 `clips/raw/` 目录：

```bash
yt-dlp -o "clips/raw/%(title)s.%(ext)s" <bilibili视频URL>
```

`yt-dlp` 原生支持B站，可直接解析播放链接。

### 第四步：提取完整音频

用 `scripts/video_to_audio.py` 将视频转为 WAV 文件（无损，便于后续处理）：

```bash
python3 .claude/skills/voice-clip-collector/scripts/video_to_audio.py <视频文件> <作品名> <角色名> --wav
```

输出：`clips/<作品名>-<角色名>.wav`

### 第五步：按静音分割

用 `scripts/speaker_split.py` 按静音段将音频切分为多个独立片段：

```bash
python3 .claude/skills/voice-clip-collector/scripts/speaker_split.py <音频文件.wav> --output-dir clips/split/<作品名>-<角色名>/
```

**原理**：ffmpeg 的 `silencedetect` 滤镜检测静音间隙（阈值 -30dB，最小静音 0.5s），在静音处切分，每段就是一个人说话的内容。

输出：`clips/split/<作品名>-<角色名>/segment_001.wav`、`segment_002.wav` ...

可调参数：
- `--threshold <dB>`：静音阈值，默认 -30dB（调高则更多分割）
- `--min-silence <s>`：最小静音时长，默认 0.5s

### 第六步：逐段确认角色

向用户展示分割结果，列出每段的时长，并**播放前几段让用户判断哪几段是目标角色**：

```
分割结果（<作品名>-<角色名>.wav）：
共 N 段，总时长 Xm Ys

逐段列表：
  segment_001.wav: 3.2s
  segment_002.wav: 2.8s
  segment_003.wav: 1.5s
  ...

请听前几段，告诉我哪几段是 吴敬中 的声音？
（输入段号，如 "001,003,005" 或 "全部" 或 "都不是"）
```

等待用户确认后，用 `scripts/extract_role.py` 将用户确认的片段拼接。

### 第七步：拼接目标角色音频

将用户确认的片段拼接为单个 MP3 文件：

```bash
python3 .claude/skills/voice-clip-collector/scripts/extract_role.py <split目录> <段号列表> <角色名> <作品名>
```

输出：
- `clips/<作品名>-<角色名>-final.mp3`（拼接后的完整音频）

### 第八步：整理输出

- 列出最终音频文件（文件名、时长、大小）
- 确认音频可正常播放（`ffprobe` 检查）
- 如果时长不足用户目标，提示继续搜索更多视频

### 第九步：汇报

向用户汇报：
- 作品名、角色名
- 下载了几个视频
- 分割出几段，用户确认了哪几段是目标角色
- 最终音频时长和文件位置

## 配置

- **原始视频**：`clips/raw/`
- **完整音频**：`clips/`（WAV）
- **分割后片段**：`clips/split/<作品名>-<角色名>/`
- **最终输出**：`clips/<作品名>-<角色名>-final.mp3`

## 依赖

| 工具 | 用途 | 状态 |
|------|------|------|
| `yt-dlp` | 下载B站视频 | 需安装 `brew install yt-dlp` |
| `ffmpeg` | 视频转音频 + 静音检测 | 已安装 |
| `pydub` | Python 音频处理 | 已安装 |

## 失败处理

| 场景 | 处理 |
|------|------|
| B站搜不到相关视频 | 换搜索词重试（"名场面"→"台词"→"片段"→"纯享"），仍无则告知用户 |
| yt-dlp 无法解析B站链接 | 尝试 `yt-dlp --cookies <cookies.txt>`，仍失败则告知用户 |
| yt-dlp 未安装 | 告知用户 `brew install yt-dlp` |
| 静音检测无分割（整段无静音） | 说明是单人连续发言，整段输出 |
| 静音检测分割过多/过少 | 调整 `--threshold` 和 `--min-silence` 参数重试 |
| 视频音质太差（噪音大/含BGM） | 仍处理，但备注告知用户 |
| 下载的视频不是该角色 | 跳过，不处理 |

## 注意事项

- 尊重版权，仅限个人学习使用
- 静音分割在含背景音乐/多人重叠时可能不准确
- 优先下载清晰、人声突出的视频
- 如果视频包含多人同时说话，无法分离，备注说明
