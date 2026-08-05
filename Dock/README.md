# Mak Dock

Dock inferior do Mak OS com animação de magnificação.

## Funcionalidades

- Ícones dos apps padrão (ver `default_icons()`).
- Magnificação suave a 60 fps: ícones próximos ao centro ficam maiores.
- Tooltips e lançamento de apps.
- Camada Layer Shell `bottom` (não rouba foco).

## Estrutura

```
src/main.rs   # entrada + layout + animação
```

## Build

```bash
cargo build --release --manifest-path Dock/Cargo.toml
```

## Personalização

A lista de apps fixados pode virar configuração GSettings
(`org.makos.dock.pinned`). Para usar apps de outro lugar, edite
`default_icons()`.
