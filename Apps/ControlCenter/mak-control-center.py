#!/usr/bin/env python3
# =============================================================================
#  Mak Control Center — central de controle do Mak OS
#  Acessível pela barra superior (ícone de status).
# =============================================================================
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, GLib  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

APP_ID = "org.makos.controlcenter"


class MakControlCenter(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = ControlCenterWindow(application=self)
        win.present()


class ControlCenterWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Central de Controle")
        self.set_default_size(320, 420)
        self.set_resizable(False)
        self.set_decorated(False)
        self.add_css_class("mak-control-window")

        # Layer Shell: painel flutuante no canto superior direito
        LayerShell.init_for_window(self)
        LayerShell.set_layer(self, LayerShell.Layer.LAYER_TOP)
        LayerShell.set_anchor(self, LayerShell.Edge.TOP, True)
        LayerShell.set_anchor(self, LayerShell.Edge.RIGHT, True)
        LayerShell.set_margin(self, LayerShell.Edge.TOP, 44)
        LayerShell.set_margin(self, LayerShell.Edge.RIGHT, 8)
        LayerShell.set_exclusive_zone(self, -1)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(14)
        root.set_margin_bottom(14)
        root.set_margin_start(14)
        root.set_margin_end(14)
        root.set_css_classes(["mak-control-panel"])

        title = Gtk.Label(label="Central de Controle", xalign=0.0)
        title.add_css_class("mak-control-title")
        root.append(title)

        # ---- brilho ----
        root.append(Gtk.Label(label="Brilho", xalign=0.0))
        brightness = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 5)
        brightness.set_value(80)
        brightness.set_draw_value(False)
        brightness.connect("value-changed", self._set_brightness)
        root.append(brightness)

        # ---- volume ----
        root.append(Gtk.Label(label="Volume", xalign=0.0))
        volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 2)
        volume.set_value(70)
        volume.set_draw_value(False)
        volume.connect("value-changed", self._set_volume)
        root.append(volume)

        # ---- toggles ----
        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        wifi = self._toggle("Wi-Fi", self._toggle_wifi, True)
        bluetooth = self._toggle("Bluetooth", self._toggle_bt, False)
        dark = self._toggle("Modo escuro", self._toggle_dark, True)
        dnd = self._toggle("Não perturbe", self._toggle_dnd, False)
        grid.attach(wifi, 0, 0, 1, 1)
        grid.attach(bluetooth, 1, 0, 1, 1)
        grid.attach(dark, 0, 1, 1, 1)
        grid.attach(dnd, 1, 1, 1, 1)
        root.append(grid)

        # ---- atalhos ----
        settings = Gtk.Button(label="Configurações")
        settings.connect("clicked", lambda *_: subprocess.Popen(["mak-settings"]))
        settings.set_hexpand(True)
        root.append(settings)

        self.set_child(root)

    def _toggle(self, label, cb, active):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_css_classes(["mak-control-toggle"])
        sw = Gtk.Switch(active=active, valign=Gtk.Align.CENTER)
        sw.connect("state-set", cb)
        lbl = Gtk.Label(label=label)
        box.append(sw)
        box.append(lbl)
        return box

    # ---- handlers ----
    @staticmethod
    def _set_volume(scale):
        val = int(scale.get_value()) / 100.0
        subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{val}"])

    @staticmethod
    def _set_brightness(scale):
        val = int(scale.get_value())
        subprocess.Popen(["brightnessctl", "set", f"{val}%"])

    @staticmethod
    def _toggle_wifi(sw, state):
        subprocess.Popen(["nmcli", "radio", "wifi", "on" if state else "off"])
        return False

    @staticmethod
    def _toggle_bt(sw, state):
        subprocess.Popen(["bluetoothctl", "power", "on" if state else "off"])
        return False

    @staticmethod
    def _toggle_dark(sw, state):
        target = "prefer-dark" if state else "prefer-light"
        subprocess.Popen(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", target])

    @staticmethod
    def _toggle_dnd(sw, state):
        mode = "true" if state else "false"
        subprocess.Popen(["gsettings", "set", "org.gnome.desktop.notifications", "show-banners", mode])


if __name__ == "__main__":
    MakControlCenter().run(None)
