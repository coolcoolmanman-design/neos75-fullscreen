# -*- coding: utf-8 -*-
"""整屏主题（Mac Studio）桥接层：主题目录、渲染、推送。

设计约束与 dash_bridge 一致：
  * 本模块只做编排，不含固件/DFU 逻辑；
  * 主题 JPEG 在本机用 Pillow 渲染（dashboard/themes）；
  * USB 推送复用现有 dashboard/push.js（经 dash_bridge.push_once）。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _project() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "project"
    return Path(__file__).resolve().parents[1]


def _ensure_path():
    root = str(_project())
    if root not in sys.path:
        sys.path.insert(0, root)


def _themes_mod():
    _ensure_path()
    from dashboard.themes import list_themes, render_theme_jpeg, resolve_theme_id

    return list_themes, render_theme_jpeg, resolve_theme_id


def _sampler_mod():
    _ensure_path()
    from dashboard.live_state_posix import Sampler

    return Sampler


def _now_playing():
    _ensure_path()
    try:
        from dashboard.media_mac import now_playing

        return now_playing()
    except Exception:
        return {
            "available": False,
            "playing": False,
            "is_playing": False,
            "title": "",
            "artist": "",
            "album": "",
            "position": 0.0,
            "duration": 0.0,
            "artwork": None,
        }


def catalog():
    """主题列表 + auto 项，供玻璃 UI 渲染页签。"""
    list_themes, _, _ = _themes_mod()
    themes = list_themes()
    return {
        "themes": themes,
        "auto": {
            "id": "auto",
            "name": "媒体自动",
            "group": "自动",
            "from": "KSS MediaThemeAutomation",
            "desc": "播放中切音乐主题，空闲回霓虹时钟",
        },
        "defaults": {"theme": "auto", "interval": 3, "playing_theme": "music", "idle_theme": "neon"},
    }


def sample_state(*, fetch_weather: bool = False, weather_city: str | None = None) -> dict:
    """本机采样 + macOS 正在播放（非 Darwin 时 available=false）。"""
    Sampler = _sampler_mod()
    state = dict(Sampler().once())
    media = _now_playing()
    state["playing"] = media
    state["music"] = media
    if fetch_weather:
        try:
            city = weather_city or os.environ.get("NEOS75_WEATHER_CITY")
            if city:
                spec = importlib.util.spec_from_file_location(
                    "neos75_sources", _project() / "desktop" / "data_sources.py"
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                state["weather"] = module.Sources().weather.read(city)
        except Exception:
            pass
    return state


def resolve(
    theme: str | None,
    state: dict | None = None,
    *,
    playing_theme: str = "music",
    idle_theme: str = "neon",
) -> str:
    _, _, resolve_theme_id = _themes_mod()
    media = (state or {}).get("playing") or {}
    playing = bool(media.get("playing") or media.get("is_playing"))
    auto = (theme or "auto") == "auto"
    return resolve_theme_id(
        None if auto else theme,
        is_playing=playing,
        auto_media=auto,
        playing_theme=playing_theme,
        idle_theme=idle_theme,
    )


def render_jpeg(
    theme: str,
    state: dict | None = None,
    *,
    quality: int = 72,
    limit: int = 30000,
    playing_theme: str = "music",
    idle_theme: str = "neon",
) -> tuple[str, bytes]:
    """渲染当前主题 JPEG，返回 (resolved_theme_id, jpeg_bytes)。"""
    _, render_theme_jpeg, _ = _themes_mod()
    state = state if state is not None else sample_state()
    tid = resolve(theme, state, playing_theme=playing_theme, idle_theme=idle_theme)
    data = render_theme_jpeg(tid, state, quality=quality, limit=limit)
    return tid, data


def push_jpeg(path: Path | str, *, on_line=None, timeout: int = 45) -> dict:
    """经现有 USB 通道推送一张 JPEG。"""
    _ensure_path()
    try:
        import dash_bridge
    except ImportError:  # pragma: no cover - source layout when cwd is repo root
        from desktop import dash_bridge  # type: ignore

    return dash_bridge.push_once("push", image=Path(path), on_line=on_line, timeout=timeout)
