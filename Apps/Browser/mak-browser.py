#!/usr/bin/env python3
# =============================================================================
#  Mak Browser — navegador leve (WebKitGTK)
# =============================================================================
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, WebKit  # noqa: E402

APP_ID = "org.makos.browser"
HOMEPAGE = "https://duckduckgo.com"


class MakBrowser(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = BrowserWindow(application=self)
        win.present()


class BrowserWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Mak Browser")
        self.set_default_size(1100, 720)
        self._stack = []

        self.web = WebKit.WebView()
        self.web.connect("load-changed", self._on_load)
        self.web.connect("create", self._on_create)

        self.address = Gtk.Entry()
        self.address.set_placeholder_text("Digite um endereço ou pesquise...")
        self.address.set_hexpand(True)
        self.address.connect("activate", self._navigate)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)

        back = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back.connect("clicked", lambda *_: self.web.go_back())
        fwd = Gtk.Button.new_from_icon_name("go-next-symbolic")
        fwd.connect("clicked", lambda *_: self.web.go_forward())
        reload_ = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        reload_.connect("clicked", lambda *_: self.web.reload())
        home = Gtk.Button.new_from_icon_name("go-home-symbolic")
        home.connect("clicked", lambda *_: self._load(HOMEPAGE))

        toolbar.append(back)
        toolbar.append(fwd)
        toolbar.append(reload_)
        toolbar.append(home)
        toolbar.append(self.address)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(toolbar)
        root.append(self.web)
        self.set_child(root)

        self._load(HOMEPAGE)

    def _load(self, url):
        self.web.load_uri(url)
        self.address.set_text(url)

    def _navigate(self, entry):
        url = entry.get_text().strip()
        if not url:
            return
        if "://" not in url:
            if " " in url or "." not in url:
                url = f"https://duckduckgo.com/?q={url.replace(' ', '+')}"
            else:
                url = "https://" + url
        self._load(url)

    def _on_load(self, _web, event):
        if event == WebKit.LoadEvent.COMMITTED:
            self.address.set_text(self.web.get_uri())
            self.set_title(self.web.get_title() or "Mak Browser")

    def _on_create(self, _web, action):
        # abre popups em nova aba da mesma janela
        window = BrowserWindow.__new__(BrowserWindow)
        Gtk.ApplicationWindow.__init__(window, application=self.get_application())
        window.set_title("Mak Browser")
        window.set_default_size(1100, 720)
        action.set_target_web_view(window.web)
        window.present()
        return window.web


if __name__ == "__main__":
    MakBrowser().run(None)
