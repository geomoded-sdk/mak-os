# Pineapple Launcher

Lançador de aplicativos do Pineapple OS (GTK4).

## Funcionalidades

- Busca por apps a partir de `.desktop` files (sistema + usuário).
- Filtro incremental com `ListBox`.
- Navegação e abertura de apps.
- Fecha com `Esc`.

## Uso

```bash
cargo build --release --manifest-path Launcher/Cargo.toml
./target/release/pineapple-launcher          # abre o launcher
./target/release/pineapple-launcher --hidden # aguarda ativação (sessão)
```

## Atalho

`Super+Espaço` abre o launcher (configurado no `rc.xml` do compositor).
