# Ícones do Pineapple OS

Conjunto de ícones próprio, gerado por script e desenhado sob medida
(sem logotipos ou marcas de terceiros).

## Estrutura

```
pineapple-icons/
├── index.theme              # tema de ícones GTK
├── scalable/apps/           # ícones de aplicativos (SVG, 128px)
└── symbolic/apps/           # ícones simbólicos de status (16px)
```

## Identidade

- Quadrados arredondados com gradiente **petróleo → coral**.
- Glifos geométricos brancos.
- Ícones simbólicos monocromáticos (herdam `currentColor`).

## Gerar

```bash
python3 Scripts/gen-icons.py
```

## Adicionar um novo app

Edite `Scripts/gen-icons.py` e adicione:

```python
write(os.path.join(APPS, "pineapple-meuapp.svg"), app_svg("meuapp", "<path .../>"))
```

## Instalar

```bash
sudo cp -r Icons/pineapple-icons /usr/share/icons/
sudo gtk-update-icon-cache -f /usr/share/icons/pineapple-icons
gsettings set org.gnome.desktop.interface icon-theme pineapple-icons
```
