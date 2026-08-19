# Temas do Pineapple OS

Temas GTK próprios com identidade visual única (nada de marcas alheias).

| Tema       | Uso                            |
|------------|--------------------------------|
| `Pineapple-HighSierra` | Claro (padrão): aqua estilo macOS High Sierra + dock de vidro |
| `Pineapple-Dark` | Escuro: grafite + azul-petróleo + coral |
| `Pineapple-Light`| Claro: superfícies brancas e acentos azul/coral  |
| `wallpapers/` | Papéis de parede oficiais (SVG) |

## Wallpapers

| Arquivo                            | Descrição                                   |
|------------------------------------|---------------------------------------------|
| `highsierra.svg`                   | Dunas ao pôr do sol (estilo macOS High Sierra) |
| `wallpaper.svg`                    | Wallpaper padrão (abstract)                 |
| `sequoia.svg`                      | Abstrato azul/turquesa (estilo macOS Sequoia) |
| `catalina/catalina-{dawn,day,sunset,night}.svg` | Pack **dinâmico** estilo macOS Catalina |

O Catalina é **dinâmico**: o daemon `pineapple-wallpaper`
(`Apps/Wallpaper/pineapple-wallpaper.py`) troca a imagem conforme o horário.

```bash
# escolher o modo (static ou catalina)
gsettings set org.pineappleos.desktop background-mode catalina
gsettings set org.pineappleos.desktop background-mode static

# imagem fixa
gsettings set org.pineappleos.desktop background \
  /usr/share/backgrounds/pineappleos/sequoia.svg
```

Geração: `python3 Scripts/gen-catalina.py` (o `Makefile` chama via `make wallpapers`).

## Estrutura de um tema GTK4

```
Pineapple-Dark/
├── index.theme        # metadados do tema
└── gtk-4.0/
    └── gtk.css        # estilos (widgets + componentes Pineapple)
```

## Instalar

```bash
sudo cp -r Themes/Pineapple-Dark Themes/Pineapple-Light Themes/Pineapple-HighSierra /usr/share/themes/
# ativar:
gsettings set org.gnome.desktop.interface gtk-theme Pineapple-HighSierra
gsettings set org.gnome.desktop.interface color-scheme prefer-light
```

## Componentes estilizados

- Barra superior (`.pineapple-bar`), menu, dock, launcher, launchpad.
- Finder, Settings, Store, Monitor, Notes, Calculator.
- Central de Controle (`.pineapple-control-panel`).

## Paleta

| Cor            | Valor     | Uso           |
|----------------|-----------|---------------|
| Petróleo       | `#4f9dde` | Acento principal |
| Coral          | `#e2776f` | Destaque      |
| Grafite (dark) | `#17181c` | Fundo escuro  |
| Papel (light)  | `#f5f6f8` | Fundo claro   |
