"""
Janela principal da aplicação.

Integra todos os componentes: thumbnail grid, image viewer,
editor panel, e barra de menu.
"""

import os
import sys
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QMenu, QStatusBar, QFileDialog,
    QMessageBox, QApplication, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

from src.parsers.pic_parser import PicParser, PicParserError, UnsupportedVersionError
from src.models.pic import Pic, PicImage
from src.ui.thumbnail_grid import ThumbnailGrid
from src.ui.image_viewer import ImageViewer
from src.ui.editor_panel import EditorPanel


class MainWindow(QMainWindow):
    """Janela principal do editor de Tibia.pic."""
    
    def __init__(self):
        super().__init__()
        
        self.parser = PicParser()
        self.pic: Optional[Pic] = None
        self.current_image_index: int = -1
        
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._apply_dark_theme()
    
    def _setup_ui(self):
        """Configura a interface principal."""
        self.setWindowTitle("Tibia PIC Editor")
        self.resize(1200, 800)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Painel esquerdo: Thumbnails
        self.thumbnail_grid = ThumbnailGrid()
        self.thumbnail_grid.setMinimumWidth(200)
        self.thumbnail_grid.setMaximumWidth(250)
        self.thumbnail_grid.image_selected.connect(self._on_image_selected)
        splitter.addWidget(self.thumbnail_grid)
        
        # Centro: Visualizador de imagem
        self.image_viewer = ImageViewer()
        splitter.addWidget(self.image_viewer)
        
        # Direita: Painel de edição
        self.editor_panel = EditorPanel()
        self.editor_panel.setMinimumWidth(280)
        self.editor_panel.setMaximumWidth(350)
        self.editor_panel.image_modified.connect(self._on_image_modified)
        splitter.addWidget(self.editor_panel)
        
        # Proporções do splitter
        splitter.setSizes([200, 600, 300])
        
        layout.addWidget(splitter)
    
    def _setup_menu(self):
        """Configura a barra de menu."""
        menubar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menubar.addMenu("&Arquivo")
        
        open_action = QAction("&Abrir...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Salvar", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Salvar &Como...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("&Exportar PNG...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_current_png)
        file_menu.addAction(export_action)
        
        export_all_action = QAction("Exportar &Todas as PNGs...", self)
        export_all_action.triggered.connect(self._export_all_pngs)
        file_menu.addAction(export_all_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Sair", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Visualizar
        view_menu = menubar.addMenu("&Visualizar")
        
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence("Ctrl++"))
        zoom_in_action.triggered.connect(lambda: self.image_viewer._zoom_in())
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_action.triggered.connect(lambda: self.image_viewer._zoom_out())
        view_menu.addAction(zoom_out_action)
        
        zoom_reset_action = QAction("&Tamanho Real", self)
        zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset_action.triggered.connect(lambda: self.image_viewer._zoom_reset())
        view_menu.addAction(zoom_reset_action)
        
        # Menu Ajuda
        help_menu = menubar.addMenu("A&juda")
        
        about_action = QAction("&Sobre", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Configura a barra de status."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.status_file = QLabel("Nenhum arquivo carregado")
        self.status_image = QLabel("")
        self.status_modified = QLabel("")
        
        self.statusbar.addWidget(self.status_file, 1)
        self.statusbar.addWidget(self.status_image)
        self.statusbar.addWidget(self.status_modified)
    
    def _apply_dark_theme(self):
        """Aplica o tema escuro."""
        self.setStyleSheet(DARK_THEME_QSS)
    
    def _open_file(self):
        """Abre um arquivo .pic."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Tibia.pic",
            "",
            "Arquivos PIC (*.pic);;Todos os arquivos (*.*)"
        )
        
        if not file_path:
            return
        
        self._load_pic(file_path)
    
    def _load_pic(self, file_path: str):
        """Carrega um arquivo .pic."""
        try:
            self.pic = self.parser.load(file_path)
            
            # Renderizar todas as imagens
            images = []
            for pic_image in self.pic.images:
                rendered = self.parser.render_image(pic_image)
                images.append(rendered)
            
            # Atualizar thumbnail grid
            self.thumbnail_grid.set_images(images)
            
            # Atualizar status
            self.status_file.setText(f"📁 {Path(file_path).name}")
            self._update_status()
            
            self.setWindowTitle(f"Tibia PIC Editor - {Path(file_path).name}")
            
        except UnsupportedVersionError as e:
            QMessageBox.warning(self, "Versão não suportada", str(e))
        except PicParserError as e:
            QMessageBox.critical(self, "Erro ao abrir", str(e))
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Erro inesperado ao abrir arquivo:\n{str(e)}"
            )
    
    def _save_file(self):
        """Salva o arquivo atual."""
        if self.pic is None:
            return
        
        if self.pic.file_path:
            self._do_save(self.pic.file_path)
        else:
            self._save_file_as()
    
    def _save_file_as(self):
        """Salva o arquivo com novo nome."""
        if self.pic is None:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo carregado.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Como",
            "",
            "Arquivos PIC (*.pic);;Todos os arquivos (*.*)"
        )
        
        if file_path:
            self._do_save(file_path)
    
    def _do_save(self, file_path: str):
        """Executa o salvamento."""
        try:
            self.parser.save(self.pic, file_path)
            self.pic.file_path = file_path
            
            # Marcar como não modificado
            for img in self.pic.images:
                img.modified = False
            
            self.status_file.setText(f"📁 {Path(file_path).name}")
            self._update_status()
            
            QMessageBox.information(
                self, "Salvo", "Arquivo salvo com sucesso!"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Erro ao salvar", f"Não foi possível salvar:\n{str(e)}"
            )
    
    def _export_current_png(self):
        """Exporta a imagem atual como PNG."""
        if self.pic is None or self.current_image_index < 0:
            QMessageBox.warning(self, "Aviso", "Selecione uma imagem primeiro.")
            return
        
        pic_image = self.pic.images[self.current_image_index]
        image = self.parser.render_image(pic_image)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar PNG",
            f"image_{self.current_image_index + 1}.png",
            "Imagens PNG (*.png)"
        )
        
        if file_path:
            try:
                image.save(file_path, "PNG")
                QMessageBox.information(
                    self, "Exportado", f"Imagem exportada para:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro", f"Não foi possível exportar:\n{str(e)}"
                )
    
    def _export_all_pngs(self):
        """Exporta todas as imagens como PNG."""
        if self.pic is None or not self.pic.images:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo carregado.")
            return
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecionar pasta de destino"
        )
        
        if not folder:
            return
        
        try:
            for i, pic_image in enumerate(self.pic.images):
                image = self.parser.render_image(pic_image)
                file_path = Path(folder) / f"image_{i + 1:04d}.png"
                image.save(str(file_path), "PNG")
            
            QMessageBox.information(
                self, "Exportado",
                f"{len(self.pic.images)} imagens exportadas para:\n{folder}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Erro durante exportação:\n{str(e)}"
            )
    
    def _on_image_selected(self, index: int):
        """Callback quando uma imagem é selecionada no grid."""
        if self.pic is None or index < 0 or index >= len(self.pic.images):
            return
        
        self.current_image_index = index
        
        pic_image = self.pic.images[index]
        rendered = self.parser.render_image(pic_image)
        
        self.image_viewer.set_image(rendered)
        self.editor_panel.set_image(rendered)
        
        self._update_status()
    
    def _on_image_modified(self, new_image):
        """Callback quando a imagem é modificada pelo editor."""
        if self.pic is None or self.current_image_index < 0:
            return
        
        pic_image = self.pic.images[self.current_image_index]
        
        # Atualizar os sprites da imagem
        self.parser.update_image_from_pil(pic_image, new_image)
        
        # Atualizar visualização
        self.image_viewer.set_image(new_image)
        
        # Atualizar thumbnail
        rendered_images = []
        for img in self.pic.images:
            rendered_images.append(self.parser.render_image(img))
        self.thumbnail_grid.set_images(rendered_images)
        self.thumbnail_grid.select_image(self.current_image_index)
        
        self._update_status()
    
    def _update_status(self):
        """Atualiza a barra de status."""
        if self.pic is None:
            self.status_image.setText("")
            self.status_modified.setText("")
            return
        
        if self.current_image_index >= 0:
            pic_image = self.pic.images[self.current_image_index]
            self.status_image.setText(
                f"Imagem {self.current_image_index + 1}/{len(self.pic.images)} | "
                f"{pic_image.pixel_width}×{pic_image.pixel_height}px"
            )
        
        if self.pic.is_modified():
            self.status_modified.setText("● Modificado")
            self.status_modified.setStyleSheet("color: #ffa500;")
        else:
            self.status_modified.setText("")
    
    def _show_about(self):
        """Mostra o diálogo Sobre."""
        QMessageBox.about(
            self,
            "Sobre Tibia PIC Editor",
            "<h2>Tibia PIC Editor</h2>"
            "<p>Editor visual para arquivos Tibia.pic</p>"
            "<p>Baseado no pic-editor de Elime1</p>"
            "<p><small>Python + PyQt6</small></p>"
        )
    
    def closeEvent(self, event):
        """Evento de fechamento."""
        if self.pic and self.pic.is_modified():
            reply = QMessageBox.question(
                self,
                "Salvar alterações?",
                "Existem alterações não salvas. Deseja salvar antes de sair?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# Tema escuro em QSS
DARK_THEME_QSS = """
QMainWindow {
    background-color: #1e1e1e;
}

QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}

QMenuBar {
    background-color: #252526;
    color: #d4d4d4;
    border-bottom: 1px solid #3c3c3c;
    padding: 4px;
}

QMenuBar::item {
    padding: 6px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #094771;
}

QMenu {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    padding: 4px;
}

QMenu::item {
    padding: 6px 30px 6px 20px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #094771;
}

QMenu::separator {
    height: 1px;
    background-color: #3c3c3c;
    margin: 4px 10px;
}

QPushButton {
    background-color: #0e639c;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1177bb;
}

QPushButton:pressed {
    background-color: #094771;
}

QPushButton:disabled {
    background-color: #3c3c3c;
    color: #888;
}

QLabel {
    color: #d4d4d4;
}

QSlider::groove:horizontal {
    background: #3c3c3c;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #0e639c;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #1177bb;
}

QSpinBox {
    background-color: #3c3c3c;
    border: 1px solid #505050;
    border-radius: 4px;
    padding: 4px 8px;
    color: #d4d4d4;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #505050;
    border: none;
    width: 16px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #606060;
}

QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #5a5a5a;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #787878;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #5a5a5a;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #787878;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QStatusBar {
    background-color: #007acc;
    color: white;
    padding: 4px 8px;
}

QStatusBar QLabel {
    color: white;
    padding: 0 8px;
}

QGroupBox {
    color: #d4d4d4;
    font-weight: bold;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QSplitter::handle {
    background-color: #3c3c3c;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QMessageBox {
    background-color: #252526;
}

QMessageBox QLabel {
    color: #d4d4d4;
}
"""
