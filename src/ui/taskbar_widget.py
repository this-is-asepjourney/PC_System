import os
import sys
import json
import math
import html
import time
import subprocess
from collections import deque
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QMenu, QApplication
)
from PySide6.QtCore import (
    Qt, QPoint, QPointF, QRectF, QTimer, Signal, QObject, QEvent,
    QElapsedTimer, QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient, QPen, QFont, QGuiApplication
)
from src.core.events import event_bus

if getattr(sys, 'frozen', False):
    _APP_ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    _APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE_PATH = os.path.join(_APP_ROOT, "data", "taskbar_config.json")


# ---------------------------------------------------------------------------
# Palette (Catppuccin Mocha inspired) & helpers
# ---------------------------------------------------------------------------
C_WHITE = "#ffffff"
C_TEXT = "#cdd6f4"
C_SUBTEXT = "#a6adc8"
C_OVERLAY = "#7f849c"
C_GREEN = "#a6e3a1"
C_YELLOW = "#f9e2af"
C_RED = "#f38ba8"
C_PEACH = "#fab387"
C_SKY = "#74c7ec"
C_BLUE = "#89b4fa"
C_NET_DL = "#38bdf8"
C_NET_UL = "#c084fc"

TOOLTIP_QSS = """
QToolTip {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 6px 8px;
    font-family: 'Segoe UI';
    font-size: 11px;
}
"""


def _qc(hex_or_color, alpha: int = None) -> QColor:
    c = QColor(hex_or_color)
    if alpha is not None:
        c.setAlpha(max(0, min(255, int(alpha))))
    return c


def _mix(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


def _status_color(value: float, warn: float, crit: float, base: QColor) -> QColor:
    """Smoothly blends accent -> yellow -> red as the load approaches thresholds."""
    yellow, red = QColor(C_YELLOW), QColor(C_RED)
    if value < warn - 10:
        return QColor(base)
    if value < warn:
        return _mix(base, yellow, (value - (warn - 10)) / 10.0)
    if value < crit - 5:
        return yellow
    if value < crit:
        return _mix(yellow, red, (value - (crit - 5)) / 5.0)
    return red


def _temp_color(t: float) -> QColor:
    green, yellow, red = QColor(C_GREEN), QColor(C_YELLOW), QColor(C_RED)
    if t < 50:
        return green
    if t < 60:
        return _mix(green, yellow, (t - 50) / 10.0)
    if t < 75:
        return yellow
    if t < 85:
        return _mix(yellow, red, (t - 75) / 10.0)
    return red


def _format_speed(b_s: float) -> str:
    if b_s < 1024:
        return f"{b_s:.0f} B/s"
    elif b_s < 1024 * 1024:
        return f"{b_s / 1024:.0f} KB/s"
    elif b_s < 1024 * 1024 * 1024:
        return f"{b_s / (1024 * 1024):.1f} MB/s"
    else:
        return f"{b_s / (1024 * 1024 * 1024):.2f} GB/s"


def _format_bytes(b: float) -> str:
    if b < 1024 ** 2:
        return f"{b / 1024:.0f} KB"
    if b < 1024 ** 3:
        return f"{b / 1024 ** 2:.0f} MB"
    if b < 1024 ** 4:
        return f"{b / 1024 ** 3:.1f} GB"
    return f"{b / 1024 ** 4:.2f} TB"


def _make_font(px: int, weight: QFont.Weight) -> QFont:
    f = QFont()
    f.setFamilies(["Segoe UI Variable Small", "Segoe UI", "Arial"])
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


# ---------------------------------------------------------------------------
# On-demand animation clock
# ---------------------------------------------------------------------------
class AnimationClock(QObject):
    """
    Single shared timer that drives every animated cell.
    - Runs at ~25 FPS only while a value is tweening (~0.4s after each data update).
    - Drops to ~11 FPS when only slow 'breathing' pulses are active (critical states).
    - Fully stops when everything is settled -> zero idle CPU wakeups.
    """
    FAST_MS = 40
    SLOW_MS = 90

    MODE_IDLE = 0
    MODE_SLOW = 1
    MODE_FAST = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = True
        self._clients = []
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.CoarseTimer)
        self._timer.timeout.connect(self._tick)
        self._elapsed = QElapsedTimer()

    def register(self, client):
        self._clients.append(client)

    def wake(self):
        if not self.enabled:
            return
        if not self._timer.isActive():
            self._elapsed.start()
            self._timer.start(self.FAST_MS)
        elif self._timer.interval() != self.FAST_MS:
            self._timer.setInterval(self.FAST_MS)

    def stop(self):
        self._timer.stop()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if not enabled:
            self._timer.stop()
            for c in self._clients:
                c.advance(0.0, False)  # snap everything to final state
        else:
            self.wake()

    def _tick(self):
        dt = min(self._elapsed.restart() / 1000.0, 0.2)
        mode = self.MODE_IDLE
        for c in self._clients:
            if c.isVisible():
                mode = max(mode, c.advance(dt, True))

        if mode == self.MODE_IDLE:
            self._timer.stop()
        elif mode == self.MODE_SLOW and self._timer.interval() != self.SLOW_MS:
            self._timer.setInterval(self.SLOW_MS)
        elif mode == self.MODE_FAST and self._timer.interval() != self.FAST_MS:
            self._timer.setInterval(self.FAST_MS)


class AnimatedCell(QWidget):
    """Base for custom-painted cells driven by the AnimationClock."""
    def __init__(self, clock: AnimationClock, parent=None):
        super().__init__(parent)
        self._clock = clock
        clock.register(self)

    def _kick(self):
        self._clock.wake()

    def advance(self, dt: float, animate: bool) -> int:
        return AnimationClock.MODE_IDLE


def _ease_towards(current: float, target: float, dt: float, speed: float, snap: float) -> tuple[float, bool]:
    """Exponential smoothing. Returns (new_value, still_moving)."""
    diff = target - current
    if abs(diff) <= snap:
        return target, False
    return current + diff * (1.0 - math.exp(-dt * speed)), True


# ---------------------------------------------------------------------------
# Visual building blocks
# ---------------------------------------------------------------------------
class DragGrip(QWidget):
    """
    Ultra-compact vertical drag grip handle.
    Width: 6px. Fits seamlessly without consuming horizontal space.
    The pill is tinted with the overall system health colour (green / yellow / red).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(6)
        self.setFixedHeight(22)
        self._hovered = False
        self._locked = False
        self._status = QColor(C_GREEN)
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("Tahan & Geser untuk memindahkan\nKlik kanan untuk Opsi")

    def set_locked(self, locked: bool):
        self._locked = locked
        self.setCursor(Qt.ArrowCursor if locked else Qt.SizeAllCursor)
        self.update()

    def set_status_color(self, color: QColor):
        if color.rgb() != self._status.rgb():
            self._status = QColor(color)
            self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._locked:
            color = QColor(108, 112, 134, 90)
        elif self._hovered:
            color = _qc(C_BLUE, 230)
        else:
            color = _qc(self._status, 170)

        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        # Single rounded slim pill handle
        painter.drawRoundedRect(QRectF(1.5, 3, 3, 16), 1.5, 1.5)


class Divider(QWidget):
    """1px vertical divider that fades out at both ends."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(1)

    def paintEvent(self, event):
        p = QPainter(self)
        h = self.height()
        g = QLinearGradient(0, 3, 0, h - 3)
        g.setColorAt(0.0, QColor(255, 255, 255, 0))
        g.setColorAt(0.5, QColor(255, 255, 255, 34))
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(0, 3, 1, h - 6), g)


class GlassContainer(AnimatedCell):
    """
    Painted rounded 'glass' background. Replaces the stylesheet + QGraphicsDropShadowEffect
    combo (the drop shadow forced an offscreen re-render of the whole widget on every repaint).
    Animated: hover border glow and a slow red 'breathing' border during sustained critical load.
    """
    RADIUS = 7.0

    def __init__(self, clock: AnimationClock, parent=None):
        super().__init__(clock, parent)
        self._opacity = 0.92
        self._hover = 0.0
        self._hover_target = 0.0
        self._alert = False
        self._phase = 0.0

    def set_opacity(self, opacity: float):
        self._opacity = opacity
        self.update()

    def set_alert(self, alert: bool):
        if alert != self._alert:
            self._alert = alert
            self._phase = 0.0
            self.update()
            self._kick()

    def enterEvent(self, event):
        self._hover_target = 1.0
        if self._clock.enabled:
            self._kick()
        else:
            self._hover = 1.0
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_target = 0.0
        if self._clock.enabled:
            self._kick()
        else:
            self._hover = 0.0
            self.update()
        super().leaveEvent(event)

    def advance(self, dt, animate):
        if not animate:
            self._hover = self._hover_target
            self._phase = 0.0
            self.update()
            return AnimationClock.MODE_IDLE

        mode = AnimationClock.MODE_IDLE
        self._hover, moving = _ease_towards(self._hover, self._hover_target, dt, 12.0, 0.01)
        if moving:
            mode = AnimationClock.MODE_FAST
        if self._alert:
            self._phase = (self._phase + dt) % 2.4
            mode = max(mode, AnimationClock.MODE_SLOW)
        if mode or moving:
            self.update()
        return mode

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        a = int(self._opacity * 255)

        # Body gradient
        g = QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0.0, QColor(32, 32, 48, a))
        g.setColorAt(1.0, QColor(16, 16, 25, a))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, self.RADIUS, self.RADIUS)

        # Top inner highlight (glass edge)
        hl = QLinearGradient(r.left(), 0, r.right(), 0)
        hl.setColorAt(0.0, QColor(255, 255, 255, 0))
        hl.setColorAt(0.5, QColor(255, 255, 255, 38))
        hl.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(QPen(hl, 1.0))
        p.drawLine(QPointF(r.left() + 6, r.top() + 1), QPointF(r.right() - 6, r.top() + 1))

        # Border: neutral -> accent on hover -> red breathing on sustained alert
        border = _mix(QColor(255, 255, 255, 24), _qc(C_BLUE, 120), self._hover)
        if self._alert:
            pulse = 0.5 + 0.5 * math.sin(self._phase / 2.4 * 2 * math.pi)
            border = _mix(border, _qc(C_RED, 200), 0.35 + 0.45 * pulse)
        p.setPen(QPen(border, 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, self.RADIUS, self.RADIUS)


class MetricRow(AnimatedCell):
    """
    Single 15px line: [TAG] [animated value %] [temp badge]
    Background: scrolling mini sparkline of the last ~30 samples.
    Bottom: 2px load bar coloured by status (accent -> yellow -> red).
    Optional activity LED on the tag (used for disk I/O).
    """
    H = 15
    TAG_W = 22
    PAD = 3
    VAL_W = 28
    SUB_W = 21
    HISTORY = 30

    def __init__(self, clock, tag: str, accent: str, warn: float, crit: float, parent=None):
        super().__init__(clock, parent)
        self.tag = tag
        self.accent = QColor(accent)
        self.warn = warn
        self.crit = crit

        self.history = deque(maxlen=self.HISTORY)
        self.target = 0.0
        self._display = 0.0
        self._scroll = 0.0
        self._phase = 0.0
        self.has_data = False

        self._sub_text = ""
        self._sub_color = QColor(C_GREEN)
        self._show_sub = True

        self._has_led = False
        self._led = 0.0
        self._led_target = 0.0

        self._f_tag = _make_font(8, QFont.Weight.ExtraBold)
        self._f_val = _make_font(10, QFont.Weight.Bold)
        self._f_sub = _make_font(8, QFont.Weight.DemiBold)

        self.setFixedHeight(self.H)
        self._update_width()

    def _update_width(self):
        w = self.TAG_W + self.PAD + self.VAL_W
        if self._show_sub:
            w += self.PAD + self.SUB_W
        self.setFixedWidth(w)

    def set_show_sub(self, show: bool):
        if show != self._show_sub:
            self._show_sub = show
            self._update_width()
            self.update()

    def enable_activity_led(self):
        self._has_led = True

    def set_activity(self, level: float):
        self._led_target = max(0.0, min(1.0, level))
        if self._clock.enabled:
            self._kick()
        else:
            self._led = self._led_target
            self.update()

    def set_value(self, value: float, sub_text: str = "", sub_color: QColor = None):
        value = max(0.0, min(100.0, float(value)))
        self.history.append(value)
        self.target = value
        self._sub_text = sub_text
        if sub_color is not None:
            self._sub_color = QColor(sub_color)

        if not self.has_data:
            self._display = value
            self.has_data = True
        elif self._clock.enabled:
            if len(self.history) > 1:
                self._scroll = 1.0
            self._kick()
        else:
            self._display = value
        self.update()

    def advance(self, dt, animate):
        if not animate:
            self._display = self.target
            self._scroll = 0.0
            self._phase = 0.0
            self._led = self._led_target
            self.update()
            return AnimationClock.MODE_IDLE

        mode = AnimationClock.MODE_IDLE

        self._display, moving = _ease_towards(self._display, self.target, dt, 11.0, 0.4)
        if moving:
            mode = AnimationClock.MODE_FAST

        if self._scroll > 0.0:
            self._scroll = max(0.0, self._scroll - dt / 0.45)
            mode = AnimationClock.MODE_FAST

        if self._has_led:
            self._led, led_moving = _ease_towards(self._led, self._led_target, dt, 8.0, 0.01)
            if led_moving:
                mode = AnimationClock.MODE_FAST

        if self.target >= self.crit:
            self._phase = (self._phase + dt) % 2.0
            mode = max(mode, AnimationClock.MODE_SLOW)
        else:
            self._phase = 0.0

        self.update()
        return mode

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        gx = self.TAG_W + self.PAD
        gw = w - gx
        status = _status_color(self._display, self.warn, self.crit, self.accent)

        # 1. Sparkline (background)
        n = len(self.history)
        if n >= 2 and gw > 4:
            top, bottom = 1.5, h - 3.0
            step = gw / (self.HISTORY - 1)
            offset = self._scroll * step
            path = QPainterPath()
            first_x = last_x = 0.0
            for i, v in enumerate(self.history):
                x = w - (n - 1 - i) * step + offset
                y = bottom - (v / 100.0) * (bottom - top)
                if i == 0:
                    path.moveTo(x, y)
                    first_x = x
                else:
                    path.lineTo(x, y)
                last_x = x
            area = QPainterPath(path)
            area.lineTo(last_x, bottom)
            area.lineTo(first_x, bottom)
            area.closeSubpath()

            p.save()
            p.setClipRect(QRectF(gx, 0, gw, h))
            fill = QLinearGradient(0, top, 0, bottom)
            fill.setColorAt(0.0, _qc(status, 50))
            fill.setColorAt(1.0, _qc(status, 0))
            p.fillPath(area, fill)
            p.setPen(QPen(_qc(status, 80), 1.0))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
            p.restore()

        # 2. Load bar (bottom)
        p.setPen(Qt.NoPen)
        bar = QRectF(gx, h - 2.0, gw, 2.0)
        p.setBrush(QColor(255, 255, 255, 20))
        p.drawRoundedRect(bar, 1, 1)
        fill_w = gw * self._display / 100.0
        if fill_w > 0.5:
            bg = QLinearGradient(gx, 0, gx + gw, 0)
            bg.setColorAt(0.0, _qc(self.accent, 170))
            bg.setColorAt(1.0, _qc(status, 255))
            p.setBrush(bg)
            p.drawRoundedRect(QRectF(gx, h - 2.0, fill_w, 2.0), 1, 1)

        # 3. Tag pill
        tag_rect = QRectF(0, 1, self.TAG_W, h - 3)
        p.setBrush(_qc(self.accent, 40))
        p.drawRoundedRect(tag_rect, 2.5, 2.5)
        p.setFont(self._f_tag)
        p.setPen(self.accent)
        p.drawText(tag_rect, Qt.AlignCenter, self.tag)

        # Activity LED (disk I/O)
        if self._has_led and self._led > 0.03:
            p.setPen(Qt.NoPen)
            p.setBrush(_qc(C_WHITE, 70 + 185 * self._led))
            p.drawEllipse(QPointF(self.TAG_W - 2.0, 2.6), 1.6, 1.6)

        # 4. Critical breathing glow behind the value
        val_rect = QRectF(gx, 0, self.VAL_W, h - 2)
        if self.target >= self.crit:
            pulse = 0.5 + 0.5 * math.sin(self._phase * math.pi)
            p.setPen(Qt.NoPen)
            p.setBrush(_qc(C_RED, 22 + 48 * pulse))
            p.drawRoundedRect(val_rect.adjusted(1, 1, 1, 0), 2, 2)

        # 5. Value text
        txt = f"{self._display:.0f}%" if self.has_data else "--%"
        txt_color = QColor(C_WHITE) if self._display < self.warn - 5 else status
        p.setFont(self._f_val)
        p.setPen(txt_color)
        p.drawText(val_rect, Qt.AlignVCenter | Qt.AlignRight, txt)

        # 6. Temperature / sub badge
        if self._show_sub and self._sub_text:
            sx = gx + self.VAL_W + self.PAD
            sub_rect = QRectF(sx, 1.5, self.SUB_W, h - 4.5)
            p.setPen(Qt.NoPen)
            p.setBrush(_qc(self._sub_color, 34))
            p.drawRoundedRect(sub_rect, 2, 2)
            p.setFont(self._f_sub)
            p.setPen(self._sub_color)
            p.drawText(sub_rect, Qt.AlignCenter, self._sub_text)


class NetRow(AnimatedCell):
    """
    Single 15px network line: animated arrow + counting speed + auto-scaled sparkline.
    The arrow 'kicks' in its flow direction whenever traffic is detected.
    """
    H = 15
    W = 60
    ICON_W = 10
    HISTORY = 30
    ACTIVE_BPS = 2048

    def __init__(self, clock, direction: str, color: str, text_color: str, parent=None):
        super().__init__(clock, parent)
        self._dir = 1 if direction == "down" else -1
        self._glyph = "↓" if direction == "down" else "↑"
        self.color = QColor(color)
        self.text_color = QColor(text_color)

        self.history = deque(maxlen=self.HISTORY)
        self.target = 0.0
        self._display = 0.0
        self._scroll = 0.0
        self._nudge = 0.0
        self._has_data = False

        self._f_icon = _make_font(10, QFont.Weight.Black)
        self._f_val = _make_font(9, QFont.Weight.Bold)
        self.setFixedSize(self.W, self.H)

    def set_speed(self, bps: float):
        bps = max(0.0, float(bps))
        self.history.append(bps)
        self.target = bps
        if not self._has_data:
            self._display = bps
            self._has_data = True
        elif self._clock.enabled:
            if len(self.history) > 1:
                self._scroll = 1.0
            if bps > self.ACTIVE_BPS:
                self._nudge = 1.0
            self._kick()
        else:
            self._display = bps
        self.update()

    def advance(self, dt, animate):
        if not animate:
            self._display = self.target
            self._scroll = 0.0
            self._nudge = 0.0
            self.update()
            return AnimationClock.MODE_IDLE

        mode = AnimationClock.MODE_IDLE
        snap = max(1.0, self.target * 0.01)
        self._display, moving = _ease_towards(self._display, self.target, dt, 10.0, snap)
        if moving:
            mode = AnimationClock.MODE_FAST
        if self._scroll > 0.0:
            self._scroll = max(0.0, self._scroll - dt / 0.45)
            mode = AnimationClock.MODE_FAST
        if self._nudge > 0.0:
            self._nudge = max(0.0, self._nudge - dt / 0.35)
            mode = AnimationClock.MODE_FAST
        self.update()
        return mode

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        gx = self.ICON_W + 1
        gw = w - gx
        active = self.target > self.ACTIVE_BPS

        # Sparkline (auto-scaled, floor at 16 KB/s so idle noise stays flat)
        n = len(self.history)
        if n >= 2:
            scale = max(max(self.history), 16 * 1024)
            top, bottom = 2.0, h - 1.0
            step = gw / (self.HISTORY - 1)
            offset = self._scroll * step
            path = QPainterPath()
            first_x = last_x = 0.0
            for i, v in enumerate(self.history):
                x = w - (n - 1 - i) * step + offset
                y = bottom - (v / scale) * (bottom - top)
                if i == 0:
                    path.moveTo(x, y)
                    first_x = x
                else:
                    path.lineTo(x, y)
                last_x = x
            area = QPainterPath(path)
            area.lineTo(last_x, bottom)
            area.lineTo(first_x, bottom)
            area.closeSubpath()
            p.save()
            p.setClipRect(QRectF(gx, 0, gw, h))
            fill = QLinearGradient(0, top, 0, bottom)
            fill.setColorAt(0.0, _qc(self.color, 38))
            fill.setColorAt(1.0, _qc(self.color, 0))
            p.fillPath(area, fill)
            p.setPen(QPen(_qc(self.color, 60), 1.0))
            p.drawPath(path)
            p.restore()

        # Arrow icon (kicks in flow direction on traffic)
        dy = self._dir * 2.0 * math.sin(self._nudge * math.pi)
        p.setFont(self._f_icon)
        p.setPen(_qc(self.color, 255 if active else 115))
        p.drawText(QRectF(0, dy - 0.5, self.ICON_W, h), Qt.AlignCenter, self._glyph)

        # Speed text
        p.setFont(self._f_val)
        p.setPen(self.text_color if active else _qc(self.text_color, 170))
        p.drawText(QRectF(gx + 1, 0, gw - 1, h), Qt.AlignVCenter | Qt.AlignLeft, _format_speed(self._display))


class BatteryRow(AnimatedCell):
    """
    Compact single-line battery widget for row 2.
    Height: 15px. Painted battery glyph with animated fill level, charging bolt,
    and a slow red breathing pulse only when the battery is low and unplugged.
    """
    H = 15
    W = 46

    def __init__(self, clock, parent=None):
        super().__init__(clock, parent)
        self.setFixedSize(self.W, self.H)
        self.percent = 0.0
        self._display = 0.0
        self.plugged = False
        self.secsleft = None
        self._phase = 0.0
        self._has_data = False
        self._f_val = _make_font(9, QFont.Weight.Bold)

    def update_battery(self, battery_data: dict):
        if not battery_data:
            self.hide()
            return
        self.percent = float(battery_data.get("percent", 0) or 0)
        self.plugged = bool(battery_data.get("power_plugged", False))
        self.secsleft = battery_data.get("secsleft")

        if not self._has_data or not self._clock.enabled:
            self._display = self.percent
            self._has_data = True
        else:
            self._kick()
        if self._is_low():
            self._kick()
        self.update()
        if not self.isVisible():
            self.show()

    def _is_low(self) -> bool:
        return self._has_data and self.percent < 20 and not self.plugged

    def _color(self) -> QColor:
        if self.plugged:
            return QColor(C_GREEN)
        if self.percent < 20:
            return QColor(C_RED)
        if self.percent < 45:
            return QColor(C_YELLOW)
        return QColor(C_GREEN)

    def advance(self, dt, animate):
        if not animate:
            self._display = self.percent
            self._phase = 0.0
            self.update()
            return AnimationClock.MODE_IDLE
        mode = AnimationClock.MODE_IDLE
        self._display, moving = _ease_towards(self._display, self.percent, dt, 8.0, 0.4)
        if moving:
            mode = AnimationClock.MODE_FAST
        if self._is_low():
            self._phase = (self._phase + dt) % 2.0
            mode = max(mode, AnimationClock.MODE_SLOW)
        elif self._phase:
            self._phase = 0.0
        self.update()
        return mode

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        color = self._color()
        alpha_mul = 1.0
        if self._is_low():
            alpha_mul = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(self._phase * math.pi))

        # Battery body + nub
        body = QRectF(0.5, 3.5, 15, 8)
        p.setPen(QPen(_qc(color, 170 * alpha_mul), 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(body, 2, 2)
        p.setPen(Qt.NoPen)
        p.setBrush(_qc(color, 170 * alpha_mul))
        p.drawRoundedRect(QRectF(16.2, 5.8, 1.6, 3.4), 0.6, 0.6)

        # Fill level
        inner_w = 12.0 * max(0.0, min(100.0, self._display)) / 100.0
        if inner_w > 0.3:
            p.setBrush(_qc(color, 235 * alpha_mul))
            p.drawRoundedRect(QRectF(2.0, 5.0, inner_w, 5.0), 1, 1)

        # Charging bolt
        if self.plugged:
            bolt = QPainterPath()
            bolt.moveTo(9.0, 3.6)
            bolt.lineTo(5.6, 8.0)
            bolt.lineTo(7.8, 8.0)
            bolt.lineTo(6.9, 11.4)
            bolt.lineTo(10.4, 7.0)
            bolt.lineTo(8.2, 7.0)
            bolt.closeSubpath()
            p.setPen(QPen(QColor(20, 20, 30, 220), 0.8))
            p.setBrush(QColor(C_WHITE))
            p.drawPath(bolt)

        # Percentage text
        p.setFont(self._f_val)
        p.setPen(_qc(color, 255 * alpha_mul))
        p.drawText(QRectF(21, 0, self.W - 21, self.H), Qt.AlignVCenter | Qt.AlignLeft,
                   f"{self._display:.0f}%" if self._has_data else "--%")


class TaskbarBridge(QObject):
    cpu_updated = Signal(dict)
    memory_updated = Signal(dict)
    disk_updated = Signal(dict)
    network_updated = Signal(dict)
    hardware_updated = Signal(dict)
    process_updated = Signal(dict)


class TaskbarWidget(QWidget):
    """
    Next-Generation Taskbar Mode Monitor.
    Defaults to Dual-Row layout (height: 36px, width: ~250px) which fits seamlessly
    inside the Windows 11 taskbar without covering pinned app icons.
    Engineered for ultra-low CPU and memory footprint:
      - every cell is custom-painted (no stylesheet re-polish on updates)
      - one shared animation timer that only runs while something is moving
      - no QGraphicsEffect (avoids offscreen re-rendering)
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        # Window Flags & Attributes for persistent taskbar overlay
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)

        # Anti-Disappear & State Tracking
        self._is_active_mode = False

        # Settings with sensible defaults
        self._settings = {
            "opacity": 0.92,
            "locked": False,
            "dock_preset": "right",
            "saved_x": None,
            "saved_y": None,
            "show_temps": True,
            "show_disk": True,
            "show_net": True,
            "show_battery": True,
            "animations": True,
            "view_mode": "dual_row"  # "dual_row", "single_compact", "single_full"
        }
        self._load_settings()

        # Shared animation engine
        self._clock = AnimationClock(self)
        self._clock.enabled = bool(self._settings.get("animations", True))

        # Telemetry Cache
        self._drag_pos = QPoint()
        self._cpu_temp_val = 40.0
        self._ram_temp_val = 36.0
        self._disk_temp_val = 33.0
        self._cpu_temp_str = "--°"
        self._ram_temp_str = "--°"
        self._disk_temp_str = "--°"

        self._cached_cpu_data = {}
        self._cached_mem_data = {}
        self._cached_disk_data = {}
        self._cached_net_data = {}
        self._cached_hw_data = {}
        self._top_cpu_proc = "-"
        self._top_mem_proc = "-"

        # Keep on top heartbeat timer (1200ms for rock-solid taskbar persistence)
        self.top_timer = QTimer(self)
        self.top_timer.timeout.connect(self._ensure_on_top)
        self.top_timer.start(1200)

        # Listen for screen resolution & taskbar geometry changes
        primary_screen = QGuiApplication.primaryScreen()
        if primary_screen:
            primary_screen.geometryChanged.connect(self._on_screen_changed)
            primary_screen.availableGeometryChanged.connect(self._on_screen_changed)

        # Build UI
        self._init_ui()

        # Fade-in animation (only used on explicit entry into taskbar mode)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(260)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Connect Event Bus
        self.bridge = TaskbarBridge()
        self.bridge.cpu_updated.connect(self.update_cpu)
        self.bridge.memory_updated.connect(self.update_memory)
        self.bridge.disk_updated.connect(self.update_disk)
        self.bridge.network_updated.connect(self.update_network)
        self.bridge.hardware_updated.connect(self.update_hardware)
        self.bridge.process_updated.connect(self.update_process)

        event_bus.subscribe("metrics_cpu", self.bridge.cpu_updated.emit)
        event_bus.subscribe("metrics_memory", self.bridge.memory_updated.emit)
        event_bus.subscribe("metrics_disk", self.bridge.disk_updated.emit)
        event_bus.subscribe("metrics_network", self.bridge.network_updated.emit)
        event_bus.subscribe("metrics_hardware", self.bridge.hardware_updated.emit)
        event_bus.subscribe("metrics_process", self.bridge.process_updated.emit)

        # Enable Tooltip on demand via EventFilter
        self.container.installEventFilter(self)

    def _init_ui(self):
        self.setStyleSheet(TOOLTIP_QSS)
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Main painted glass container
        self.container = GlassContainer(self._clock)
        self.container.setObjectName("TaskbarContainer")
        self.container.set_opacity(self._settings["opacity"])
        root_layout.addWidget(self.container)

        # Content Layout
        self.content_layout = QHBoxLayout(self.container)
        self.content_layout.setContentsMargins(5, 2, 4, 2)
        self.content_layout.setSpacing(5)

        # 1. Drag Grip Handle (Left)
        self.grip = DragGrip(self)
        self.grip.set_locked(self._settings["locked"])
        self.content_layout.addWidget(self.grip)

        # 2. Column 1: CPU (Row 1) & RAM (Row 2)
        self.col_cpu_ram = QWidget()
        layout_col1 = QVBoxLayout(self.col_cpu_ram)
        layout_col1.setContentsMargins(0, 0, 0, 0)
        layout_col1.setSpacing(1)

        self.item_cpu = MetricRow(self._clock, "CPU", C_SKY, warn=60, crit=90, parent=self.col_cpu_ram)
        self.item_ram = MetricRow(self._clock, "RAM", C_GREEN, warn=75, crit=90, parent=self.col_cpu_ram)
        layout_col1.addWidget(self.item_cpu, 0, Qt.AlignLeft)
        layout_col1.addWidget(self.item_ram, 0, Qt.AlignLeft)
        self.content_layout.addWidget(self.col_cpu_ram)

        # Divider 1
        self.div1 = Divider()
        self.content_layout.addWidget(self.div1)

        # 3. Column 2: DSK (Row 1) & Battery (Row 2)
        self.col_dsk_bat = QWidget()
        layout_col2 = QVBoxLayout(self.col_dsk_bat)
        layout_col2.setContentsMargins(0, 0, 0, 0)
        layout_col2.setSpacing(1)

        self.item_dsk = MetricRow(self._clock, "DSK", C_PEACH, warn=85, crit=95, parent=self.col_dsk_bat)
        self.item_dsk.enable_activity_led()
        self.item_bat = BatteryRow(self._clock, self.col_dsk_bat)
        layout_col2.addWidget(self.item_dsk, 0, Qt.AlignLeft)
        layout_col2.addWidget(self.item_bat, 0, Qt.AlignLeft)
        self.content_layout.addWidget(self.col_dsk_bat)

        # Divider 2
        self.div2 = Divider()
        self.content_layout.addWidget(self.div2)

        # 4. Column 3: Network Bandwidth (Down & Up stacked)
        self.net_block = QWidget()
        layout_net = QVBoxLayout(self.net_block)
        layout_net.setContentsMargins(0, 0, 0, 0)
        layout_net.setSpacing(1)
        self.net_dl = NetRow(self._clock, "down", C_NET_DL, C_WHITE, self.net_block)
        self.net_ul = NetRow(self._clock, "up", C_NET_UL, C_TEXT, self.net_block)
        layout_net.addWidget(self.net_dl)
        layout_net.addWidget(self.net_ul)
        self.content_layout.addWidget(self.net_block)

        # 5. Quick Restore Button (↗)
        self.btn_restore = QPushButton("↗")
        self.btn_restore.setFixedSize(14, 14)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.setToolTip("Buka Window Utama (atau Double Click)")
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #6c7086;
                font-size: 10px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: rgba(137, 180, 250, 0.22);
                border-radius: 3px;
            }
        """)
        self.btn_restore.clicked.connect(self.restore_window_mode)
        self.content_layout.addWidget(self.btn_restore)

        self._apply_element_visibility()

    def _apply_container_style(self):
        self.container.set_opacity(self._settings["opacity"])

    def _apply_element_visibility(self):
        show_temps = self._settings["show_temps"]
        show_disk = self._settings["show_disk"]
        show_net = self._settings["show_net"]
        show_bat = self._settings["show_battery"]

        self.item_cpu.set_show_sub(show_temps)
        self.item_ram.set_show_sub(show_temps)
        self.item_dsk.set_show_sub(show_temps)

        # DSK & Battery Column
        self.col_dsk_bat.setVisible(show_disk or show_bat)
        self.item_dsk.setVisible(show_disk)
        self.item_bat.setVisible(show_bat)
        self.div1.setVisible(show_disk or show_bat)

        # Net Column
        self.net_block.setVisible(show_net)
        self.div2.setVisible(show_net and (show_disk or show_bat))

        self.adjustSize()

    # Health evaluation
    def _overall_level(self) -> int:
        """0 = normal, 1 = high load, 2 = critical. Uses short averages to avoid flicker."""
        level = 0
        for row in (self.item_cpu, self.item_ram):
            if not row.has_data:
                continue
            recent = list(row.history)[-3:]
            v = sum(recent) / len(recent)
            if v >= row.crit:
                level = 2
            elif v >= row.warn:
                level = max(level, 1)
        if self._cpu_temp_val >= 85:
            level = 2
        elif self._cpu_temp_val >= 75:
            level = max(level, 1)
        return level

    def _refresh_status(self):
        level = self._overall_level()
        self.grip.set_status_color(QColor((C_GREEN, C_YELLOW, C_RED)[level]))

        # Container alert only on *sustained* critical load (last 5 samples)
        alert = False
        for row in (self.item_cpu, self.item_ram):
            recent = list(row.history)[-5:]
            if len(recent) >= 5 and min(recent) >= row.crit:
                alert = True
        if self._cpu_temp_val >= 88:
            alert = True
        self.container.set_alert(alert)

    # Updaters
    def update_hardware(self, data: dict):
        self._cached_hw_data = data
        temps = data.get("temperatures", {})
        if "cpu" in temps and temps["cpu"]:
            curr = getattr(temps["cpu"][0], "current", temps["cpu"][0].get("current") if isinstance(temps["cpu"][0], dict) else 40.0)
            self._cpu_temp_val = float(curr)
            self._cpu_temp_str = f"{self._cpu_temp_val:.0f}°"

        if "ram" in temps and temps["ram"]:
            curr = getattr(temps["ram"][0], "current", temps["ram"][0].get("current") if isinstance(temps["ram"][0], dict) else 36.0)
            self._ram_temp_val = float(curr)
            self._ram_temp_str = f"{self._ram_temp_val:.0f}°"

        if "disk" in temps and temps["disk"]:
            curr = getattr(temps["disk"][0], "current", temps["disk"][0].get("current") if isinstance(temps["disk"][0], dict) else 33.0)
            self._disk_temp_val = float(curr)
            self._disk_temp_str = f"{self._disk_temp_val:.0f}°"

        if not self.isVisible():
            return

        # Battery update
        if self._settings["show_battery"]:
            battery_data = data.get("battery")
            if battery_data:
                self.item_bat.update_battery(battery_data)
            else:
                self.item_bat.hide()

    def update_cpu(self, data: dict):
        self._cached_cpu_data = data
        if not self.isVisible():
            return
        usage = data.get('usage', 0.0)
        self.item_cpu.set_value(usage, self._cpu_temp_str, _temp_color(self._cpu_temp_val))
        self._refresh_status()
        # Periodically re-assert topmost without extra timers
        self._force_topmost()

    def update_memory(self, data: dict):
        self._cached_mem_data = data
        if not self.isVisible():
            return
        pct = data.get('percent', 0.0)
        self.item_ram.set_value(pct, self._ram_temp_str, _temp_color(self._ram_temp_val))

    def update_disk(self, data: dict):
        self._cached_disk_data = data
        if not self.isVisible() or not self._settings["show_disk"]:
            return
        partitions = data.get("partitions", [])
        pct = partitions[0]['percent'] if partitions else 0.0
        self.item_dsk.set_value(pct, self._disk_temp_str, _temp_color(self._disk_temp_val))

        # Disk I/O activity LED (0 at idle, full brightness ~8 MB/s+)
        io = float(data.get("read_speed", 0.0) or 0.0) + float(data.get("write_speed", 0.0) or 0.0)
        level = 0.0 if io < 64 * 1024 else min(1.0, (io / (8 * 1024 * 1024)) ** 0.5 + 0.25)
        self.item_dsk.set_activity(level)

    def update_network(self, data: dict):
        self._cached_net_data = data
        if not self.isVisible() or not self._settings["show_net"]:
            return
        self.net_dl.set_speed(data.get('download_speed', 0.0))
        self.net_ul.set_speed(data.get('upload_speed', 0.0))

    def update_process(self, data: dict):
        procs = data.get("processes", [])
        if procs:
            top_cpu = procs[0]
            self._top_cpu_proc = f"{top_cpu.get('name', 'App')} ({top_cpu.get('cpu', 0):.1f}%)"
            top_mem = max(procs, key=lambda p: p.get('memory', 0), default=None)
            if top_mem:
                mem_mb = top_mem.get('memory', 0) / (1024 * 1024)
                self._top_mem_proc = f"{top_mem.get('name', 'App')} ({mem_mb:.0f} MB)"

    # Tooltip on Demand
    def eventFilter(self, watched, event):
        if event.type() == QEvent.ToolTip:
            self._generate_tooltip()
        return super().eventFilter(watched, event)

    def _generate_tooltip(self):
        GB = 1024 ** 3
        cpu = self._cached_cpu_data
        mem = self._cached_mem_data
        dsk = self._cached_disk_data
        net = self._cached_net_data
        hw = self._cached_hw_data

        def temp_span(val: float, txt: str) -> str:
            return f"<span style='color:{_temp_color(val).name()};'>{txt}C</span>"

        def row(tag, color, main, extra=""):
            return (f"<tr><td style='color:{color}; font-weight:700; padding:2px 10px 0 0;'>{tag}</td>"
                    f"<td style='color:#cdd6f4; padding-top:2px;'>{main}</td>"
                    f"<td align='right' style='padding:2px 0 0 14px;'>{extra}</td></tr>")

        def sub(text):
            return (f"<tr><td></td><td colspan='2' style='color:{C_OVERLAY}; font-size:10px; "
                    f"padding-bottom:3px;'>{text}</td></tr>")

        def stats(hist):
            h = list(hist)
            return (sum(h) / len(h), max(h)) if h else (0.0, 0.0)

        rows = []

        # CPU
        usage = cpu.get('usage', 0.0)
        freq = cpu.get('frequency', 0.0) or 0.0
        cores = cpu.get('cores') or '-'
        threads = cpu.get('threads') or '-'
        c_avg, c_peak = stats(self.item_cpu.history)
        rows.append(row("CPU", C_SKY, f"<b>{usage:.0f}%</b> &nbsp;·&nbsp; {freq / 1000:.2f} GHz &nbsp;·&nbsp; {cores}C/{threads}T",
                        temp_span(self._cpu_temp_val, self._cpu_temp_str)))
        rows.append(sub(f"Rata-rata 30 dtk {c_avg:.0f}% &nbsp;·&nbsp; puncak {c_peak:.0f}%"))

        # RAM
        mem_pct = mem.get('percent', 0.0)
        total_gb = mem.get('total', 0) / GB
        used_gb = mem.get('used', 0) / GB
        avail_gb = mem.get('available', 0) / GB
        r_avg, r_peak = stats(self.item_ram.history)
        rows.append(row("RAM", C_GREEN, f"<b>{mem_pct:.0f}%</b> &nbsp;·&nbsp; {used_gb:.1f} / {total_gb:.1f} GB",
                        temp_span(self._ram_temp_val, self._ram_temp_str)))
        rows.append(sub(f"Tersedia {avail_gb:.1f} GB &nbsp;·&nbsp; rata-rata {r_avg:.0f}% &nbsp;·&nbsp; puncak {r_peak:.0f}%"))

        # Disk
        parts = dsk.get("partitions", [])
        if parts:
            p0 = parts[0]
            mount = html.escape(str(p0.get('mountpoint', '')).rstrip('\\'))
            rows.append(row("DSK", C_PEACH,
                            f"<b>{p0.get('percent', 0):.0f}%</b> &nbsp;·&nbsp; {mount} sisa {_format_bytes(p0.get('free', 0))} dari {_format_bytes(p0.get('total', 0))}",
                            temp_span(self._disk_temp_val, self._disk_temp_str)))
            rows.append(sub(f"Baca {_format_speed(dsk.get('read_speed', 0.0) or 0.0)} &nbsp;·&nbsp; "
                            f"Tulis {_format_speed(dsk.get('write_speed', 0.0) or 0.0)}"
                            + (f" &nbsp;·&nbsp; {len(parts)} partisi" if len(parts) > 1 else "")))

        # Network
        dl_b = net.get('download_speed', 0.0)
        ul_b = net.get('upload_speed', 0.0)
        dl_peak = max(self.net_dl.history) if self.net_dl.history else 0.0
        ul_peak = max(self.net_ul.history) if self.net_ul.history else 0.0
        rows.append(row("NET", C_NET_DL,
                        f"<span style='color:{C_NET_DL};'>↓</span> {_format_speed(dl_b)} &nbsp; "
                        f"<span style='color:{C_NET_UL};'>↑</span> {_format_speed(ul_b)}"))
        totals = ""
        if net.get('bytes_recv') is not None:
            totals = f" &nbsp;·&nbsp; total sejak boot ↓ {_format_bytes(net.get('bytes_recv', 0))} ↑ {_format_bytes(net.get('bytes_sent', 0))}"
        rows.append(sub(f"Puncak 30 dtk ↓ {_format_speed(dl_peak)} ↑ {_format_speed(ul_peak)}{totals}"))

        # Battery
        batt = hw.get("battery") if hw else None
        if batt:
            b_pct = batt.get("percent", 0) or 0
            secs = batt.get("secsleft")
            if batt.get("power_plugged"):
                b_state = "Terisi penuh" if b_pct >= 99 else "Mengisi daya"
            elif isinstance(secs, (int, float)) and secs > 0:
                b_state = f"≈ {int(secs // 3600)}j {int(secs % 3600 // 60)}m tersisa"
            else:
                b_state = "Menggunakan baterai"
            rows.append(row("BAT", C_GREEN if b_pct >= 45 or batt.get("power_plugged") else (C_YELLOW if b_pct >= 20 else C_RED),
                            f"<b>{b_pct:.0f}%</b> &nbsp;·&nbsp; {b_state}"))

        # Status header & uptime
        level = self._overall_level()
        status_txt, status_col = [("Normal", C_GREEN), ("Beban Tinggi", C_YELLOW), ("Kritis", C_RED)][level]
        uptime = ""
        try:
            import psutil
            up = time.time() - psutil.boot_time()
            d, rem = divmod(int(up), 86400)
            hrs, rem = divmod(rem, 3600)
            mins = rem // 60
            uptime = f"Uptime {d} hari {hrs}j {mins}m" if d else f"Uptime {hrs}j {mins}m"
        except Exception:
            pass

        tt = f"""
            <div style="font-family: 'Segoe UI', Arial; font-size: 11px;">
                <table cellspacing="0" cellpadding="0" width="100%">
                    <tr>
                        <td style="color:#ffffff; font-weight:700; font-size:12px;">PC System Monitor</td>
                        <td align="right" style="color:{status_col}; font-weight:700; padding-left:16px;">● {status_txt}</td>
                    </tr>
                </table>
                <div style="color:{C_OVERLAY}; font-size:10px; margin-bottom:4px;">{uptime}</div>
                <table cellspacing="0" cellpadding="0">
                    {''.join(rows)}
                </table>
                <hr style="border:none; background-color:#313244; height:1px;">
                <div style="color:{C_SUBTEXT};">
                    <b style="color:{C_SKY};">Top CPU</b> &nbsp;{html.escape(self._top_cpu_proc)}<br>
                    <b style="color:{C_GREEN};">Top RAM</b> &nbsp;{html.escape(self._top_mem_proc)}
                </div>
                <div style="color:{C_OVERLAY}; font-size:10px; margin-top:4px;">
                    Klik 2× untuk Dashboard &nbsp;·&nbsp; Klik kanan untuk Opsi
                </div>
            </div>
        """
        self.container.setToolTip(tt)

    # Window Dragging & Mouse Events
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._settings["locked"]:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._settings["locked"]:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self._settings["locked"]:
            self._settings["dock_preset"] = "custom"
            self._settings["saved_x"] = self.x()
            self._settings["saved_y"] = self.y()
            self._save_settings()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.restore_window_mode()
            event.accept()

    def _ensure_on_top(self):
        if self.isVisible() and self._is_active_mode:
            self._force_topmost()

    def _apply_win32_styles(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOPMOST = 0x00000008
            current = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST)

            # Win32 Window Ownership:
            # Set Shell_TrayWnd (Windows Taskbar) as the OWNER window (GWLP_HWNDPARENT).
            # Microsoft Win32 Rule: "An owned window is always displayed ABOVE its owner window in the z-order."
            # This completely stops Windows from covering this widget when the user clicks anywhere on the taskbar!
            tray_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if tray_hwnd:
                GWLP_HWNDPARENT = -8
                user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, tray_hwnd)
        except Exception:
            pass

    def _force_topmost(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            HWND_TOPMOST = -1
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        except Exception:
            self.raise_()

    def show_mode(self):
        """Explicit entry into taskbar mode."""
        self._is_active_mode = True
        if self._clock.enabled:
            self.setWindowOpacity(0.0)
        self.showNormal()
        self.show()
        self._apply_win32_styles()
        self._force_topmost()
        QTimer.singleShot(20, self.position_in_taskbar)
        self._replay_cached_metrics()
        if self._clock.enabled:
            self._fade_anim.stop()
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()
        else:
            self.setWindowOpacity(1.0)

    def _replay_cached_metrics(self):
        """Fill the cells immediately with the last known values instead of waiting a tick."""
        if self._cached_hw_data:
            self.update_hardware(self._cached_hw_data)
        if self._cached_cpu_data and not self.item_cpu.has_data:
            self.update_cpu(self._cached_cpu_data)
        if self._cached_mem_data and not self.item_ram.has_data:
            self.update_memory(self._cached_mem_data)
        if self._cached_disk_data and not self.item_dsk.has_data:
            self.update_disk(self._cached_disk_data)

    def hide_mode(self):
        """Explicit exit from taskbar mode."""
        self._is_active_mode = False
        self._fade_anim.stop()
        self._clock.stop()
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            GWLP_HWNDPARENT = -8
            user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, 0)
        except Exception:
            pass
        self.hide()
        self.setWindowOpacity(1.0)

    def restore_window_mode(self):
        self.hide_mode()
        self.main_window.show()
        self.main_window.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_win32_styles()
        self._force_topmost()
        self.adjustSize()
        QTimer.singleShot(20, self.position_in_taskbar)

    def hideEvent(self, event):
        super().hideEvent(event)
        # If involuntarily hidden by Windows (e.g. Win+D Show Desktop or taskbar click), immediately restore!
        if self._is_active_mode:
            QTimer.singleShot(40, self._restore_taskbar_visibility)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized() and self._is_active_mode:
                self.showNormal()
                self._force_topmost()

    def _restore_taskbar_visibility(self):
        if self._is_active_mode:
            self.showNormal()
            self.show()
            self._apply_win32_styles()
            self._force_topmost()

    def _on_screen_changed(self, *args):
        if self.isVisible() and self._is_active_mode:
            self.position_in_taskbar()

    def position_in_taskbar(self, align: str = None):
        """
        Calculates exact coordinates and docks widget safely in taskbar
        with dynamic Windows 11 system tray detection, multi-monitor support, and screen clamping.
        """
        if align:
            self._settings["dock_preset"] = align
            self._save_settings()
        else:
            align = self._settings.get("dock_preset", "right")

        screen = self.screen() or QGuiApplication.primaryScreen()
        if not screen:
            return

        geom = screen.geometry()
        avail = screen.availableGeometry()

        self.adjustSize()
        widget_w = max(self.sizeHint().width(), self.width(), 200)
        widget_h = 36  # Ergonomic height for 2 rows in taskbar
        self.setFixedHeight(widget_h)

        # Detect native Windows Taskbar and System Tray bounds dynamically
        tray_notify_left = None
        native_taskbar_y = None
        native_taskbar_h = None
        try:
            import ctypes, ctypes.wintypes
            user32 = ctypes.windll.user32
            tray_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if tray_hwnd:
                t_rect = ctypes.wintypes.RECT()
                if user32.GetWindowRect(tray_hwnd, ctypes.byref(t_rect)):
                    native_taskbar_y = t_rect.top
                    native_taskbar_h = t_rect.bottom - t_rect.top

                notify_hwnd = user32.FindWindowExW(tray_hwnd, None, "TrayNotifyWnd", None)
                if notify_hwnd:
                    n_rect = ctypes.wintypes.RECT()
                    if user32.GetWindowRect(notify_hwnd, ctypes.byref(n_rect)):
                        if n_rect.left > 0:
                            tray_notify_left = n_rect.left
        except Exception:
            pass

        # Target Y calculation: vertically center inside taskbar
        if native_taskbar_y is not None and native_taskbar_h is not None and native_taskbar_h > 0:
            target_y = native_taskbar_y + (native_taskbar_h - widget_h) // 2
        elif avail.top() > geom.top():
            # Top taskbar
            tb_height = avail.top() - geom.top()
            target_y = geom.top() + (tb_height - widget_h) // 2
        elif avail.bottom() < geom.bottom():
            # Bottom taskbar (default Windows 10/11)
            tb_height = geom.bottom() - avail.bottom()
            target_y = avail.bottom() + (tb_height - widget_h) // 2
        else:
            # Auto-hidden taskbar or fullscreen
            target_y = geom.bottom() - widget_h - 4

        # Target X based on alignment preset
        if align == "right":
            if tray_notify_left and tray_notify_left > (geom.left() + widget_w + 50):
                # Pixel-perfect alignment right to the left of the Windows 11 system tray cluster
                target_x = tray_notify_left - widget_w - 12
            else:
                target_x = avail.right() - widget_w - 230
        elif align == "center":
            target_x = geom.left() + (geom.width() - widget_w) // 2
        elif align == "left":
            target_x = geom.left() + 140
        elif align == "custom" and self._settings.get("saved_x") is not None:
            target_x = self._settings["saved_x"]
            target_y = self._settings.get("saved_y", target_y)
        else:
            target_x = avail.right() - widget_w - 230

        # Strict screen clamping to guarantee it is NEVER placed offscreen
        min_x = geom.left() + 5
        max_x = geom.right() - widget_w - 5
        min_y = geom.top()
        max_y = geom.bottom() - widget_h

        target_x = max(min_x, min(max_x, target_x))
        target_y = max(min_y, min(max_y, target_y))

        self.move(target_x, target_y)
        self._apply_win32_styles()
        self._force_topmost()

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', Arial;
                font-size: 12px;
            }
            QMenu::item {
                padding: 5px 20px 5px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #313244;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #313244;
                margin: 4px 6px;
            }
        """)

        act_dashboard = menu.addAction("🖥️  Buka Window Mode (Dashboard)")
        act_dashboard.triggered.connect(self.restore_window_mode)

        act_mini = menu.addAction("🗗  Buka Mini Widget")
        act_mini.triggered.connect(self._switch_to_mini)

        act_opt = menu.addAction("🚀  Buka Optimizer")
        act_opt.triggered.connect(self._open_optimizer)

        act_tm = menu.addAction("⚙️  Buka Windows Task Manager")
        act_tm.triggered.connect(self._open_task_manager)

        menu.addSeparator()

        # Component Toggles submenu
        comp_menu = menu.addMenu("👁️  Elemen Ditampilkan")
        comp_menu.setStyleSheet(menu.styleSheet())

        act_t_temps = comp_menu.addAction(f"{'✓ ' if self._settings['show_temps'] else '    '}Suhu (°C)")
        act_t_temps.triggered.connect(self._toggle_temps)

        act_t_disk = comp_menu.addAction(f"{'✓ ' if self._settings['show_disk'] else '    '}Kolom Penyimpanan (DSK)")
        act_t_disk.triggered.connect(self._toggle_disk)

        act_t_net = comp_menu.addAction(f"{'✓ ' if self._settings['show_net'] else '    '}Kolom Network (NET)")
        act_t_net.triggered.connect(self._toggle_net)

        act_t_batt = comp_menu.addAction(f"{'✓ ' if self._settings['show_battery'] else '    '}Baterai (jika ada)")
        act_t_batt.triggered.connect(self._toggle_battery)

        # Animation toggle (power saver)
        act_anim = menu.addAction(
            f"{'✓ ' if self._settings.get('animations', True) else '    '}✨ Animasi Halus"
        )
        act_anim.setToolTip("Matikan untuk mode hemat daya maksimal")
        act_anim.triggered.connect(self._toggle_animations)

        # Docking submenu
        dock_menu = menu.addMenu("📍  Dock ke Taskbar")
        dock_menu.setStyleSheet(menu.styleSheet())

        act_dock_reset = dock_menu.addAction("🔄  Reset ke Posisi Standar (Kanan)")
        act_dock_reset.triggered.connect(lambda: self.position_in_taskbar("right"))

        dock_menu.addSeparator()

        act_dock_r = dock_menu.addAction("Kanan (Dekat System Tray)")
        act_dock_r.triggered.connect(lambda: self.position_in_taskbar("right"))

        act_dock_c = dock_menu.addAction("Tengah")
        act_dock_c.triggered.connect(lambda: self.position_in_taskbar("center"))

        act_dock_l = dock_menu.addAction("Kiri")
        act_dock_l.triggered.connect(lambda: self.position_in_taskbar("left"))

        # Lock toggle
        act_lock = menu.addAction(f"{'🔓 Buka Kunci Posisi' if self._settings['locked'] else '🔒 Kunci Posisi'}")
        act_lock.triggered.connect(self._toggle_lock)

        # Opacity submenu
        opacity_menu = menu.addMenu("👁️  Transparansi")
        opacity_menu.setStyleSheet(menu.styleSheet())
        for pct, val in [("100%", 1.0), ("92%", 0.92), ("85%", 0.85), ("75%", 0.75)]:
            act_op = opacity_menu.addAction(f"{'✓ ' if abs(self._settings['opacity'] - val) < 0.02 else '    '}{pct}")
            act_op.triggered.connect(lambda checked=False, v=val: self._set_opacity(v))

        menu.addSeparator()
        act_quit = menu.addAction("✕  Keluar Aplikasi")
        act_quit.triggered.connect(self._quit_app)

        menu.exec(pos)

    def _toggle_temps(self):
        self._settings["show_temps"] = not self._settings["show_temps"]
        self._apply_element_visibility()
        self._save_settings()
        self.position_in_taskbar()

    def _toggle_disk(self):
        self._settings["show_disk"] = not self._settings["show_disk"]
        self._apply_element_visibility()
        self._save_settings()
        self.position_in_taskbar()

    def _toggle_net(self):
        self._settings["show_net"] = not self._settings["show_net"]
        self._apply_element_visibility()
        self._save_settings()
        self.position_in_taskbar()

    def _toggle_battery(self):
        self._settings["show_battery"] = not self._settings["show_battery"]
        self._apply_element_visibility()
        self._save_settings()
        self.position_in_taskbar()

    def _toggle_animations(self):
        enabled = not self._settings.get("animations", True)
        self._settings["animations"] = enabled
        self._clock.set_enabled(enabled)
        self._save_settings()

    def _toggle_lock(self):
        self._settings["locked"] = not self._settings["locked"]
        self.grip.set_locked(self._settings["locked"])
        self._save_settings()

    def _set_opacity(self, val: float):
        self._settings["opacity"] = val
        self._apply_container_style()
        self._save_settings()

    def _switch_to_mini(self):
        self.hide_mode()
        if hasattr(self.main_window, "mini_widget"):
            self.main_window.mini_widget.show()
            self.main_window.mini_widget.activateWindow()

    def _open_optimizer(self):
        self.restore_window_mode()
        if hasattr(self.main_window, "change_page"):
            self.main_window.change_page("optimizer")

    def _open_task_manager(self):
        try:
            subprocess.Popen(["taskmgr"], shell=True)
        except Exception:
            pass

    def _quit_app(self):
        QApplication.instance().quit()

    # Settings Persistence
    def _load_settings(self):
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._settings.update(loaded)
            except Exception:
                pass

    def _save_settings(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass
