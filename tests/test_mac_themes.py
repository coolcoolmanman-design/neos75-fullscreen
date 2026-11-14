# -*- coding: utf-8 -*-
"""Mac Studio theme draft tests (offline, no USB)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.live_state_posix import Sampler  # noqa: E402
from dashboard.media_mac import now_playing  # noqa: E402
from dashboard.themes import THEMES, list_themes, render_theme_jpeg, resolve_theme_id  # noqa: E402


class ThemeCatalog(unittest.TestCase):
    def test_expected_theme_ids(self):
        ids = {m["id"] for m in list_themes()}
        for needed in ("neon", "flip", "dot", "music", "stock", "perf", "desk"):
            self.assertIn(needed, ids)
        self.assertEqual(set(THEMES), ids)

    def test_auto_media_switch(self):
        self.assertEqual(resolve_theme_id(None, is_playing=True, auto_media=True), "music")
        self.assertEqual(resolve_theme_id(None, is_playing=False, auto_media=True), "neon")
        self.assertEqual(
            resolve_theme_id("perf", is_playing=True, auto_media=False),
            "perf",
        )


class ThemeRender(unittest.TestCase):
    def setUp(self):
        self.state = {
            "timestamp": "2026-11-14T12:34:56",
            "cpu_percent": 22,
            "mem_percent": 48,
            "battery_percent": 77,
            "net_down_mbps": 1.2,
            "net_up_mbps": 0.4,
            "playing": {
                "available": True,
                "playing": True,
                "title": "Demo Track",
                "artist": "Neos",
                "position": 42,
                "duration": 180,
            },
            "weather": {"label": "今天", "temp": 18, "days": [
                {"label": "今天", "temp": 18},
                {"label": "明天", "temp": 20},
                {"label": "后天", "temp": 16},
            ]},
        }

    def test_each_theme_renders_jpeg_under_limit(self):
        from PIL import Image

        for tid in THEMES:
            data = render_theme_jpeg(tid, self.state, quality=72, limit=30000)
            self.assertTrue(data.startswith(b"\xff\xd8"), tid)
            self.assertLessEqual(len(data), 30000, tid)
            img = Image.open(io.BytesIO(data))
            self.assertEqual(img.size, (480, 360), tid)
            self.assertEqual(img.format, "JPEG", tid)


class SamplerAndMedia(unittest.TestCase):
    def test_sampler_once_keys(self):
        state = Sampler().once()
        for key in ("cpu_percent", "mem_percent", "net_down_mbps", "net_up_mbps", "timestamp"):
            self.assertIn(key, state)
        self.assertIsInstance(state["cpu_percent"], float)

    def test_now_playing_shape(self):
        media = now_playing()
        self.assertIn("available", media)
        self.assertIn("playing", media)
        self.assertIn("title", media)


class StudioCli(unittest.TestCase):
    def test_list_and_dry(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        list_out = subprocess.check_output(
            [sys.executable, str(ROOT / "mac" / "studio.py"), "list"],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        self.assertIn("neon", list_out)
        dry = subprocess.check_output(
            [sys.executable, str(ROOT / "mac" / "studio.py"), "dry", "--theme", "neon", "--out",
             str(ROOT / "build" / "test-theme-neon.jpg")],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        payload = json.loads(dry.strip().splitlines()[-1])
        self.assertEqual(payload["event"], "dry")
        self.assertEqual(payload["theme"], "neon")
        self.assertGreater(payload["bytes"], 500)
        self.assertTrue(Path(payload["out"]).is_file())


if __name__ == "__main__":
    unittest.main()
