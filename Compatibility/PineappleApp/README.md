# Pineapple App Wrapper

O wrapper unifica o registro de aplicativos no Pineapple OS. Ele identifica o
formato pela assinatura do arquivo e escolhe a camada correspondente:

| Formato | Runtime |
|---|---|
| ELF | execução Linux nativa |
| PE/EXE | Wine |
| Mach-O | Darling + LPNU |
| AppImage | execução direta |
| Flatpak | detectado para integração com o App Center |

## Uso

```bash
python3 Compatibility/PineappleApp/pineapple_app.py detect ./MeuApp
python3 Compatibility/PineappleApp/pineapple_app.py register ./MeuApp
python3 Compatibility/PineappleApp/pineapple_app.py launch ./MeuApp
```

O registro cria um arquivo `.desktop` em `~/.local/share/applications`, então o
app aparece no Finder, Launcher, Launchpad, Dock e Spotlight como qualquer app
nativo. A detecção usa magic numbers, não apenas a extensão.

O suporte Mach-O usa o runtime Darling e o LPNU integrado ao Pineapple Kernel.
LPNU fornece a camada de compatibilidade de baixo nivel; o wrapper apenas
seleciona o runtime e integra o app ao desktop.

Arquivos desconhecidos nao sao executados automaticamente. Wine, Darling,
Flatpak e demais runtimes continuam opcionais e precisam estar instalados.
