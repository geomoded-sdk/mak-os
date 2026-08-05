# Installer

Geração da ISO bootável do Mak OS com **live-build** (Debian/Ubuntu).

## Estrutura

```
live-build/      # config gerada (builds)
schemas/         # schemas GSettings do Mak OS
systemd/         # serviços de sessão (user)
grub/            # tema GRUB
plymouth/        # tema de boot (splash)
sddm/            # tema de login (SDDM)
calamares/       # instalador
```

## Requisitos

```bash
sudo apt install -y live-build debootstrap calamares
```

## Gerar a ISO

```bash
./Scripts/build-iso.sh                 # Debian stable amd64
DISTRO=ubuntu SUITE=noble ./Scripts/build-iso.sh
```

## Darling pré-instalado

O Mak OS já vem com o **Darling** (camada para aplicativos macOS) na ISO.
Compile e gere o pacote antes de montar a imagem:

```bash
./Scripts/build-darling-deb.sh        # Debian (detecta dependências)
DISTRO=ubuntu ./Scripts/build-darling-deb.sh
```

O `.deb` gerado em `Scripts/debs/` é incluído automaticamente pelo `build-iso.sh`
(em `config/packages.chroot/`). O build exige clang e demora de 30 a 60 minutos.

## O que a imagem inclui

- Kernel otimizado (`linux-image-amd64`) + firmware.
- Compositor **labwc**, GTK4, PipeWire, NetworkManager.
- Todos os componentes do Mak OS em `/usr/share/makos`.
- Flatpak, Wine, **Darling**, AppArmor e o instalador **Calamares**.

## Instalar no disco

1. Grave a ISO: `dd if=makos.iso of=/dev/sdX bs=4M status=progress`
2. Boot pelo pendrive → "Instalar Mak OS" (Calamares).

## Serviços systemd

Instale com:

```bash
./Scripts/setup-systemd.sh
```

Componentes rodam como serviços do usuário dentro do `makos-session.target`.
