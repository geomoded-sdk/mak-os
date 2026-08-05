# Temas do Mak OS

Temas GTK próprios com identidade visual única (nada de marcas alheias).

| Tema       | Uso                            |
|------------|--------------------------------|
| `Mak-HighSierra` | Claro (padrão): aqua estilo macOS High Sierra + dock de vidro |
| `Mak-Dark` | Escuro: grafite + azul-petróleo + coral |
| `Mak-Light`| Claro: superfícies brancas e acentos azul/coral  |
| `wallpapers/` | Papéis de parede oficiais (SVG): `wallpaper.svg`, `highsierra.svg` |

## Estrutura de um tema GTK4

```
Mak-Dark/
├── index.theme        # metadados do tema
└── gtk-4.0/
    └── gtk.css        # estilos (widgets + componentes Mak)
```

## Instalar

```bash
sudo cp -r Themes/Mak-Dark Themes/Mak-Light Themes/Mak-HighSierra /usr/share/themes/
# ativar:
gsettings set org.gnome.desktop.interface gtk-theme Mak-HighSierra
gsettings set org.gnome.desktop.interface color-scheme prefer-light
```

## Componentes estilizados

- Barra superior (`.mak-bar`), menu, dock, launcher, launchpad.
- Finder, Settings, Store, Monitor, Notes, Calculator.
- Central de Controle (`.mak-control-panel`).

## Paleta

| Cor            | Valor     | Uso           |
|----------------|-----------|---------------|
| Petróleo       | `#4f9dde` | Acento principal |
| Coral          | `#e2776f` | Destaque      |
| Grafite (dark) | `#17181c` | Fundo escuro  |
| Papel (light)  | `#f5f6f8` | Fundo claro   |
