#!/usr/bin/env python3
# =============================================================================
#  pineapple-ai — CLI do assistente Pineapple OS. A lógica vive em pineapple_ai.py.
# =============================================================================
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pineapple_ai import Agent, OllamaClient  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: pineapple-ai 'mensagem'")
        return 1
    agent = Agent(OllamaClient())
    print(agent.handle(" ".join(sys.argv[1:])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
