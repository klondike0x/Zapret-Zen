from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from zapret_zen.ui.pages.base import BasePage, PageHost


class ServicesPage(BasePage):
    """Services page — choose service categories for bypass rules."""

    def __init__(self, host: PageHost, parent: QWidget | None = None) -> None:
        super().__init__(host, parent)
        self.setProperty("class", "pageRoot")

        self._title_label: QLabel | None = None
        self._subtitle_label: QLabel | None = None
        self._hint_label: QLabel | None = None
        self._count_label: QLabel | None = None
        self._scroll: QScrollArea | None = None
        self._category_cards: list = []

        root = QVBoxLayout(self)
        root.setContentsMargins(1, 0, 1, 0)
        root.setSpacing(12)

        hero, hero_layout = self._card()
        hero_layout.setContentsMargins(16, 16, 16, 16)
        hero_layout.setSpacing(10)

        title = QLabel(self._t("Выберите сервисы", "Choose services"))
        title.setProperty("class", "title")
        self._title_label = title
        hero_layout.addWidget(title)

        subtitle = QLabel(
            self._t(
                "Выберите категории сервисов, которыми вы пользуетесь.",
                "Choose the service categories you actually use.",
            )
        )
        subtitle.setProperty("class", "muted")
        subtitle.setWordWrap(True)
        self._subtitle_label = subtitle
        hero_layout.addWidget(subtitle)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 2, 0, 0)
        meta_row.setSpacing(10)
        count_label = QLabel()
        count_label.setObjectName("ServicesCountChip")
        count_label.setProperty("class", "modMeta")
        self._count_label = count_label
        meta_row.addWidget(count_label, 0, Qt.AlignmentFlag.AlignLeft)

        hint = QLabel(
            self._t(
                "Приложение автоматически настраивает свою работу для обеспечения доступа к выбранным сервисам.",
                "The app automatically adjusts its behavior to provide access to the selected services.",
            )
        )
        hint.setProperty("class", "muted")
        hint.setWordWrap(True)
        self._hint_label = hint
        meta_row.addWidget(hint, 1)
        hero_layout.addLayout(meta_row)
        root.addWidget(hero)

        scroll = QScrollArea()
        scroll.setObjectName("ServicesScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        canvas = QWidget()
        canvas.setObjectName("ServicesCanvas")
        canvas.setProperty("class", "pageCanvas")
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(0, 14, 0, 14)
        canvas_layout.setSpacing(0)
        cards_layout = QHBoxLayout()
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)
        canvas_layout.addLayout(cards_layout)
        scroll.setWidget(canvas)
        self._register_scroll_fade(scroll)
        self._register_smooth_scroll(scroll, duration=250, angle_divisor=3.0)
        self._scroll = scroll
        root.addWidget(scroll, 1)
