"""Image viewer with pixel-accurate zoom, scroll, pan and inspection overlays."""

from __future__ import annotations

from typing import Optional

from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.ui.inspectable_image_canvas import InspectableImageCanvas


# Backwards-compatible name for integrations importing the former canvas class.
ImageCanvas = InspectableImageCanvas


class ImageViewer(QWidget):
    """Scrollable image viewer. Coordinates emitted by the canvas are unscaled."""

    zoom_changed = pyqtSignal(float)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_image: Optional[Image.Image] = None
        self._zoom = 1.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background-color: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 4px; }"
        )
        self.canvas = InspectableImageCanvas()
        self.scroll_area.setWidget(self.canvas)
        self.canvas.zoom_requested.connect(self._zoom_at)
        self.canvas.pan_requested.connect(self._pan)
        layout.addWidget(self.scroll_area, 1)

        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(8)
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedSize(32, 32)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        zoom_layout.addWidget(self.btn_zoom_out)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(25, 1600)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        zoom_layout.addWidget(self.zoom_slider, 1)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(32, 32)
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        zoom_layout.addWidget(self.btn_zoom_in)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(54)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_layout.addWidget(self.zoom_label)

        self.btn_fit = QPushButton("Fit")
        self.btn_fit.setFixedSize(44, 32)
        self.btn_fit.clicked.connect(self.fit_image)
        zoom_layout.addWidget(self.btn_fit)

        self.btn_zoom_reset = QPushButton("100%")
        self.btn_zoom_reset.setFixedSize(52, 32)
        self.btn_zoom_reset.clicked.connect(self._zoom_reset)
        zoom_layout.addWidget(self.btn_zoom_reset)
        layout.addLayout(zoom_layout)

    def set_image(self, image: Optional[Image.Image]) -> None:
        self._current_image = image
        self.canvas.set_image(image)

    def get_image(self) -> Optional[Image.Image]:
        return self._current_image

    def set_inspection_enabled(self, enabled: bool) -> None:
        self.canvas.set_inspection_enabled(enabled)

    def _set_zoom(
        self,
        zoom: float,
        image_anchor: Optional[QPointF] = None,
        viewport_anchor: Optional[QPointF] = None,
    ) -> None:
        zoom = max(0.25, min(16.0, float(zoom)))
        if image_anchor is None and self._current_image is not None:
            center = self.scroll_area.viewport().rect().center()
            canvas_point = self.canvas.mapFrom(self.scroll_area.viewport(), center)
            image_anchor = self.canvas.widget_to_image(QPointF(canvas_point))
            viewport_anchor = QPointF(center)
        self._zoom = zoom
        self.canvas.set_zoom(zoom)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(round(zoom * 100))
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"{round(zoom * 100)}%")
        self.zoom_changed.emit(zoom)
        if image_anchor is not None and viewport_anchor is not None:
            QTimer.singleShot(0, lambda: self._restore_anchor(image_anchor, viewport_anchor))

    def _restore_anchor(self, image_anchor: QPointF, viewport_anchor: QPointF) -> None:
        target = self.canvas.image_to_widget(image_anchor)
        self.scroll_area.horizontalScrollBar().setValue(round(target.x() - viewport_anchor.x()))
        self.scroll_area.verticalScrollBar().setValue(round(target.y() - viewport_anchor.y()))

    def _zoom_at(self, factor: float, image_point: QPointF, canvas_point: QPointF) -> None:
        viewport_point = self.canvas.mapTo(
            self.scroll_area.viewport(), QPoint(round(canvas_point.x()), round(canvas_point.y()))
        )
        self._set_zoom(self._zoom * factor, image_point, QPointF(viewport_point))

    def _pan(self, dx: int, dy: int) -> None:
        horizontal = self.scroll_area.horizontalScrollBar()
        vertical = self.scroll_area.verticalScrollBar()
        horizontal.setValue(horizontal.value() - dx)
        vertical.setValue(vertical.value() - dy)

    def _zoom_in(self) -> None:
        self._set_zoom(self._zoom * 1.25)

    def _zoom_out(self) -> None:
        self._set_zoom(self._zoom / 1.25)

    def _zoom_reset(self) -> None:
        self._set_zoom(1.0)

    def fit_image(self) -> None:
        if self._current_image is None:
            return
        viewport = self.scroll_area.viewport().size()
        available_width = max(1, viewport.width() - 4)
        available_height = max(1, viewport.height() - 4)
        zoom = min(
            available_width / self._current_image.width,
            available_height / self._current_image.height,
        )
        self._set_zoom(zoom)

    def center_on_selection(self) -> None:
        selection = self.canvas.selection
        if selection is None:
            return
        center = self.canvas.image_to_widget(QPointF(
            selection.x() + selection.width() / 2,
            selection.y() + selection.height() / 2,
        ))
        self.scroll_area.horizontalScrollBar().setValue(
            round(center.x() - self.scroll_area.viewport().width() / 2)
        )
        self.scroll_area.verticalScrollBar().setValue(
            round(center.y() - self.scroll_area.viewport().height() / 2)
        )

    def _on_slider_changed(self, value: int) -> None:
        self._set_zoom(value / 100.0)
