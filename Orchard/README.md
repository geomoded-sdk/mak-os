# Orchard — instalador do Pineapple OS

> Instalador gráfico **próprio em Rust nativo** (substitui o Calamares).
> UI estilo macOS (fiel ao mockup `ui.html`) via **GTK4 + CSS** — sem HTML/JS/WebKit.
> Motor: **`orchard-core`** — apaga e grava disco de verdade (sfdisk, mkfs, rsync, chroot).

## Arquitetura

```
Orchard/crates/
├── orchard-core/     # motor: discos, partição, cópia, boot, PNFS (Rust robusto)
├── orchard-render/   # framework de UI imediata (Gtk4/GLS) — base opcional
└── orchard-app/      # instalador: GTK4 nativo + CSS + fluxo completo
```

- **`orchard-core`** — `InstallConfig`, `Installer::run`, `list_disks`.
  A UI só consome essa API. Toca disco via `sfdisk`, `mkfs.*`, `rsync`, `chroot`.
- **`orchard-app`** — Rust + GTK4. Janela sem decoração do WM, traffic lights,
  listas, botões, progresso. Fluxo fiel ao mockup:

  Idioma → Utilitários → Instalar → Licença → Concordar → **Disco** →
  **Instalar (motor real)** → País → Teclado → Rede → Migração → ID Pineapple →
  Termos → Conta → Express → Concluído → Desktop.

## Por que Rust (não HTML/JS)

O instalador **apaga partições e grava o sistema no disco**. Isso exige:

- tipagem forte e sem vazamentos de memória
- controle fino de erros (`Result`) em cada etapa
- threads seguras para não travar a UI durante `rsync`/`mkfs`
- binário estático e auditável no ISO

HTML/JS só serviria como mockup visual; a implementação real é Rust.

## Build

```bash
cd Orchard
cargo build --release
# deps: libgtk-4-dev
```

Binário: `target/release/pineapple-orchard`.

## Rodar

```bash
# demo (não toca disco)
./target/release/pineapple-orchard --dry-run

# real (precisa sudo; define o PowerBook ID)
POWERBOOK_ID=PB-2026 sudo -E ./target/release/pineapple-orchard
```

## UI

O visual segue o mockup do usuário (`ui.html`): gradiente de desktop,
janela branca com border-radius, traffic lights (vermelho fecha), listas
selecionáveis, botões primary azuis, barra de progresso. Tudo em CSS GTK4
(`CSS` em `main.rs`), sem WebKit.

PowerBook ID: env `POWERBOOK_ID` (obrigatório no boot real; dry-run usa `PB-DRYRUN`).
