# -*- coding: utf-8 -*-
"""Glass desktop Studio tab: catalog, preview, sync (offline, no USB)."""

from __future__ import annotations

import base64
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))
sys.path.insert(0, str(ROOT))

import studio_bridge  # noqa: E402
from glass import Api  # noqa: E402


class StudioBridgeUnit(unittest.TestCase):
    def test_catalog_has_auto_and_core_themes(self):
        cat = studio_bridge.catalog()
        ids = {t["id"] for t in cat["themes"]}
        for needed in ("neon", "flip", "dot", "music", "stock", "perf", "desk"):
            self.assertIn(needed, ids)
        self.assertEqual(cat["auto"]["id"], "auto")
        self.assertEqual(cat["defaults"]["theme"], "auto")

    def test_resolve_auto_media(self):
        playing = {"playing": {"playing": True, "title": "X"}}
        idle = {"playing": {"playing": False}}
        self.assertEqual(studio_bridge.resolve("auto", playing), "music")
        self.assertEqual(studio_bridge.resolve("auto", idle), "neon")
        self.assertEqual(studio_bridge.resolve("perf", playing), "perf")

    def test_render_jpeg_neon(self):
        from PIL import Image

        state = {
            "timestamp": "2026-11-14T12:34:56",
            "cpu_percent": 22,
            "mem_percent": 48,
            "battery_percent": 77,
            "net_down_mbps": 1.2,
            "net_up_mbps": 0.4,
            "playing": {"available": False, "playing": False, "title": "", "artist": ""},
        }
        tid, data = studio_bridge.render_jpeg("neon", state)
        self.assertEqual(tid, "neon")
        self.assertTrue(data.startswith(b"\xff\xd8"))
        self.assertLessEqual(len(data), 30000)
        img = Image.open(io.BytesIO(data))
        self.assertEqual(img.size, (480, 360))


class GlassStudioWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.core = Mock(VERSION="test-studio")
        self.pushed = []
        outer = self

        class FakeDash:
            def push_once(self, mode, image=None, on_line=None, timeout=45):
                data = Path(image).read_bytes()
                outer.pushed.append({"mode": mode, "bytes": len(data)})
                if on_line:
                    on_line('{"ok":true}')
                return {"ok": True, "bytes": len(data)}

        self.core.dash.return_value = FakeDash()
        self.sampler = Mock()
        self.sampler.read.return_value = {
            "timestamp": "2026-11-14T12:34:56",
            "clock": "12:34:56",
            "cpu_percent": 10,
            "cpu_load": 10,
            "mem_percent": 40,
            "mem_pct": 40,
            "net_down_mbps": 0.5,
            "net_up_mbps": 0.1,
            "battery_percent": 80,
            "playing": {"available": True, "playing": False, "title": "", "artist": ""},
            "music": {"available": True, "playing": False, "title": "", "artist": ""},
            "media": None,
        }
        self.api = Api(
            self.temp.name,
            self.core,
            sampler=self.sampler,
            sources=Mock(read=Mock(return_value={})),
        )

    def wait(self):
        if self.api._thread:
            self.api._thread.join(8)
            self.assertFalse(self.api._thread.is_alive())

    def test_bootstrap_exposes_studio_catalog(self):
        data = self.api.bootstrap()
        self.assertIn("studio", data)
        ids = {t["id"] for t in data["studio"]["themes"]}
        self.assertIn("neon", ids)
        self.assertEqual(data["config"]["studio_theme"], "auto")
        self.assertEqual(data["config"]["studio_interval"], 3)

    def test_preview_sets_data_uri(self):
        self.assertTrue(self.api.studio_preview()["ok"])
        self.wait()
        snap = self.api.snapshot()
        self.assertTrue(snap["studioPreview"].startswith("data:image/jpeg;base64,"))
        raw = base64.b64decode(snap["studioPreview"].split(",", 1)[1])
        self.assertTrue(raw.startswith(b"\xff\xd8"))
        self.assertEqual(snap["studioResolved"], "neon")
        self.assertEqual(self.api.snapshot()["state"]["phase"], "idle")

    def test_configure_studio_theme_and_push(self):
        cfg = dict(self.api.bootstrap()["config"])
        cfg["studio_theme"] = "desk"
        self.assertTrue(self.api.configure(cfg)["ok"])
        self.assertTrue(self.api.studio_push()["ok"])
        self.wait()
        self.assertEqual(len(self.pushed), 1)
        self.assertGreater(self.pushed[0]["bytes"], 500)
        self.assertEqual(self.api.snapshot()["studioResolved"], "desk")

    def test_studio_stream_stop(self):
        import time

        self.assertTrue(self.api.studio_start()["ok"])
        for _ in range(80):
            if self.pushed:
                break
            time.sleep(0.05)
        self.assertTrue(self.pushed)
        self.assertTrue(self.api.stop()["ok"])
        self.wait()
        self.assertFalse(self.api.snapshot()["state"]["busy"])
        self.assertIsNone(self.api.snapshot()["state"]["kind"])

    def test_html_has_studio_tab(self):
        html = (ROOT / "desktop" / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("tab-studio", html)
        self.assertIn('id="studio"', html)

    def test_build_pack_includes_studio_bridge(self):
        text = (ROOT / "desktop" / "build_exe.py").read_text(encoding="utf-8")
        self.assertIn("studio_bridge.py", text)


if __name__ == "__main__":
    unittest.main()
