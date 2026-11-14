"""KSS-inspired full-screen themes for Neos75 480×360.

These are whole-screen compositions (not widget grids). Host-rendered to
baseline JPEG and pushed over the existing USB wallpaper channel.
"""

from .catalog import THEMES, list_themes, resolve_theme_id
from .render_theme import render_theme_jpeg

__all__ = ["THEMES", "list_themes", "resolve_theme_id", "render_theme_jpeg"]
