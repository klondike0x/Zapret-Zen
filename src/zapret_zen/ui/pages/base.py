from __future__ import annotations

from typing import Protocol, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from zapret_zen.bootstrap import ApplicationContext


class PageHost(Protocol):
    """Protocol that MainWindow implements — pages use this to access shared state."""

    context: ApplicationContext

    def _t(self, ru: str, en: str) -> str: ...
    def _card(self) -> tuple[QFrame, QVBoxLayout]: ...
    def _icon(self, name: str): ...
    def _attach_button_animations(self, btn: QWidget) -> None: ...
    def _register_scroll_fade(self, scroll: QScrollArea, **kwargs: Any) -> None: ...
    def _register_smooth_scroll(self, scroll: QScrollArea, **kwargs: Any) -> None: ...
    def _submit_backend_task(self, action: str, payload: dict[str, Any] | None = None, *, action_id: str = "") -> str: ...
    def _show_error(self, title: str, message: str) -> None: ...
    def _show_info(self, title: str, message: str) -> None: ...
    def _ask_yes_no(self, title: str, message: str) -> bool: ...


class BasePage(QFrame):
    """Base class for extracted pages. Holds a reference to the host for shared operations."""

    def __init__(self, host: PageHost, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._host = host

    @property
    def context(self) -> ApplicationContext:
        return self._host.context

    def _t(self, ru: str, en: str) -> str:
        return self._host._t(ru, en)

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        return self._host._card()

    def _icon(self, name: str):
        return self._host._icon(name)

    def _attach_button_animations(self, btn: QWidget) -> None:
        self._host._attach_button_animations(btn)

    def _register_scroll_fade(self, scroll: QScrollArea, **kwargs: Any) -> None:
        self._host._register_scroll_fade(scroll, **kwargs)

    def _register_smooth_scroll(self, scroll: QScrollArea, **kwargs: Any) -> None:
        self._host._register_smooth_scroll(scroll, **kwargs)
