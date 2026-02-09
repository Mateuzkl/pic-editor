# Tibia PIC Editor

Editor visual em Python para arquivos Tibia.pic com interface moderna PyQt6.

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

## Funcionalidades

- Carregar arquivos Tibia.pic (versão 7.0+)
- Visualizar todas as imagens da interface em grid
- Editar cores, importar PNGs, aplicar filtros
- Salvar alterações de volta para .pic

## Estrutura

```
src/
├── parsers/    # Leitura/escrita de arquivos .pic
├── models/     # Classes de dados (Pic, PicImage, Sprite)
├── ui/         # Interface gráfica PyQt6
├── editors/    # Ferramentas de edição de imagem
└── utils/      # Utilitários auxiliares
```
