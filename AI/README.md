# Pineapple AI — assistente local

O Pineapple OS integra o **Ollama** como assistente local, garantindo privacidade
(nada sai da máquina) e funcionamento offline.

## Componentes

| Arquivo            | Descrição                                              |
|--------------------|--------------------------------------------------------|
| `pineapple_ai.py`        | Módulo do agente (ferramentas + interpretação)         |
| `pineapple-ai.py`        | CLI: `pineapple-ai "pergunta"`                               |
| `pineapple-assistant.py` | Interface gráfica GTK4 de chat                         |
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
- **Executar tarefas** — `executar pineapple-finder` (whitelist segura)
- **Perguntas gerais** — responde via modelo local (`llama3.1`)

### Segurança

A automação de comandos é limitada a uma whitelist (`ALLOWED_BINARIES`).
O agente nunca executa comandos arbitrários.

## API do agente (uso em outros apps)

```python
from pineapple_ai import Agent, OllamaClient

agent = Agent(OllamaClient())
print(agent.handle("abrir o monitor"))
```

## Modelo

- Padrão: `llama3.1` (~4.7 GB de RAM).
- Para máquinas modestas: `qwen2.5:1.5b` ou `llama3.2:1b`
  (defina `PINEAPPLE_AI_MODEL`).

```bash
export PINEAPPLE_AI_MODEL=qwen2.5:1.5b
```
