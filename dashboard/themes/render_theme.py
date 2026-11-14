# -*- coding: utf-8 -*-
"""Render KSS-style full-screen themes to Neos75 480x360 baseline JPEG."""

from __future__ import annotations

import datetime as dt
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .catalog import THEMES

W, H = 480, 360

ACCENT = (46, 196, 168)
TXT = (236, 239, 245)
DIM = (130, 140, 158)
BG = (12, 13, 18)
CARD = (26, 29, 38)
GOOD = (61, 184, 138)
BAD = (226, 91, 91)
TRACK = (44, 48, 60)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    candidates += [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size, index=0)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def _center(draw, text, font, y, fill=TXT, x0=0, x1=W):
    tw, th = _text_size(draw, text, font)
    draw.text((x0 + (x1 - x0 - tw) / 2, y), text, font=font, fill=fill)


def _pct(state, key, default=0.0):
    val = state.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except Exception:
        return default


def _now(state) -> dt.datetime:
    raw = state.get("timestamp") or state.get("time")
    if isinstance(raw, str) and raw:
        try:
            return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
        except Exception:
            pass
    return dt.datetime.now()


def _music(state) -> dict:
    m = state.get("playing") or state.get("music") or {}
    if not isinstance(m, dict):
        return {"available": False, "is_playing": False, "title": "未在播放", "artist": ""}
    title = m.get("title") or m.get("name") or "未在播放"
    artist = m.get("artist") or m.get("albumArtist") or ""
    playing = bool(m.get("playing") or m.get("isPlaying") or m.get("is_playing"))
    available = bool(m.get("available", bool(title and title != "未在播放")))
    return {
        "available": available,
        "is_playing": playing,
        "title": title,
        "artist": artist,
        "position": float(m.get("position") or m.get("position_sec") or 0),
        "duration": float(m.get("duration") or m.get("duration_sec") or 0),
        "artwork": m.get("artwork"),
    }


def _bar(d, x, y, w, h, frac, fill=ACCENT, track=TRACK):
    d.rounded_rectangle((x, y, x + w, y + h), radius=max(2, h // 2), fill=track)
    fw = int(w * max(0.0, min(1.0, frac)))
    if fw > 0:
        d.rounded_rectangle((x, y, x + max(h, fw), y + h), radius=max(2, h // 2), fill=fill)


def draw_neon(img, state):
    d = ImageDraw.Draw(img)
    now = _now(state)
    d.text((24, 22), "NEOS75  ·  NEON", font=_font(14), fill=DIM)
    bat = state.get("battery_percent")
    if bat is not None:
        d.text((360, 22), f"BAT {int(bat)}%", font=_font(14, True), fill=ACCENT)
    time_s = now.strftime("%H:%M")
    font = _font(92, True)
    tw, _ = _text_size(d, time_s, font)
    d.text(((W - tw) / 2, 88), time_s, font=font, fill=ACCENT)
    _center(d, now.strftime("%A  ·  %b %d"), _font(20), 210, fill=DIM)
    cpu = _pct(state, "cpu_percent", _pct(state, "cpu"))
    mem = _pct(state, "mem_percent", _pct(state, "memory_percent"))
    d.text((24, 300), f"CPU {cpu:.0f}%", font=_font(16), fill=DIM)
    d.text((140, 300), f"RAM {mem:.0f}%", font=_font(16), fill=DIM)
    d.rounded_rectangle((280, 308, 456, 322), radius=6, fill=TRACK)
    fill_x = 280 + int(176 * max(0, min(100, mem)) / 100)
    d.rounded_rectangle((280, 308, max(286, fill_x), 322), radius=6, fill=ACCENT)


def draw_flip(img, state):
    d = ImageDraw.Draw(img)
    now = _now(state)
    for i, val in enumerate([now.strftime("%H"), now.strftime("%M")]):
        x = 24 + i * 228
        d.rounded_rectangle((x, 24, x + 210, 168), radius=16, fill=(42, 49, 60))
        d.line((x + 8, 96, x + 202, 96), fill=(0, 0, 0), width=2)
        font = _font(72, True)
        tw, th = _text_size(d, val, font)
        d.text((x + (210 - tw) / 2, 24 + (144 - th) / 2), val, font=font, fill=TXT)
    weather = state.get("weather") or {}
    days = weather.get("days") or []
    if not days:
        label = weather.get("label") or weather.get("text") or "今天"
        temp = weather.get("temp") or weather.get("temperature")
        days = [
            {"label": label, "temp": temp},
            {"label": "明天", "temp": None},
            {"label": "后天", "temp": None},
        ]
    for i, day in enumerate(days[:3]):
        x = 24 + i * 152
        d.rounded_rectangle((x, 200, x + 140, 332), radius=12, fill=CARD)
        name = str(day.get("label") or day.get("name") or f"D{i+1}")
        d.text((x + 14, 214), name[:6], font=_font(16, True), fill=DIM)
        temp = day.get("temp") if day.get("temp") is not None else day.get("high")
        if temp is not None:
            d.text((x + 14, 260), f"{int(float(temp))}°", font=_font(36, True), fill=TXT)
        else:
            d.text((x + 14, 268), "—", font=_font(28, True), fill=DIM)


DOT = [
    "01110",
    "10001",
    "10001",
    "10001",
    "10001",
    "10001",
    "01110",
]
DIGITS = {
    "0": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["01110", "10001", "00001", "00110", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["01110", "10000", "11110", "10001", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
}


def draw_dot(img, state):
    d = ImageDraw.Draw(img)
    now = _now(state)
    d.text((24, 22), "NEOS75  ·  DOT MATRIX", font=_font(14), fill=DIM)
    text = now.strftime("%H:%M")
    cell, gap = 10, 4
    total_w = 0
    for ch in text:
        total_w += 5 * cell + gap
    total_w -= gap
    x0 = (W - total_w) // 2
    y0 = 120
    x = x0
    for ch in text:
        grid = DIGITS.get(ch, DOT)
        for r, row in enumerate(grid):
            for c, bit in enumerate(row):
                if bit == "1":
                    px = x + c * cell
                    py = y0 + r * cell
                    d.ellipse((px, py, px + cell - 2, py + cell - 2), fill=ACCENT)
        x += 5 * cell + gap
    _center(d, now.strftime("%Y-%m-%d"), _font(18), 280, fill=DIM)


def draw_music(img, state, *, minimal: bool = False):
    d = ImageDraw.Draw(img)
    m = _music(state)
    d.text((24, 22), "NEOS75  ·  MUSIC", font=_font(14), fill=DIM)
    if not minimal:
        art = m.get("artwork")
        box = (24, 56, 184, 216)
        d.rounded_rectangle(box, radius=12, fill=CARD)
        if isinstance(art, (bytes, bytearray)) and art:
            try:
                cover = Image.open(io.BytesIO(art)).convert("RGB").resize((148, 148))
                img.paste(cover, (32, 64))
            except Exception:
                d.text((60, 120), "♪", font=_font(48), fill=ACCENT)
        else:
            d.text((70, 110), "♪", font=_font(48), fill=ACCENT)
        tx = 210
    else:
        tx = 24
    title = (m.get("title") or "未在播放")[:28]
    artist = (m.get("artist") or "")[:32]
    d.text((tx, 70 if not minimal else 90), title, font=_font(28, True), fill=TXT)
    d.text(
        (tx, 120 if not minimal else 150),
        artist or ("播放中" if m.get("is_playing") else "已暂停"),
        font=_font(18),
        fill=DIM,
    )
    dur = m.get("duration") or 0
    pos = m.get("position") or 0
    frac = (pos / dur) if dur > 0 else 0.0
    _bar(d, tx, 200 if not minimal else 230, W - tx - 24, 10, frac, fill=GOOD if m.get("is_playing") else ACCENT)
    if dur > 0:
        stamp = f"{int(pos)//60}:{int(pos)%60:02d} / {int(dur)//60}:{int(dur)%60:02d}"
        d.text((tx, 220 if not minimal else 250), stamp, font=_font(14), fill=DIM)


def draw_music_minimal(img, state):
    draw_music(img, state, minimal=True)


def draw_stock(img, state):
    d = ImageDraw.Draw(img)
    d.text((24, 22), "NEOS75  ·  STOCK", font=_font(14), fill=DIM)
    rows = state.get("stocks") or state.get("quotes") or []
    if not rows:
        rows = [
            {"symbol": "AAPL", "price": 190.2, "change_pct": 0.8},
            {"symbol": "MSFT", "price": 420.1, "change_pct": -0.3},
            {"symbol": "NVDA", "price": 880.5, "change_pct": 1.4},
            {"symbol": "TSLA", "price": 248.0, "change_pct": -1.1},
        ]
    y = 58
    for row in rows[:6]:
        sym = str(row.get("symbol") or row.get("name") or "?")
        price = row.get("price")
        chg = row.get("change_pct")
        if chg is None:
            chg = row.get("change")
        color = GOOD if (chg or 0) >= 0 else BAD
        d.rounded_rectangle((24, y, 456, y + 40), radius=8, fill=CARD)
        d.text((36, y + 10), sym, font=_font(18, True), fill=TXT)
        if price is not None:
            d.text((180, y + 10), f"{float(price):.2f}", font=_font(18), fill=TXT)
        if chg is not None:
            d.text((340, y + 10), f"{float(chg):+.2f}%", font=_font(18, True), fill=color)
        y += 48


def draw_perf(img, state):
    d = ImageDraw.Draw(img)
    d.text((24, 22), "NEOS75  ·  PERFORMANCE", font=_font(14), fill=DIM)
    cpu = _pct(state, "cpu_percent", _pct(state, "cpu_load", _pct(state, "cpu")))
    mem = _pct(state, "mem_percent", _pct(state, "mem_pct", _pct(state, "memory_percent")))
    down = _pct(state, "net_down_mbps")
    up = _pct(state, "net_up_mbps")
    metrics = [
        ("CPU", cpu, ACCENT),
        ("MEM", mem, GOOD),
        ("DOWN NET", min(down, 100.0), (90, 160, 255)),
        ("UP NET", min(up, 100.0), (255, 170, 80)),
    ]
    y = 70
    for label, value, color in metrics:
        d.text((24, y), label, font=_font(16, True), fill=DIM)
        d.text((400, y), f"{value:.1f}", font=_font(16, True), fill=TXT)
        _bar(d, 24, y + 28, 432, 14, value / 100.0, fill=color)
        y += 66


def draw_desk(img, state):
    d = ImageDraw.Draw(img)
    now = _now(state)
    d.text((24, 18), "NEOS75  ·  DESK", font=_font(14), fill=DIM)
    time_s = now.strftime("%H:%M")
    font = _font(64, True)
    tw, _ = _text_size(d, time_s, font)
    d.text((24, 48), time_s, font=font, fill=TXT)
    d.text((24 + tw + 16, 78), now.strftime("%m/%d"), font=_font(22), fill=DIM)

    cpu = _pct(state, "cpu_percent", _pct(state, "cpu_load", _pct(state, "cpu")))
    mem = _pct(state, "mem_percent", _pct(state, "mem_pct", _pct(state, "memory_percent")))
    down = _pct(state, "net_down_mbps")
    up = _pct(state, "net_up_mbps")
    bat = state.get("battery_percent")

    cards = [
        ("CPU", f"{cpu:.0f}%"),
        ("RAM", f"{mem:.0f}%"),
        ("NET", f"D{down:.1f} U{up:.1f}"),
        ("BAT", f"{int(bat)}%" if bat is not None else "n/a"),
    ]
    for i, (label, value) in enumerate(cards):
        x = 24 + (i % 2) * 220
        y = 160 + (i // 2) * 90
        d.rounded_rectangle((x, y, x + 200, y + 76), radius=12, fill=CARD)
        d.text((x + 16, y + 12), label, font=_font(14), fill=DIM)
        d.text((x + 16, y + 36), value, font=_font(22, True), fill=ACCENT)

    m = _music(state)
    if m.get("available"):
        d.text((24, 330), f"♪ {m.get('title')}", font=_font(14), fill=DIM)


DRAWERS = {
    "neon": draw_neon,
    "flip": draw_flip,
    "dot": draw_dot,
    "music": draw_music,
    "music-minimal": draw_music_minimal,
    "stock": draw_stock,
    "perf": draw_perf,
    "desk": draw_desk,
}


def render_theme_jpeg(theme_id: str, state: dict | None = None, *, quality: int = 72, limit: int = 30000) -> bytes:
    """Render one full-screen theme to baseline JPEG bytes (<= limit when possible)."""
    state = state or {}
    tid = theme_id if theme_id in THEMES else "neon"
    img = Image.new("RGB", (W, H), BG)
    drawer = DRAWERS.get(tid, draw_neon)
    drawer(img, state)

    q = max(20, min(95, int(quality)))
    data = b""
    while q >= 20:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q, optimize=True, progressive=False, subsampling=2)
        data = buf.getvalue()
        if len(data) <= limit or q <= 20:
            break
        q -= 5
    return data
