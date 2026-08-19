# Pineapple OS

> Um sistema operacional inspirado na experiência do macOS — boot estilo Apple
> (fundo claro + abacaxi), login estilo macOS, wallpapers dinâmicos e uma
> identidade própria.

**Base:** Debian/Ubuntu (live-build) · **Interface:** GTK4 + Wayland · **Linguagens:** Rust, C, Python

## Características

- **Boot estilo Apple**: fundo `#c2bec2` + abacaxi de contorno (mordida à
  direita, levemente inclinado) — GRUB invisível, boot direto.
- **Login estilo macOS**: wallpaper escurecido, relógio, avatar do usuário e
  campo de senha (SDDM).
- **Kernel panic por PowerBook ID**: o sistema só inicia com o argumento de
  boot `-pineapplepowerbookid=<ID>` (ID válido de `ids.txt`); sem ele, o
  kernel entra em panic estilo macOS.
- **Volume BFS obrigatório**: fora do modo live, o boot também exige um volume
  de dados BFS (exFAT + `.bfsprivate`) via `-pineapplefs=<dev>` (ou detectado
  no `/etc/fstab`); sem ele → kernel panic (como o macOS exige APFS).
- **Logs de boot silenciosos** (`quiet loglevel=0`), como no macOS.
- **Wallpapers**: High Sierra (dunas), Catalina **dinâmico** (troca conforme
  o horário, via daemon `pineapple-wallpaper`) e Sequoia.
- **BFS — Pineapple File System**: sistema de arquivos de usuário baseado em
  **exFAT** com recursos estilo **APFS/HFS+** — `._*` AppleDouble, `.bfsprivate`,
  snapshots, clones copy-on-write, arquivos esparsos "expandidos", case-
  insensitive, checksums e a pasta `_PINEAPPLE` em .zip (como o macOS).
- Interface fluida com aceleração por GPU; barra superior, Dock, Launchpad,
  Mission Control e gestos de touchpad estilo macOS.
- Modo Claro e Escuro, temas e ícones próprios.
- IA integrada (Ollama) como assistente local, com voz (STT/TTS offline).
- Instalador gráfico (Calamares), `.deb` e repositório apt próprio com OTA.
- Suporte nativo a Flatpak, AppImage, Wine, Darling e Waydroid.
- **ISO x64 gerada pela CI** (GitHub Actions) e publicada como artefato.

## Estrutura

```
PineappleOS/
├── Desktop/       # Shell do sistema (barra superior + session manager)
├── Dock/          # Componente do dock (biblioteca GTK4)
├── Finder/        # Gerenciador de arquivos
├── Launcher/      # Lançador de aplicativos
├── Launchpad/     # Grade de aplicativos estilo macOS
├── Mission/       # Mission Control + Spaces
├── Gestures/      # Gesto de 3 dedos (libinput)
├── AI/            # Integração com Ollama (assistente local)
├── Settings/      # Aplicativo de configurações
├── Store/         # Loja de aplicativos
├── Themes/        # Temas GTK + wallpapers (High Sierra/Catalina/Sequoia)
├── Icons/         # Conjunto de ícones próprio (gerado por script)
├── Filesystem/    # BFS: exFAT + recursos APFS/HFS+ (._*, .bfsprivate, snapshots, clones)
├── Installer/     # live-build, GRUB, Plymouth, SDDM, schemas, systemd, initramfs
├── Kernel/        # Config do kernel ("Pineapple Kernel") e docs de boot
├── Apps/          # Aplicativos nativos (Python/GTK4) + daemon de wallpaper
├── Compatibility/ # Flatpak, AppImage, Wine, Darling, Waydroid
├── Scripts/       # Scripts de build, install, testes e geração de imagens
├── tests/         # Suíte de testes (unittest)
├── Documentation/ # Documentação técnica
├── ids.txt        # PowerBook IDs válidos (obrigatório no boot)
└── .github/       # CI (GitHub Actions) — inclui build da ISO x64
```

## Aplicativos nativos

| Aplicativo   | Linguagem | Descrição                       |
|--------------|-----------|---------------------------------|
| Pineapple Finder   | Rust/GTK4 | Gerenciador de arquivos         |
| Pineapple Terminal | Rust/GTK4 | Terminal (VTE)                  |
| Pineapple Store    | Rust/GTK4 | Loja de aplicativos             |
| Pineapple Settings | Python    | Configurações do sistema        |
| Pineapple Monitor  | Python    | Monitor de recursos             |
| Pineapple Notes    | Python    | Notas com sincronização local   |
| Pineapple Photos   | Python    | Visualizador de fotos           |
| Pineapple Browser  | Python    | Navegador (WebKitGTK)           |
| Pineapple Music    | Python    | Player de música                     |
| Pineapple Calc     | Python    | Calculadora                          |
| Central Controle | Python | Controles rápidos (brilho, som, rede) |
| Notificações | Python    | Central de notificações (D-Bus)      |
| Wallpaper (daemon) | Python | Papel de parede dinâmico estilo Catalina |

## Boot e PowerBook ID

1. GRUB (fundo claro + abacaxi) carrega o kernel com
   `quiet loglevel=0 splash` e `-pineapplepowerbookid=<ID>`.
2. O initramfs **valida o ID** em `ids.txt`; se ausente/inválido → kernel panic.
3. Plymouth mostra o abacaxi + barra de progresso.
4. systemd inicia o `pineappleos-session.target` (compositor + shell + dock).

Para a ISO, defina o ID no build:

```bash
POWERBOOK_ID=SEU_ID ./Scripts/build-iso.sh
```

> **Sobre o kernel**: o Pineapple OS usa o kernel Linux compilado com
> configuração própria e identidade "Pineapple Kernel" — o mesmo modelo do
> Android. Leia [Kernel/README.md](Kernel/README.md) para todos os detalhes.

## Requisitos para build

- Linux (Debian 12+ ou Ubuntu 24.04+ recomendados)
- `live-build`, `debootstrap`, `gtk4`, `meson`, `ninja`, `cargo`
- Para a interface: `libgtk-4-dev`, `libgtk-4-layer-shell-dev`, `pkg-config`

## Build rápido

```bash
make build                          # ícones + backgrounds + wallpapers + apps
./Scripts/build.sh                  # compila o shell e os apps
POWERBOOK_ID=SEU_ID ./Scripts/build-iso.sh  # gera a ISO live (live-build)
./Scripts/build-debs.sh             # gera pacotes .deb em dist/
./Scripts/setup-repo.sh             # cria repositório apt assinado
./Scripts/pineapple-update.sh       # atualização OTA (pineapple-os-*)
./Scripts/setup-boot-themes.sh      # aplica GRUB/Plymouth/SDDM + PowerBook check
```

> **ISO x64 sem Linux local**: a CI (GitHub Actions) compila a ISO amd64
> automaticamente e a disponibiliza como artefato de download.

## Instalação

1. Grave a ISO em um pendrive: `dd if=pineappleos.iso of=/dev/sdX bs=4M status=progress`
2. Inicialize pelo pendrive (informe o `-pineapplepowerbookid=<ID>` se exigido)
   e escolha "Instalar Pineapple OS".
3. Siga o instalador gráfico (Calamares).
4. Após instalar, defina o PowerBook ID em `/etc/default/grub` (veja
   `Scripts/setup-powerbook-check.sh`).

## Contribuir

Veja [Documentation/ARCHITECTURE.md](Documentation/ARCHITECTURE.md) e
[Documentation/CONTRIBUTING.md](Documentation/CONTRIBUTING.md).

Para a evolucao da navegacao e da estrutura de pastas mac-like, consulte
[Documentation/MACLIKE_ARCHITECTURE.md](Documentation/MACLIKE_ARCHITECTURE.md).

## Licença

Open source — veja o arquivo `LICENSE` na raiz do repositório.
