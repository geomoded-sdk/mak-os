#!/usr/bin/env python3
# =============================================================================
#  Mak Settings — configurações do sistema (aparência, rede, conta)
# =============================================================================
import subprocess

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

APP_ID = "org.makos.settings"


class MakSettings(Gtk.Application):
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
        self.set_title("Mak Settings")
        self.set_default_size(900, 600)

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # ---- sidebar de categorias ----
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)

        categories = [
            ("mak-appearance", "Aparência", self._appearance_page),
            ("mak-display", "Tela", self._display_page),
            ("mak-network", "Rede", self._network_page),
            ("mak-account", "Conta", self._account_page),
            ("mak-about", "Sobre", self._about_page),
        ]

        sidebar = Gtk.ListBox()
        sidebar.set_css_classes(["mak-settings-sidebar"])
        sidebar.set_width_request(220)
        for ident, title, _factory in categories:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=title, xalign=0.0)
            lbl.set_margin_top(10)
            lbl.set_margin_bottom(10)
            lbl.set_margin_start(12)
            row.set_child(lbl)
            row.set_data("ident", ident)
            sidebar.append(row)
            self.stack.add_named(_factory(self), ident)

        sidebar.connect("row-selected", self._on_category)

        root.append(sidebar)
        root.append(self.stack)
        self.set_child(root)

    def _on_category(self, _list, row):
        if row is not None:
            self.stack.set_visible_child_name(row.get_data("ident"))

    # ------------------------------ páginas ------------------------------
    def _appearance_page(self, _win):
        page = self._page("Aparência", "Modo claro/escuro, temas e ícones.")

        mode = Gtk.ComboBoxText()
        mode.append_text("Claro")
        mode.append_text("Escuro")
        mode.append_text("Automático")
        mode.set_active(1)  # padrão escuro
        mode.connect("changed", self._set_mode)
        page.append(self._row("Modo de exibição", mode))

        theme = Gtk.ComboBoxText()
        theme.append_text("Mak-Dark")
        theme.append_text("Mak-Light")
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
                ("Mak OS", self._os_version()),
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
            with open("/etc/makos-version") as f:
                return f.read().strip()
        except OSError:
            return "dev"

    def _set_mode(self, combo):
        mode = combo.get_active()
        target = "Mak-Light" if mode == 0 else "Mak-Dark"
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
        t.add_css_class("mak-settings-title")
        s = Gtk.Label(label=subtitle, xalign=0.0)
        s.add_css_class("mak-settings-subtitle")
        page.append(t)
        page.append(s)
        return page


if __name__ == "__main__":
    MakSettings().run(None)
