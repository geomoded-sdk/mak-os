# Roadmap do Pineapple OS

## Fase 0 — Fundação (v0.1)
- [x] Estrutura do projeto
- [x] Documentação de arquitetura
- [x] Configuração live-build (Debian/Ubuntu)
- [x] Kernel config inicial (Kernel/)
- [x] Compositor labwc configurado (atalhos + áreas virtuais)
- [x] Session manager `pineapple-session`
- [ ] Primeira ISO bootável testada

## Fase 1 — Shell (v0.2)
- [x] `pineapple-shell`: barra superior funcional
- [x] `pineapple-dock`: dock com animações
- [x] `pineapple-launcher`: lançador de apps + ações de sistema
- [x] Tema GTK claro/escuro
- [x] Ícones próprios (gerados por script)
- [x] Central de Controle (painel Layer Shell)
- [x] Central de Notificações (D-Bus)

## Fase 2 — Aplicativos (v0.3)
- [x] Pineapple Calculator (com testes unitários)
- [x] Pineapple Terminal (multi-abas, zoom, atalhos)
- [x] Pineapple Notes (busca, exportar/importar Markdown)
- [x] Pineapple Settings
- [x] Pineapple Finder (menu de contexto: copiar/colar/renomear/excluir/nova pasta)
- [x] Pineapple Monitor (gráficos CPU+RAM e lista de processos)
- [x] Pineapple Photos
- [x] Pineapple Music
- [x] Pineapple Browser
- [x] Pineapple Store (categorias)

## Fase 3 — Sistema (v0.4)
- [x] Áreas de Trabalho Virtuais (config no compositor)
- [x] Serviços systemd (user) para todos os componentes
- [x] Schemas GSettings centralizados
- [x] Instalador Calamares personalizado (branding + módulos)
- [x] Tema GRUB + Plymouth com identidade Pineapple
- [x] Tema SDDM de login com identidade Pineapple
- [x] Empacotamento .deb (4 pacotes) + repositório apt assinado
- [x] Atualizações OTA (`pineapple-update`)
- [ ] Repositório remoto público

## Fase 4 — IA (v0.5)
- [x] Agente `pineapple_ai` (Ollama) + CLI
- [x] Assistente gráfico GTK4
- [x] Automação de tarefas (whitelist segura)
- [x] Pesquisa de arquivos e resumo de documentos
- [x] Voz local (STT Vosk + TTS espeak-ng/piper)

## Fase 5 — Compatibilidade (v0.6)
- [x] Flatpak por padrão + integração com o Store
- [x] AppImage manager (`pineapple-appimage`)
- [x] Wine + frontend `pineapple-wine`
- [x] Darling setup script
- [x] Waydroid setup automatizado

## Fase 6 — Qualidade e Release (v1.0)
- [x] Testes automatizados (Python) — CI no GitHub Actions
- [x] Makefile, .gitignore e CI
- [x] Documentação do usuário final (GUIA.md)
- [ ] Release estável e ISO oficial

## Fase 7 — Experiência macOS (v0.7)
- [x] Launchpad (grade de apps em tela cheia; F4 + ícone do dock)
- [x] Mission Control / Spaces (F3, Ctrl+Up, gesto de 3 dedos)
- [x] Efeito de minimizar estilo macOS (janelas minimizam para o Dock com animação; clique restaura)
