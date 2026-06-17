from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from zapret_zen.ui.pages.base import BasePage, PageHost


class LogsPage(BasePage):
    """Logs page — displays application and component logs."""

    def __init__(self, host: PageHost, parent: QWidget | None = None) -> None:
        super().__init__(host, parent)
        self.setProperty("class", "pageRoot")
        self._current_log_source = "all"
        self._pending_logs_payload: dict[str, object] | None = None
        self._logs_force_scroll_bottom = True

        root = QVBoxLayout(self)
        root.setContentsMargins(1, 0, 1, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        label = QLabel(self._t("Логи", "Logs"))
        label.setProperty("class", "title")
        self._title_label = label
        top.addWidget(label)

        self._source_combo = QComboBox()
        self._source_combo.setObjectName("LogsSourceCombo")
        self._source_combo.setView(QListView())
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        self._rebuild_source_combo()
        top.addWidget(self._source_combo)
        top.addStretch(1)
        root.addLayout(top)

        self._logs_text = QTextEdit()
        self._logs_text.setReadOnly(True)
        self._logs_text.selectionChanged.connect(self._on_selection_changed)
        self._register_scroll_fade(self._logs_text)
        self._register_smooth_scroll(self._logs_text)

        self._logs_stack = QStackedWidget()
        logs_loading = QLabel(self._t("Загрузка логов...", "Loading logs..."))
        logs_loading.setProperty("class", "muted")
        logs_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label = logs_loading
        self._logs_stack.addWidget(logs_loading)
        self._logs_stack.addWidget(self._logs_text)
        root.addWidget(self._logs_stack)

    @property
    def logs_text(self) -> QTextEdit:
        return self._logs_text

    @property
    def source_combo(self) -> QComboBox:
        return self._source_combo

    @property
    def current_log_source(self) -> str:
        return self._current_log_source

    def _rebuild_source_combo(self) -> None:
        sources = [
            ("all", self._t("Все", "All")),
            ("app", "App"),
            ("zapret", "Zapret"),
            ("tg", "TG Proxy"),
        ]
        self._source_combo.blockSignals(True)
        self._source_combo.clear()
        for key, label in sources:
            self._source_combo.addItem(label, key)
        self._source_combo.blockSignals(False)

    def _on_source_changed(self, _index: int) -> None:
        data = self._source_combo.currentData()
        if data:
            self._current_log_source = str(data)

    def _on_selection_changed(self) -> None:
        cursor = self._logs_text.textCursor()
        if not cursor.hasSelection() and self._pending_logs_payload is not None:
            payload = self._pending_logs_payload
            self._pending_logs_payload = None
            self._apply_payload(payload)

    def _apply_payload(self, payload: dict[str, object]) -> None:
        lines = payload.get("lines", []) if isinstance(payload, dict) else []
        if isinstance(lines, list):
            text = "\n".join(str(line) for line in lines)
        else:
            text = str(lines) if lines else ""
        self._logs_text.setPlainText(text)
        if self._logs_force_scroll_bottom:
            sb = self._logs_text.verticalScrollBar()
            if sb is not None:
                sb.setValue(sb.maximum())

    def refresh(self, payload: object | None = None) -> None:
        if payload is None:
            return
        if isinstance(payload, dict):
            source = str(payload.get("source", self._current_log_source))
            if source:
                self._current_log_source = source
        cursor = self._logs_text.textCursor()
        if cursor.hasSelection():
            self._pending_logs_payload = payload
            return
        self._apply_payload(payload)

    def set_live_enabled(self, enabled: bool) -> None:
        pass

    def view_update_locked(self) -> bool:
        cursor = self._logs_text.textCursor()
        return cursor.hasSelection()
