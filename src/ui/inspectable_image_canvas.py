"""Pixel-accurate canvas used by the Coordinate Inspector."""

from __future__ import annotations

import math
from typing import Optional

from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QWidget

from src.utils.coordinate_transform import CoordinateTransform
from src.utils.image_utils import composite_on_checkerboard, pil_to_qpixmap


class InspectableImageCanvas(QWidget):
    """Draw an atlas and keep every interaction in real image pixels."""

    mouse_image_position_changed = pyqtSignal(object)
    selection_changed = pyqtSignal(object)
    zoom_requested = pyqtSignal(float, object, object)
    pan_requested = pyqtSignal(int, int)
    magic_select_requested = pyqtSignal(int, int)

    HANDLE_NAMES = (
        "top_left", "top", "top_right", "right",
        "bottom_right", "bottom", "bottom_left", "left",
    )

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._image: Optional[Image.Image] = None
        self._pixmap: Optional[QPixmap] = None
        self._zoom = 1.0
        self._inspection_enabled = False
        self._magic_select_enabled = False
        self._snap_to_grid = False
        self._selection: Optional[QRect] = None
        self._detected_regions: list[QRect] = []
        self._show_sprite_grid = False
        self._show_pixel_grid = False
        self._show_rulers = False
        self._show_coordinates = False

        self._drag_mode: Optional[str] = None
        self._drag_start = QPoint()
        self._drag_current = QPoint()
        self._drag_original: Optional[QRect] = None
        self._pan_last = QPoint()
        self._space_down = False
        self._pending_detected: Optional[QRect] = None

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._update_canvas_size()

    @property
    def zoom(self) -> float:
        return self._zoom

    @property
    def image(self) -> Optional[Image.Image]:
        return self._image

    @property
    def selection(self) -> Optional[QRect]:
        return QRect(self._selection) if self._selection is not None else None

    def set_image(self, image: Optional[Image.Image]) -> None:
        self._image = image
        self._selection = None
        self._detected_regions.clear()
        if image is None:
            self._pixmap = None
        else:
            rgba = image if image.mode == "RGBA" else image.convert("RGBA")
            self._image = rgba
            self._pixmap = pil_to_qpixmap(composite_on_checkerboard(rgba))
        self._update_canvas_size()
        self.selection_changed.emit(None)
        self.update()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.25, min(16.0, float(zoom)))
        self._update_canvas_size()
        self.update()

    def set_inspection_enabled(self, enabled: bool) -> None:
        self._inspection_enabled = enabled
        if not enabled:
            self._drag_mode = None
        self.setCursor(
            Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def set_magic_select_enabled(self, enabled: bool) -> None:
        self._magic_select_enabled = enabled

    def set_snap_to_grid(self, enabled: bool) -> None:
        self._snap_to_grid = enabled

    def set_overlay_options(
        self,
        *,
        sprite_grid: Optional[bool] = None,
        pixel_grid: Optional[bool] = None,
        rulers: Optional[bool] = None,
        coordinates: Optional[bool] = None,
    ) -> None:
        if sprite_grid is not None:
            self._show_sprite_grid = sprite_grid
        if pixel_grid is not None:
            self._show_pixel_grid = pixel_grid
        if rulers is not None:
            self._show_rulers = rulers
        if coordinates is not None:
            self._show_coordinates = coordinates
        self.update()

    def set_detected_regions(self, regions: list[tuple[int, int, int, int]]) -> None:
        self._detected_regions = [QRect(*region) for region in regions]
        self.update()

    def clear_detected_regions(self) -> None:
        self._detected_regions.clear()
        self.update()

    def set_selection(
        self,
        rect: Optional[QRect | tuple[int, int, int, int]],
        *,
        apply_snap: bool = True,
    ) -> None:
        if rect is None:
            self.clear_selection()
            return
        candidate = QRect(*rect) if isinstance(rect, tuple) else QRect(rect)
        if apply_snap and self._snap_to_grid and self._image is not None:
            left = (candidate.x() // 32) * 32
            top = (candidate.y() // 32) * 32
            right = min(
                math.ceil((candidate.x() + candidate.width()) / 32) * 32,
                self._image.width,
            )
            bottom = min(
                math.ceil((candidate.y() + candidate.height()) / 32) * 32,
                self._image.height,
            )
            candidate = QRect(left, top, right - left, bottom - top)
        candidate = self._constrain_rect(candidate)
        self._selection = candidate if candidate.width() > 0 and candidate.height() > 0 else None
        self.selection_changed.emit(self.selection)
        self.update()

    def clear_selection(self) -> None:
        if self._selection is None:
            return
        self._selection = None
        self.selection_changed.emit(None)
        self.update()

    def select_all(self) -> None:
        if self._image is not None:
            self.set_selection(QRect(0, 0, self._image.width, self._image.height))

    def move_selection(self, dx: int, dy: int) -> None:
        if self._selection is None:
            return
        self.set_selection(self._selection.translated(dx, dy))

    def resize_selection(self, dw: int, dh: int) -> None:
        if self._selection is None:
            return
        rect = QRect(self._selection)
        rect.setWidth(max(1, rect.width() + dw))
        rect.setHeight(max(1, rect.height() + dh))
        self.set_selection(rect)

    def widget_to_image(self, point: QPointF) -> QPointF:
        return self._transform().widget_to_image(point)

    def image_to_widget(self, point: QPointF) -> QPointF:
        return self._transform().image_to_widget(point)

    def image_rect_to_widget(self, rect: QRectF) -> QRectF:
        return self._transform().image_rect_to_widget(rect)

    def _transform(self) -> CoordinateTransform:
        size = QSize(0, 0) if self._image is None else QSize(*self._image.size)
        return CoordinateTransform(self._zoom, size)

    def _update_canvas_size(self) -> None:
        if self._image is None:
            self.setFixedSize(1, 1)
            return
        width = max(1, int(round(self._image.width * self._zoom)))
        height = max(1, int(round(self._image.height * self._zoom)))
        self.setFixedSize(width, height)

    def _image_point(self, widget_point: QPointF) -> Optional[QPoint]:
        if self._image is None:
            return None
        mapped = self.widget_to_image(widget_point)
        x, y = math.floor(mapped.x()), math.floor(mapped.y())
        if not (0 <= x < self._image.width and 0 <= y < self._image.height):
            return None
        return QPoint(x, y)

    def _clamped_image_point(self, widget_point: QPointF) -> Optional[QPoint]:
        if self._image is None:
            return None
        mapped = self.widget_to_image(widget_point)
        return QPoint(
            min(max(math.floor(mapped.x()), 0), self._image.width - 1),
            min(max(math.floor(mapped.y()), 0), self._image.height - 1),
        )

    def _constrain_rect(self, rect: QRect) -> QRect:
        if self._image is None:
            return QRect()
        width = min(max(rect.width(), 1), self._image.width)
        height = min(max(rect.height(), 1), self._image.height)
        x = min(max(rect.x(), 0), self._image.width - width)
        y = min(max(rect.y(), 0), self._image.height - height)
        return QRect(x, y, width, height)

    def _selection_from_points(self, first: QPoint, second: QPoint) -> QRect:
        left, right = sorted((first.x(), second.x()))
        top, bottom = sorted((first.y(), second.y()))
        rect = QRect(left, top, right - left + 1, bottom - top + 1)
        if self._snap_to_grid:
            start_x = (rect.x() // 32) * 32
            start_y = (rect.y() // 32) * 32
            end_x = min(math.ceil((rect.x() + rect.width()) / 32) * 32, self._image.width)
            end_y = min(math.ceil((rect.y() + rect.height()) / 32) * 32, self._image.height)
            rect = QRect(start_x, start_y, end_x - start_x, end_y - start_y)
        return self._constrain_rect(rect)

    def _handle_points(self, rect: QRect) -> dict[str, QPointF]:
        left, top = float(rect.x()), float(rect.y())
        right, bottom = float(rect.x() + rect.width()), float(rect.y() + rect.height())
        center_x, center_y = (left + right) / 2, (top + bottom) / 2
        return {
            "top_left": QPointF(left, top), "top": QPointF(center_x, top),
            "top_right": QPointF(right, top), "right": QPointF(right, center_y),
            "bottom_right": QPointF(right, bottom), "bottom": QPointF(center_x, bottom),
            "bottom_left": QPointF(left, bottom), "left": QPointF(left, center_y),
        }

    def _hit_test(self, point: QPoint) -> Optional[str]:
        if self._selection is None:
            return None
        radius = max(1.5, 6.0 / self._zoom)
        for name, handle in self._handle_points(self._selection).items():
            if abs(point.x() - handle.x()) <= radius and abs(point.y() - handle.y()) <= radius:
                return name
        rect = self._selection
        if rect.x() <= point.x() < rect.x() + rect.width() and rect.y() <= point.y() < rect.y() + rect.height():
            return "move"
        return None

    def _resize_from_drag(self, point: QPoint) -> QRect:
        assert self._drag_original is not None and self._drag_mode is not None
        original = self._drag_original
        dx, dy = point.x() - self._drag_start.x(), point.y() - self._drag_start.y()
        left, top = original.x(), original.y()
        right, bottom = left + original.width(), top + original.height()
        mode = self._drag_mode
        if "left" in mode:
            left = min(left + dx, right - 1)
        if "right" in mode:
            right = max(right + dx, left + 1)
        if "top" in mode:
            top = min(top + dy, bottom - 1)
        if "bottom" in mode:
            bottom = max(bottom + dy, top + 1)
        left = max(0, left)
        top = max(0, top)
        right = min(self._image.width, right)
        bottom = min(self._image.height, bottom)
        return QRect(left, top, max(1, right - left), max(1, bottom - top))

    def _region_at(self, point: QPoint) -> Optional[QRect]:
        for region in reversed(self._detected_regions):
            if region.contains(point):
                return QRect(region)
        return None

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#2d2d2d"))
        if self._pixmap is None or self._image is None:
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(self.rect(), self._pixmap)
        self._draw_grids(painter, event.rect())
        self._draw_detected_regions(painter)
        self._draw_selection(painter)
        if self._show_rulers:
            self._draw_rulers(painter, event.rect())

    def _draw_grids(self, painter: QPainter, clip: QRect) -> None:
        if self._image is None:
            return
        if self._show_pixel_grid and self._zoom >= 8.0:
            painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
            first_x = max(0, int(clip.left() / self._zoom))
            last_x = min(self._image.width, int(clip.right() / self._zoom) + 2)
            first_y = max(0, int(clip.top() / self._zoom))
            last_y = min(self._image.height, int(clip.bottom() / self._zoom) + 2)
            for x in range(first_x, last_x + 1):
                sx = int(round(x * self._zoom))
                painter.drawLine(sx, clip.top(), sx, clip.bottom())
            for y in range(first_y, last_y + 1):
                sy = int(round(y * self._zoom))
                painter.drawLine(clip.left(), sy, clip.right(), sy)
        if self._show_sprite_grid:
            painter.setPen(QPen(QColor(0, 210, 255, 180), 1))
            for x in range(0, self._image.width + 1, 32):
                sx = int(round(x * self._zoom))
                if clip.left() <= sx <= clip.right():
                    painter.drawLine(sx, clip.top(), sx, clip.bottom())
                    if self._show_coordinates and self._zoom >= 0.5:
                        painter.drawText(sx + 3, max(12, clip.top() + 12), str(x // 32))
            for y in range(0, self._image.height + 1, 32):
                sy = int(round(y * self._zoom))
                if clip.top() <= sy <= clip.bottom():
                    painter.drawLine(clip.left(), sy, clip.right(), sy)
                    if self._show_coordinates and self._zoom >= 0.5:
                        painter.drawText(max(3, clip.left() + 3), sy + 12, str(y // 32))

    def _draw_detected_regions(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(255, 180, 0, 210), 1, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(255, 180, 0, 25))
        for region in self._detected_regions:
            painter.drawRect(self.image_rect_to_widget(QRectF(region)))

    def _draw_selection(self, painter: QPainter) -> None:
        if self._selection is None:
            return
        widget_rect = self.image_rect_to_widget(QRectF(self._selection))
        painter.setPen(QPen(QColor(0, 220, 255), 2))
        painter.setBrush(QColor(0, 180, 255, 55))
        painter.drawRect(widget_rect)
        handle_size = 7
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(QColor("#00aeea"))
        for point in self._handle_points(self._selection).values():
            widget_point = self.image_to_widget(point)
            painter.drawRect(QRectF(
                widget_point.x() - handle_size / 2,
                widget_point.y() - handle_size / 2,
                handle_size,
                handle_size,
            ))
        label = f"x={self._selection.x()} y={self._selection.y()}  {self._selection.width()}x{self._selection.height()}"
        metrics = painter.fontMetrics()
        label_rect = metrics.boundingRect(label).adjusted(-4, -2, 4, 2)
        label_rect.moveBottomLeft(QPoint(int(widget_rect.left()), max(0, int(widget_rect.top()) - 3)))
        painter.fillRect(label_rect, QColor(0, 0, 0, 190))
        painter.setPen(QColor("white"))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_rulers(self, painter: QPainter, clip: QRect) -> None:
        if self._image is None:
            return
        ruler = 22
        painter.fillRect(QRect(clip.left(), clip.top(), clip.width(), ruler), QColor(20, 20, 20, 210))
        painter.fillRect(QRect(clip.left(), clip.top(), ruler, clip.height()), QColor(20, 20, 20, 210))
        painter.setPen(QPen(QColor(230, 230, 230, 190), 1))
        step = 32 if self._zoom >= 0.5 else 64
        start_x = max(0, int(clip.left() / self._zoom / step) * step)
        end_x = min(self._image.width, int(clip.right() / self._zoom) + step)
        for x in range(start_x, end_x + 1, step):
            sx = int(round(x * self._zoom))
            painter.drawLine(sx, clip.top(), sx, clip.top() + 6)
            painter.drawText(sx + 2, clip.top() + 18, str(x))
        start_y = max(0, int(clip.top() / self._zoom / step) * step)
        end_y = min(self._image.height, int(clip.bottom() / self._zoom) + step)
        for y in range(start_y, end_y + 1, step):
            sy = int(round(y * self._zoom))
            painter.drawLine(clip.left(), sy, clip.left() + 6, sy)
            painter.save()
            painter.translate(clip.left() + 17, sy + 2)
            painter.rotate(-90)
            painter.drawText(0, 0, str(y))
            painter.restore()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._space_down
        ):
            self._drag_mode = "pan"
            self._pan_last = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if not self._inspection_enabled or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        point = self._image_point(event.position())
        if point is None:
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if self._magic_select_enabled:
            self.magic_select_requested.emit(point.x(), point.y())
            return
        self._drag_start = point
        self._drag_current = point
        self._drag_original = self.selection
        self._pending_detected = self._region_at(point)
        self._drag_mode = self._hit_test(point) or "select"
        if self._drag_mode == "select":
            self._selection = self._selection_from_points(point, point)
            self.selection_changed.emit(self.selection)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        point = self._image_point(event.position())
        if point is not None and self._image is not None:
            color = self._image.getpixel((point.x(), point.y()))
            self.mouse_image_position_changed.emit({"x": point.x(), "y": point.y(), "color": color})
        else:
            self.mouse_image_position_changed.emit(None)
        if self._drag_mode == "pan":
            current = event.position().toPoint()
            delta = current - self._pan_last
            self._pan_last = current
            self.pan_requested.emit(delta.x(), delta.y())
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._drag_mode is None:
            return
        point = self._clamped_image_point(event.position())
        if point is None:
            return
        self._drag_current = point
        if point != self._drag_start:
            self._pending_detected = None
        if self._drag_mode == "select":
            rect = self._selection_from_points(self._drag_start, point)
        elif self._drag_mode == "move" and self._drag_original is not None:
            rect = self._drag_original.translated(
                point.x() - self._drag_start.x(), point.y() - self._drag_start.y()
            )
            rect = self._constrain_rect(rect)
        else:
            rect = self._resize_from_drag(point)
        self._selection = rect
        self.selection_changed.emit(self.selection)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_mode == "pan":
            self._drag_mode = None
            self.setCursor(Qt.CursorShape.CrossCursor if self._inspection_enabled else Qt.CursorShape.ArrowCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton and self._drag_mode is not None:
            if self._pending_detected is not None:
                self.set_selection(self._pending_detected)
            elif self._selection is not None:
                self.selection_changed.emit(self.selection)
            self._drag_mode = None
            self._drag_original = None
            self._pending_detected = None

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.mouse_image_position_changed.emit(None)
        super().leaveEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            image_point = self.widget_to_image(event.position())
            self.zoom_requested.emit(factor, image_point, event.position())
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space:
            self._space_down = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.clear_selection()
            event.accept()
            return
        directions = {
            Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1),
        }
        if self._inspection_enabled and self._selection is not None and event.key() in directions:
            dx, dy = directions[event.key()]
            amount = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                self.resize_selection(dx * amount, dy * amount)
            else:
                self.move_selection(dx * amount, dy * amount)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space:
            self._space_down = False
            if self._drag_mode != "pan":
                self.setCursor(Qt.CursorShape.CrossCursor if self._inspection_enabled else Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().keyReleaseEvent(event)
