from __future__ import annotations

import math

from PySide6.QtCore import (
    QEasingCurve,
    Property,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    QSizeF,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QFrame, QWidget

from zapret_zen.ui.theme import is_light_theme

try:
    from PySide6.QtGui import QPaintEvent
except ImportError:
    from PySide6.QtCore import QEvent as QPaintEvent


class BaseServiceCard(QFrame):
    """Shared logic for ServiceCardFrame and ServiceCategoryCard."""

    def __init__(self, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self._selected = False
        self._theme = "dark"
        self._visual_scope = "main"
        self._burst_progress = 0.0
        self._press_progress = 0.0
        self._burst_anim: QPropertyAnimation | None = None
        self._press_anim: QPropertyAnimation | None = None
        self.setStyleSheet("background: transparent;")

    def _card_accent(self) -> QColor:
        raise NotImplementedError

    def _burst_origin_widget(self) -> QFrame:
        raise NotImplementedError

    def _compose_slot_pixmap(self, pixmap, slot_size: QSize, fill_ratio: float):
        from PySide6.QtGui import QPixmap as QPix
        if pixmap.isNull() or not slot_size.isValid():
            return pixmap
        dpr = max(1.0, float(pixmap.devicePixelRatio()))
        logical_width = float(slot_size.width())
        logical_height = float(slot_size.height())
        physical_width = max(1, int(round(logical_width * dpr)))
        physical_height = max(1, int(round(logical_height * dpr)))
        canvas = QPix(physical_width, physical_height)
        canvas.fill(Qt.GlobalColor.transparent)
        canvas.setDevicePixelRatio(dpr)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if hasattr(QPainter.RenderHint, "LosslessImageRendering"):
            painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
        source_size = pixmap.deviceIndependentSize() if hasattr(pixmap, "deviceIndependentSize") else QSizeF(
            float(pixmap.width()) / max(1.0, float(pixmap.devicePixelRatio())),
            float(pixmap.height()) / max(1.0, float(pixmap.devicePixelRatio())),
        )
        target_width = float(source_size.width())
        target_height = float(source_size.height())
        max_box = min(logical_width, logical_height) * max(0.1, min(1.0, float(fill_ratio)))
        if target_width > 0.0 and target_height > 0.0:
            scale = min(max_box / target_width, max_box / target_height, 1.0)
            target_width *= scale
            target_height *= scale
        painter.drawPixmap(
            QRectF((logical_width - target_width) / 2.0, (logical_height - target_height) / 2.0, target_width, target_height),
            pixmap,
            QRectF(0, 0, pixmap.width(), pixmap.height()),
        )
        painter.end()
        return canvas

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        shrink = 1.8 * self._press_progress
        glow_pad = 6.0 if self._visual_scope == "onboarding" else 0.0
        rect = QRectF(self.rect()).adjusted(0.5 + glow_pad + shrink, 0.5 + glow_pad + shrink, -0.5 - glow_pad - shrink, -0.5 - glow_pad - shrink)
        card_radius = 12.0
        accent = self._card_accent()
        light = is_light_theme(self._theme)
        base_fill = QColor("#ffffff") if light else QColor("#141922" if self._theme == "night" else "#171b20")
        if self._theme == "oled" and not self._visual_scope == "onboarding":
            base_fill = QColor("#111418")
        fill = QColor(base_fill)
        border = QColor("#d9e3f1" if light else "#252d38")
        if self._selected and self._visual_scope == "onboarding":
            fill = QColor(base_fill.lighter(102 if light else 106))
            border = QColor(accent)
            border.setAlpha(112 if light else 96)
        elif self._selected:
            fill = QColor(base_fill.lighter(102 if light else 106))
            border = QColor(accent)
            border.setAlpha(112 if light else 96)
        if self._selected and self._visual_scope == "onboarding":
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            glow_spread = 4.0
            outer_radius = card_radius + glow_spread * 1.35
            outer_glow_rect = rect.adjusted(-glow_spread, -glow_spread, glow_spread, glow_spread)
            glow = QRadialGradient(
                rect.center(),
                max(outer_glow_rect.width(), outer_glow_rect.height()) * 0.86,
            )
            glow_color = QColor(accent)
            glow_color.setAlpha(36 if light else 48)
            glow.setColorAt(0.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), max(12, glow_color.alpha() // 3)))
            glow.setColorAt(0.50, glow_color)
            glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
            painter.setBrush(glow)
            painter.drawRoundedRect(outer_glow_rect, outer_radius, outer_radius)
            painter.restore()
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, card_radius, card_radius)

        glow = QRadialGradient(rect.left() + 40, rect.top() + 30, max(rect.width(), rect.height()) * 0.72)
        glow_color = QColor(accent)
        glow_color.setAlpha(18 if self._selected else 0)
        glow.setColorAt(0.0, glow_color)
        glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawRoundedRect(rect, card_radius, card_radius)
        if self._burst_progress > 0.0:
            self._paint_burst(painter, accent)

    def _paint_burst(self, painter: QPainter, accent: QColor) -> None:
        progress = max(0.0, min(1.0, self._burst_progress))
        opacity = int(145 * (1.0 - progress))
        if opacity <= 0:
            return
        origin = QPointF(30.0, 28.0)
        try:
            icon_center = self._burst_origin_widget().mapTo(self, self._burst_origin_widget().rect().center())
            origin = QPointF(float(icon_center.x()), float(icon_center.y()))
        except Exception:
            pass
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(7):
            angle = (-140 + index * 46) * math.pi / 180.0
            distance = 8.0 + 28.0 * progress
            radius = 2.8 - 1.1 * progress + (0.35 if index % 2 else 0.0)
            color = QColor(accent)
            color.setAlpha(max(0, opacity - index * 6))
            point = QPointF(
                origin.x() + math.cos(angle) * distance,
                origin.y() + math.sin(angle) * distance,
            )
            painter.setBrush(color)
            painter.drawEllipse(point, max(1.1, radius), max(1.1, radius))
        painter.restore()

    def _play_select_feedback(self) -> None:
        if self._press_anim is not None:
            self._press_anim.stop()
        press = QPropertyAnimation(self, b"pressProgress", self)
        press.setDuration(170)
        press.setStartValue(0.0)
        press.setKeyValueAt(0.45, 1.0)
        press.setEndValue(0.0)
        press.setEasingCurve(QEasingCurve.Type.OutCubic)
        press.start()
        self._press_anim = press

        if self._burst_anim is not None:
            self._burst_anim.stop()
        burst = QPropertyAnimation(self, b"burstProgress", self)
        burst.setDuration(420)
        burst.setStartValue(0.0)
        burst.setEndValue(1.0)
        burst.setEasingCurve(QEasingCurve.Type.OutCubic)
        burst.start()
        self._burst_anim = burst

    def _get_burst_progress(self) -> float:
        return self._burst_progress

    def _set_burst_progress(self, value: float) -> None:
        self._burst_progress = float(value)
        self.update()

    def _get_press_progress(self) -> float:
        return self._press_progress

    def _set_press_progress(self, value: float) -> None:
        self._press_progress = float(value)
        self.update()

    burstProgress = Property(float, _get_burst_progress, _set_burst_progress)
    pressProgress = Property(float, _get_press_progress, _set_press_progress)
