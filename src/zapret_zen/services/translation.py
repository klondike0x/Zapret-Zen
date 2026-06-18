from __future__ import annotations

import json
from pathlib import Path

_current_language: str = "en"
_translations: dict[str, str] = {}


def _load_translations(lang: str) -> None:
    global _translations
    p = Path(__file__).resolve().parent.parent / "translations" / f"{lang}.json"
    try:
        _translations = json.loads(p.read_text("utf-8"))
    except Exception:
        _translations = {}


def set_language(lang: str) -> None:
    global _current_language
    if lang != _current_language:
        _current_language = lang
        _load_translations(lang)


def current_language() -> str:
    return _current_language


def t(key: str) -> str:
    return _translations.get(key, key)
