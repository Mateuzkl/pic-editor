"""
Parser para arquivos Tibia.pic

Implementa leitura e escrita de arquivos .pic conforme
o formato usado pelo cliente Tibia (versão 7.0+).

Baseado na implementação Java do pic-editor:
https://github.com/Elime1/pic-editor
"""

import struct
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

from src.models.pic import Pic, PicImage, Sprite, SPRITE_SIZE


class PicParserError(Exception):
    """Erro durante parsing do arquivo .pic"""
    pass


class UnsupportedVersionError(PicParserError):
    """Versão do arquivo .pic não suportada"""
    pass


class PicParser:
    """
    Parser para arquivos Tibia.pic.
    
    Suporta leitura e escrita de arquivos .pic de Tibia 7.0+.
    Versões anteriores (signature 0x1fd0302) não são suportadas.
    """
    
    # Assinatura de versões antigas (antes de 7.0)
    OLD_SIGNATURE = 0x1fd0302
    
    def __init__(self):
        self.pic: Optional[Pic] = None
    
    def load(self, file_path: str) -> Pic:
        """
        Carrega um arquivo .pic.
        
        Args:
            file_path: Caminho para o arquivo Tibia.pic
            
        Returns:
            Objeto Pic com todas as imagens carregadas
            
        Raises:
            FileNotFoundError: Se o arquivo não existir
            UnsupportedVersionError: Se for versão antiga (< 7.0)
            PicParserError: Se houver erro no parsing
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        with open(path, 'rb') as f:
            data = f.read()
        
        return self._parse(data, str(path))
    
    def _parse(self, data: bytes, file_path: str) -> Pic:
        """
        Faz o parsing dos dados binários do arquivo .pic.
        
        Args:
            data: Dados binários do arquivo
            file_path: Caminho original do arquivo
            
        Returns:
            Objeto Pic parseado
        """
        if len(data) < 6:
            raise PicParserError("Arquivo muito pequeno para ser um .pic válido")
        
        pos = 0
        
        # Ler assinatura (4 bytes, uint32 little-endian)
        signature = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        # Verificar versão antiga
        if signature == self.OLD_SIGNATURE:
            raise UnsupportedVersionError(
                "Arquivo .pic de versão antiga (anterior a Tibia 7.0) não é suportado."
            )
        
        # Ler número de imagens (2 bytes, uint16)
        num_images = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        
        # Criar objeto Pic
        pic = Pic(signature=signature, file_path=file_path)
        
        # Ler cada imagem
        for i in range(num_images):
            pic_image, pos = self._parse_image(data, pos)
            pic.images.append(pic_image)
        
        self.pic = pic
        return pic
    
    def _parse_image(self, data: bytes, pos: int) -> Tuple[PicImage, int]:
        """
        Faz o parsing de uma imagem individual.
        
        Args:
            data: Dados binários completos
            pos: Posição atual no buffer
            
        Returns:
            Tupla (PicImage, nova_posição)
        """
        # Ler dimensões da imagem em sprites
        width = data[pos]
        height = data[pos + 1]
        pos += 2
        
        # Ler cor de fundo RGB
        bg_r = data[pos]
        bg_g = data[pos + 1]
        bg_b = data[pos + 2]
        pos += 3
        
        pic_image = PicImage(
            width=width,
            height=height,
            bg_color=(bg_r, bg_g, bg_b)
        )
        
        num_sprites = width * height
        sprite_offsets = []
        
        # Ler offsets dos sprites
        for _ in range(num_sprites):
            offset = struct.unpack_from('<I', data, pos)[0]
            sprite_offsets.append(offset)
            pos += 4
        
        # Ler dados de cada sprite
        for offset in sprite_offsets:
            # Ir para a posição do sprite
            sprite_pos = offset
            
            # Ler tamanho dos dados (2 bytes)
            sprite_size = struct.unpack_from('<H', data, sprite_pos)[0]
            sprite_pos += 2
            
            # Ler dados do sprite
            pixel_data = data[sprite_pos:sprite_pos + sprite_size]
            
            sprite = Sprite(pixel_data=pixel_data)
            pic_image.sprites.append(sprite)
        
        return pic_image, pos
    
    def save(self, pic: Pic, file_path: str) -> None:
        """
        Salva um objeto Pic para arquivo .pic.
        
        Args:
            pic: Objeto Pic a ser salvo
            file_path: Caminho de destino
        """
        data = self._compile(pic)
        
        with open(file_path, 'wb') as f:
            f.write(data)
    
    def _compile(self, pic: Pic) -> bytes:
        """
        Compila um objeto Pic para bytes.
        
        Args:
            pic: Objeto Pic a compilar
            
        Returns:
            Dados binários do arquivo .pic
        """
        # Calcular tamanho total necessário
        total_size = self._calculate_total_size(pic)
        buffer = bytearray(total_size)
        pos = 0
        
        # Escrever assinatura
        struct.pack_into('<I', buffer, pos, pic.signature)
        pos += 4
        
        # Escrever número de imagens
        struct.pack_into('<H', buffer, pos, pic.num_images)
        pos += 2
        
        # Calcular onde os sprites vão começar
        sprite_data_pos = pos
        for img in pic.images:
            # 2 bytes dimensões + 3 bytes cor + 4 bytes por offset
            sprite_data_pos += 5 + (img.num_sprites * 4)
        
        # Escrever cada imagem
        for img in pic.images:
            # Dimensões
            buffer[pos] = img.width
            buffer[pos + 1] = img.height
            pos += 2
            
            # Cor de fundo
            buffer[pos] = img.bg_color[0]
            buffer[pos + 1] = img.bg_color[1]
            buffer[pos + 2] = img.bg_color[2]
            pos += 3
            
            # Escrever offsets e dados dos sprites
            for sprite in img.sprites:
                # Escrever offset para esta posição
                struct.pack_into('<I', buffer, pos, sprite_data_pos)
                pos += 4
                
                # Escrever dados do sprite na posição calculada
                sprite_size = len(sprite.pixel_data)
                struct.pack_into('<H', buffer, sprite_data_pos, sprite_size)
                sprite_data_pos += 2
                
                buffer[sprite_data_pos:sprite_data_pos + sprite_size] = sprite.pixel_data
                sprite_data_pos += sprite_size
        
        return bytes(buffer[:sprite_data_pos])
    
    def _calculate_total_size(self, pic: Pic) -> int:
        """Calcula o tamanho total do arquivo compilado."""
        size = 6  # signature + num_images
        
        for img in pic.images:
            size += 5  # width + height + bg_color
            size += img.num_sprites * 4  # offsets
            
            for sprite in img.sprites:
                size += 2 + len(sprite.pixel_data)  # size + data
        
        return size
    
    def decode_sprite(self, sprite: Sprite, bg_color: Tuple[int, int, int]) -> Image.Image:
        """
        Decodifica os dados RLE de um sprite para uma imagem PIL.
        
        Args:
            sprite: Sprite a decodificar
            bg_color: Cor de fundo RGB
            
        Returns:
            Imagem PIL RGBA de 32x32 pixels
        """
        img = Image.new('RGBA', (SPRITE_SIZE, SPRITE_SIZE), (0, 0, 0, 0))
        pixels = img.load()
        
        data = sprite.pixel_data
        if not data:
            return img
        
        pos = 0
        x = 0
        y = 0
        
        while pos < len(data) and y < SPRITE_SIZE:
            if pos + 4 > len(data):
                break
            
            # Ler contagem de pixels de fundo e coloridos
            bg_pixels = struct.unpack_from('<H', data, pos)[0]
            colored_pixels = struct.unpack_from('<H', data, pos + 2)[0]
            pos += 4
            
            # Preencher pixels de fundo (transparentes ou com cor de fundo)
            for _ in range(bg_pixels):
                if y >= SPRITE_SIZE:
                    break
                # Usar transparência ao invés de cor de fundo
                pixels[x, y] = (bg_color[0], bg_color[1], bg_color[2], 255)
                x += 1
                if x >= SPRITE_SIZE:
                    x = 0
                    y += 1
            
            # Ler e preencher pixels coloridos
            for _ in range(colored_pixels):
                if y >= SPRITE_SIZE:
                    break
                if pos + 3 > len(data):
                    break
                
                r = data[pos]
                g = data[pos + 1]
                b = data[pos + 2]
                pos += 3
                
                pixels[x, y] = (r, g, b, 255)
                x += 1
                if x >= SPRITE_SIZE:
                    x = 0
                    y += 1
        
        return img
    
    def encode_sprite(self, img: Image.Image, bg_color: Tuple[int, int, int]) -> Sprite:
        """
        Codifica uma imagem PIL para um Sprite com dados RLE.
        
        Args:
            img: Imagem PIL 32x32
            bg_color: Cor de fundo para identificar pixels de fundo
            
        Returns:
            Sprite com dados codificados
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        if img.size != (SPRITE_SIZE, SPRITE_SIZE):
            img = img.resize((SPRITE_SIZE, SPRITE_SIZE), Image.NEAREST)
        
        pixels = img.load()
        output = bytearray()
        
        x = 0
        y = 0
        total_pixels = SPRITE_SIZE * SPRITE_SIZE
        pixel_count = 0
        
        while pixel_count < total_pixels:
            bg_count = 0
            colored_data = bytearray()
            
            # Contar pixels de fundo consecutivos
            while pixel_count < total_pixels:
                px = pixels[x, y]
                
                # Verificar se é pixel de fundo (transparente ou cor de fundo)
                is_bg = (px[3] == 0) or (px[0] == bg_color[0] and px[1] == bg_color[1] and px[2] == bg_color[2])
                
                if not is_bg:
                    break
                
                bg_count += 1
                pixel_count += 1
                x += 1
                if x >= SPRITE_SIZE:
                    x = 0
                    y += 1
            
            # Coletar pixels coloridos consecutivos
            while pixel_count < total_pixels:
                px = pixels[x, y]
                
                is_bg = (px[3] == 0) or (px[0] == bg_color[0] and px[1] == bg_color[1] and px[2] == bg_color[2])
                
                if is_bg:
                    break
                
                colored_data.extend([px[0], px[1], px[2]])
                pixel_count += 1
                x += 1
                if x >= SPRITE_SIZE:
                    x = 0
                    y += 1
            
            # Escrever chunk RLE
            colored_count = len(colored_data) // 3
            output.extend(struct.pack('<HH', bg_count, colored_count))
            output.extend(colored_data)
        
        return Sprite(pixel_data=bytes(output))
    
    def render_image(self, pic_image: PicImage) -> Image.Image:
        """
        Renderiza uma PicImage completa para uma imagem PIL.
        
        Args:
            pic_image: Imagem do .pic a renderizar
            
        Returns:
            Imagem PIL RGBA completa
        """
        if pic_image._cached_image is not None:
            return pic_image._cached_image
        
        width = pic_image.pixel_width
        height = pic_image.pixel_height
        
        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        sprite_index = 0
        for row in range(pic_image.height):
            for col in range(pic_image.width):
                if sprite_index >= len(pic_image.sprites):
                    break
                
                sprite = pic_image.sprites[sprite_index]
                sprite_img = self.decode_sprite(sprite, pic_image.bg_color)
                
                x = col * SPRITE_SIZE
                y = row * SPRITE_SIZE
                result.paste(sprite_img, (x, y))
                
                sprite_index += 1
        
        pic_image._cached_image = result
        return result
    
    def update_image_from_pil(self, pic_image: PicImage, pil_image: Image.Image) -> None:
        """
        Atualiza uma PicImage a partir de uma imagem PIL.
        
        Args:
            pic_image: Imagem do .pic a atualizar
            pil_image: Imagem PIL fonte (deve ter mesmas dimensões)
        """
        if pil_image.size != (pic_image.pixel_width, pic_image.pixel_height):
            raise ValueError(
                f"Imagem deve ter {pic_image.pixel_width}x{pic_image.pixel_height} pixels"
            )
        
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        
        pic_image.sprites.clear()
        
        for row in range(pic_image.height):
            for col in range(pic_image.width):
                x = col * SPRITE_SIZE
                y = row * SPRITE_SIZE
                
                # Extrair região do sprite
                sprite_region = pil_image.crop((x, y, x + SPRITE_SIZE, y + SPRITE_SIZE))
                
                # Codificar sprite
                sprite = self.encode_sprite(sprite_region, pic_image.bg_color)
                pic_image.sprites.append(sprite)
        
        pic_image.invalidate_cache()
