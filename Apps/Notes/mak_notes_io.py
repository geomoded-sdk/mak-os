#!/usr/bin/env python3
# =============================================================================
#  mak_notes_io.py — serialização/parse de notas em Markdown (módulo puro)
# =============================================================================


def note_to_markdown(title, body):
    """Converte título + corpo de uma nota em texto Markdown."""
    title = title.strip() or "(sem título)"
    body = (body or "").strip()
    content = f"# {title}"
    if body:
        content += f"\n\n{body}"
    return content + "\n"


def note_from_markdown(content):
    """Extrai (título, corpo) de um texto Markdown.

    A primeira linha que não for vazia vira o título; o restante é o corpo.
    Um título em forma '# Título' tem a cerquilha removida.
    """
    lines = (content or "").splitlines()
    title = ""
    body_lines = []
    for line in lines:
        stripped = line.strip()
        if not title and stripped:
            if stripped.startswith("# "):
                title = stripped[2:].strip()
            else:
                title = stripped
            continue
        body_lines.append(line)
    return title, "\n".join(body_lines).strip()
