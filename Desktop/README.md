# Mak Shell / Desktop

Shell do Mak OS: barra superior, session manager e compositor.

## Componentes

| Binário       | Descrição                                        |
|---------------|--------------------------------------------------|
| `mak-shell`   | Barra superior (Layer Shell) + menu + status     |
| `mak-session` | Gerenciador de sessão (compositor + componentes) |

## Estrutura

```
src/
├── main.rs            # entrypoint do mak-shell
├── shell.rs           # barra superior (Layer Shell top)
├── status.rs          # relógio e área de status
├── menu.rs            # menu MaK (popover)
└── bin/mak-session.rs # gerenciador de sessão
data/
└── labwc/rc.xml       # config do compositor (atalhos, áreas virtuais)
```

## Build

```bash
cargo build --release --manifest-path Desktop/Cargo.toml
```

## Configuração do compositor

- Compositor: **labwc** (wlroots).
- Áreas de Trabalho Virtuais: 4 por padrão, troca por `Super+1..4`.
- Atalhos: ver `data/labwc/rc.xml`.

## Sessão

`mak-session` inicia o compositor e sobe os componentes da interface.
Em modo systemd, cada componente é um serviço `user` (ver
`Installer/systemd/`).
