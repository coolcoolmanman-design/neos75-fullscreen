#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Neos75 Mac Studio — KSS-worth screen themes + Neos USB push.

Mac-first draft:
  - Full-screen themes ported from Keyboard Screen Studio ideas
  - Media auto-switch (play → music theme, stop → idle theme)
  - Keeps Neos strengths: USB JPEG push, existing fullscreen/knob/native tools

Usage:
  python mac/studio.py list
  python mac/studio.py dry --theme neon
  python mac/studio.py once --theme auto
  python mac/studio.py loop --theme auto --interval 3
  python mac/studio.py push path/to.jpg
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Windows CI consoles default to a legacy code page; keep list/dry JSON printable.
for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from dashboard.live_state_posix import Sampler  # noqa: E402
from dashboard.themes import list_themes, render_theme_jpeg, resolve_theme_id  # noqa: E402

try:
    from dashboard.media_mac import now_playing
except Exception:  # pragma: no cover
    def now_playing():
        return {"available": False, "playing": False, "title": "", "artist": ""}


def _node() -> str:
    return os.environ.get("NEOS75_NODE") or "node"


def push_jpeg(path: Path, retries: int = 4) -> dict:
    """Reuse existing dashboard/push.js USB path (Neos strength)."""
    cmd = [_node(), str(ROOT / "dashboard" / "push.js"), "push", str(path), "--json", "--retries", str(retries)]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (proc.stdout or "").strip().splitlines()
    last = {}
    for line in out:
        try:
            last = json.loads(line)
        except Exception:
            continue
    if proc.returncode != 0 and not last:
        err = (proc.stderr or proc.stdout or "push failed").strip()
        raise RuntimeError(err)
    last["exitCode"] = proc.returncode
    return last


def enrich(state: dict, *, fetch_weather: bool = False) -> dict:
    media = now_playing()
    state = dict(state)
    state["playing"] = media
    state["music"] = media
    if fetch_weather:
        try:
            from desktop.data_sources import Sources

            src = Sources()
            # city comes from env for draft; optional
            city = os.environ.get("NEOS75_WEATHER_CITY")
            if city:
                state["weather"] = src.weather.read(city)
        except Exception:
            pass
    return state


def pick_theme(args, state) -> str:
    media = state.get("playing") or {}
    playing = bool(media.get("playing") or media.get("is_playing"))
    return resolve_theme_id(
        None if args.theme == "auto" else args.theme,
        is_playing=playing,
        auto_media=(args.theme == "auto" or args.auto_media),
        playing_theme=args.playing_theme,
        idle_theme=args.idle_theme,
    )


def cmd_list(_args):
    for meta in list_themes():
        print(f"{meta['id']:16} {meta['name']:12}  {meta['from']}")
    print("\nauto             媒体自动切换（播放→music，停止→idle）")
    return 0


def cmd_dry(args):
    state = enrich(Sampler().once(), fetch_weather=args.weather)
    theme = pick_theme(args, state)
    data = render_theme_jpeg(theme, state, quality=args.quality, limit=args.limit)
    out = Path(args.out or (ROOT / "build" / f"theme-{theme}.jpg"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(json.dumps({
        "event": "dry",
        "theme": theme,
        "bytes": len(data),
        "out": str(out),
        "playing": bool((state.get("playing") or {}).get("playing")),
    }, ensure_ascii=False))
    return 0


def cmd_once(args):
    state = enrich(Sampler().once(), fetch_weather=args.weather)
    theme = pick_theme(args, state)
    data = render_theme_jpeg(theme, state, quality=args.quality, limit=args.limit)
    tmp = Path(args.out or (ROOT / "build" / "studio-once.jpg"))
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    result = {"event": "once", "theme": theme, "bytes": len(data), "out": str(tmp)}
    if not args.no_push:
        result["push"] = push_jpeg(tmp, retries=args.retries)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_loop(args):
    sampler = Sampler()
    round_i = 0
    print(f"# Neos75 Mac Studio loop theme={args.theme} interval={args.interval}s", flush=True)
    print("# Ctrl+C 停止。推送后请看屏确认（原厂协议无最终 ACK）。", flush=True)
    try:
        while True:
            t0 = time.time()
            state = enrich(sampler.once(), fetch_weather=args.weather)
            theme = pick_theme(args, state)
            data = render_theme_jpeg(theme, state, quality=args.quality, limit=args.limit)
            tmp = ROOT / "build" / "studio-loop.jpg"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(data)
            round_i += 1
            payload = {
                "event": "loop",
                "round": round_i,
                "theme": theme,
                "bytes": len(data),
                "playing": bool((state.get("playing") or {}).get("playing")),
                "title": (state.get("playing") or {}).get("title") or "",
            }
            if not args.no_push:
                try:
                    payload["push"] = push_jpeg(tmp, retries=args.retries)
                except Exception as exc:
                    payload["error"] = str(exc)
            print(json.dumps(payload, ensure_ascii=False), flush=True)
            rest = args.interval - (time.time() - t0)
            if rest > 0:
                time.sleep(rest)
    except KeyboardInterrupt:
        print(json.dumps({"event": "stop", "rounds": round_i}), flush=True)
        return 0


def cmd_push(args):
    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"文件不存在: {path}")
    print(json.dumps(push_jpeg(path, retries=args.retries), ensure_ascii=False))
    return 0


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--theme", default="auto", help="theme id or 'auto'")
    common.add_argument("--auto-media", action="store_true", help="force media auto-switch even if theme fixed")
    common.add_argument("--playing-theme", default="music")
    common.add_argument("--idle-theme", default="neon")
    common.add_argument("--quality", type=int, default=72)
    common.add_argument("--limit", type=int, default=30000)
    common.add_argument("--interval", type=float, default=3.0)
    common.add_argument("--retries", type=int, default=4)
    common.add_argument("--out", default=None)
    common.add_argument("--weather", action="store_true")
    common.add_argument("--no-push", action="store_true", help="render only")

    ap = argparse.ArgumentParser(
        description="Neos75 Mac Studio (KSS themes + Neos USB)",
        parents=[common],
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", parents=[common])
    sub.add_parser("dry", parents=[common])
    sub.add_parser("once", parents=[common])
    sub.add_parser("loop", parents=[common])
    p = sub.add_parser("push", parents=[common])
    p.add_argument("file")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "dry":
        return cmd_dry(args)
    if args.cmd == "once":
        return cmd_once(args)
    if args.cmd == "loop":
        return cmd_loop(args)
    if args.cmd == "push":
        return cmd_push(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
