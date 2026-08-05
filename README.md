# Mak OS

> Um sistema operacional Linux moderno, bonito, rápido e inspirado na experiência
> do macOS — com identidade, design e componentes próprios.

**Base:** Debian/Ubuntu (live-build) · **Interface:** GTK4 + Wayland · **Linguagens:** Rust, C, Python

## Características

- Interface extremamente elegante e fluida com aceleração por GPU.
- Base Linux estável (Debian/Ubuntu) e fácil de instalar.
- Baixo consumo de RAM e alto desempenho.
- Totalmente open source e modular.
- Dock inferior com animações suaves.
- Barra superior, Launcher de aplicativos, Central de Controle e Central de Notificações.
- Áreas de Trabalho Virtuais.
- Modo Claro e Escuro, temas e ícones próprios.
- IA integrada (Ollama) como assistente local, com voz (STT/TTS offline).
- Instalador gráfico (Calamares) com branding próprio e tema de boot (GRUB/Plymouth).
- Empacotamento `.deb` e repositório apt próprio com atualizações OTA.
- Suporte nativo a Flatpak, AppImage, Wine, Darling e Waydroid.

## Estrutura

```
MakOS/
├── Desktop/       # Shell do sistema (barra superior + session manager)
├── Dock/          # Componente do dock (biblioteca GTK4)
├── Finder/        # Gerenciador de arquivos
├── Launcher/      # Lançador de aplicativos
├── AI/            # Integração com Ollama (assistente local)
├── Settings/      # Aplicativo de configurações
├── Store/         # Loja de aplicativos
├── Themes/        # Temas GTK (claro/escuro) + wallpaper
├── Icons/         # Conjunto de ícones próprio (gerado por script)
├── Installer/     # live-build, schemas GSettings e serviços systemd
├── Kernel/        # Configuração do kernel e módulos
├── Apps/          # Aplicativos nativos (Python/GTK4)
├── Compatibility/ # Flatpak, AppImage, Wine, Darling, Waydroid
├── Scripts/       # Scripts de build, install, testes e geração de ícones
├── tests/         # Suíte de testes (unittest)
├── Documentation/ # Documentação técnica
└── .github/       # CI (GitHub Actions)
```

## Aplicativos nativos

| Aplicativo   | Linguagem | Descrição                       |
|--------------|-----------|---------------------------------|
| Mak Finder   | Rust/GTK4 | Gerenciador de arquivos         |
| Mak Terminal | Rust/GTK4 | Terminal (VTE)                  |
| Mak Store    | Rust/GTK4 | Loja de aplicativos             |
| Mak Settings | Python    | Configurações do sistema        |
| Mak Monitor  | Python    | Monitor de recursos             |
| Mak Notes    | Python    | Notas com sincronização local   |
| Mak Photos   | Python    | Visualizador de fotos           |
| Mak Browser  | Python    | Navegador (WebKitGTK)           |
| Mak Music    | Python    | Player de música                     |
| Mak Calc     | Python    | Calculadora                          |
| Central Controle | Python | Controles rápidos (brilho, som, rede) |
| Notificações | Python    | Central de notificações (D-Bus)      |

## Requisitos para build

- Linux (Debian 12+ ou Ubuntu 24.04+ recomendados)
- `live-build`, `debootstrap`, `gtk4`, `meson`, `ninja`, `cargo`
- Para a interface: `libgtk-4-dev`, `libgtk-4-layer-shell-dev`, `pkg-config`

## Build rápido

```bash
./Scripts/build.sh              # compila o shell e os apps
./Scripts/build-iso.sh          # gera a ISO live (live-build)
./Scripts/build-debs.sh         # gera pacotes .deb em dist/
./Scripts/setup-repo.sh         # cria repositório apt assinado
./Scripts/mak-update.sh         # atualização OTA (mak-os-*)
./Scripts/setup-boot-themes.sh  # aplica GRUB/Plymouth do Mak OS
```

## Instalação

1. Grave a ISO em um pendrive: `dd if=makos.iso of=/dev/sdX bs=4M status=progress`
2. Inicialize pelo pendrive e escolha "Instalar Mak OS".
3. Siga o instalador gráfico (Calamares).

## Contribuir

Veja [Documentation/ARCHITECTURE.md](Documentation/ARCHITECTURE.md) e
[Documentation/CONTRIBUTING.md](Documentation/CONTRIBUTING.md).

## Licença

Open source — veja o arquivo `LICENSE` na raiz do repositório.
