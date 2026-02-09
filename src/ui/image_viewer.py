"""
Widget de visualização de imagem com zoom.

Exibe uma imagem do .pic em tamanho real com suporte
a zoom in/out e fundo de tabuleiro para transparência.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen
from PIL import Image

from src.utils.image_utils import pil_to_qpixmap, composite_on_checkerboard


class ImageCanvas(QLabel):
    """Canvas para desenhar a imagem com zoom."""
    
    def __init__(self):
        super().__init__()
        self._pixmap: Optional[QPixmap] = None
        self._zoom: float = 1.0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #2d2d2d;")
    
    def set_image(self, image: Optional[Image.Image]):
        """Define a imagem a ser exibida."""
        if image is None:
            self._pixmap = None
            self.clear()
            return
        
        # Compor sobre fundo de tabuleiro para mostrar transparência
        composite = composite_on_checkerboard(image)
        self._pixmap = pil_to_qpixmap(composite)
        self._update_display()
    
    def set_zoom(self, zoom: float):
        """Define o nível de zoom."""
        self._zoom = max(0.25, min(4.0, zoom))
        self._update_display()
    
    def _update_display(self):
        """Atualiza a exibição com o zoom atual."""
        if self._pixmap is None:
            self.clear()
            return
        
        scaled_w = int(self._pixmap.width() * self._zoom)
        scaled_h = int(self._pixmap.height() * self._zoom)
        
        scaled = self._pixmap.scaled(
            scaled_w, scaled_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.setPixmap(scaled)


class ImageViewer(QWidget):
    """
    Widget de visualização de imagem com controles de zoom.
    
    Signals:
        zoom_changed: Emitido quando o zoom muda (float)
    """
    
    zoom_changed = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self._current_image: Optional[Image.Image] = None
        self._zoom: float = 1.0
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura a interface do widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Área de scroll para a imagem
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        
        self.canvas = ImageCanvas()
        self.scroll_area.setWidget(self.canvas)
        layout.addWidget(self.scroll_area, 1)
        
        # Controles de zoom
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(8)
        
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(32, 32)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        zoom_layout.addWidget(self.btn_zoom_out)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(25)
        self.zoom_slider.setMaximum(400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        zoom_layout.addWidget(self.zoom_slider, 1)
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(32, 32)
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        zoom_layout.addWidget(self.btn_zoom_in)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_layout.addWidget(self.zoom_label)
        
        self.btn_zoom_reset = QPushButton("1:1")
        self.btn_zoom_reset.setFixedSize(40, 32)
        self.btn_zoom_reset.clicked.connect(self._zoom_reset)
        zoom_layout.addWidget(self.btn_zoom_reset)
        
        layout.addLayout(zoom_layout)
    
    def set_image(self, image: Optional[Image.Image]):
        """Define a imagem a ser exibida."""
        self._current_image = image
        self.canvas.set_image(image)
    
    def get_image(self) -> Optional[Image.Image]:
        """Retorna a imagem atual."""
        return self._current_image
    
    def _set_zoom(self, zoom: float):
        """Define o zoom e atualiza a UI."""
        self._zoom = max(0.25, min(4.0, zoom))
        self.canvas.set_zoom(self._zoom)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(self._zoom * 100))
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"{int(self._zoom * 100)}%")
        self.zoom_changed.emit(self._zoom)
    
    def _zoom_in(self):
        """Aumenta o zoom."""
        self._set_zoom(self._zoom + 0.25)
    
    def _zoom_out(self):
        """Diminui o zoom."""
        self._set_zoom(self._zoom - 0.25)
    
    def _zoom_reset(self):
        """Reseta o zoom para 100%."""
        self._set_zoom(1.0)
    
    def _on_slider_changed(self, value: int):
        """Callback do slider de zoom."""
        self._set_zoom(value / 100.0)
