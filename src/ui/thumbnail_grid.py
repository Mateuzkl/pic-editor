"""
Grid de thumbnails para navegação entre imagens.

Exibe miniaturas de todas as imagens do arquivo .pic
em um grid scrollável.
"""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGridLayout,
    QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QMouseEvent
from PIL import Image

from src.utils.image_utils import pil_to_qpixmap, composite_on_checkerboard
from src.utils.i18n import tr, Translator


class ThumbnailItem(QFrame):
    """Item individual de thumbnail clicável."""
    
    clicked = pyqtSignal(int)  # Emite o índice quando clicado
    
    def __init__(self, index: int, image: Optional[Image.Image] = None):
        super().__init__()
        self._index = index
        self._selected = False
        self._setup_ui()
        
        if image is not None:
            self.set_image(image)
    
    def _setup_ui(self):
        """Configura a interface do thumbnail."""
        self.setFixedSize(80, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Imagem
        self.image_label = QLabel()
        self.image_label.setFixedSize(72, 72)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")
        layout.addWidget(self.image_label)
        
        # Índice
        self.index_label = QLabel(f"#{self._index + 1}")
        self.index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.index_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.index_label)
    
    def _update_style(self):
        """Atualiza o estilo baseado na seleção."""
        if self._selected:
            self.setStyleSheet("""
                ThumbnailItem {
                    background-color: #0e639c;
                    border: 2px solid #1177bb;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                ThumbnailItem {
                    background-color: #2d2d2d;
                    border: 1px solid #3c3c3c;
                    border-radius: 6px;
                }
                ThumbnailItem:hover {
                    background-color: #3c3c3c;
                    border: 1px solid #505050;
                }
            """)
    
    def set_image(self, image: Image.Image):
        """Define a imagem do thumbnail."""
        # Redimensionar para caber no thumbnail
        thumb = image.copy()
        thumb.thumbnail((64, 64), Image.Resampling.NEAREST)
        
        # Compor sobre tabuleiro
        composite = composite_on_checkerboard(thumb)
        pixmap = pil_to_qpixmap(composite)
        
        self.image_label.setPixmap(pixmap)
    
    def set_selected(self, selected: bool):
        """Define o estado de seleção."""
        self._selected = selected
        self._update_style()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Evento de clique."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)
        super().mousePressEvent(event)


class ThumbnailGrid(QWidget):
    """
    Grid de thumbnails para navegação.
    
    Signals:
        image_selected: Emitido quando uma imagem é selecionada (int)
    """
    
    image_selected = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self._thumbnails: List[ThumbnailItem] = []
        self._selected_index: int = -1
        self._image_count: int = 0
        self._setup_ui()
        
        # Registrar para mudanças de idioma
        Translator.instance().register_callback(self._update_texts)
    
    def _setup_ui(self):
        """Configura a interface do grid."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Título
        self.title = QLabel(tr("images"))
        self.title.setStyleSheet("""
            QLabel {
                color: #fff;
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #252526;
            }
        """)
        layout.addWidget(self.title)
        
        # Área de scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
        """)
        
        # Container do grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setSpacing(8)
        
        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area, 1)
        
        # Info
        self.info_label = QLabel(tr("no_file"))
        self.info_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #252526;
            }
        """)
        layout.addWidget(self.info_label)
    
    def _update_texts(self):
        """Atualiza textos quando o idioma muda."""
        self.title.setText(tr("images"))
        if self._image_count > 0:
            self.info_label.setText(tr("total_images", count=self._image_count))
        else:
            self.info_label.setText(tr("no_file"))
    
    def set_images(self, images: List[Image.Image]):
        """
        Define a lista de imagens a exibir.
        
        Args:
            images: Lista de imagens PIL
        """
        # Limpar thumbnails existentes
        self.clear()
        
        # Calcular colunas baseado na largura
        columns = 2
        
        for i, image in enumerate(images):
            thumb = ThumbnailItem(i, image)
            thumb.clicked.connect(self._on_thumbnail_clicked)
            self._thumbnails.append(thumb)
            
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(thumb, row, col)
        
        self._image_count = len(images)
        self.info_label.setText(tr("total_images", count=self._image_count))
        
        # Selecionar primeira imagem
        if images:
            self.select_image(0)
    
    def clear(self):
        """Remove todos os thumbnails."""
        for thumb in self._thumbnails:
            thumb.deleteLater()
        self._thumbnails.clear()
        self._selected_index = -1
        self._image_count = 0
        
        # Limpar layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def select_image(self, index: int):
        """
        Seleciona uma imagem pelo índice.
        
        Args:
            index: Índice da imagem
        """
        if index < 0 or index >= len(self._thumbnails):
            return
        
        # Desselecionar anterior
        if 0 <= self._selected_index < len(self._thumbnails):
            self._thumbnails[self._selected_index].set_selected(False)
        
        # Selecionar novo
        self._selected_index = index
        self._thumbnails[index].set_selected(True)
        
        # Scroll para visibilidade
        self.scroll_area.ensureWidgetVisible(self._thumbnails[index])
    
    def _on_thumbnail_clicked(self, index: int):
        """Callback quando um thumbnail é clicado."""
        self.select_image(index)
        self.image_selected.emit(index)
    
    def get_selected_index(self) -> int:
        """Retorna o índice selecionado."""
        return self._selected_index
