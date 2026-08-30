"""Single source of truth for canvas/widget and image coordinates."""

from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, QSize


@dataclass(frozen=True, slots=True)
class CoordinateTransform:
    zoom: float
    image_size: QSize

    def widget_to_image(self, point: QPointF) -> QPointF:
        if self.zoom <= 0:
            return QPointF()
        return QPointF(point.x() / self.zoom, point.y() / self.zoom)

    def image_to_widget(self, point: QPointF) -> QPointF:
        return QPointF(point.x() * self.zoom, point.y() * self.zoom)

    def image_rect_to_widget(self, rect: QRectF) -> QRectF:
        top_left = self.image_to_widget(rect.topLeft())
        return QRectF(
            top_left.x(),
            top_left.y(),
            rect.width() * self.zoom,
            rect.height() * self.zoom,
        )

    def contains_image_point(self, point: QPointF) -> bool:
        return (
            0 <= point.x() < self.image_size.width()
            and 0 <= point.y() < self.image_size.height()
        )

    def clamp_image_point(self, point: QPointF) -> QPointF:
        width = max(0, self.image_size.width())
        height = max(0, self.image_size.height())
        return QPointF(
            min(max(point.x(), 0.0), float(width)),
            min(max(point.y(), 0.0), float(height)),
        )
