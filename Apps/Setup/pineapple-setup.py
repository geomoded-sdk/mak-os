#!/usr/bin/env python3
"""Pineapple OS first-run setup assistant."""
import os
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

APP_ID = "org.pineappleos.setup"
MARKER = Path.home() / ".config/pineappleos/first-run-complete"


class SetupApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        if MARKER.exists():
            self.quit()
            return
        window = SetupWindow(application=self)
        window.present()


class SetupWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Configurar o Pineapple OS")
        self.set_default_size(900, 600)
        self.set_resizable(False)
        self.page_index = 0

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self.stack.set_transition_duration(220)
        self.pages = [
            self._welcome_page(),
            self._region_page(),
            self._keyboard_page(),
            self._network_page(),
            self._migration_page(),
            self._account_page(),
            self._privacy_page(),
            self._finish_page(),
        ]
        for index, page in enumerate(self.pages):
            self.stack.add_named(page, f"page-{index}")

        self.back = Gtk.Button(label="Voltar")
        self.back.connect("clicked", self._back)
        self.next = Gtk.Button(label="Continuar")
        self.next.add_css_class("suggested-action")
        self.next.connect("clicked", self._next)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.set_halign(Gtk.Align.END)
        footer.set_margin_top(12)
        footer.set_margin_bottom(20)
        footer.set_margin_start(32)
        footer.set_margin_end(32)
        footer.append(self.back)
        footer.append(self.next)

        self.progress = Gtk.Label(xalign=0.0)
        self.progress.add_css_class("pineapple-file-meta")

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(self.stack)
        root.append(self.progress)
        root.append(footer)
        self.set_child(root)
        self._update_buttons()

    def _page(self, title, subtitle):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        page.set_margin_top(54)
        page.set_margin_bottom(28)
        page.set_margin_start(72)
        page.set_margin_end(72)
        title_label = Gtk.Label(label=title, xalign=0.0)
        title_label.add_css_class("pineapple-pref-title")
        subtitle_label = Gtk.Label(label=subtitle, xalign=0.0, wrap=True)
        subtitle_label.add_css_class("pineapple-file-meta")
        page.append(title_label)
        page.append(subtitle_label)
        return page

    def _welcome_page(self):
        page = self._page(
            "Bem-vindo ao Pineapple OS",
            "Vamos preparar seu ambiente com a experiência Pineapple.",
        )
        body = Gtk.Label(
            label="Seu Canopy, Dock, Launchpad e apps compatíveis já estão prontos. "
            "Você poderá alterar tudo depois em Preferências do Sistema.",
            wrap=True,
            xalign=0.0,
        )
        body.set_max_width_chars(70)
        page.append(body)
        return page

    def _region_page(self):
        page = self._page(
            "Escolha seu país ou região",
            "Isso define formatos de data, hora, moeda e serviços locais.",
        )
        region = Gtk.DropDown.new_from_strings(["Brasil", "Portugal", "Estados Unidos", "Outro"])
        region.set_halign(Gtk.Align.START)
        page.append(region)
        return page

    def _keyboard_page(self):
        page = self._page(
            "Escolha o layout do teclado",
            "Você pode alterar o layout depois em Preferências do Sistema.",
        )
        keyboard = Gtk.DropDown.new_from_strings(["Português (Brasil)", "Português", "US", "UK"])
        keyboard.set_halign(Gtk.Align.START)
        page.append(keyboard)
        return page

    def _network_page(self):
        page = self._page(
            "Conecte-se à rede",
            "A rede é usada para atualizações, apps e serviços online.",
        )
        button = Gtk.Button(label="Abrir Preferências de Rede")
        button.set_halign(Gtk.Align.START)
        button.connect("clicked", lambda *_: self._open_settings("network"))
        page.append(button)
        return page

    def _migration_page(self):
        page = self._page(
            "Transfira seus dados",
            "Copie documentos e preferências de outro computador ou comece do zero.",
        )
        migrate = Gtk.Button(label="Abrir Ferramenta de Migração")
        migrate.set_halign(Gtk.Align.START)
        migrate.connect("clicked", lambda *_: self._open_settings("migration"))
        page.append(migrate)
        page.append(Gtk.Label(label="Você também pode fazer isso mais tarde.", xalign=0.0))
        return page

    def _account_page(self):
        page = self._page(
            "Crie sua experiência Pineapple",
            "A conta atual do sistema será usada para seus arquivos, apps e preferências.",
        )
        page.append(Gtk.Label(label=f"Usuário: {os.environ.get('USER', 'pineapple')}", xalign=0.0))
        page.append(Gtk.Label(label="Uma conta online é opcional. O sistema funciona localmente.", xalign=0.0))
        return page

    def _privacy_page(self):
        page = self._page(
            "Privacidade e compatibilidade",
            "O Pineapple mantém seus dados no sistema Linux e controla permissões por portals.",
        )
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for text in (
            "Apps Flatpak usam sandbox quando disponível.",
            "Wine e Darling ficam separados de seus arquivos do sistema.",
            "O Spotlight indexa apenas locais visíveis e permitidos.",
        ):
            row.append(Gtk.Label(label=text, xalign=0.0))
        page.append(row)
        return page

    def _finish_page(self):
        page = self._page(
            "Tudo pronto",
            "O Pineapple OS está configurado. Você pode reabrir as Preferências a qualquer momento.",
        )
        return page

    def _open_settings(self, category):
        subprocess.Popen(["pineapple-settings", "--category", category])

    def _back(self, *_):
        if self.page_index > 0:
            self.page_index -= 1
            self.stack.set_visible_child_name(f"page-{self.page_index}")
            self._update_buttons()

    def _next(self, *_):
        if self.page_index < len(self.pages) - 1:
            self.page_index += 1
            self.stack.set_visible_child_name(f"page-{self.page_index}")
            self._update_buttons()
            return
        MARKER.parent.mkdir(parents=True, exist_ok=True)
        MARKER.write_text("completed\n", encoding="utf-8")
        self.get_application().quit()

    def _update_buttons(self):
        self.back.set_visible(self.page_index > 0)
        self.next.set_label("Começar a usar" if self.page_index == len(self.pages) - 1 else "Continuar")
        self.progress.set_label(f"Etapa {self.page_index + 1} de {len(self.pages)}")


if __name__ == "__main__":
    SetupApp().run()
