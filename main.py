"""
Tibia PIC Editor - Entry Point

Editor visual para arquivos Tibia.pic com interface moderna.
"""

import sys
import os

# Adicionar src ao path
src_path = os.path.dirname(os.path.abspath(__file__))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from src.ui.main_window import MainWindow


def main():
    """Função principal da aplicação."""
    # Habilitar High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Tibia PIC Editor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("TibiaTools")
    
    # Aplicar estilo Fusion para melhor aparência em Windows
    app.setStyle("Fusion")
    
    # Criar e mostrar janela principal
    window = MainWindow()
    window.show()
    
    # Executar loop de eventos
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
