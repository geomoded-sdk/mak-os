# Compatibilidade no Pineapple OS

O Pineapple OS oferece suporte nativo a múltiplas camadas de compatibilidade,
permitindo rodar aplicativos de outros ecossistemas.

## Resumo

| Tecnologia  | O que roda                  | Setup                            |
|-------------|-----------------------------|----------------------------------|
| Flatpak     | Aplicativos Linux sandboxed | `Compatibility/Flatpak/setup-flatpak.sh` |
| AppImage    | Aplicativos portáteis       | `Compatibility/AppImage/pineapple-appimage.sh` |
| Wine        | Aplicativos Windows         | `Compatibility/Wine/setup-wine.sh`       |
| Darling     | Aplicativos macOS (parcial) | `Compatibility/Darling/setup-darling.sh`  |
| Waydroid    | Aplicativos Android         | `Compatibility/Waydroid/setup-waydroid.sh`|

## Detalhes

### Flatpak
- Flathub habilitado por padrão no instalador.
- O **Pineapple Store** usa Flatpak como backend de instalação.
- Sandbox com AppArmor.

### AppImage
- Ferramenta `pineapple-appimage` registra AppImages como apps do Launcher:
  ```bash
  pineapple-appimage ~/Downloads/MeuApp.AppImage
  pineapple-appimage --list
  ```

### Wine
- Arquitetura 32 bits habilitada, prefixo dedicado `~/.wine-pineappleos`.
- Frontend `pineapple-wine` e **Winetricks** para dependências.

### Darling
- Camada de compatibilidade para executar binários macOS.
- **Status:** pré-instalado na ISO do Pineapple OS.
- O `Scripts/build-darling-deb.sh` compila o Darling e gera `Scripts/debs/darling_*.deb`,
  que é incluído automaticamente na imagem pelo `build-iso.sh`. Para instalação manual
  fora da ISO, veja `Compatibility/Darling/setup-darling.sh`.

### Waydroid
- Android em contêiner (LXC) com Wayland.
- Requer kernel com `binder` e `overlayfs` (já incluídos em `Kernel/config-6.1-pineappleos`).
- Gerenciado pelo atalho `pineapple-waydroid`.

## Notas de segurança

- Todas as camadas rodam no sandbox do AppArmor do Pineapple OS.
- O Waydroid e o Wine não têm acesso ao disco do sistema além do prefixo/contêiner.
