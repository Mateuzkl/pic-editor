# Tibia PIC Editor

Editor visual em PyQt6 para abrir, editar, salvar e inspecionar arquivos `Tibia.pic` (Tibia 7.0+). O modo **Coordinate Inspector** localiza com precisão botões, ícones e regiões de atlas e gera coordenadas prontas para uso em C++.

## Instalação

Requer Python 3.13 ou superior. No Windows, execute `start.bat`; ele instala as dependências quando necessário. Manualmente:

```bash
pip install -r requirements.txt
python main.py
```

## Funcionalidades

- Abrir e salvar `Tibia.pic`, mantendo o parser e o fluxo de edição existentes.
- Navegação por thumbnails e exportação de uma ou todas as imagens em PNG.
- Troca de cores, brilho, contraste, saturação e importação de PNG.
- Interface em português e inglês.
- Zoom nítido de 25% a 1600%, Fit, 100%, rolagem e pan.
- Seleção manual em pixels reais, movimento, redimensionamento e ajuste por campos X/Y/W/H.
- Grades de pixels e sprites 32×32, réguas e coordenadas.
- Leitura em tempo real de X/Y, RGBA, coluna, linha e índice do sprite.
- Geração de retângulo, constantes C++, `SpriteRect`, `drawPicture`, JSON e CSV.
- Detecção automática de regiões e seleção mágica por componente conectado.
- Projetos laterais `*.regions.json`, validados por assinatura, tamanho e SHA-256 do PIC.
- Exportação exata da seleção e das regiões salvas, sem escala nem suavização.

## Como inspecionar uma coordenada

1. Abra `Tibia.pic` com `Ctrl+O`.
2. Escolha a imagem na coluna esquerda.
3. Abra a aba **Inspecionar** ou pressione `Ctrl+I`.
4. Arraste sobre o ícone. A seleção pode começar em qualquer direção.
5. Ajuste X, Y, W e H pelas alças, campos ou setas.
6. Defina um nome como `CHAT_TOGGLE`.
7. Use **Copiar retângulo**, **Copiar constantes C++** ou **Copiar drawPicture**.

Os IDs de imagem usados pelo Inspector e pelo JSON são **zero-based**. `Right` e `Bottom` são **exclusivos**: uma região `(x=10, y=20, w=4, h=3)` ocupa X `10..13` e Y `20..22`, com `Right=14` e `Bottom=23`.

## Navegação e seleção

- Roda do mouse: rolagem.
- `Ctrl` + roda: zoom preservando o pixel sob o cursor.
- Botão central ou `Espaço` + arrastar: pan.
- Setas: mover a seleção 1 pixel.
- `Shift` + setas: mover 10 pixels.
- `Alt` + setas: alterar largura/altura; combine com `Shift` para 10 pixels.
- **Encaixar na grade 32×32**: alinha posição e dimensões aos sprites.
- **Seleção mágica**: clique num pixel que não seja o fundo para selecionar seu componente.

## Atalhos

| Atalho | Ação |
|---|---|
| `Ctrl+O` | Abrir PIC |
| `Ctrl+I` | Alternar Editar/Inspecionar |
| `Ctrl+C` | Copiar retângulo no modo Inspector |
| `Ctrl+Shift+C` | Copiar constantes C++ |
| `G` | Grade 32×32 |
| `P` | Grade de pixels (visível em 800%+) |
| `F` | Ajustar imagem à viewport |
| `1` | Zoom 100% |
| `Esc` | Limpar seleção |

## Regiões salvas

**Adicionar** guarda a seleção atual com nome, imagem, dimensões e observações. Um clique numa região salva navega até a imagem e centraliza o retângulo. O projeto é salvo separadamente, normalmente como `Tibia.pic.regions.json`; o `Tibia.pic` não é alterado por essa operação. O sidecar padrão é reaberto automaticamente quando corresponde ao PIC.

Se assinatura, tamanho ou SHA-256 não corresponderem ao PIC aberto, o projeto é rejeitado com aviso. Consulte [docs/COORDINATE_INSPECTOR.md](docs/COORDINATE_INSPECTOR.md) para o formato e os cálculos.

## Testes

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:TIBIA_PIC_PATH='C:\caminho\Tibia.pic'
python -B -m unittest discover -s tests -v
```

## English summary

Open a `Tibia.pic`, select an image, switch to **Inspect**, and drag over an atlas element. All reported positions are unscaled real-image pixels. Zoom, scroll and pan do not change the result. The Inspector can copy C++/JSON/CSV, auto-detect foreground components, save hash-validated sidecar region projects, and export exact PNG crops.

Based on [Elime1/pic-editor](https://github.com/Elime1/pic-editor).
