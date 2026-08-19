#!/usr/bin/env python3
# =============================================================================
#  pineapple_ai — módulo do agente do Pineapple OS (Ollama)
#
#  Funcionalidades:
#   - responder perguntas (modelo local via Ollama)
#   - abrir aplicativos
#   - pesquisar arquivos
#   - resumir documentos
#   - auxiliar programação
#   - executar tarefas automatizadas (whitelist de comandos)
# =============================================================================
import json
import os
import re
import shlex
import subprocess
import urllib.request
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("PINEAPPLE_AI_MODEL", "llama3.1")

# Comandos autorizados para a automação (sandbox local)
ALLOWED_BINARIES = {
    "pineapple-canopy", "pineapple-terminal", "pineapple-settings", "pineapple-calculator",
    "pineapple-monitor", "pineapple-notes", "pineapple-photos", "pineapple-music", "pineapple-browser",
    "pineapple-store", "xdg-open", "notify-send",
}

KNOWN_APPS = {
    "finder": "pineapple-canopy", "arquivos": "pineapple-canopy", "files": "pineapple-canopy",
    "canopy": "pineapple-canopy",
    "terminal": "pineapple-terminal", "settings": "pineapple-settings", "configurações": "pineapple-settings",
    "calculadora": "pineapple-calculator", "calc": "pineapple-calculator",
    "monitor": "pineapple-monitor", "notes": "pineapple-notes", "notas": "pineapple-notes",
    "fotos": "pineapple-photos", "photos": "pineapple-photos",
    "música": "pineapple-music", "music": "pineapple-music",
    "navegador": "pineapple-browser", "browser": "pineapple-browser", "store": "pineapple-store",
}


class OllamaClient:
    def __init__(self, base_url=OLLAMA_URL):
        self.base = base_url.rstrip("/")

    def available(self):
        try:
            urllib.request.urlopen(f"{self.base}/api/tags", timeout=2)
            return True
        except OSError:
            return False

    def chat(self, messages, stream=False):
        body = json.dumps({
            "model": MODEL,
            "messages": messages,
            "stream": stream,
        }).encode()
        req = urllib.request.Request(
            f"{self.base}/api/chat", data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())


class Agent:
    """Agente do Pineapple OS: interpreta comandos e executa ações locais."""

    def __init__(self, client=None):
        self.client = client or OllamaClient()
        self.home = Path.home()

    # ---------------------------------------------------------- ferramentas
    def open_app(self, name: str) -> str:
        for key, bin_name in KNOWN_APPS.items():
            if key in name.lower():
                return self._launch(bin_name)
        found = self._find_desktop(name)
        if found:
            return self._launch(found)
        return f"não encontrei um aplicativo para '{name}'"

    def _launch(self, bin_name: str) -> str:
        try:
            subprocess.Popen([bin_name])
            return f"abri {bin_name}"
        except FileNotFoundError:
            return f"aplicativo '{bin_name}' não está instalado"

    def search_files(self, query: str, base: str | None = None, limit=20) -> list[str]:
        base = Path(base or self.home)
        results = []
        try:
            for p in base.rglob("*"):
                if p.name.startswith("."):
                    continue
                if query.lower() in p.name.lower():
                    results.append(str(p))
                if len(results) >= limit:
                    break
        except (PermissionError, OSError):
            pass
        return results

    def summarize_file(self, path: str) -> str:
        p = Path(path).expanduser()
        if not p.is_file():
            return "arquivo não encontrado"
        try:
            text = p.read_text(errors="ignore")[:6000]
        except OSError:
            return "não foi possível ler o arquivo"
        if not self.client.available():
            return f"Ollama offline. Resumo não disponível.\n\nPrimeiras linhas:\n{text[:500]}"
        reply = self.client.chat([
            {"role": "system", "content": "Você é o assistente do Pineapple OS. Resuma o texto em português, em até 120 palavras."},
            {"role": "user", "content": text},
        ])
        return reply.get("message", {}).get("content", "sem resposta")

    def run_command(self, command: str) -> str:
        """Executa apenas comandos na whitelist (segurança)."""
        parts = shlex.split(command)
        if not parts:
            return "comando vazio"
        prog = os.path.basename(parts[0])
        if prog not in ALLOWED_BINARIES:
            return f"comando não autorizado: {prog}"
        try:
            result = subprocess.run(parts, capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return f"comando '{prog}' não está instalado"
        return result.stdout[-2000:] + result.stderr[-2000:]

    # ---------------------------------------------------------- processamento
    def detect_action(self, text: str) -> dict | None:
        t = text.lower()

        if re.match(r"^(abra|abrir|open)\s+", t):
            target = re.split(r"^(abra|abrir|open)\s+", t)[2].strip()
            if not target:
                target = t
            return {"type": "open_app", "target": target}

        m = re.search(r"(resumir?|sumariz[ae]|resume)\s+(.+?)(\?|$)", t)
        if m:
            return {"type": "summarize", "target": m.group(2).strip()}

        m = re.search(r"(procurar?|pesquisar?|encontrar?|find|search)\s+[\"']?([\w\s.\-]+)", t)
        if m:
            return {"type": "search_files", "target": m.group(2).strip()}

        m = re.search(r"(execute|executar|rode|rodar)\s+(.+)", t)
        if m:
            return {"type": "run", "target": m.group(2).strip()}

        return None

    def handle(self, text: str) -> str:
        action = self.detect_action(text)
        if not action:
            if not self.client.available():
                return "Ollama não está rodando. Inicie com: ollama serve"
            reply = self.client.chat([
                {"role": "system", "content": (
                    "Você é o Pineapple AI, assistente do sistema operacional Pineapple OS. "
                    "Responda em português, de forma concisa e útil."
                )},
                {"role": "user", "content": text},
            ])
            return reply.get("message", {}).get("content", "sem resposta")

        if action["type"] == "open_app":
            return self.open_app(action["target"])
        if action["type"] == "search_files":
            results = self.search_files(action["target"])
            if not results:
                return "nenhum arquivo encontrado"
            return "Encontrados:\n" + "\n".join(results[:15])
        if action["type"] == "summarize":
            return self.summarize_file(action["target"])
        if action["type"] == "run":
            return self.run_command(action["target"])
        return "não entendi"

    # ---------------------------------------------------------- helpers
    def _find_desktop(self, name: str) -> str | None:
        for d in ("/usr/share/applications", str(self.home / ".local/share/applications")):
            for f in Path(d).glob("*.desktop"):
                try:
                    content = f.read_text(errors="ignore")
                except OSError:
                    continue
                if f'Name={name}' in content:
                    m = re.search(r"Exec=(\S+)", content)
                    if m:
                        return m.group(1)
        return None
