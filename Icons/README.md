# Ícones do Mak OS

Conjunto de ícones próprio, gerado por script e desenhado sob medida
(sem logotipos ou marcas de terceiros).

## Estrutura

```
mak-icons/
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
write(os.path.join(APPS, "mak-meuapp.svg"), app_svg("meuapp", "<path .../>"))
```

## Instalar

```bash
sudo cp -r Icons/mak-icons /usr/share/icons/
sudo gtk-update-icon-cache -f /usr/share/icons/mak-icons
gsettings set org.gnome.desktop.interface icon-theme mak-icons
```
