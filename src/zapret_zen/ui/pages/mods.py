from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from urllib.request import urlopen

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from zapret_zen.ui.pages.base import BasePage, PageHost
from zapret_zen.ui.theme import is_light_theme


COLS = 3

MOD_CATALOG_URL = "https://raw.githubusercontent.com/peshk0v/Zapret-Hub-Zen-Mods/refs/heads/main/catalog.json"
MOD_CATALOG_INSTALL = "install_mod_from_catalog"
MOD_CATALOG_CHECK = "mods/catalog_installed"


class ModsPage(BasePage):
    def __init__(self, host: PageHost, parent: QWidget | None = None) -> None:
        super().__init__(host, parent)
        self.setProperty("class", "pageRoot")

        self._title_label: QLabel | None = None
        self._subtitle_label: QLabel | None = None
        self._add_btn: QPushButton | None = None
        self._catalog_btn: QPushButton | None = None
        self.summary_chip: QLabel | None = None
        self.enabled_chip: QLabel | None = None
        self.import_hint: QLabel | None = None
        self.scroll: QScrollArea | None = None
        self.canvas: QWidget | None = None
        self.cards_layout: QVBoxLayout | None = None
        self._catalog_canvas: QWidget | None = None
        self._catalog_layout: QGridLayout | None = None
        self._catalog_scroll: QScrollArea | None = None
        self._catalog_data: list[dict[str, Any]] = []
        self._catalog_loaded = False
        self._catalog_installed_ids: set[str] = set()
        self._catalog_installed_versions: dict[str, str] = {}
        self._catalog_installing: set[str] = set()

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

        self._catalog_btn = QPushButton(self._t("Каталог", "Catalog"))
        self._catalog_btn.setProperty("class", "primary")
        self._catalog_btn.setMinimumHeight(38)
        self._catalog_btn.clicked.connect(self._toggle_catalog)
        self._attach_button_animations(self._catalog_btn)
        hero_top.addWidget(self._catalog_btn)
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

        self._catalog_scroll = QScrollArea()
        self._catalog_scroll.setObjectName("ModsCatalogScroll")
        self._catalog_scroll.setWidgetResizable(True)
        self._catalog_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._catalog_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._catalog_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._catalog_canvas = QWidget()
        self._catalog_canvas.setObjectName("ModsCatalogCanvas")
        self._catalog_canvas.setProperty("class", "pageCanvas")
        self._catalog_layout = QGridLayout(self._catalog_canvas)
        self._catalog_layout.setContentsMargins(1, 0, 1, 12)
        self._catalog_layout.setSpacing(12)
        for c in range(COLS):
            self._catalog_layout.setColumnStretch(c, 1)
        self._catalog_scroll.setWidget(self._catalog_canvas)
        self._catalog_scroll.hide()
        self._register_scroll_fade(self._catalog_scroll)
        self._register_smooth_scroll(self._catalog_scroll)
        root.addWidget(self._catalog_scroll, 1)

    def refresh_mods(self, payload: dict[str, Any]) -> None:
        if self._catalog_loaded:
            self._sync_installed_state()
            if self._catalog_scroll is not None and self._catalog_scroll.isVisible():
                self._render_catalog()

    def _load_catalog(self) -> None:
        def _on_data(data: list[dict[str, Any]]) -> None:
            self._catalog_data = data
            self._catalog_loaded = True
            self._catalog_installing.clear()
            self._sync_installed_state()
            if self._catalog_scroll is not None and self._catalog_scroll.isVisible():
                self._render_catalog()

        local_path = Path.home() / "Documents" / "Zapret-Hub-Zen-Mods" / "catalog.json"
        if local_path.is_file():
            try:
                data: list[dict[str, Any]] = json.loads(local_path.read_bytes())
                _on_data(data)
            except Exception:
                import traceback
                traceback.print_exc()

        def _fetch():
            try:
                resp = urlopen(MOD_CATALOG_URL, timeout=15)
                data: list[dict[str, Any]] = json.loads(resp.read().decode("utf-8"))
                QTimer.singleShot(0, lambda: _on_data(data))
            except Exception:
                import traceback
                traceback.print_exc()

        threading.Thread(target=_fetch, daemon=True).start()

    def _sync_installed_state(self) -> None:
        base = Path(self.context.paths.mods_dir)
        self._catalog_installed_ids.clear()
        self._catalog_installed_versions.clear()
        for entry in self._catalog_data:
            tag = str(entry.get("Tag", ""))
            ver = str(entry.get("Version", ""))
            folder = base / tag
            if folder.is_dir():
                self._catalog_installed_ids.add(tag)
                self._catalog_installed_versions[tag] = ver

    def _render_catalog(self) -> None:
        if self._catalog_layout is None or not self._catalog_data:
            return
        self._clear_layout(self._catalog_layout)
        try:
            for idx, entry in enumerate(self._catalog_data):
                row = idx // COLS
                col = idx % COLS
                card = self._build_catalog_card(entry)
                self._catalog_layout.addWidget(card, row, col)
        except Exception:
            import traceback
            traceback.print_exc()

    def _build_catalog_card(self, entry: dict[str, Any]) -> QFrame:
        title = str(entry.get("Title", ""))
        description = str(entry.get("Description", ""))
        author = str(entry.get("Author", ""))
        tag = str(entry.get("Tag", ""))
        version = str(entry.get("Version", ""))

        card = QFrame()
        card.setProperty("class", "modCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)

        header_family = getattr(self._host, "_headers_font_family", "Headers")
        theme = self.context.settings.get().theme
        title_color = "#f5f7fc" if not is_light_theme(theme) else "#111827"

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-family: '{header_family}'; font-size: 16pt; "
            f"font-weight: 400; color: {title_color};"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)
        meta_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        author_lbl = QLabel(author)
        author_lbl.setProperty("class", "modMeta")
        meta_row.addWidget(author_lbl)

        version_lbl = QLabel(f"v{version}")
        version_lbl.setProperty("class", "modMeta")
        meta_row.addWidget(version_lbl)
        layout.addLayout(meta_row)

        desc_lbl = QLabel(description)
        desc_lbl.setProperty("class", "modBody")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        layout.addStretch(1)

        btn = QPushButton()
        if tag in self._catalog_installing:
            btn.setText(self._t("Установка...", "Installing..."))
            btn.setEnabled(False)
            btn.setMinimumHeight(34)
            btn.setStyleSheet(
                "QPushButton {"
                "background: transparent;"
                "border: 1px solid rgba(128, 128, 128, 120);"
                "border-radius: 8px;"
                "padding: 6px 16px;"
                "color: rgba(128, 128, 128, 200);"
                "font-weight: 600;"
                "}"
            )
        elif tag in self._catalog_installed_ids:
            btn.setText(self._t("Установлено", "Installed"))
            btn.setEnabled(False)
            btn.setMinimumHeight(34)
            btn.setStyleSheet(
                "QPushButton {"
                "background: transparent;"
                "border: 1px solid rgba(128, 128, 128, 120);"
                "border-radius: 8px;"
                "padding: 6px 16px;"
                "color: rgba(128, 128, 128, 200);"
                "font-weight: 600;"
                "}"
            )
        else:
            btn.setText(self._t("Установить", "Install"))
            btn.clicked.connect(lambda _=False, t=tag, v=version: self._catalog_install(t, v))
        btn.setProperty("class", "primary")
        self._attach_button_animations(btn)
        layout.addWidget(btn)

        return card

    def _catalog_install(self, tag: str, version: str) -> None:
        self._submit_backend_task(
            MOD_CATALOG_INSTALL,
            {"tag": tag, "version": version},
        )
        self._catalog_installing.add(tag)
        self._render_catalog()
        QTimer.singleShot(1000, lambda: self._check_install_result(tag, version, retries=30))

    def _check_install_result(self, tag: str, version: str, retries: int = 30) -> None:
        folder = Path(self.context.paths.mods_dir) / tag
        if folder.is_dir():
            self._catalog_installing.discard(tag)
            self._catalog_installed_ids.add(tag)
            self._catalog_installed_versions[tag] = version
            if self._catalog_scroll is not None and self._catalog_scroll.isVisible():
                self._render_catalog()
            try:
                self._host._mark_dirty("mods")
            except Exception:
                pass
        elif retries > 0:
            if self._catalog_scroll is not None and not self._catalog_scroll.isVisible():
                return
            QTimer.singleShot(1000, lambda: self._check_install_result(tag, version, retries - 1))

    def _show_local(self) -> None:
        self._catalog_scroll.hide()
        self.scroll.show()
        if self._catalog_btn is not None:
            self._catalog_btn.setText(self._t("Каталог", "Catalog"))

    def _show_catalog(self) -> None:
        self.scroll.hide()
        self._catalog_scroll.show()
        if self._catalog_btn is not None:
            self._catalog_btn.setText(self._t("Локальные", "Local"))
        if not self._catalog_loaded:
            self._load_catalog()
        else:
            self._sync_installed_state()
            self._render_catalog()

    def _toggle_catalog(self) -> None:
        if self._catalog_scroll is not None and self.scroll is not None:
            if self._catalog_scroll.isVisible():
                self._show_local()
            else:
                self._show_catalog()

    @staticmethod
    def _clear_layout(layout: QGridLayout) -> None:
        for _ in range(layout.count()):
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
