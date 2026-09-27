from __future__ import annotations

from pathlib import Path

import pygame

FONT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"

REGULAR_PATH = FONT_DIR / "NotoSansJP-Regular.ttf"
BOLD_PATH = FONT_DIR / "NotoSansJP-Bold.ttf"

_cache: dict[tuple[int, bool], pygame.font.Font] = {}


class FontError(RuntimeError):
    pass


def get(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _cache:
        path = BOLD_PATH if bold else REGULAR_PATH
        if not path.exists():
            raise FontError(
                f"フォントが見つかりません: {path}\n"
                "assets/fonts/ に NotoSansJP-Regular.ttf と NotoSansJP-Bold.ttf を置いてください。"
            )
        _cache[key] = pygame.font.Font(str(path), size)
    return _cache[key]


def clear_cache() -> None:
    _cache.clear()
