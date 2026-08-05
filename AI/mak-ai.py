#!/usr/bin/env python3
# =============================================================================
#  mak-ai — CLI do assistente Mak OS. A lógica vive em mak_ai.py.
# =============================================================================
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mak_ai import Agent, OllamaClient  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: mak-ai 'mensagem'")
        return 1
    agent = Agent(OllamaClient())
    print(agent.handle(" ".join(sys.argv[1:])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
