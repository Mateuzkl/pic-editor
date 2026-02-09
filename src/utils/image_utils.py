"""
Utilitários para manipulação de imagens.

Funções auxiliares para conversão entre PIL e Qt,
aplicação de filtros, e manipulação de cores.
"""

from typing import Tuple, Optional
from PIL import Image, ImageEnhance
from PyQt6.QtGui import QImage, QPixmap
import numpy as np


def pil_to_qpixmap(pil_image: Optional[Image.Image]) -> QPixmap:
    """
    Converte uma imagem PIL para QPixmap do Qt.
    
    Args:
        pil_image: Imagem PIL (pode ser None)
        
    Returns:
        QPixmap correspondente
    """
    if pil_image is None:
        return QPixmap()
    
    if pil_image.mode == 'RGBA':
        data = pil_image.tobytes('raw', 'RGBA')
        qimage = QImage(
            data,
            pil_image.width,
            pil_image.height,
            pil_image.width * 4,
            QImage.Format.Format_RGBA8888
        )
    elif pil_image.mode == 'RGB':
        data = pil_image.tobytes('raw', 'RGB')
        qimage = QImage(
            data,
            pil_image.width,
            pil_image.height,
            pil_image.width * 3,
            QImage.Format.Format_RGB888
        )
    else:
        # Converter para RGBA
        pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes('raw', 'RGBA')
        qimage = QImage(
            data,
            pil_image.width,
            pil_image.height,
            pil_image.width * 4,
            QImage.Format.Format_RGBA8888
        )
    
    return QPixmap.fromImage(qimage.copy())


def qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    """
    Converte um QPixmap para imagem PIL.
    
    Args:
        pixmap: QPixmap do Qt
        
    Returns:
        Imagem PIL RGBA
    """
    qimage = pixmap.toImage()
    qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
    
    width = qimage.width()
    height = qimage.height()
    
    ptr = qimage.bits()
    ptr.setsize(height * width * 4)
    
    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    return Image.fromarray(arr, 'RGBA')


def apply_brightness(image: Image.Image, factor: float) -> Image.Image:
    """
    Aplica ajuste de brilho.
    
    Args:
        image: Imagem PIL
        factor: Fator de brilho (1.0 = original, >1 = mais brilho)
        
    Returns:
        Imagem ajustada
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Separar canal alpha
    r, g, b, a = image.split()
    rgb = Image.merge('RGB', (r, g, b))
    
    enhancer = ImageEnhance.Brightness(rgb)
    rgb = enhancer.enhance(factor)
    
    # Recompor com alpha
    r, g, b = rgb.split()
    return Image.merge('RGBA', (r, g, b, a))


def apply_contrast(image: Image.Image, factor: float) -> Image.Image:
    """
    Aplica ajuste de contraste.
    
    Args:
        image: Imagem PIL
        factor: Fator de contraste (1.0 = original)
        
    Returns:
        Imagem ajustada
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    r, g, b, a = image.split()
    rgb = Image.merge('RGB', (r, g, b))
    
    enhancer = ImageEnhance.Contrast(rgb)
    rgb = enhancer.enhance(factor)
    
    r, g, b = rgb.split()
    return Image.merge('RGBA', (r, g, b, a))


def apply_saturation(image: Image.Image, factor: float) -> Image.Image:
    """
    Aplica ajuste de saturação.
    
    Args:
        image: Imagem PIL
        factor: Fator de saturação (1.0 = original, 0 = grayscale)
        
    Returns:
        Imagem ajustada
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    r, g, b, a = image.split()
    rgb = Image.merge('RGB', (r, g, b))
    
    enhancer = ImageEnhance.Color(rgb)
    rgb = enhancer.enhance(factor)
    
    r, g, b = rgb.split()
    return Image.merge('RGBA', (r, g, b, a))


def replace_color(
    image: Image.Image,
    old_color: Tuple[int, int, int],
    new_color: Tuple[int, int, int],
    tolerance: int = 0
) -> Image.Image:
    """
    Substitui uma cor por outra na imagem.
    
    Args:
        image: Imagem PIL
        old_color: Cor a ser substituída (R, G, B)
        new_color: Nova cor (R, G, B)
        tolerance: Tolerância para matching (0-255)
        
    Returns:
        Imagem com cores substituídas
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    data = np.array(image)
    
    # Criar máscara para pixels que batem com a cor antiga
    r_match = np.abs(data[:, :, 0].astype(int) - old_color[0]) <= tolerance
    g_match = np.abs(data[:, :, 1].astype(int) - old_color[1]) <= tolerance
    b_match = np.abs(data[:, :, 2].astype(int) - old_color[2]) <= tolerance
    
    mask = r_match & g_match & b_match
    
    # Substituir cores
    data[mask, 0] = new_color[0]
    data[mask, 1] = new_color[1]
    data[mask, 2] = new_color[2]
    
    return Image.fromarray(data, 'RGBA')


def create_checkerboard(width: int, height: int, square_size: int = 8) -> Image.Image:
    """
    Cria um padrão de tabuleiro para visualizar transparência.
    
    Args:
        width: Largura da imagem
        height: Altura da imagem
        square_size: Tamanho de cada quadrado
        
    Returns:
        Imagem PIL RGB com padrão de tabuleiro
    """
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    
    color1 = (200, 200, 200)
    color2 = (255, 255, 255)
    
    for y in range(height):
        for x in range(width):
            if ((x // square_size) + (y // square_size)) % 2 == 0:
                pixels[x, y] = color1
            else:
                pixels[x, y] = color2
    
    return img


def composite_on_checkerboard(image: Image.Image) -> Image.Image:
    """
    Compõe uma imagem RGBA sobre um fundo de tabuleiro.
    
    Args:
        image: Imagem PIL RGBA
        
    Returns:
        Imagem RGB com fundo de tabuleiro
    """
    if image.mode != 'RGBA':
        return image.convert('RGB')
    
    background = create_checkerboard(image.width, image.height)
    background.paste(image, (0, 0), image)
    
    return background
