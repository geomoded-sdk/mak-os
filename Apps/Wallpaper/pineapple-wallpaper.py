#!/usr/bin/env python3
# =============================================================================
#  pineapple-wallpaper — daemon de papel de parede do Pineapple OS
#
#  Responsabilidades:
#    1. Aplicar o papel de parede escolhido (modo "static") via swaybg.
#    2. No modo "catalina", trocar o wallpaper dinamicamente conforme o
#       horário do dia (amanhecer → dia → pôr do sol → noite), como o
#       papel de parede dinâmico do macOS Catalina.
#    3. Reagir a mudanças de configuração (gsettings) em tempo real.
#
#  Configuração (gsettings org.pineappleos.desktop):
#    background        caminho da imagem fixa (modo static)
#    background-mode   "static" | "catalina"
#    background-dir    pasta com os wallpapers (catalina-N.svg etc.)
#
#  O renderizador usado é o swaybg (compositor Wayland wlroots/labwc).
# =============================================================================
import os
import subprocess
import sys
import time

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

SCHEMA = "org.pineappleos.desktop"
DEFAULT_DIR = "/usr/share/backgrounds/pineappleos"

# ---------------------------------------------------------------------------
#  Mapa de horários → imagem do Catalina (estilo macOS)
# ---------------------------------------------------------------------------
# (hora inicial inclusiva, hora final exclusiva, arquivo)
CATALINA_SCHEDULE = [
    (5, 8, "catalina-dawn.svg"),    # amanhecer: 05:00–07:59
    (8, 17, "catalina-day.svg"),    # dia:       08:00–16:59
    (17, 20, "catalina-sunset.svg"),  # pôr do sol: 17:00–19:59
    (20, 5, "catalina-night.svg"),  # noite:     20:00–04:59 (vira o dia)
]


def hora_atual():
    """Devolve a hora corrente (0–23)."""
    return time.localtime().tm_hour


def catalina_arquivo(hora, base_dir):
    """Escolhe o arquivo do Catalina correspondente à hora."""
    for inicio, fim, nome in CATALINA_SCHEDULE:
        if fim > inicio:
            dentro = inicio <= hora < fim
        else:
            # intervalo que vira a meia-noite (ex.: noite 20:00–04:59)
            dentro = hora >= inicio or hora < fim
        if dentro:
            return os.path.join(base_dir, "catalina", nome)
    # não deveria acontecer, mas garante um retorno
    return os.path.join(base_dir, "catalina", "catalina-day.svg")


def aplicar_swaybg(imagem):
    """Aplica a imagem de fundo usando swaybg (recarrega o processo)."""
    subprocess.run(["pkill", "-x", "swaybg"], check=False)
    proc = subprocess.Popen(
        ["swaybg", "-i", imagem, "-m", "fill"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


class WallpaperDaemon:
    def __init__(self):
        settings = Gio.Settings.new(SCHEMA)
        settings.connect("changed", self.on_changed)
        self.settings = settings
        self.process = None

    # --- lógica de escolha ---
    def imagem_escolhida(self):
        modo = self.settings.get_string("background-mode")
        base = self.settings.get_string("background-dir") or DEFAULT_DIR
        if modo == "catalina":
            return catalina_arquivo(hora_atual(), base)
        fixa = self.settings.get_string("background")
        return fixa if os.path.exists(fixa) else os.path.join(base, "wallpaper.svg")

    # --- aplicação ---
    def aplicar(self):
        imagem = self.imagem_escolhida()
        if not os.path.exists(imagem):
            return
        self.process = aplicar_swaybg(imagem)

    # --- temporizador do modo dinâmico (Catalina) ---
    def tick(self):
        if self.settings.get_string("background-mode") == "catalina":
            self.aplicar()
        return True  # mantém o timer ativo

    def on_changed(self, settings, key, *args):
        # Mudou configuração → reaplica imediatamente.
        self.aplicar()

    def run(self):
        self.aplicar()
        # Checa a cada minuto se o horário exige outra imagem do Catalina.
        GLib.timeout_add_seconds(60, self.tick)
        GLib.MainLoop().run()


def main():
    if "--print" in sys.argv:
        # Modo utilitário: imprime a imagem que seria usada agora.
        daemon = WallpaperDaemon()
        print(daemon.imagem_escolhida())
        return 0
    WallpaperDaemon().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())