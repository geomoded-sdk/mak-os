# Temas do Mak OS

Temas GTK próprios com identidade visual única (nada de marcas alheias).

| Tema       | Uso                            |
|------------|--------------------------------|
| `Mak-Dark` | Escuro (padrão): grafite + azul-petróleo + coral |
| `Mak-Light`| Claro: superfícies brancas e acentos azul/coral  |
| `wallpapers/` | Papel de parede oficial (SVG)              |

## Estrutura de um tema GTK4

```
Mak-Dark/
├── index.theme        # metadados do tema
└── gtk-4.0/
    └── gtk.css        # estilos (widgets + componentes Mak)
```

## Instalar

```bash
sudo cp -r Themes/Mak-Dark Themes/Mak-Light /usr/share/themes/
# ativar:
gsettings set org.gnome.desktop.interface gtk-theme Mak-Dark
gsettings set org.gnome.desktop.interface color-scheme prefer-dark
```

## Componentes estilizados

- Barra superior (`.mak-bar`), menu, dock, launcher.
- Finder, Settings, Store, Monitor, Notes, Calculator.
- Central de Controle (`.mak-control-panel`).

## Paleta

| Cor            | Valor     | Uso           |
|----------------|-----------|---------------|
| Petróleo       | `#4f9dde` | Acento principal |
| Coral          | `#e2776f` | Destaque      |
| Grafite (dark) | `#17181c` | Fundo escuro  |
| Papel (light)  | `#f5f6f8` | Fundo claro   |
