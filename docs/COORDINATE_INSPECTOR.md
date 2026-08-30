# Coordinate Inspector — referência técnica

## Objetivo e integridade

O Inspector trabalha sobre a imagem PIL já renderizada por `PicParser.render_image()`. Ele não decodifica novamente o formato, não altera RLE, offsets, assinatura, sprites ou pixels. Somente as ferramentas da aba **Editar**, seguidas por um comando explícito de salvar, modificam o PIC.

Regiões, nomes e observações ficam num arquivo lateral JSON.

## Sistemas de coordenadas

Existem quatro espaços distintos:

1. **Imagem real**: pixels do atlas; é o único espaço usado nos resultados.
2. **Canvas escalado**: imagem real multiplicada pelo zoom.
3. **Viewport**: parte visível do `QScrollArea`.
4. **Tela**: coordenadas globais do sistema operacional; nunca entram nos cálculos do atlas.

`CoordinateTransform` é a fonte única de conversão:

```python
image_x = widget_x / zoom
image_y = widget_y / zoom

widget_x = image_x * zoom
widget_y = image_y * zoom
```

O canvas tem exatamente `image_size × zoom`. Quando a imagem é menor que a viewport, o `QScrollArea` centraliza o widget; eventos recebidos pelo canvas continuam locais a ele. Scroll e pan movem o widget na viewport, mas não mudam a transformação local. O zoom sob o cursor guarda o ponto real antes de redimensionar o canvas e reposiciona as barras para preservar a âncora visual.

Nearest-neighbor é mantido desativando `SmoothPixmapTransform` e usando a transformação rápida. A imagem base é convertida para `QPixmap` uma única vez; mouse e overlays não recriam o atlas.

## Retângulos

Todos os retângulos usam:

- `left` e `top` inclusivos;
- `right = x + width` exclusivo;
- `bottom = y + height` exclusivo.

Assim, `(724, 266, 32, 32)` ocupa X `724..755` e Y `266..297`, com `Right=756` e `Bottom=298`. A exportação PIL usa diretamente:

```python
image.crop((x, y, x + width, y + height))
```

O arraste inverso é normalizado. O pixel sob o ponto inicial e o pixel sob o ponto final participam da seleção manual. As coordenadas são limitadas às dimensões reais do atlas.

## Sprites 32×32

Para o pixel sob o mouse:

```python
sprite_col = x // 32
sprite_row = y // 32
sprite_index = sprite_row * pic_image.width + sprite_col
```

Para todos os sprites tocados por uma região:

```python
start_col = x // 32
start_row = y // 32
end_col = (x + width - 1) // 32
end_row = (y + height - 1) // 32
```

A enumeração é feita por linhas, usando a largura da `PicImage` em sprites. Seleções não precisam estar alinhadas. O snap opcional expande/alinha os quatro limites à grade 32×32.

## Índices de imagem

O modelo, os formatos copiados e o arquivo de projeto usam índices **zero-based**, iguais aos índices da lista `Pic.images`. A grade visual antiga pode apresentar numeração amigável começando em 1; o painel Inspector mostra explicitamente o ID técnico zero-based.

## Projeto JSON

Estrutura resumida:

```json
{
  "formatVersion": 1,
  "pic": {
    "signature": 123456789,
    "fileSize": 2502979,
    "sha256": "...",
    "sourceName": "Tibia.pic"
  },
  "regions": [
    {
      "name": "CHAT_TOGGLE",
      "imageIndex": 3,
      "x": 724,
      "y": 266,
      "width": 32,
      "height": 32,
      "imageWidth": 1024,
      "imageHeight": 768,
      "notes": "estado normal"
    }
  ]
}
```

Ao abrir um projeto, assinatura, tamanho e SHA-256 precisam corresponder ao arquivo aberto. Um projeto divergente não é aplicado silenciosamente. Salvar o projeto nunca escreve no PIC.

## Detecção automática

`foreground_mask()` compara cada RGB com `pic_image.bg_color` usando a maior diferença por canal e a tolerância escolhida. Pixels transparentes são ignorados por padrão. A busca de componentes suporta vizinhança 4 ou 8, filtros mínimos e união por distância.

**Auto Detect Regions** executa apenas sob comando e em uma `QThread`; a thread recebe uma cópia imutável da imagem e só devolve caixas e progresso. Widgets permanecem na thread principal. **Magic Select** usa a mesma máscara, mantida em cache por imagem/opções, e encontra somente o componente conectado ao pixel clicado.

Limitações inevitáveis:

- elementos encostados podem formar uma caixa única;
- partes desconectadas podem virar caixas diferentes;
- detalhes com a cor do fundo podem desaparecer da máscara;
- tolerância alta pode unir cores próximas;
- união por distância pode agrupar elementos independentes.

Por isso, a seleção manual e o ajuste X/Y/W/H são a referência final.

## Código gerado

O nome é convertido para maiúsculas, caracteres inválidos viram `_` e nomes iniciados por número recebem o prefixo `REGION_`. Os formatos disponíveis são:

- `x, y, width, height`;
- quatro constantes C++;
- `constexpr SpriteRect`;
- template configurável de `renderer->drawPicture(...)`;
- JSON;
- CSV.

## Performance

- `PicParser.render_image()` mantém o cache já existente.
- O canvas mantém uma única `QPixmap` da imagem atual.
- Overlays são desenhados por `QPainter`.
- A grade por pixel aparece somente a partir de 800%.
- A detecção completa não roda durante movimento do mouse.
- O resultado da máscara de seleção mágica é invalidado ao trocar ou editar a imagem.

## Testes

Os testes cobrem transformações em 25%, 100%, 400%, 800% e 1600%, seleção inversa, snap, scroll/pan, cobertura de sprites, clipboard C++, PNG exato, detecção, seleção mágica, round-trip do projeto e mismatch de hash. Com `TIBIA_PIC_PATH`, também abrem, renderizam, salvam e reabrem o `Tibia.pic` real.
