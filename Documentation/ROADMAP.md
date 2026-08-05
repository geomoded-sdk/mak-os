# Roadmap do Mak OS

## Fase 0 — Fundação (v0.1)
- [x] Estrutura do projeto
- [x] Documentação de arquitetura
- [x] Configuração live-build (Debian/Ubuntu)
- [x] Kernel config inicial (Kernel/)
- [x] Compositor labwc configurado (atalhos + áreas virtuais)
- [x] Session manager `mak-session`
- [ ] Primeira ISO bootável testada

## Fase 1 — Shell (v0.2)
- [x] `mak-shell`: barra superior funcional
- [x] `mak-dock`: dock com animações
- [x] `mak-launcher`: lançador de apps + ações de sistema
- [x] Tema GTK claro/escuro
- [x] Ícones próprios (gerados por script)
- [x] Central de Controle (painel Layer Shell)
- [x] Central de Notificações (D-Bus)

## Fase 2 — Aplicativos (v0.3)
- [x] Mak Calculator (com testes unitários)
- [x] Mak Terminal (multi-abas, zoom, atalhos)
- [x] Mak Notes (busca, exportar/importar Markdown)
- [x] Mak Settings
- [x] Mak Finder (menu de contexto: copiar/colar/renomear/excluir/nova pasta)
- [x] Mak Monitor (gráficos CPU+RAM e lista de processos)
- [x] Mak Photos
- [x] Mak Music
- [x] Mak Browser
- [x] Mak Store (categorias)

## Fase 3 — Sistema (v0.4)
- [x] Áreas de Trabalho Virtuais (config no compositor)
- [x] Serviços systemd (user) para todos os componentes
- [x] Schemas GSettings centralizados
- [x] Instalador Calamares personalizado (branding + módulos)
- [x] Tema GRUB + Plymouth com identidade Mak
- [x] Tema SDDM de login com identidade Mak
- [x] Empacotamento .deb (4 pacotes) + repositório apt assinado
- [x] Atualizações OTA (`mak-update`)
- [ ] Repositório remoto público

## Fase 4 — IA (v0.5)
- [x] Agente `mak_ai` (Ollama) + CLI
- [x] Assistente gráfico GTK4
- [x] Automação de tarefas (whitelist segura)
- [x] Pesquisa de arquivos e resumo de documentos
- [x] Voz local (STT Vosk + TTS espeak-ng/piper)

## Fase 5 — Compatibilidade (v0.6)
- [x] Flatpak por padrão + integração com o Store
- [x] AppImage manager (`mak-appimage`)
- [x] Wine + frontend `mak-wine`
- [x] Darling setup script
- [x] Waydroid setup automatizado

## Fase 6 — Qualidade e Release (v1.0)
- [x] Testes automatizados (Python) — CI no GitHub Actions
- [x] Makefile, .gitignore e CI
- [x] Documentação do usuário final (GUIA.md)
- [ ] Release estável e ISO oficial

## Fase 7 — Experiência macOS (v0.7)
- [x] Launchpad (grade de apps em tela cheia; F4 + ícone do dock)
- [ ] Mission Control / Spaces
- [ ] Efeito de minimizar estilo macOS
- [ ] Gesto de 3 dedos (daemon libinput) para abrir o Launchpad
