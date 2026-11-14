"""Theme registry and media auto-switch rules (KSS MediaThemeAutomation)."""

from __future__ import annotations

THEMES = {
    "neon": {
        "id": "neon",
        "name": "霓虹时钟",
        "group": "时钟",
        "from": "KSS clock-neon",
        "desc": "大号发光时间 + CPU/RAM 摘要",
    },
    "flip": {
        "id": "flip",
        "name": "翻页时钟·天气",
        "group": "时钟",
        "from": "KSS clock-flip + 五日天气",
        "desc": "翻页卡片 + 三日预报",
    },
    "dot": {
        "id": "dot",
        "name": "点阵时钟",
        "group": "点阵",
        "from": "KSS clock-dot-matrix",
        "desc": "点阵数字时钟",
    },
    "music": {
        "id": "music",
        "name": "音乐海报",
        "group": "媒体",
        "from": "KSS music-poster",
        "desc": "封面主视觉 + 曲名进度",
        "music": True,
    },
    "music-minimal": {
        "id": "music-minimal",
        "name": "音乐极简",
        "group": "媒体",
        "from": "KSS music-minimal",
        "desc": "无封面纯文字音乐页",
        "music": True,
    },
    "stock": {
        "id": "stock",
        "name": "股票看板",
        "group": "资讯",
        "from": "KSS stock",
        "desc": "多只行情列表",
    },
    "perf": {
        "id": "perf",
        "name": "性能曲线",
        "group": "系统",
        "from": "KSS 性能可视化",
        "desc": "CPU / MEM / NET 多轨",
    },
    "desk": {
        "id": "desk",
        "name": "桌面常驻",
        "group": "系统",
        "from": "Neos desk preset + KSS layout",
        "desc": "时间 + 系统 + 网络一屏",
    },
}

MUSIC_THEME_IDS = {tid for tid, meta in THEMES.items() if meta.get("music")}


def list_themes():
    return [dict(meta) for meta in THEMES.values()]


def resolve_theme_id(
    selected: str | None,
    *,
    is_playing: bool,
    auto_media: bool = True,
    playing_theme: str = "music",
    idle_theme: str = "neon",
) -> str:
    """Port of KSS MediaThemeAutomation.ResolveThemeId."""
    if auto_media:
        if is_playing:
            return playing_theme if playing_theme in THEMES else "music"
        return idle_theme if idle_theme in THEMES and idle_theme not in MUSIC_THEME_IDS else "neon"
    chosen = selected or "neon"
    return chosen if chosen in THEMES else "neon"
