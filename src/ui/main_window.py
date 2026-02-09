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
from PyQt6.QtGui import QAction, QKeySequence, QActionGroup

from src.parsers.pic_parser import PicParser, PicParserError, UnsupportedVersionError
from src.models.pic import Pic, PicImage
from src.ui.thumbnail_grid import ThumbnailGrid
from src.ui.image_viewer import ImageViewer
from src.ui.editor_panel import EditorPanel
from src.utils.i18n import tr, Translator, LANGUAGES


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
        
        # Registrar para mudanças de idioma
        Translator.instance().register_callback(self._update_texts)
    
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
        self.file_menu = menubar.addMenu(tr("menu_file"))
        
        self.open_action = QAction(tr("menu_open"), self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self._open_file)
        self.file_menu.addAction(self.open_action)
        
        self.save_action = QAction(tr("menu_save"), self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self._save_file)
        self.file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction(tr("menu_save_as"), self)
        self.save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.save_as_action.triggered.connect(self._save_file_as)
        self.file_menu.addAction(self.save_as_action)
        
        self.file_menu.addSeparator()
        
        self.export_action = QAction(tr("menu_export_png"), self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.triggered.connect(self._export_current_png)
        self.file_menu.addAction(self.export_action)
        
        self.export_all_action = QAction(tr("menu_export_all"), self)
        self.export_all_action.triggered.connect(self._export_all_pngs)
        self.file_menu.addAction(self.export_all_action)
        
        self.file_menu.addSeparator()
        
        self.exit_action = QAction(tr("menu_exit"), self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)
        
        # Menu Visualizar
        self.view_menu = menubar.addMenu(tr("menu_view"))
        
        self.zoom_in_action = QAction(tr("menu_zoom_in"), self)
        self.zoom_in_action.setShortcut(QKeySequence("Ctrl++"))
        self.zoom_in_action.triggered.connect(lambda: self.image_viewer._zoom_in())
        self.view_menu.addAction(self.zoom_in_action)
        
        self.zoom_out_action = QAction(tr("menu_zoom_out"), self)
        self.zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        self.zoom_out_action.triggered.connect(lambda: self.image_viewer._zoom_out())
        self.view_menu.addAction(self.zoom_out_action)
        
        self.zoom_reset_action = QAction(tr("menu_zoom_reset"), self)
        self.zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        self.zoom_reset_action.triggered.connect(lambda: self.image_viewer._zoom_reset())
        self.view_menu.addAction(self.zoom_reset_action)
        
        # Menu Idioma
        self.lang_menu = menubar.addMenu(tr("menu_language"))
        self.lang_action_group = QActionGroup(self)
        self.lang_actions = {}
        
        for lang_code, lang_name in LANGUAGES.items():
            action = QAction(lang_name, self)
            action.setCheckable(True)
            action.setChecked(lang_code == Translator.instance().get_language())
            action.triggered.connect(lambda checked, lc=lang_code: self._change_language(lc))
            self.lang_action_group.addAction(action)
            self.lang_menu.addAction(action)
            self.lang_actions[lang_code] = action
        
        # Menu Ajuda
        self.help_menu = menubar.addMenu(tr("menu_help"))
        
        self.about_action = QAction(tr("menu_about"), self)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.about_action)
    
    def _setup_statusbar(self):
        """Configura a barra de status."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.status_file = QLabel(tr("no_file_loaded"))
        self.status_image = QLabel("")
        self.status_modified = QLabel("")
        
        self.statusbar.addWidget(self.status_file, 1)
        self.statusbar.addWidget(self.status_image)
        self.statusbar.addWidget(self.status_modified)
    
    def _apply_dark_theme(self):
        """Aplica o tema escuro."""
        self.setStyleSheet(DARK_THEME_QSS)
    
    def _change_language(self, lang_code: str):
        """Muda o idioma da aplicação."""
        Translator.instance().set_language(lang_code)
        
        # Atualizar checkmarks
        for lc, action in self.lang_actions.items():
            action.setChecked(lc == lang_code)
    
    def _update_texts(self):
        """Atualiza todos os textos quando o idioma muda."""
        # Menus
        self.file_menu.setTitle(tr("menu_file"))
        self.open_action.setText(tr("menu_open"))
        self.save_action.setText(tr("menu_save"))
        self.save_as_action.setText(tr("menu_save_as"))
        self.export_action.setText(tr("menu_export_png"))
        self.export_all_action.setText(tr("menu_export_all"))
        self.exit_action.setText(tr("menu_exit"))
        
        self.view_menu.setTitle(tr("menu_view"))
        self.zoom_in_action.setText(tr("menu_zoom_in"))
        self.zoom_out_action.setText(tr("menu_zoom_out"))
        self.zoom_reset_action.setText(tr("menu_zoom_reset"))
        
        self.lang_menu.setTitle(tr("menu_language"))
        
        self.help_menu.setTitle(tr("menu_help"))
        self.about_action.setText(tr("menu_about"))
        
        # Status bar
        if self.pic is None:
            self.status_file.setText(tr("no_file_loaded"))
        
        self._update_status()
    
    def _open_file(self):
        """Abre um arquivo .pic."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("open_pic"),
            "",
            f"{tr('pic_files')};;{tr('all_files')}"
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
            QMessageBox.warning(self, tr("unsupported_version"), str(e))
        except PicParserError as e:
            QMessageBox.critical(self, tr("open_error"), str(e))
        except Exception as e:
            QMessageBox.critical(
                self, tr("error"), f"{tr('open_error')}:\n{str(e)}"
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
            QMessageBox.warning(self, tr("warning"), tr("no_file_loaded"))
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("save_as"),
            "",
            f"{tr('pic_files')};;{tr('all_files')}"
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
                self, tr("saved"), tr("file_saved")
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, tr("save_error"), f"{tr('save_error')}:\n{str(e)}"
            )
    
    def _export_current_png(self):
        """Exporta a imagem atual como PNG."""
        if self.pic is None or self.current_image_index < 0:
            QMessageBox.warning(self, tr("warning"), tr("select_image"))
            return
        
        pic_image = self.pic.images[self.current_image_index]
        image = self.parser.render_image(pic_image)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("export_png"),
            f"image_{self.current_image_index + 1}.png",
            tr("png_files")
        )
        
        if file_path:
            try:
                image.save(file_path, "PNG")
                QMessageBox.information(
                    self, tr("exported"), tr("image_exported", path=file_path)
                )
            except Exception as e:
                QMessageBox.critical(
                    self, tr("error"), tr("export_error", error=str(e))
                )
    
    def _export_all_pngs(self):
        """Exporta todas as imagens como PNG."""
        if self.pic is None or not self.pic.images:
            QMessageBox.warning(self, tr("warning"), tr("no_file_loaded"))
            return
        
        folder = QFileDialog.getExistingDirectory(
            self,
            tr("select_folder")
        )
        
        if not folder:
            return
        
        try:
            for i, pic_image in enumerate(self.pic.images):
                image = self.parser.render_image(pic_image)
                file_path = Path(folder) / f"image_{i + 1:04d}.png"
                image.save(str(file_path), "PNG")
            
            QMessageBox.information(
                self, tr("exported"),
                tr("images_exported", count=len(self.pic.images), folder=folder)
            )
        except Exception as e:
            QMessageBox.critical(
                self, tr("error"), tr("export_error", error=str(e))
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
                tr("image_info",
                   current=self.current_image_index + 1,
                   total=len(self.pic.images),
                   width=pic_image.pixel_width,
                   height=pic_image.pixel_height)
            )
        
        if self.pic.is_modified():
            self.status_modified.setText(tr("modified"))
            self.status_modified.setStyleSheet("color: #ffa500;")
        else:
            self.status_modified.setText("")
    
    def _show_about(self):
        """Mostra o diálogo Sobre."""
        QMessageBox.about(
            self,
            tr("about_title"),
            tr("about_text")
        )
    
    def closeEvent(self, event):
        """Evento de fechamento."""
        if self.pic and self.pic.is_modified():
            reply = QMessageBox.question(
                self,
                tr("unsaved_changes"),
                tr("unsaved_question"),
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
