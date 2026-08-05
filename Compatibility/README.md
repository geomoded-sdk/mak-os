# Compatibilidade no Mak OS

O Mak OS oferece suporte nativo a múltiplas camadas de compatibilidade,
permitindo rodar aplicativos de outros ecossistemas.

## Resumo

| Tecnologia  | O que roda                  | Setup                            |
|-------------|-----------------------------|----------------------------------|
| Flatpak     | Aplicativos Linux sandboxed | `Compatibility/Flatpak/setup-flatpak.sh` |
| AppImage    | Aplicativos portáteis       | `Compatibility/AppImage/mak-appimage.sh` |
| Wine        | Aplicativos Windows         | `Compatibility/Wine/setup-wine.sh`       |
| Darling     | Aplicativos macOS (parcial) | `Compatibility/Darling/setup-darling.sh`  |
| Waydroid    | Aplicativos Android         | `Compatibility/Waydroid/setup-waydroid.sh`|

## Detalhes

### Flatpak
- Flathub habilitado por padrão no instalador.
- O **Mak Store** usa Flatpak como backend de instalação.
- Sandbox com AppArmor.

### AppImage
- Ferramenta `mak-appimage` registra AppImages como apps do Launcher:
  ```bash
  mak-appimage ~/Downloads/MeuApp.AppImage
  mak-appimage --list
  ```

### Wine
- Arquitetura 32 bits habilitada, prefixo dedicado `~/.wine-makos`.
- Frontend `mak-wine` e **Winetricks** para dependências.

### Darling
- Camada de compatibilidade para executar binários macOS.
- **Status:** experimental — compilação manual requerida (veja o script).

### Waydroid
- Android em contêiner (LXC) com Wayland.
- Requer kernel com `binder` e `overlayfs` (já incluídos em `Kernel/config-6.1-makos`).
- Gerenciado pelo atalho `mak-waydroid`.

## Notas de segurança

- Todas as camadas rodam no sandbox do AppArmor do Mak OS.
- O Waydroid e o Wine não têm acesso ao disco do sistema além do prefixo/contêiner.
