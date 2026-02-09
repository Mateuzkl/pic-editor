"""
Painel de edição com ferramentas de edição de imagem.

Contém controles para troca de cores, filtros, e importação.
"""

from typing import Optional, Tuple, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QFrame, QColorDialog,
    QSpinBox, QGroupBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PIL import Image

from src.utils.image_utils import replace_color, apply_brightness, apply_contrast, apply_saturation
from src.utils.i18n import tr, Translator


class ColorButton(QPushButton):
    """Botão que exibe e permite selecionar uma cor."""
    
    color_changed = pyqtSignal(tuple)
    
    def __init__(self, color: Tuple[int, int, int] = (255, 255, 255)):
        super().__init__()
        self._color = color
        self.setFixedSize(40, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self.clicked.connect(self._pick_color)
    
    def _update_style(self):
        """Atualiza o estilo com a cor atual."""
        r, g, b = self._color
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                border: 2px solid #555;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #888;
            }}
        """)
    
    def _pick_color(self):
        """Abre o diálogo de seleção de cor."""
        initial = QColor(*self._color)
        color = QColorDialog.getColor(initial, self)
        if color.isValid():
            self._color = (color.red(), color.green(), color.blue())
            self._update_style()
            self.color_changed.emit(self._color)
    
    def get_color(self) -> Tuple[int, int, int]:
        """Retorna a cor atual."""
        return self._color
    
    def set_color(self, color: Tuple[int, int, int]):
        """Define a cor."""
        self._color = color
        self._update_style()


class EditorPanel(QWidget):
    """
    Painel de ferramentas de edição.
    
    Signals:
        image_modified: Emitido quando a imagem é modificada (Image)
    """
    
    image_modified = pyqtSignal(object)  # PIL Image
    
    def __init__(self):
        super().__init__()
        self._current_image: Optional[Image.Image] = None
        self._original_image: Optional[Image.Image] = None
        self._setup_ui()
        
        # Registrar para mudanças de idioma
        Translator.instance().register_callback(self._update_texts)
    
    def _setup_ui(self):
        """Configura a interface do painel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Título
        self.title = QLabel(tr("editing_tools"))
        self.title.setStyleSheet("""
            QLabel {
                color: #fff;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.title)
        
        # === Seção: Troca de Cores ===
        self.color_group = QGroupBox(tr("color_swap"))
        self.color_group.setStyleSheet("""
            QGroupBox {
                color: #ddd;
                font-weight: bold;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        color_layout = QVBoxLayout(self.color_group)
        
        # Linha: Cor Original → Nova Cor
        color_row = QHBoxLayout()
        self.lbl_from = QLabel(tr("from"))
        color_row.addWidget(self.lbl_from)
        self.color_from = ColorButton((255, 0, 255))
        color_row.addWidget(self.color_from)
        color_row.addWidget(QLabel("→"))
        self.color_to = ColorButton((0, 0, 0))
        color_row.addWidget(self.color_to)
        color_row.addStretch()
        color_layout.addLayout(color_row)
        
        # Tolerância
        tol_row = QHBoxLayout()
        self.lbl_tolerance = QLabel(tr("tolerance"))
        tol_row.addWidget(self.lbl_tolerance)
        self.tolerance_spin = QSpinBox()
        self.tolerance_spin.setRange(0, 128)
        self.tolerance_spin.setValue(10)
        tol_row.addWidget(self.tolerance_spin)
        tol_row.addStretch()
        color_layout.addLayout(tol_row)
        
        # Botão aplicar
        self.btn_apply_color = QPushButton(tr("apply_color"))
        self.btn_apply_color.clicked.connect(self._apply_color_replacement)
        color_layout.addWidget(self.btn_apply_color)
        
        layout.addWidget(self.color_group)
        
        # === Seção: Filtros ===
        self.filter_group = QGroupBox(tr("filters"))
        self.filter_group.setStyleSheet(self.color_group.styleSheet())
        filter_layout = QVBoxLayout(self.filter_group)
        
        # Brilho
        self.brightness_slider = self._create_slider(tr("brightness"), -100, 100, 0)
        filter_layout.addLayout(self.brightness_slider[0])
        
        # Contraste
        self.contrast_slider = self._create_slider(tr("contrast"), -100, 100, 0)
        filter_layout.addLayout(self.contrast_slider[0])
        
        # Saturação
        self.saturation_slider = self._create_slider(tr("saturation"), -100, 100, 0)
        filter_layout.addLayout(self.saturation_slider[0])
        
        # Botão aplicar filtros
        self.btn_apply_filters = QPushButton(tr("apply_filters"))
        self.btn_apply_filters.clicked.connect(self._apply_filters)
        filter_layout.addWidget(self.btn_apply_filters)
        
        layout.addWidget(self.filter_group)
        
        # === Seção: Importar Imagem ===
        self.import_group = QGroupBox(tr("replace_image"))
        self.import_group.setStyleSheet(self.color_group.styleSheet())
        import_layout = QVBoxLayout(self.import_group)
        
        self.btn_import = QPushButton(tr("import_png"))
        self.btn_import.clicked.connect(self._import_image)
        import_layout.addWidget(self.btn_import)
        
        layout.addWidget(self.import_group)
        
        # === Botões de ação ===
        action_layout = QHBoxLayout()
        
        self.btn_reset = QPushButton(tr("reset"))
        self.btn_reset.clicked.connect(self._reset_image)
        action_layout.addWidget(self.btn_reset)
        
        layout.addLayout(action_layout)
        
        # Espaçador
        layout.addStretch()
    
    def _update_texts(self):
        """Atualiza textos quando o idioma muda."""
        self.title.setText(tr("editing_tools"))
        self.color_group.setTitle(tr("color_swap"))
        self.lbl_from.setText(tr("from"))
        self.lbl_tolerance.setText(tr("tolerance"))
        self.btn_apply_color.setText(tr("apply_color"))
        self.filter_group.setTitle(tr("filters"))
        self.brightness_slider[3].setText(tr("brightness"))
        self.contrast_slider[3].setText(tr("contrast"))
        self.saturation_slider[3].setText(tr("saturation"))
        self.btn_apply_filters.setText(tr("apply_filters"))
        self.import_group.setTitle(tr("replace_image"))
        self.btn_import.setText(tr("import_png"))
        self.btn_reset.setText(tr("reset"))
    
    def _create_slider(self, label: str, min_val: int, max_val: int, default: int):
        """Cria um slider com label e valor."""
        layout = QHBoxLayout()
        
        lbl = QLabel(label)
        lbl.setFixedWidth(70)
        layout.addWidget(lbl)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        layout.addWidget(slider, 1)
        
        value_lbl = QLabel(str(default))
        value_lbl.setFixedWidth(40)
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        slider.valueChanged.connect(lambda v: value_lbl.setText(str(v)))
        layout.addWidget(value_lbl)
        
        return (layout, slider, value_lbl, lbl)
    
    def set_image(self, image: Optional[Image.Image]):
        """Define a imagem atual para edição."""
        self._current_image = image.copy() if image else None
        self._original_image = image.copy() if image else None
        
        # Resetar sliders
        self.brightness_slider[1].setValue(0)
        self.contrast_slider[1].setValue(0)
        self.saturation_slider[1].setValue(0)
    
    def get_image(self) -> Optional[Image.Image]:
        """Retorna a imagem atual."""
        return self._current_image
    
    def _apply_color_replacement(self):
        """Aplica a troca de cor."""
        if self._current_image is None:
            return
        
        old_color = self.color_from.get_color()
        new_color = self.color_to.get_color()
        tolerance = self.tolerance_spin.value()
        
        self._current_image = replace_color(
            self._current_image, old_color, new_color, tolerance
        )
        self.image_modified.emit(self._current_image)
    
    def _apply_filters(self):
        """Aplica os filtros de imagem."""
        if self._original_image is None:
            return
        
        # Começar do original
        img = self._original_image.copy()
        
        # Aplicar brilho (converter -100..100 para 0..2)
        brightness = self.brightness_slider[1].value()
        if brightness != 0:
            factor = 1.0 + (brightness / 100.0)
            img = apply_brightness(img, factor)
        
        # Aplicar contraste
        contrast = self.contrast_slider[1].value()
        if contrast != 0:
            factor = 1.0 + (contrast / 100.0)
            img = apply_contrast(img, factor)
        
        # Aplicar saturação
        saturation = self.saturation_slider[1].value()
        if saturation != 0:
            factor = 1.0 + (saturation / 100.0)
            img = apply_saturation(img, factor)
        
        self._current_image = img
        self.image_modified.emit(self._current_image)
    
    def _import_image(self):
        """Importa uma imagem PNG para substituir."""
        if self._current_image is None:
            QMessageBox.warning(self, tr("warning"), tr("select_image"))
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("import_png"),
            "",
            f"{tr('png_files')};;{tr('all_files')}"
        )
        
        if not file_path:
            return
        
        try:
            new_image = Image.open(file_path)
            
            # Verificar dimensões
            if new_image.size != self._current_image.size:
                reply = QMessageBox.question(
                    self,
                    tr("resize"),
                    tr("resize_question",
                       w1=new_image.size[0], h1=new_image.size[1],
                       w2=self._current_image.size[0], h2=self._current_image.size[1]),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    new_image = new_image.resize(
                        self._current_image.size,
                        Image.Resampling.LANCZOS
                    )
                else:
                    return
            
            if new_image.mode != 'RGBA':
                new_image = new_image.convert('RGBA')
            
            self._current_image = new_image
            self._original_image = new_image.copy()
            self.image_modified.emit(self._current_image)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("error"),
                f"{tr('error')}: {str(e)}"
            )
    
    def _reset_image(self):
        """Reseta a imagem para o original."""
        if self._original_image is not None:
            self._current_image = self._original_image.copy()
            
            # Resetar sliders
            self.brightness_slider[1].setValue(0)
            self.contrast_slider[1].setValue(0)
            self.saturation_slider[1].setValue(0)
            
            self.image_modified.emit(self._current_image)
