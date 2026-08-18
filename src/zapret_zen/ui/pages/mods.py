from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from zapret_zen.ui.pages.base import BasePage, PageHost


class ModsPage(BasePage):
    def __init__(self, host: PageHost, parent: QWidget | None = None) -> None:
        super().__init__(host, parent)
        self.setProperty("class", "pageRoot")

        self._title_label: QLabel | None = None
        self._subtitle_label: QLabel | None = None
        self._add_btn: QPushButton | None = None
        self.summary_chip: QLabel | None = None
        self.enabled_chip: QLabel | None = None
        self.import_hint: QLabel | None = None
        self.scroll: QScrollArea | None = None
        self.canvas: QWidget | None = None
        self.cards_layout: QVBoxLayout | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(1, 0, 1, 0)
        root.setSpacing(12)

        hero, hero_layout = self._card()
        hero.setProperty("class", "modHero")
        hero_layout.setContentsMargins(14, 14, 14, 14)

        hero_top = QHBoxLayout()
        hero_top.setContentsMargins(0, 0, 0, 0)
        hero_top.setSpacing(10)

        title_wrap = QVBoxLayout()
        title_wrap.setContentsMargins(0, 0, 0, 0)
        title_wrap.setSpacing(4)
        label = QLabel(self._t("Модификации", "Mods"))
        label.setProperty("class", "title")
        self._title_label = label
        subtitle = QLabel(
            self._t(
                "Здесь можно аккуратно подключать свои сборки, не ломая базовую конфигурацию.",
                "This is where you can attach your own packs without touching the base configuration.",
            )
        )
        subtitle.setProperty("class", "muted")
        subtitle.setWordWrap(True)
        self._subtitle_label = subtitle
        title_wrap.addWidget(label)
        title_wrap.addWidget(subtitle)
        hero_top.addLayout(title_wrap, 1)

        self._add_btn = QPushButton(self._t("Добавить", "Add"))
        self._add_btn.setProperty("class", "primary")
        self._add_btn.setMinimumHeight(38)
        self._attach_button_animations(self._add_btn)
        hero_top.addWidget(self._add_btn)
        hero_layout.addLayout(hero_top)

        summary_row = QHBoxLayout()
        summary_row.setContentsMargins(0, 0, 0, 0)
        summary_row.setSpacing(10)

        self.summary_chip = QLabel()
        self.summary_chip.setObjectName("ModsSummaryChip")
        self.summary_chip.setProperty("class", "modMeta")
        summary_row.addWidget(self.summary_chip)

        self.enabled_chip = QLabel()
        self.enabled_chip.setObjectName("ModsEnabledChip")
        self.enabled_chip.setProperty("class", "modMeta")
        summary_row.addWidget(self.enabled_chip)

        self.import_hint = QLabel(
            self._t(
                "Можно добавить папку, ZIP, отдельные файлы или целый GitHub-репозиторий.",
                "You can add a folder, ZIP, selected files, or a full GitHub repository.",
            )
        )
        self.import_hint.setProperty("class", "modHint")
        self.import_hint.setWordWrap(True)
        summary_row.addWidget(self.import_hint, 1)
        hero_layout.addLayout(summary_row)
        root.addWidget(hero)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ModsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.canvas = QWidget()
        self.canvas.setObjectName("ModsCanvas")
        self.canvas.setProperty("class", "pageCanvas")
        self.cards_layout = QVBoxLayout(self.canvas)
        self.cards_layout.setContentsMargins(1, 0, 1, 12)
        self.cards_layout.setSpacing(12)
        self.scroll.setWidget(self.canvas)
        self._register_scroll_fade(self.scroll)
        self._register_smooth_scroll(self.scroll)
        root.addWidget(self.scroll, 1)

    def refresh_mods(self, payload: dict[str, Any]) -> None:
        pass
