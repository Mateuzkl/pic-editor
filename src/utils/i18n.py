"""
Sistema de internacionalização (i18n) para o Tibia PIC Editor.

Suporte a múltiplos idiomas: Português e Inglês.
"""

from typing import Dict

# Idiomas disponíveis
LANGUAGES = {
    "pt_BR": "Português",
    "en_US": "English"
}

# Traduções
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "pt_BR": {
        # Menu
        "menu_file": "&Arquivo",
        "menu_open": "&Abrir...",
        "menu_save": "&Salvar",
        "menu_save_as": "Salvar &Como...",
        "menu_export_png": "&Exportar PNG...",
        "menu_export_all": "Exportar &Todas as PNGs...",
        "menu_exit": "&Sair",
        "menu_view": "&Visualizar",
        "menu_zoom_in": "Zoom &In",
        "menu_zoom_out": "Zoom &Out",
        "menu_zoom_reset": "&Tamanho Real",
        "menu_language": "&Idioma",
        "menu_help": "A&juda",
        "menu_about": "&Sobre",
        
        # Thumbnail Grid
        "images": "Imagens",
        "no_file": "Nenhum arquivo carregado",
        "total_images": "Total: {count} imagens",
        
        # Editor Panel
        "editing_tools": "Ferramentas de Edição",
        "color_swap": "🎨 Trocar Cor",
        "from": "De:",
        "tolerance": "Tolerância:",
        "apply_color": "Aplicar Troca de Cor",
        "filters": "🌈 Filtros",
        "brightness": "Brilho",
        "contrast": "Contraste",
        "saturation": "Saturação",
        "apply_filters": "Aplicar Filtros",
        "replace_image": "🖼️ Substituir Imagem",
        "import_png": "Importar PNG...",
        "reset": "↩️ Resetar",
        
        # Dialogs
        "open_pic": "Abrir Tibia.pic",
        "save_as": "Salvar Como",
        "export_png": "Exportar PNG",
        "select_folder": "Selecionar pasta de destino",
        "select_image": "Selecione uma imagem primeiro.",
        "warning": "Aviso",
        "error": "Erro",
        "saved": "Salvo",
        "exported": "Exportado",
        "file_saved": "Arquivo salvo com sucesso!",
        "image_exported": "Imagem exportada para:\n{path}",
        "images_exported": "{count} imagens exportadas para:\n{folder}",
        "resize": "Redimensionar",
        "resize_question": "A imagem importada ({w1}x{h1}) tem dimensões diferentes da original ({w2}x{h2}).\n\nDeseja redimensionar automaticamente?",
        "open_error": "Erro ao abrir",
        "save_error": "Erro ao salvar",
        "export_error": "Erro durante exportação:\n{error}",
        "unsupported_version": "Versão não suportada",
        "unsaved_changes": "Salvar alterações?",
        "unsaved_question": "Existem alterações não salvas. Deseja salvar antes de sair?",
        
        # Status
        "no_file_loaded": "Nenhum arquivo carregado",
        "image_info": "Imagem {current}/{total} | {width}×{height}px",
        "modified": "● Modificado",
        
        # About
        "about_title": "Sobre Tibia PIC Editor",
        "about_text": "<h2>Tibia PIC Editor</h2><p>Editor visual para arquivos Tibia.pic</p><p>Baseado no pic-editor de Elime1</p><p><small>Python + PyQt6</small></p>",
        
        # File filters
        "pic_files": "Arquivos PIC (*.pic)",
        "png_files": "Imagens PNG (*.png)",
        "all_files": "Todos os arquivos (*.*)",

        # Coordinate Inspector
        "mode_edit": "Editar",
        "mode_inspect": "Inspecionar",
        "menu_fit": "Ajustar imagem",
        "menu_actual_size": "Zoom 100%",
        "inspector_info": "Inspetor de Coordenadas",
        "inspector_image": "Imagem:",
        "inspector_mouse": "Posição do mouse:",
        "inspector_selection": "Região selecionada",
        "inspector_sprites": "Sprites:",
        "inspector_snap_grid": "Encaixar na grade 32×32",
        "inspector_snap_pixel": "Seleção livre por pixel",
        "inspector_clear": "Limpar",
        "inspector_full_image": "Imagem inteira",
        "inspector_overlays": "Sobreposições",
        "inspector_sprite_grid": "Mostrar grade de sprites 32×32",
        "inspector_pixel_grid": "Mostrar grade de pixels (800%+)",
        "inspector_rulers": "Mostrar réguas",
        "inspector_coordinates": "Mostrar coordenadas",
        "inspector_code": "Copiar código para DLL",
        "inspector_constant_name": "Nome da constante:",
        "inspector_image_expression": "Imagem C++:",
        "inspector_renderer_expression": "Renderer C++:",
        "inspector_copy_rect": "Copiar retângulo",
        "inspector_copy_cpp": "Copiar constantes C++",
        "inspector_copy_struct": "Copiar estrutura C++",
        "inspector_copy_draw": "Copiar drawPicture",
        "inspector_copy_json": "Copiar JSON",
        "inspector_copy_csv": "Copiar CSV",
        "inspector_detection": "Detecção de regiões",
        "inspector_tolerance": "Tolerância do fundo",
        "inspector_min_width": "Largura mínima",
        "inspector_min_height": "Altura mínima",
        "inspector_min_area": "Área mínima",
        "inspector_merge": "Distância para unir",
        "inspector_margin": "Margem da seleção",
        "inspector_connectivity": "Conectividade",
        "inspector_include_transparent": "Incluir regiões transparentes",
        "inspector_magic_select": "Seleção mágica por clique",
        "inspector_detect": "Detectar regiões",
        "inspector_clear_boxes": "Limpar caixas",
        "inspector_saved_regions": "Regiões salvas",
        "inspector_region_name": "Nome",
        "inspector_region_image": "Imagem",
        "inspector_notes": "Observações da região",
        "inspector_add": "Adicionar",
        "inspector_rename": "Atualizar",
        "inspector_duplicate": "Duplicar",
        "inspector_remove": "Remover",
        "inspector_sort": "Ordenar",
        "inspector_save_project": "Salvar projeto",
        "inspector_load_project": "Abrir projeto",
        "inspector_export_region": "Exportar região PNG",
        "inspector_export_all_regions": "Exportar todas",
        "inspector_select_first": "Selecione uma região da imagem primeiro.",
        "inspector_hash_mismatch": "Este projeto pertence a outro arquivo PIC (assinatura, tamanho ou SHA-256 diferente). Nenhuma região foi aplicada.",
    },
    
    "en_US": {
        # Menu
        "menu_file": "&File",
        "menu_open": "&Open...",
        "menu_save": "&Save",
        "menu_save_as": "Save &As...",
        "menu_export_png": "&Export PNG...",
        "menu_export_all": "Export &All PNGs...",
        "menu_exit": "E&xit",
        "menu_view": "&View",
        "menu_zoom_in": "Zoom &In",
        "menu_zoom_out": "Zoom &Out",
        "menu_zoom_reset": "&Actual Size",
        "menu_language": "&Language",
        "menu_help": "&Help",
        "menu_about": "&About",
        
        # Thumbnail Grid
        "images": "Images",
        "no_file": "No file loaded",
        "total_images": "Total: {count} images",
        
        # Editor Panel
        "editing_tools": "Editing Tools",
        "color_swap": "🎨 Color Swap",
        "from": "From:",
        "tolerance": "Tolerance:",
        "apply_color": "Apply Color Swap",
        "filters": "🌈 Filters",
        "brightness": "Brightness",
        "contrast": "Contrast",
        "saturation": "Saturation",
        "apply_filters": "Apply Filters",
        "replace_image": "🖼️ Replace Image",
        "import_png": "Import PNG...",
        "reset": "↩️ Reset",
        
        # Dialogs
        "open_pic": "Open Tibia.pic",
        "save_as": "Save As",
        "export_png": "Export PNG",
        "select_folder": "Select destination folder",
        "select_image": "Select an image first.",
        "warning": "Warning",
        "error": "Error",
        "saved": "Saved",
        "exported": "Exported",
        "file_saved": "File saved successfully!",
        "image_exported": "Image exported to:\n{path}",
        "images_exported": "{count} images exported to:\n{folder}",
        "resize": "Resize",
        "resize_question": "The imported image ({w1}x{h1}) has different dimensions from the original ({w2}x{h2}).\n\nDo you want to resize automatically?",
        "open_error": "Error opening file",
        "save_error": "Error saving file",
        "export_error": "Error during export:\n{error}",
        "unsupported_version": "Unsupported version",
        "unsaved_changes": "Save changes?",
        "unsaved_question": "There are unsaved changes. Do you want to save before exiting?",
        
        # Status
        "no_file_loaded": "No file loaded",
        "image_info": "Image {current}/{total} | {width}×{height}px",
        "modified": "● Modified",
        
        # About
        "about_title": "About Tibia PIC Editor",
        "about_text": "<h2>Tibia PIC Editor</h2><p>Visual editor for Tibia.pic files</p><p>Based on pic-editor by Elime1</p><p><small>Python + PyQt6</small></p>",
        
        # File filters
        "pic_files": "PIC Files (*.pic)",
        "png_files": "PNG Images (*.png)",
        "all_files": "All files (*.*)",

        # Coordinate Inspector
        "mode_edit": "Edit",
        "mode_inspect": "Inspect",
        "menu_fit": "Fit image",
        "menu_actual_size": "100% zoom",
        "inspector_info": "Coordinate Inspector",
        "inspector_image": "Image:",
        "inspector_mouse": "Mouse position:",
        "inspector_selection": "Selected region",
        "inspector_sprites": "Sprites:",
        "inspector_snap_grid": "Snap to 32×32 sprite grid",
        "inspector_snap_pixel": "Free pixel selection",
        "inspector_clear": "Clear",
        "inspector_full_image": "Full image",
        "inspector_overlays": "Overlays",
        "inspector_sprite_grid": "Show 32×32 sprite grid",
        "inspector_pixel_grid": "Show pixel grid (800%+)",
        "inspector_rulers": "Show rulers",
        "inspector_coordinates": "Show coordinates",
        "inspector_code": "Copy code for DLL",
        "inspector_constant_name": "Constant name:",
        "inspector_image_expression": "C++ image:",
        "inspector_renderer_expression": "C++ renderer:",
        "inspector_copy_rect": "Copy Rect",
        "inspector_copy_cpp": "Copy C++ Constants",
        "inspector_copy_struct": "Copy C++ Struct",
        "inspector_copy_draw": "Copy drawPicture",
        "inspector_copy_json": "Copy JSON",
        "inspector_copy_csv": "Copy CSV",
        "inspector_detection": "Region Detection",
        "inspector_tolerance": "Background tolerance",
        "inspector_min_width": "Minimum width",
        "inspector_min_height": "Minimum height",
        "inspector_min_area": "Minimum area",
        "inspector_merge": "Merge distance",
        "inspector_margin": "Selection margin",
        "inspector_connectivity": "Connectivity",
        "inspector_include_transparent": "Include transparent regions",
        "inspector_magic_select": "Magic Select on click",
        "inspector_detect": "Auto Detect Regions",
        "inspector_clear_boxes": "Clear boxes",
        "inspector_saved_regions": "Saved Regions",
        "inspector_region_name": "Name",
        "inspector_region_image": "Image",
        "inspector_notes": "Region notes",
        "inspector_add": "Add",
        "inspector_rename": "Update",
        "inspector_duplicate": "Duplicate",
        "inspector_remove": "Remove",
        "inspector_sort": "Sort",
        "inspector_save_project": "Save project",
        "inspector_load_project": "Open project",
        "inspector_export_region": "Export Region PNG",
        "inspector_export_all_regions": "Export all",
        "inspector_select_first": "Select an image region first.",
        "inspector_hash_mismatch": "This project belongs to another PIC file (different signature, size, or SHA-256). No region was applied.",
    }
}


class Translator:
    """Gerencia traduções e idioma atual."""
    
    _instance = None
    _current_lang = "pt_BR"
    _callbacks = []
    
    @classmethod
    def instance(cls) -> 'Translator':
        """Retorna a instância singleton."""
        if cls._instance is None:
            cls._instance = Translator()
        return cls._instance
    
    def get_language(self) -> str:
        """Retorna o idioma atual."""
        return self._current_lang
    
    def set_language(self, lang: str):
        """Define o idioma."""
        if lang in TRANSLATIONS:
            self._current_lang = lang
            self._notify_callbacks()
    
    def tr(self, key: str, **kwargs) -> str:
        """
        Traduz uma chave para o idioma atual.
        
        Args:
            key: Chave da tradução
            **kwargs: Variáveis para substituir na string
            
        Returns:
            String traduzida
        """
        translations = TRANSLATIONS.get(self._current_lang, TRANSLATIONS["en_US"])
        text = translations.get(key, key)
        
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    def register_callback(self, callback):
        """Registra callback para mudança de idioma."""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """Remove callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Notifica callbacks sobre mudança de idioma."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass


# Função de conveniência
def tr(key: str, **kwargs) -> str:
    """Traduz uma chave."""
    return Translator.instance().tr(key, **kwargs)
