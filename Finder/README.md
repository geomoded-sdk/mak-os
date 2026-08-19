# Pineapple Finder

Gerenciador de arquivos do Pineapple OS (Rust/GTK4).

## Funcionalidades

- Navegação: voltar, avançar, subir.
- Barra lateral com favoritos (Início, Documentos, Downloads, Imagens).
- Visualização em lista com ícones por tipo de arquivo e tamanho.
- Pesquisa no diretório atual.
- Duplo clique: entra em pastas / abre arquivos via handler padrão (GIO).

## Estrutura

```
src/main.rs   # lógica completa do Finder
```

## Build

```bash
cargo build --release --manifest-path Finder/Cargo.toml
```

## Extensões futuras

- Visualização em grade.
- Copiar/colar/renomear via menu de contexto.
- Montagens e protocolos remotos (GVfs).
