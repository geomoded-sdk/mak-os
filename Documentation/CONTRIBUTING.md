# Contribuindo para o Mak OS

Obrigado pelo interesse em contribuir! Este documento define as regras do projeto.

## Configuração do ambiente

### Dependências (Debian/Ubuntu)

```bash
sudo apt install -y \
  build-essential pkg-config meson ninja-build \
  libgtk-4-dev libgtk-4-layer-shell-dev \
  libadwaita-1-dev libvte-3-90-dev libwebkitgtk-6.0-dev \
  cargo rustc python3 python3-gi gir1.2-gtk-4.0 \
  live-build debootstrap calamares \
  libsystemd-dev libdbus-1-dev
```

### Compilando

```bash
./Scripts/build.sh
```

## Padrões de código

### Rust (shell, dock, launcher, launchpad, finder, gestures)
- Use `cargo fmt` e `cargo clippy -- -D warnings`.
- GTK4: siga o padrão `gio::Application` / `gtk4::Application`.
- Nunca bloqueie a thread principal; use async (glib MainContext).

### Python (apps utilitários, daemons)
- Use PyGObject (GObject Introspection) — `import gi`.
- Padrão de app: `Gtk.Application` com `Gtk.ApplicationWindow`.
- Fique no estilo da PEP 8, sem docstrings excessivas.

### C (módulos de baixo nível)
- Compile com `-Wall -Wextra -Werror`.
- Sem vazamentos de memória: use `-fsanitize=address` em testes.

## Estrutura de um componente

Todo componente segue o padrão:

```
Component/
├── Cargo.toml            # (Rust) ou setup.py / meson.build
├── src/                  # código-fonte
├── data/                 # .desktop, schemas GSettings, CSS
└── tests/                # testes
```

## Commits e branches

- Commit message em inglês, imperativo: `feat(dock): add magnification animation`.
- Convenção de tipos: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`.
- Cada componente vive em seu próprio diretório; mantenha mudanças focadas.

## Testes

- Rust: `cargo test`.
- Python: `pytest` (adicione testes para novos apps).
- UI: teste manual com o `mak-session` (session de desenvolvimento).

## Reportando problemas

Abra uma issue descrevendo: versão, distribuição, e saída de
`journalctl -b` se aplicável.
