#!/usr/bin/env python3
# =============================================================================
#  gen-catalina.py — gera os wallpapers "Catalina" do Pineapple OS
#
#  Reproduz o estilo do papel de parede dinâmico do macOS Catalina: camadas
#  de ondas suaves e abstratas que mudam de paleta ao longo do dia.
#  São 4 imagens (amanhecer, dia, pôr do sol, noite) trocadas pelo daemon
#  pineapple-wallpaper de acordo com o horário.
#
#  Saída: Themes/wallpapers/catalina/catalina-{dawn,day,sunset,night}.svg
#
#  Sem dependências externas.
# =============================================================================
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Themes", "wallpapers", "catalina")
W, H = 2560, 1440

# ---------------------------------------------------------------------------
#  Paletas por horário (estilo macOS Catalina)
# ---------------------------------------------------------------------------
# Cada paleta: (topo do céu, base do céu, cor do brilho, cores das ondas)
PALETTES = {
    "dawn": (
        "#33406b", "#e8a07e",
        "#ffd9a8",
        ["#7f6a93", "#a86f86", "#c86f7a", "#e08576", "#f2a184"],
    ),
    "day": (
        "#3fa7d6", "#cfeef8",
        "#fff8e0",
        ["#2e8cc0", "#39a6d4", "#4fc1e8", "#7ad6f0", "#b4ecfb"],
    ),
    "sunset": (
        "#3b2d5e", "#f5a25a",
        "#ffcf8a",
        ["#5d3a7a", "#8a4a7d", "#b4556f", "#d9785e", "#f2a464"],
    ),
    "night": (
        "#0b1226", "#2a3f6b",
        "#e8f0ff",
        ["#152647", "#1e3a63", "#2a4f7d", "#386497", "#4c79ab"],
    ),
}


def wave_path(layer, n):
    """Gera um caminho SVG de onda suave.

    layer: índice da camada (0 = mais longe, 4 = mais perto)
    n:     total de camadas

    A forma é uma soma de senóides para ficar orgânica (como as ondas do
    macOS Catalina) e fechada na base da imagem.
    """
    base_y = 540 + (layer / max(n - 1, 1)) * 700     # posição média da onda
    amp = 60 + layer * 34                              # amplitude cresce na frente
    freq = 0.0009 + layer * 0.00025
    phase = layer * 1.7

    pts = []
    for x in range(0, W + 1, 40):
        y = base_y - amp * math.sin(x * freq + phase)
        y += (amp * 0.5) * math.sin(x * freq * 2.6 + phase * 1.8)
        pts.append(f"{x},{round(y, 1)}")

    return "M 0,0 " + " L ".join(pts) + f" L {W},{H} L 0,{H} Z"


def build_svg(name, sky_top, sky_bottom, glow, waves):
    """Monta o SVG completo do wallpaper."""
    defs = f"""
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0"    stop-color="{sky_top}"/>
      <stop offset="0.55" stop-color="{sky_bottom}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0"    stop-color="{glow}" stop-opacity="0.95"/>
      <stop offset="0.4"  stop-color="{glow}" stop-opacity="0.4"/>
      <stop offset="1"    stop-color="{glow}" stop-opacity="0"/>
    </radialGradient>
  </defs>"""

    glow_cy = "620"
    layers = "\n".join(
        f'  <path d="{wave_path(i, len(waves))}" fill="{c}" opacity="0.85"/>'
        for i, c in enumerate(waves)
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!--
  Pineapple OS — wallpaper dinâmico "Catalina" ({name})
  Estilo das ondas abstratas do macOS Catalina. Trocado pelo daemon
  pineapple-wallpaper de acordo com o horário.
-->
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
{defs}

  <rect width="{W}" height="{H}" fill="url(#sky)"/>

  <ellipse cx="1280" cy="{glow_cy}" rx="900" ry="520" fill="url(#glow)"/>

{layers}
</svg>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (sky_top, sky_bottom, glow, waves) in PALETTES.items():
        path = os.path.join(OUT, f"catalina-{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_svg(name, sky_top, sky_bottom, glow, waves))
        print("gerado:", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()