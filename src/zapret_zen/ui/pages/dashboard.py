from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from zapret_zen.ui.pages.base import BasePage, PageHost


class DashboardPage(BasePage):
    """Dashboard page — power button, status badges, quick access."""

    def __init__(self, host: PageHost, parent: QWidget | None = None) -> None:
        super().__init__(host, parent)
        self.setProperty("class", "pageRoot")

        self._title_label: QLabel | None = None
        self._status_badges: dict[str, tuple[QFrame, QLabel, QLabel]] = {}
        self._power_block: QWidget | None = None
        self._power_stage: QWidget | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 12)
        root.setSpacing(4)

        top, top_layout = self._card()
        top_layout.setContentsMargins(14, 14, 14, 14)
        title = QLabel(self._t("Быстрый доступ", "Quick Access"))
        title.setObjectName("DashboardTitle")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        title.setContentsMargins(0, 0, 0, 0)
        title.setMaximumHeight(22)
        self._title_label = title
        top_layout.addWidget(title)

        top_layout.addStretch(1)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(10)
        for key, icon_name, title_text in [
            ("app", "status_ok.svg", self._t("Приложение", "App")),
            ("zapret", "status_warn.svg", "Zapret"),
            ("tg", "status_warn.svg", "TG Proxy"),
            ("mods", "status_mod.svg", "Mods"),
        ]:
            badge = self._build_status_badge(key, icon_name, title_text)
            badges_row.addWidget(badge)
        badges_row.setStretch(0, 1)
        badges_row.setStretch(1, 1)
        badges_row.setStretch(2, 1)
        badges_row.setStretch(3, 1)
        top_layout.addLayout(badges_row)
        root.addWidget(top)

    def _build_status_badge(self, key: str, icon_name: str, title: str) -> QWidget:
        card, layout = self._card()
        card.setMinimumHeight(96)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        head = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(self._icon(icon_name).pixmap(18, 18))
        text_label = QLabel(title)
        text_label.setProperty("class", "muted")
        head.addWidget(icon_label)
        head.addWidget(text_label)
        head.addStretch(1)
        layout.addLayout(head)
        value_label = QLabel("")
        value_label.setProperty("class", "title")
        value_label.setWordWrap(True)
        layout.addWidget(value_label)
        self._status_badges[key] = (card, icon_label, value_label)
        return card

    def set_badge(self, key: str, text: str, icon_name: str | None = None) -> None:
        badge = self._status_badges.get(key)
        if badge is None:
            return
        _, icon_label, value_label = badge
        value_label.setText(text)
        if icon_name:
            icon_label.setPixmap(self._icon(icon_name).pixmap(18, 18))

    def set_badge_title(self, key: str, title: str) -> None:
        badge = self._status_badges.get(key)
        if badge is None:
            return
        card, _, _ = badge
        child_labels = card.findChildren(QLabel)
        if len(child_labels) >= 2:
            child_labels[1].setText(title)
