# Mak Store

Loja de aplicativos do Mak OS. Usa **Flatpak** como backend.

## Funcionalidades

- Lista apps de repositórios Flatpak (Flathub por padrão).
- Busca e cards de apps.
- Instalação com `flatpak install`.
- Fallback para apps nativos quando o Flatpak não está disponível.

## Requisitos

- `flatpak` instalado e Flathub configurado:

```bash
./Compatibility/Flatpak/setup-flatpak.sh
```

## Estrutura

```
mak-store.py   # app GTK4
```

## Rodar

```bash
python3 Apps/Store/mak-store.py
```
