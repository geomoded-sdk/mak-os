#!/usr/bin/env python3
# =============================================================================
#  pineapple_store_categories.py — categorias da Pineapple Store (módulo puro, testável)
# =============================================================================

CATEGORIES = [
    ("todos", "Todos"),
    ("nativos", "Nativos"),
    ("graficos", "Gráficos"),
    ("escritorio", "Escritório"),
    ("midia", "Mídia"),
    ("internet", "Internet"),
    ("desenvolvimento", "Desenvolvimento"),
    ("jogos", "Jogos"),
    ("outros", "Outros"),
]

_GRAPHICS = ("gimp", "inkscape", "krita", "darktable", "rawtherapee")
_OFFICE = ("libreoffice", "onlyoffice", "collabora")
_MEDIA = ("vlc", "spotify", "audacity", "kodi", "strawberry", "parole")
_INTERNET = ("firefox", "chromium", "google", "brave", "discord", "telegram", "element", "slack", "whatsapp")
_DEV = ("code", "eclipse", "intellij", "android-studio", "pycharm", "gitkraken", "node")
_GAMES = ("steam", "lutris", "supertux", "0ad", "warsow", "retroarch")


def category_for(app_id):
    """Infere a categoria de um app a partir do seu id Flatpak."""
    app_id = (app_id or "").lower()
    if app_id.startswith("org.pineappleos"):
        return "nativos"
    if any(k in app_id for k in _GRAPHICS):
        return "graficos"
    if any(k in app_id for k in _OFFICE):
        return "escritorio"
    if any(k in app_id for k in _MEDIA):
        return "midia"
    if any(k in app_id for k in _INTERNET):
        return "internet"
    if any(k in app_id for k in _DEV):
        return "desenvolvimento"
    if any(k in app_id for k in _GAMES):
        return "jogos"
    return "outros"


def category_label(key):
    """Rótulo legível de uma categoria."""
    for k, label in CATEGORIES:
        if k == key:
            return label
    return "Outros"
