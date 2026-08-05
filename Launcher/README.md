# Mak Launcher

Lançador de aplicativos do Mak OS (GTK4).

## Funcionalidades

- Busca por apps a partir de `.desktop` files (sistema + usuário).
- Filtro incremental com `ListBox`.
- Navegação e abertura de apps.
- Fecha com `Esc`.

## Uso

```bash
cargo build --release --manifest-path Launcher/Cargo.toml
./target/release/mak-launcher          # abre o launcher
./target/release/mak-launcher --hidden # aguarda ativação (sessão)
```

## Atalho

`Super+Espaço` abre o launcher (configurado no `rc.xml` do compositor).
