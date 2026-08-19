#!/usr/bin/env python3
# =============================================================================
#  Pineapple Settings — configurações do sistema (aparência, rede, conta)
# =============================================================================
import subprocess

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

APP_ID = "org.pineappleos.settings"


class PineappleSettings(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SettingsWindow(application=self)
        win.present()


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Preferências do Sistema")
        self.set_default_size(860, 560)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ---- grid de categorias (estilo Preferências do Sistema) ----
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)

        self.stack.add_named(self._grid_page(), "grid")

        categories = [
            ("pineapple-appearance", "Aparência", self._appearance_page),
            ("pineapple-monitor", "Tela", self._display_page),
            ("pineapple-network", "Rede", self._network_page),
            ("pineapple-user", "Conta", self._account_page),
            ("pineapple-about", "Sobre", self._about_page),
        ]

        for ident, title, factory in categories:
            self.stack.add_named(self._category_page(title, factory), ident)

        self.stack.set_visible_child_name("grid")
        root.append(self.stack)
        self.set_child(root)

    # ------------------------------ grid principal ------------------------------
    def _grid_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_top(32)
        page.set_margin_bottom(32)
        page.set_margin_start(40)
        page.set_margin_end(40)

        t = Gtk.Label(label="Preferências do Sistema", xalign=0.0)
        t.add_css_class("pineapple-pref-title")

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Pesquisar")
        search.set_width_request(280)
        search.set_halign(Gtk.Align.START)
        search.connect("search-changed", self._on_search)

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(6)
        flow.set_min_children_per_line(3)
        flow.set_row_spacing(10)
        flow.set_column_spacing(10)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_vexpand(True)

        for icon, title, ident in [
            ("pineapple-appearance", "Aparência", "pineapple-appearance"),
            ("pineapple-monitor", "Tela", "pineapple-monitor"),
            ("pineapple-network", "Rede", "pineapple-network"),
            ("pineapple-user", "Conta", "pineapple-user"),
            ("pineapple-about", "Sobre", "pineapple-about"),
        ]:
            flow.append(self._grid_tile(icon, title, ident))

        page.append(t)
        page.append(search)
        page.append(flow)
        return page

    def _grid_tile(self, icon, title, ident):
        btn = Gtk.Button()
        btn.set_css_classes(["pineapple-pref-tile"])
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        img = Gtk.Image(icon_name=icon, pixel_size=72)
        lbl = Gtk.Label(label=title)
        box.append(img)
        box.append(lbl)
        btn.set_child(box)
        btn.set_tooltip_text(title)
        btn.connect("clicked", lambda _w, name=ident: self._show_category(name))
        return btn

    def _category_page(self, title, factory):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(14)
        header.set_margin_bottom(6)
        header.set_margin_start(20)
        header.set_margin_end(20)

        back = Gtk.Button(label="‹ Todos")
        back.set_css_classes(["pineapple-back-button"])
        back.set_tooltip_text("Voltar às categorias")
        back.connect("clicked", lambda _w: self._show_grid())

        header.append(back)
        page.append(header)
        page.append(factory(self))
        return page

    def _show_grid(self):
        self.stack.set_visible_child_name("grid")

    def _show_category(self, name):
        self.stack.set_visible_child_name(name)

    def _on_search(self, entry):
        q = entry.get_text().strip().lower()
        target = None
        for ident in ("pineapple-appearance", "pineapple-monitor", "pineapple-network", "pineapple-user", "pineapple-about"):
            name = {
                "pineapple-appearance": "Aparência",
                "pineapple-monitor": "Tela",
                "pineapple-network": "Rede",
                "pineapple-user": "Conta",
                "pineapple-about": "Sobre",
            }[ident]
            if q and q in name.lower():
                target = ident
                break
        if target:
            self.stack.set_visible_child_name(target)

    # ------------------------------ páginas ------------------------------
    def _appearance_page(self, _win):
        page = self._page("Aparência", "Modo claro/escuro, temas e ícones.")

        mode = Gtk.ComboBoxText()
        mode.append_text("Claro")
        mode.append_text("Escuro")
        mode.append_text("Automático")
        mode.set_active(0)  # padrão claro
        mode.connect("changed", self._set_mode)
        page.append(self._row("Modo de exibição", mode))

        theme = Gtk.ComboBoxText()
        theme.append_text("Pineapple-HighSierra")
        theme.append_text("Pineapple-Light")
        theme.append_text("Pineapple-Dark")
        theme.set_active(0)
        page.append(self._row("Tema GTK", theme))

        accel = Gtk.Switch(active=True)
        page.append(self._row("Aceleração por GPU", accel))
        return page

    def _display_page(self, _win):
        page = self._page("Tela", "Resolução, escala e HDR.")
        res = Gtk.ComboBoxText()
        res.append_text("Automático")
        res.append_text("1920 × 1080")
        res.append_text("2560 × 1440")
        res.append_text("3840 × 2160")
        res.set_active(0)
        page.append(self._row("Resolução", res))

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 50, 200, 5)
        scale.set_value(100)
        scale.set_hexpand(True)
        page.append(self._row("Escala (%)", scale))

        night = Gtk.Switch(active=False)
        page.append(self._row("Luz noturna", night))
        return page

    def _network_page(self, _win):
        page = self._page("Rede", "Wi-Fi, Ethernet e proxy.")
        wifi = Gtk.Switch(active=True)
        page.append(self._row("Wi-Fi", wifi))
        vpn = Gtk.Switch(active=False)
        page.append(self._row("VPN", vpn))
        return page

    def _account_page(self, _win):
        page = self._page("Conta", "Usuário e segurança.")
        name = Gtk.Entry()
        name.set_placeholder_text("Nome de usuário")
        page.append(self._row("Usuário", name))

        auto = Gtk.Switch(active=True)
        page.append(self._row("Login automático", auto))
        return page

    def _about_page(self, _win):
        page = self._page("Sobre", "Informações do sistema.")
        try:
            import platform

            info = [
                ("Pineapple OS", self._os_version()),
                ("Kernel", platform.release()),
                ("Arquitetura", platform.machine()),
                ("Python", platform.python_version()),
            ]
            for k, v in info:
                lbl = Gtk.Label(label=f"{k}:  {v}", xalign=0.0)
                lbl.set_margin_top(6)
                lbl.set_margin_bottom(6)
                page.append(lbl)
        except Exception:
            pass
        return page

    # ------------------------------ helpers ------------------------------
    @staticmethod
    def _os_version():
        try:
            with open("/etc/pineappleos-version") as f:
                return f.read().strip()
        except OSError:
            return "dev"

    def _set_mode(self, combo):
        mode = combo.get_active()
        target = "Pineapple-HighSierra" if mode == 0 else "Pineapple-Dark"
        subprocess.Popen(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme",
                          "prefer-light" if mode == 0 else "prefer-dark"])
        subprocess.Popen(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", target])

    @staticmethod
    def _row(title, control):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(16)
        box.set_margin_end(16)
        lbl = Gtk.Label(label=title, xalign=0.0, hexpand=True)
        box.append(lbl)
        box.append(control)
        return box

    @staticmethod
    def _page(title, subtitle):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        page.set_margin_start(24)
        page.set_margin_end(24)
        t = Gtk.Label(label=title, xalign=0.0)
        t.add_css_class("pineapple-settings-title")
        s = Gtk.Label(label=subtitle, xalign=0.0)
        s.add_css_class("pineapple-settings-subtitle")
        page.append(t)
        page.append(s)
        return page


if __name__ == "__main__":
    PineappleSettings().run(None)
