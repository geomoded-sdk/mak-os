#!/usr/bin/env python3
# =============================================================================
#  gen-icons.py — gera o conjunto de ícones SVG do Pineapple OS
#
#  Identidade: quadrados arredondados com gradiente "petróleo → coral"
#  e glifos geométricos brancos, desenhados sob medida (sem marcas alheias).
# =============================================================================
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = os.path.join(BASE, "Icons", "pineapple-icons", "scalable", "apps")
SYM = os.path.join(BASE, "Icons", "pineapple-icons", "symbolic", "apps")
os.makedirs(APPS, exist_ok=True)
os.makedirs(SYM, exist_ok=True)

GRAD = (
    'defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#3f7fbf"/><stop offset="0.55" stop-color="#4f9dde"/>'
    '<stop offset="1" stop-color="#e2776f"/></linearGradient></defs>'
)


def app_svg(name, glyph, accent=None):
    """Gera um ícone de app: 128x128, cantos arredondados, glifo branco."""
    if accent:
        grad = f'defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">{accent}</linearGradient></defs>'
    else:
        grad = GRAD
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <{grad}
  <rect x="4" y="4" width="120" height="120" rx="28" fill="url(#g)"/>
  <g fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
    {glyph}
  </g>
</svg>
'''


def symbolic_svg(name, body):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <g fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
    {body}
  </g>
</svg>
'''


def write(fname, content):
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    print("gerado:", os.path.relpath(fname, BASE))


# ------------------------------- apps -------------------------------
write(os.path.join(APPS, "pineapple-logo.svg"), app_svg(
    "logo",
    # Coroa de folhas do abacaxi
    '<path d="M64 38 L57 20 M64 38 L64 16 M64 38 L71 20 M64 38 L50 23 M64 38 L78 23"/>'
    # Corpo (elipse)
    '<ellipse cx="64" cy="66" rx="17" ry="24"/>'
    # Textura losangular (linhas finas)
    '<path d="M54 50 l20 -13 M52 58 l22 -15 M52 66 l22 -15 M52 74 l22 -15" stroke-width="3"/>'
    '<path d="M74 50 l-20 -13 M76 58 l-22 -15 M76 66 l-22 -15 M76 74 l-22 -15" stroke-width="3"/>',
))

write(os.path.join(APPS, "pineapple-canopy.svg"), app_svg(
    "canopy",
    '<rect x="38" y="30" width="52" height="68" rx="10"/>'
    '<line x1="46" y1="48" x2="82" y2="48"/><line x1="46" y1="58" x2="82" y2="58"/>'
    '<line x1="46" y1="68" x2="70" y2="68"/>',
))

write(os.path.join(APPS, "pineapple-terminal.svg"), app_svg(
    "terminal",
    '<rect x="28" y="32" width="72" height="64" rx="10"/>'
    '<path d="M44 52 l10 8 -10 8"/><line x1="60" y1="68" x2="80" y2="68"/>',
))

write(os.path.join(APPS, "pineapple-browser.svg"), app_svg(
    "browser",
    '<circle cx="64" cy="64" r="34"/>'
    '<path d="M64 30 v68"/><path d="M30 64 a34 34 0 0 0 68 0"/>',
))

write(os.path.join(APPS, "pineapple-music.svg"), app_svg(
    "music",
    '<path d="M56 88 V44 l28 -8 v44"/>'
    '<circle cx="48" cy="88" r="10"/><circle cx="76" cy="80" r="10"/>',
))

write(os.path.join(APPS, "pineapple-photos.svg"), app_svg(
    "photos",
    '<rect x="26" y="34" width="76" height="60" rx="10"/>'
    '<circle cx="46" cy="54" r="8"/>'
    '<path d="M30 88 l20 -22 14 14 12 -12 22 20"/>',
))

write(os.path.join(APPS, "pineapple-notes.svg"), app_svg(
    "notes",
    '<path d="M38 24 h38 l14 14 v66 h-52 z"/>'
    '<path d="M76 24 v14 h14"/><line x1="44" y1="56" x2="78" y2="56"/>'
    '<line x1="44" y1="68" x2="78" y2="68"/>',
))

write(os.path.join(APPS, "pineapple-store.svg"), app_svg(
    "store",
    '<path d="M30 52 h68 l-6 40 h-56 z"/>'
    '<path d="M44 52 a8 8 0 0 1 16 0 a8 8 0 0 1 16 0" stroke-width="6"/>',
))

write(os.path.join(APPS, "pineapple-settings.svg"), app_svg(
    "settings",
    '<circle cx="64" cy="64" r="14"/>'
    '<path d="M64 26 v12 M64 90 v12 M26 64 h12 M90 64 h12 '
    'M37 37 l8 8 M83 83 l8 8 M83 37 l-8 8 M37 83 l8 -8"/>',
))

write(os.path.join(APPS, "pineapple-calc.svg"), app_svg(
    "calc",
    '<rect x="38" y="24" width="52" height="80" rx="10"/>'
    '<circle cx="48" cy="42" r="3" fill="#fff" stroke="none"/>'
    '<circle cx="64" cy="42" r="3" fill="#fff" stroke="none"/>'
    '<circle cx="80" cy="42" r="3" fill="#fff" stroke="none"/>'
    '<line x1="48" y1="62" x2="80" y2="62"/>'
    '<line x1="48" y1="76" x2="80" y2="76"/>'
    '<line x1="48" y1="90" x2="80" y2="90"/>',
))

write(os.path.join(APPS, "pineapple-monitor.svg"), app_svg(
    "monitor",
    '<rect x="28" y="34" width="72" height="52" rx="10"/>'
    '<path d="M64 86 v14"/><line x1="50" y1="100" x2="78" y2="100"/>',
))

write(os.path.join(APPS, "pineapple-appearance.svg"), app_svg(
    "appearance",
    '<line x1="32" y1="44" x2="96" y2="44"/><circle cx="44" cy="44" r="7"/>'
    '<line x1="32" y1="64" x2="96" y2="64"/><circle cx="80" cy="64" r="7"/>'
    '<line x1="32" y1="84" x2="96" y2="84"/><circle cx="56" cy="84" r="7"/>',
))

write(os.path.join(APPS, "pineapple-network.svg"), app_svg(
    "network",
    '<circle cx="64" cy="64" r="34"/>'
    '<path d="M64 30 a34 34 0 0 1 0 68 M64 30 a34 34 0 0 0 0 68"/>'
    '<ellipse cx="64" cy="64" rx="14" ry="34"/>',
))

write(os.path.join(APPS, "pineapple-user.svg"), app_svg(
    "user",
    '<circle cx="64" cy="48" r="20"/>'
    '<path d="M36 100 c0 -24 56 -24 56 0"/>',
))

write(os.path.join(APPS, "pineapple-about.svg"), app_svg(
    "about",
    '<circle cx="64" cy="64" r="32"/>'
    '<line x1="64" y1="60" x2="64" y2="86"/>'
    '<circle cx="64" cy="46" r="3" fill="#fff" stroke="none"/>',
))

write(os.path.join(APPS, "pineapple-assistant.svg"), app_svg(
    "assistant",
    '<circle cx="64" cy="50" r="24"/>'
    '<path d="M40 92 c0 -16 48 -16 48 0"/>',
))

write(os.path.join(APPS, "pineapple-launchpad.svg"), app_svg(
    "launchpad",
    '<rect x="30" y="30" width="20" height="20" rx="5"/>'
    '<rect x="54" y="30" width="20" height="20" rx="5"/>'
    '<rect x="78" y="30" width="20" height="20" rx="5"/>'
    '<rect x="30" y="54" width="20" height="20" rx="5"/>'
    '<rect x="54" y="54" width="20" height="20" rx="5"/>'
    '<rect x="78" y="54" width="20" height="20" rx="5"/>'
    '<rect x="30" y="78" width="20" height="20" rx="5"/>'
    '<rect x="54" y="78" width="20" height="20" rx="5"/>'
    '<rect x="78" y="78" width="20" height="20" rx="5"/>',
))

write(os.path.join(APPS, "pineapple-mission.svg"), app_svg(
    "mission",
    '<rect x="36" y="36" width="56" height="44" rx="9"/>'
    '<rect x="44" y="50" width="56" height="44" rx="9" opacity="0.75"/>'
    '<rect x="52" y="64" width="56" height="44" rx="9"/>'
    '<circle cx="80" cy="40" r="3" fill="#ffffff" stroke="none"/>',
))

# ------------------------------- simbólicos (status) -------------------------------
write(os.path.join(SYM, "pineapple-volume-high-symbolic.svg"), symbolic_svg(
    "vol",
    '<path d="M2 6 h3 l4 -4 v12 l-4 -4 h-3 z" fill="currentColor" stroke="none"/>'
    '<path d="M11 5 a5 5 0 0 1 0 6 M14 3 a9 9 0 0 1 0 10"/>',
))
write(os.path.join(SYM, "pineapple-wifi-symbolic.svg"), symbolic_svg(
    "wifi",
    '<path d="M2 6 a10 10 0 0 1 12 0 M5 9 a6 6 0 0 1 6 0"/>'
    '<circle cx="8" cy="13" r="1.4" fill="currentColor" stroke="none"/>',
))
write(os.path.join(SYM, "pineapple-battery-symbolic.svg"), symbolic_svg(
    "battery",
    '<rect x="1" y="4" width="12" height="8" rx="1.5"/>'
    '<rect x="14" y="6" width="1.5" height="4" rx="0.5"/>'
    '<rect x="3" y="6" width="7" height="4" fill="currentColor" stroke="none"/>',
))
write(os.path.join(SYM, "pineapple-control-center-symbolic.svg"), symbolic_svg(
    "ctrl",
    '<path d="M3 4 h6 M13 4 h0 M3 8 h2 M9 8 h4 M3 12 h8 M15 12 h0"/>'
    '<circle cx="11" cy="4" r="2"/><circle cx="7" cy="8" r="2"/><circle cx="13" cy="12" r="2"/>',
))
write(os.path.join(SYM, "pineapple-wifi-disabled-symbolic.svg"), symbolic_svg(
    "wifioff",
    '<path d="M2 2 l12 12 M2 6 a10 10 0 0 1 5 -3 M8 8 a6 6 0 0 1 3 -1"/>',
))

# ------------------------------- index.theme -------------------------------
theme = os.path.join(BASE, "Icons", "pineapple-icons", "index.theme")
with open(theme, "w", encoding="utf-8") as f:
    f.write("""[Icon Theme]
Name=Pineapple Icons
Comment=Ícones próprios do Pineapple OS
Example=pineapple-canopy

Directory=scalable/apps
Size=128
MinSize=16
MaxSize=512
Type=Scalable

Directory=symbolic/apps
Size=16
Type=Scalable
""")
print("gerado:", os.path.relpath(theme, BASE))
