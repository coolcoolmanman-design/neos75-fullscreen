# Mac Studio 一稿

面向 macOS 的屏幕主题入口：把 Keyboard Screen Studio 最值得搬的整屏主题做到 480×360，并继续使用 Neos 的 USB 推送 / 全屏补丁 / 旋钮 / 原生文字。

## 安装

```bash
pip install -r requirements-mac.txt
```

## 命令

```bash
python3 mac/studio.py list
python3 mac/studio.py dry --theme neon
python3 mac/studio.py once --theme auto --no-push
python3 mac/studio.py loop --theme auto --interval 3
```

- `list`：列出主题
- `dry`：只渲染 JPEG 到 `build/`
- `once` / `loop`：渲染后经现有 `dashboard/push.js` USB 推送（可用 `--no-push` 跳过）
- `--theme auto`：播放中切到 `music`，空闲回到 `neon`（可用 `--playing-theme` / `--idle-theme` 改）

## 主题

| id | 说明 |
| --- | --- |
| neon | 霓虹大时钟 + CPU/RAM |
| flip | 翻页时钟 + 三日天气条 |
| dot | 点阵时钟 |
| music | 音乐海报（封面位 + 进度） |
| music-minimal | 无封面纯文字音乐页 |
| stock | 股票看板 |
| perf | CPU / MEM / NET 多轨 |
| desk | 时间 + 系统摘要一屏 |

## 模块

- `mac/studio.py` — CLI 入口
- `dashboard/themes/` — 整屏主题渲染
- `dashboard/live_state_posix.py` — macOS/Linux 采样（psutil）
- `dashboard/media_mac.py` — macOS 正在播放（Music / Spotify AppleScript）

## 说明

本 fork 草稿保留 Neos 既有 USB `push.js`、全屏补丁、旋钮与原生文字能力；主题侧只新增主机渲染与推送路径。Mac USB/DFU 仍需真机验收。
