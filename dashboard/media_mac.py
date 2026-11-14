# -*- coding: utf-8 -*-
"""macOS now-playing probe for Mac Studio.

Uses MediaRemote / AppleScript when available. Returns a stable dict shape;
never invents a track title when nothing is playing.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess


def _empty(**overrides):
    base = {
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
    base.update(overrides)
    return base


def _osascript(script: str) -> str:
    osa = shutil.which("osascript")
    if not osa:
        return ""
    proc = subprocess.run(
        [osa, "-e", script],
        capture_output=True,
        text=True,
        timeout=3,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _from_music_app() -> dict | None:
    # Best-effort: Music.app / Spotify via AppleScript. Silent on non-macOS CI.
    script = r'''
    set out to ""
    try
      tell application "System Events"
        set musicRunning to (name of processes) contains "Music"
        set spotRunning to (name of processes) contains "Spotify"
      end tell
      if musicRunning then
        tell application "Music"
          if player state is playing or player state is paused then
            set t to name of current track
            set a to artist of current track
            set p to player position
            set dur to duration of current track
            set st to player state as string
            return t & linefeed & a & linefeed & p & linefeed & dur & linefeed & st
          end if
        end tell
      end if
      if spotRunning then
        tell application "Spotify"
          if player state is playing or player state is paused then
            set t to name of current track
            set a to artist of current track
            set p to player position
            set dur to duration of current track
            set st to player state as string
            return t & linefeed & a & linefeed & p & linefeed & (dur / 1000) & linefeed & st
          end if
        end tell
      end if
    end try
    return ""
    '''
    raw = _osascript(script)
    if not raw:
        return None
    parts = raw.splitlines()
    if len(parts) < 2:
        return None
    title, artist = parts[0].strip(), parts[1].strip()
    if not title:
        return None
    try:
        position = float(parts[2]) if len(parts) > 2 else 0.0
    except ValueError:
        position = 0.0
    try:
        duration = float(parts[3]) if len(parts) > 3 else 0.0
    except ValueError:
        duration = 0.0
    status = (parts[4] if len(parts) > 4 else "").lower()
    playing = "play" in status and "pause" not in status
    return _empty(
        available=True,
        playing=playing,
        is_playing=playing,
        title=title,
        artist=artist,
        position=position,
        duration=duration,
    )


def now_playing() -> dict:
    if platform.system() != "Darwin":
        return _empty()
    try:
        found = _from_music_app()
        if found:
            return found
    except Exception:
        pass
    return _empty()


def main():
    print(json.dumps(now_playing(), ensure_ascii=False))


if __name__ == "__main__":
    main()
