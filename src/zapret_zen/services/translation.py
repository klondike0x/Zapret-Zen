from __future__ import annotations

import json
import sys
from pathlib import Path

_current_language: str = "en"
_translations: dict[str, str] = {}


def _load_translations(lang: str) -> None:
    global _translations
    candidates = [
        Path(__file__).resolve().parent.parent / "translations" / f"{lang}.json",
        Path(sys.executable).resolve().parent / "_internal" / "zapret_zen" / "translations" / f"{lang}.json",
    ]
    for p in candidates:
        try:
            _translations = json.loads(p.read_text("utf-8"))
            return
        except Exception:
            continue
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
