#!/usr/bin/env python3
# =============================================================================
#  pineapple-notifyd — central de notificações do Pineapple OS
#
#  Implementa org.freedesktop.Notifications (D-Bus) e mostra banners
#  usando notify-send (ou o daemon do desktop ativo).
# =============================================================================
import subprocess

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gio  # noqa: E402

APP_ID = "org.pineappleos.notifyd"
D_BUS_NAME = "org.freedesktop.Notifications"
D_BUS_PATH = "/org/freedesktop/Notifications"


class NotifyDaemon:
    """Proxy D-Bus: encaminha notificações para o serviço ativo."""

    def __init__(self):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self.proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications",
                None,
            )
        except Exception:
            self.proxy = None

    def notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, timeout):
        try:
            if self.proxy is not None:
                self.proxy.call_sync(
                    "Notify",
                    GLib.Variant(
                        "(susssasa{sv}i)",
                        (app_name, replaces_id, app_icon, summary, body, actions, hints, timeout),
                    ),
                    Gio.DBusCallFlags.NONE,
                    500,
                    None,
                )
                return replaces_id
        except Exception:
            pass
        # fallback: notify-send
        try:
            subprocess.run(["notify-send", summary, body], check=False)
        except FileNotFoundError:
            print(f"[pineapple-notifyd] {summary}: {body}")
        return 0


class PineappleNotifyd(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        self.hold()
        daemon = NotifyDaemon()

        def on_notify(_conn, _sender, _path, _iface, _sig, params):
            args = params.unpack()
            daemon.notify(*args)

        try:
            self._bus = Gio.bus_own_name_on_connection(
                Gio.bus_get_sync(Gio.BusType.SESSION, None),
                D_BUS_NAME,
                Gio.BusNameOwnerFlags.NONE,
                None,
                None,
            )
        except Exception:
            pass

        GLib.timeout_add_seconds(1, lambda: True)  # mantém vivo


if __name__ == "__main__":
    PineappleNotifyd().run(None)
