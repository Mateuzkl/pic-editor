"""
Modelos de dados para o arquivo Tibia.pic

Classes que representam a estrutura do arquivo .pic conforme
implementado no pic-editor original (Java).
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from PIL import Image


# Tamanho padrão de um sprite em pixels (32x32)
SPRITE_SIZE = 32


@dataclass
class Sprite:
    """
    Representa um sprite individual dentro de uma PicImage.
    
    Attributes:
        pixel_data: Dados de pixel codificados em RLE
    """
    pixel_data: bytes = field(default_factory=bytes)
    
    def get_size(self) -> int:
        """Retorna o tamanho dos dados do sprite em bytes."""
        return len(self.pixel_data)


@dataclass
class PicImage:
    """
    Representa uma imagem dentro do arquivo .pic.
    
    Cada imagem é composta por múltiplos sprites organizados
    em uma grade (width x height).
    
    Attributes:
        width: Número de sprites na horizontal
        height: Número de sprites na vertical
        bg_color: Cor de fundo RGB (R, G, B)
        sprites: Lista de sprites que compõem a imagem
        _cached_image: Cache da imagem PIL renderizada
    """
    width: int = 1
    height: int = 1
    bg_color: Tuple[int, int, int] = (255, 0, 255)  # Magenta padrão
    sprites: List[Sprite] = field(default_factory=list)
    _cached_image: Optional[Image.Image] = field(default=None, repr=False)
    modified: bool = field(default=False, repr=False)
    
    @property
    def pixel_width(self) -> int:
        """Largura total em pixels."""
        return self.width * SPRITE_SIZE
    
    @property
    def pixel_height(self) -> int:
        """Altura total em pixels."""
        return self.height * SPRITE_SIZE
    
    @property
    def num_sprites(self) -> int:
        """Número total de sprites na imagem."""
        return self.width * self.height
    
    def invalidate_cache(self):
        """Invalida o cache da imagem renderizada."""
        self._cached_image = None
        self.modified = True
    
    def get_sprite_data_size(self) -> int:
        """Calcula o tamanho total dos dados de sprites em bytes."""
        size = 0
        for sprite in self.sprites:
            # 4 bytes para offset + 2 bytes para tamanho + dados
            size += 4 + 2 + sprite.get_size()
        return size


@dataclass
class Pic:
    """
    Representa um arquivo Tibia.pic completo.
    
    Attributes:
        signature: Assinatura de versão do arquivo (4 bytes)
        images: Lista de imagens contidas no arquivo
        file_path: Caminho do arquivo original (se carregado)
    """
    signature: int = 0
    images: List[PicImage] = field(default_factory=list)
    file_path: Optional[str] = None
    
    @property
    def num_images(self) -> int:
        """Número total de imagens no arquivo."""
        return len(self.images)
    
    def get_image(self, index: int) -> Optional[PicImage]:
        """Retorna uma imagem pelo índice."""
        if 0 <= index < len(self.images):
            return self.images[index]
        return None
    
    def is_modified(self) -> bool:
        """Verifica se alguma imagem foi modificada."""
        return any(img.modified for img in self.images)
