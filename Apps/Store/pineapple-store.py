#!/usr/bin/env python3
# =============================================================================
#  Pineapple Store — loja de aplicativos (Flatpak) com categorias e repositório próprio
# =============================================================================
import subprocess

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from pineapple_store_categories import CATEGORIES, category_for  # noqa: E402

APP_ID = "org.pineappleos.store"
FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"


class PineappleStore(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = StoreWindow(application=self)
        win.present()


class StoreWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Pineapple Store")
        self.set_default_size(1000, 680)
        self._apps = []
        self._category = "todos"

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(8)
        header.set_margin_bottom(8)
        header.set_margin_start(12)
        header.set_margin_end(12)

        title = Gtk.Label(label="Pineapple Store", xalign=0.0)
        title.add_css_class("pineapple-settings-title")
        self.search = Gtk.SearchEntry()
        self.search.set_hexpand(True)
        self.search.set_placeholder_text("Pesquisar apps...")
        self.search.connect("search-changed", lambda *_: self._refresh())

        refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh.connect("clicked", lambda *_: self._load_apps())

        header.append(title)
        header.append(self.search)
        header.append(refresh)

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # ---- sidebar de categorias ----
        self.cat_list = Gtk.ListBox()
        self.cat_list.set_css_classes(["pineapple-sidebar"])
        self.cat_list.set_width_request(170)
        for key, label in CATEGORIES:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(10)
            img = Gtk.Image.new_from_icon_name(self._cat_icon(key))
            img.set_pixel_size(16)
            lbl = Gtk.Label(label=label, xalign=0.0)
            box.append(img)
            box.append(lbl)
            row.set_child(box)
            row.set_data("cat", key)
            self.cat_list.append(row)
        self.cat_list.connect("row-selected", self._on_cat)

        # ---- grid de apps ----
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right.append(header)

        self.flow = Gtk.FlowBox()
        self.flow.set_max_children_per_line(4)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_halign(Gtk.Align.FILL)

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(self.flow)
        scroller.set_vexpand(True)
        right.append(scroller)

        self.status = Gtk.Label(label="Carregando...", xalign=0.0)
        self.status.set_margin_top(4)
        self.status.set_margin_bottom(4)
        self.status.set_margin_start(12)
        right.append(self.status)

        main.append(self.cat_list)
        main.append(right)
        root.append(main)
        self.set_child(root)

        GLib.idle_add(self._ensure_flatpak)
        GLib.idle_add(self._load_apps)

    @staticmethod
    def _cat_icon(key):
        icons = {
            "todos": "view-grid-symbolic",
            "nativos": "applications-system-symbolic",
            "graficos": "image-x-generic-symbolic",
            "escritorio": "x-office-document-symbolic",
            "midia": "multimedia-player-symbolic",
            "internet": "web-browser-symbolic",
            "desenvolvimento": "applications-development-symbolic",
            "jogos": "applications-games-symbolic",
            "outros": "application-x-executable-symbolic",
        }
        return icons.get(key, "application-x-executable-symbolic")

    # ---------------- categorias ----------------
    def _on_cat(self, _list, row):
        if row is None:
            return
        self._category = row.get_data("cat") or "todos"
        self._refresh()

    # ---------------- flatpak ----------------
    def _ensure_flatpak(self):
        if not self._flatpak_remotes():
            subprocess.Popen(["flatpak", "remote-add", "--if-not-exists", "flathub", FLATHUB])
        return False

    @staticmethod
    def _flatpak_remotes():
        try:
            out = subprocess.run(["flatpak", "remotes"], capture_output=True, text=True).stdout
            return "flathub" in out
        except FileNotFoundError:
            return False

    def _load_apps(self):
        self.status.set_label("Consultando repositórios...")
        apps = self._query_flatpak()
        if not apps:
            apps = self._fallback_apps()
            self.status.set_label("Flatpak indisponível — mostrando apps nativos")
        else:
            self.status.set_label(f"{len(apps)} apps disponíveis")
        self._apps = apps
        self._refresh()

    def _query_flatpak(self):
        if not self._flatpak_remotes():
            return []
        try:
            out = subprocess.run(
                ["flatpak", "search", "--columns=name,application,description", ""],
                capture_output=True, text=True, timeout=30,
            ).stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        result = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and "." in parts[1]:
                result.append({
                    "name": parts[0],
                    "id": parts[1],
                    "desc": parts[2],
                    "cat": category_for(parts[1]),
                })
            if len(result) >= 60:
                break
        return result

    def _fallback_apps(self):
        return [
            {"name": "Pineapple Calculator", "id": "org.pineappleos.calculator", "desc": "Calculadora nativa", "cat": "nativos", "installed": True},
            {"name": "Pineapple Terminal", "id": "org.pineappleos.terminal", "desc": "Terminal nativo", "cat": "nativos", "installed": True},
            {"name": "Pineapple Notes", "id": "org.pineappleos.notes", "desc": "Notas", "cat": "nativos", "installed": True},
            {"name": "Pineapple Photos", "id": "org.pineappleos.photos", "desc": "Fotos", "cat": "nativos", "installed": True},
            {"name": "Pineapple Music", "id": "org.pineappleos.music", "desc": "Música", "cat": "nativos", "installed": True},
            {"name": "Pineapple Browser", "id": "org.pineappleos.browser", "desc": "Navegador", "cat": "nativos", "installed": True},
            {"name": "Pineapple Monitor", "id": "org.pineappleos.monitor", "desc": "Monitor de recursos", "cat": "nativos", "installed": True},
            {"name": "GIMP", "id": "org.gimp.GIMP", "desc": "Editor de imagens", "cat": "graficos", "installed": False},
            {"name": "Inkscape", "id": "org.inkscape.Inkscape", "desc": "Vetores", "cat": "graficos", "installed": False},
            {"name": "LibreOffice", "id": "org.libreoffice.LibreOffice", "desc": "Suíte de escritório", "cat": "escritorio", "installed": False},
            {"name": "VLC", "id": "org.videolan.VLC", "desc": "Player de mídia", "cat": "midia", "installed": False},
            {"name": "Spotify", "id": "com.spotify.Client", "desc": "Streaming de música", "cat": "midia", "installed": False},
            {"name": "Firefox", "id": "org.mozilla.firefox", "desc": "Navegador", "cat": "internet", "installed": False},
            {"name": "Discord", "id": "com.discordapp.Discord", "desc": "Chat e voz", "cat": "internet", "installed": False},
            {"name": "VS Code", "id": "com.visualstudio.code", "desc": "Editor de código", "cat": "desenvolvimento", "installed": False},
            {"name": "RetroArch", "id": "org.libretro.RetroArch", "desc": "Emulador de consoles", "cat": "jogos", "installed": False},
        ]

    def _refresh(self):
        while (child := self.flow.get_first_child()) is not None:
            self.flow.remove(child)
        q = self.search.get_text().lower()
        for app in self._apps:
            if self._category not in ("todos", None) and app.get("cat", "outros") != self._category:
                continue
            if q and q not in app["name"].lower() and q not in app["id"].lower():
                continue
            self.flow.append(self._app_card(app))

    def _app_card(self, app):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_size_request(220, 150)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.add_css_class("pineapple-store-card")

        icon = Gtk.Image.new_from_icon_name("application-x-executable")
        icon.set_pixel_size(40)
        box.append(icon)

        name = Gtk.Label(label=app["name"], xalign=0.0)
        name.add_css_class("pineapple-store-name")
        box.append(name)

        desc = Gtk.Label(label=app.get("desc", "")[:80], xalign=0.0, wrap=True)
        desc.add_css_class("pineapple-store-desc")
        desc.set_max_width_chars(26)
        box.append(desc)

        btn_label = "Abrir" if app.get("installed") else "Instalar"
        btn = Gtk.Button(label=btn_label)
        app_id = app["id"]
        btn.connect("clicked", lambda *_: self._install(app_id))
        box.append(btn)
        return box

    def _install(self, app_id):
        if not self._flatpak_remotes():
            self.status.set_label("Flatpak não configurado")
            return
        self.status.set_label(f"Instalando {app_id}...")
        subprocess.Popen(["flatpak", "install", "-y", "flathub", app_id])


if __name__ == "__main__":
    PineappleStore().run(None)
