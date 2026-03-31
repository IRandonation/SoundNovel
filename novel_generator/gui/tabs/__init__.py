"""Tab modules for GUI application."""

from .config_tab import render as render_config_tab
from .generation_tab import render as render_generation_tab
from .outline_tab import render as render_outline_tab
from .expand_tab import render as render_expand_tab
from .review_tab import render as render_review_tab

__all__ = [
    "render_config_tab",
    "render_generation_tab",
    "render_outline_tab",
    "render_expand_tab",
    "render_review_tab",
]