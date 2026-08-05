# Mak Settings

Configurações do sistema do Mak OS (GTK4/Python).

## Categorias

- **Aparência** — modo claro/escuro, tema GTK, aceleração por GPU.
- **Tela** — resolução, escala, luz noturna.
- **Rede** — Wi-Fi, VPN.
- **Conta** — usuário, login automático.
- **Sobre** — versão do sistema, kernel, arquitetura.

## Integração

- Modifica o esquema de cores e tema via `gsettings` (org.gnome.desktop.interface).
- Configurações persistidas em GSettings (schemas em
  `Installer/schemas/org.makos.gschema.xml`).

## Rodar

```bash
python3 Apps/Settings/mak-settings.py
```

## Estrutura

```
Apps/Settings/mak-settings.py   # implementação
Settings/                       # (este diretório: docs e dados)
```
