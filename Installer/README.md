# Installer

Geração da ISO bootável do Pineapple OS com **live-build** (Debian/Ubuntu).

## Estrutura

```
live-build/      # config gerada (builds)
schemas/         # schemas GSettings do Pineapple OS
systemd/         # serviços de sessão (user)
grub/            # tema GRUB (fundo claro estilo Apple)
plymouth/        # tema de boot (abacaxi + barra de progresso)
sddm/            # tema de login (estilo macOS)
initramfs/       # PowerBook ID check (hooks + init-bottom)
calamares/       # instalador
os-release       # identidade do sistema (NAME=Pineapple OS)
```

## Gerar a ISO

```bash
POWERBOOK_ID=SEU_ID ./Scripts/build-iso.sh        # Debian stable amd64
DISTRO=ubuntu SUITE=noble POWERBOOK_ID=SEU_ID ./Scripts/build-iso.sh
```

> **PowerBook ID**: sem o argumento `-pineapplepowerbookid=<ID>` o live boot
> entra em kernel panic (ver `initramfs/` e `Kernel/README.md`).

## Boot estilo Apple

- **GRUB** (`grub/theme/`): fundo claro + menu escuro, sem "GNU/Linux".
- **Plymouth** (`plymouth/theme/`): abacaxi sobre fundo branco/cinza + barra
  de progresso, igual ao boot do macOS.
- **SDDM** (`sddm/theme/`): login estilo macOS (wallpaper escurecido, relógio,
  avatar e senha).
- Logs de kernel ocultos com `quiet loglevel=0`.

## PowerBook ID (kernel panic)

1. `ids.txt` (raiz) lista os IDs válidos.
2. O hook de initramfs embute a lista no initramfs.
3. No boot, `pineapple-powerbook-check` valida o argumento
   `-pineapplepowerbookid=<ID>`; se ausente/inválido → **kernel panic**.
4. Para instalar no sistema: `./Scripts/setup-powerbook-check.sh`

## Volume BFS obrigatório (kernel panic sem ele)

Fora do modo live, o boot também exige um volume **BFS** (exFAT +
`.bfsprivate/volume.info`). O initramfs valida o dispositivo de
`-pineapplefs=<dev>` (ou o detecta pelo `/etc/fstab` em `/home`/`/data`);
sem volume BFS válido → **kernel panic**.

```bash
sudo ./Scripts/setup-bfs.sh /dev/sdb2        # formata exFAT + BFS em /data
# /etc/default/grub:
# GRUB_CMDLINE_LINUX_DEFAULT="... -pineapplepowerbookid=SEU_ID -pineapplefs=/dev/sdb2"
sudo update-grub
```

## Darling pré-instalado

O Pineapple OS já vem com o **Darling** (camada para aplicativos macOS) na ISO.

## LPNU (kernel compatibility layer — obrigatório na imagem)

A ISO embute o **LPNU v2.0.0** compilado **do fonte contra o kernel da própria
imagem** (via `live-build/hooks/pineapple-lpnu.hook.chroot`):

- `lpnu.ko` — compatibilidade de binários macOS no kernel;
- `apfs.ko` — filesystem APFS (linux-apfs-rw v0.3.19);
- `ld-mac` — Mach-O loader em `/usr/local/bin/ld-mac`;

com carregamento automático no boot (`/etc/modules-load.d/pineapple-lpnu.conf`).
Os `.ko` pré-compilados do release não seriam usados (são do kernel
`6.17.0-1011-azure` — vermagic não bate); por isso o build do fonte é
**obrigatório** e aborta a ISO em caso de falha.
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
- Todos os componentes do Pineapple OS em `/usr/share/pineappleos`.
- Flatpak, Wine, **Darling**, AppArmor e o instalador **Calamares**.

## Instalar no disco

1. Grave a ISO: `dd if=pineappleos.iso of=/dev/sdX bs=4M status=progress`
2. Boot pelo pendrive → "Instalar Pineapple OS" (Calamares).

## Serviços systemd

Instale com:

```bash
./Scripts/setup-systemd.sh
```

Componentes rodam como serviços do usuário dentro do `pineappleos-session.target`.
