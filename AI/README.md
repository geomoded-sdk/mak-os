# Mak AI — assistente local

O Mak OS integra o **Ollama** como assistente local, garantindo privacidade
(nada sai da máquina) e funcionamento offline.

## Componentes

| Arquivo            | Descrição                                              |
|--------------------|--------------------------------------------------------|
| `mak_ai.py`        | Módulo do agente (ferramentas + interpretação)         |
| `mak-ai.py`        | CLI: `mak-ai "pergunta"`                               |
| `mak-assistant.py` | Interface gráfica GTK4 de chat                         |
| `setup-ollama.sh`  | Instala Ollama + serviço systemd + modelo              |

## Instalação

```bash
./AI/setup-ollama.sh
```

## Capacidades do agente

O agente reconhece **ações locais** em português/inglês:

- **Abrir apps** — `abrir calculadora`, `abra o terminal`
- **Pesquisar arquivos** — `pesquisar relatorio`, `find planilha`
- **Resumir documentos** — `resumir ~/Documentos/contrato.txt`
- **Executar tarefas** — `executar mak-finder` (whitelist segura)
- **Perguntas gerais** — responde via modelo local (`llama3.1`)

### Segurança

A automação de comandos é limitada a uma whitelist (`ALLOWED_BINARIES`).
O agente nunca executa comandos arbitrários.

## API do agente (uso em outros apps)

```python
from mak_ai import Agent, OllamaClient

agent = Agent(OllamaClient())
print(agent.handle("abrir o monitor"))
```

## Modelo

- Padrão: `llama3.1` (~4.7 GB de RAM).
- Para máquinas modestas: `qwen2.5:1.5b` ou `llama3.2:1b`
  (defina `MAK_AI_MODEL`).

```bash
export MAK_AI_MODEL=qwen2.5:1.5b
```
