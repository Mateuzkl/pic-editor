"""
Janela principal da aplicação.

Integra todos os componentes: thumbnail grid, image viewer,
editor panel, e barra de menu.
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar, QFileDialog,
    QMessageBox, QLabel, QTabWidget, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QActionGroup, QShortcut

from src.parsers.pic_parser import PicParser, PicParserError, UnsupportedVersionError
from src.models.pic import Pic
from src.models.region import AtlasRegion
from src.ui.thumbnail_grid import ThumbnailGrid
from src.ui.image_viewer import ImageViewer
from src.ui.editor_panel import EditorPanel
from src.ui.coordinate_inspector import CoordinateInspector
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
        self.resize(1320, 840)
        
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
        self.editor_panel.image_modified.connect(self._on_image_modified)
        self.coordinate_inspector = CoordinateInspector(self.image_viewer)
        self.coordinate_inspector.region_activated.connect(self._on_region_activated)
        self.side_tabs = QTabWidget()
        self.side_tabs.setMinimumWidth(380)
        self.side_tabs.setMaximumWidth(520)
        self.side_tabs.addTab(self.editor_panel, tr("mode_edit"))
        self.side_tabs.addTab(self.coordinate_inspector, tr("mode_inspect"))
        self.side_tabs.currentChanged.connect(self._on_mode_changed)
        splitter.addWidget(self.side_tabs)
        
        # Proporções do splitter
        splitter.setSizes([200, 700, 400])
        
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

        self.fit_action = QAction(tr("menu_fit"), self)
        self.fit_action.triggered.connect(self.image_viewer.fit_image)
        self.view_menu.addAction(self.fit_action)

        self.actual_size_action = QAction(tr("menu_actual_size"), self)
        self.actual_size_action.triggered.connect(self.image_viewer._zoom_reset)
        self.view_menu.addAction(self.actual_size_action)

        self.view_menu.addSeparator()
        self.inspector_action = QAction(tr("mode_inspect"), self)
        self.inspector_action.setShortcut(QKeySequence("Ctrl+I"))
        self.inspector_action.triggered.connect(self._toggle_inspector)
        self.view_menu.addAction(self.inspector_action)

        self.sprite_grid_action = QAction(tr("inspector_sprite_grid"), self)
        self.sprite_grid_action.triggered.connect(self.coordinate_inspector.toggle_sprite_grid)
        self.view_menu.addAction(self.sprite_grid_action)

        self.pixel_grid_action = QAction(tr("inspector_pixel_grid"), self)
        self.pixel_grid_action.triggered.connect(self.coordinate_inspector.toggle_pixel_grid)
        self.view_menu.addAction(self.pixel_grid_action)

        self.copy_rect_action = QAction(tr("inspector_copy_rect"), self)
        self.copy_rect_action.setShortcut(QKeySequence("Ctrl+C"))
        self.copy_rect_action.triggered.connect(
            lambda: self._copy_inspector_format("rect")
        )
        self.addAction(self.copy_rect_action)

        self.copy_cpp_action = QAction(tr("inspector_copy_cpp"), self)
        self.copy_cpp_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.copy_cpp_action.triggered.connect(
            lambda: self._copy_inspector_format("constants")
        )
        self.addAction(self.copy_cpp_action)

        # Single-key shortcuts belong to the canvas so they never steal text input.
        self.fit_shortcut = QShortcut(QKeySequence("F"), self.image_viewer.canvas)
        self.fit_shortcut.activated.connect(self.image_viewer.fit_image)
        self.actual_size_shortcut = QShortcut(QKeySequence("1"), self.image_viewer.canvas)
        self.actual_size_shortcut.activated.connect(self.image_viewer._zoom_reset)
        self.sprite_grid_shortcut = QShortcut(QKeySequence("G"), self.image_viewer.canvas)
        self.sprite_grid_shortcut.activated.connect(self.coordinate_inspector.toggle_sprite_grid)
        self.pixel_grid_shortcut = QShortcut(QKeySequence("P"), self.image_viewer.canvas)
        self.pixel_grid_shortcut.activated.connect(self.coordinate_inspector.toggle_pixel_grid)
        for shortcut in (
            self.fit_shortcut,
            self.actual_size_shortcut,
            self.sprite_grid_shortcut,
            self.pixel_grid_shortcut,
        ):
            shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        
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
        self.fit_action.setText(tr("menu_fit"))
        self.actual_size_action.setText(tr("menu_actual_size"))
        self.inspector_action.setText(tr("mode_inspect"))
        self.sprite_grid_action.setText(tr("inspector_sprite_grid"))
        self.pixel_grid_action.setText(tr("inspector_pixel_grid"))
        self.copy_rect_action.setText(tr("inspector_copy_rect"))
        self.copy_cpp_action.setText(tr("inspector_copy_cpp"))
        self.side_tabs.setTabText(0, tr("mode_edit"))
        self.side_tabs.setTabText(1, tr("mode_inspect"))
        self.coordinate_inspector.retranslate_ui()
        
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
            self.coordinate_inspector.set_pic(self.pic)
            if images:
                self.thumbnail_grid.select_image(0)
                self._on_image_selected(0)
            
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
            self.coordinate_inspector.refresh_pic_identity()
            
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
        self.coordinate_inspector.set_context(
            self.pic, index, pic_image, rendered
        )
        
        self._update_status()
    
    def _on_image_modified(self, new_image):
        """Callback quando a imagem é modificada pelo editor."""
        if self.pic is None or self.current_image_index < 0:
            return
        
        pic_image = self.pic.images[self.current_image_index]
        
        # Atualizar os sprites da imagem
        self.parser.update_image_from_pil(pic_image, new_image)
        
        # Atualizar visualização
        rendered_images = []
        for img in self.pic.images:
            rendered_images.append(self.parser.render_image(img))
        current_rendered = rendered_images[self.current_image_index]
        self.image_viewer.set_image(current_rendered)
        self.coordinate_inspector.set_context(
            self.pic,
            self.current_image_index,
            pic_image,
            current_rendered,
        )
        self.thumbnail_grid.set_images(rendered_images)
        self.thumbnail_grid.select_image(self.current_image_index)

        self._update_status()

    def _on_mode_changed(self, index: int):
        """Keep editing and coordinate selection as distinct modes."""
        self.image_viewer.set_inspection_enabled(index == 1)
        if index == 1:
            self.image_viewer.canvas.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _toggle_inspector(self):
        self.side_tabs.setCurrentIndex(0 if self.side_tabs.currentIndex() == 1 else 1)

    def _copy_inspector_format(self, format_name: str):
        if self.side_tabs.currentIndex() == 1:
            focus_widget = QApplication.focusWidget()
            if format_name == "rect" and focus_widget is not None and hasattr(focus_widget, "copy"):
                focus_widget.copy()
                return
            self.coordinate_inspector.copy_format(format_name)

    def _on_region_activated(self, region: AtlasRegion):
        if self.pic is None or not (0 <= region.image_index < len(self.pic.images)):
            return
        self.thumbnail_grid.select_image(region.image_index)
        self._on_image_selected(region.image_index)
        self.side_tabs.setCurrentIndex(1)
        self.image_viewer.canvas.set_selection(
            (region.x, region.y, region.width, region.height),
            apply_snap=False,
        )
        self.image_viewer.center_on_selection()

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
        self.coordinate_inspector.shutdown()
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

QWidget#coordinateInspector QPushButton {
    padding: 6px 8px;
    font-size: 11px;
}

QLineEdit, QTextEdit, QComboBox, QTreeWidget {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #505050;
    border-radius: 4px;
    padding: 4px;
    selection-background-color: #0e639c;
}

QTreeWidget::item:selected {
    background-color: #094771;
}

QHeaderView::section {
    background-color: #333333;
    color: #d4d4d4;
    border: none;
    border-right: 1px solid #505050;
    padding: 4px;
}

QTabWidget::pane {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #252526;
    color: #aaaaaa;
    padding: 8px 16px;
    border: 1px solid #3c3c3c;
}

QTabBar::tab:selected {
    background-color: #0e639c;
    color: white;
}

QProgressBar {
    background-color: #252526;
    border: 1px solid #505050;
    border-radius: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0e639c;
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
