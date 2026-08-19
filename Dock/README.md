# Pineapple Dock

Dock inferior do Pineapple OS com animação de magnificação.

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
(`org.pineappleos.dock.pinned`). Para usar apps de outro lugar, edite
`default_icons()`.
