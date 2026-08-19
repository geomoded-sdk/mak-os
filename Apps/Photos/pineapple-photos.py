#!/usr/bin/env python3
# =============================================================================
#  Pineapple Photos — visualizador de fotos (pastas de imagens)
# =============================================================================
import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, GdkPixbuf  # noqa: E402

APP_ID = "org.pineappleos.photos"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".heic")


class PineapplePhotos(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = PhotosWindow(application=self)
        win.present()


class PhotosWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Pineapple Photos")
        self.set_default_size(1000, 680)
        self._images = []
        self._index = 0
        self._folder = self._pictures_dir()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)

        self.folder_label = Gtk.Label(label=self._folder, xalign=0.0, hexpand=True)
        self.folder_label.add_css_class("pineapple-path")
        open_btn = Gtk.Button(label="Abrir pasta")
        open_btn.connect("clicked", self._pick_folder)
        toolbar.append(self.folder_label)
        toolbar.append(open_btn)
        root.append(toolbar)

        self.image = Gtk.Image()
        self.image.set_vexpand(True)
        self.image.set_hexpand(True)
        self.image.set_css_classes(["pineapple-photo-view"])

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_child(self.image)
        root.append(self.scroller)

        self.nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.nav.set_halign(Gtk.Align.CENTER)
        self.nav.set_margin_top(6)
        self.nav.set_margin_bottom(8)
        prev = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        next_ = Gtk.Button.new_from_icon_name("go-next-symbolic")
        prev.connect("clicked", self._prev)
        next_.connect("clicked", self._next)
        self.counter = Gtk.Label(label="")
        self.nav.append(prev)
        self.nav.append(self.counter)
        self.nav.append(next_)
        root.append(self.nav)

        self.set_child(root)
        self._load_folder()

    @staticmethod
    def _pictures_dir():
        d = os.path.join(os.path.expanduser("~"), "Imagens")
        return d if os.path.isdir(d) else os.path.expanduser("~")

    def _pick_folder(self, *_):
        dialog = Gtk.FileDialog()
        dialog.select_folder(None, None, self._on_folder, None)

    def _on_folder(self, _dialog, result):
        try:
            folder = _dialog.select_folder_finish(result).get_path()
            self._folder = folder
            self.folder_label.set_label(folder)
            self._load_folder()
        except Exception:
            pass

    def _load_folder(self):
        self._images = sorted(
            f for f in os.listdir(self._folder)
            if f.lower().endswith(IMAGE_EXTS)
        )
        self._index = 0 if self._images else -1
        self._show_current()

    def _show_current(self):
        if self._index < 0 or not self._images:
            self.image.clear()
            self.counter.set_label("sem fotos")
            return
        path = os.path.join(self._folder, self._images[self._index])
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            self.image.set_from_pixbuf(pixbuf)
            self.counter.set_label(f"{self._index + 1} / {len(self._images)}")
            self.set_title(f"Pineapple Photos — {self._images[self._index]}")
        except Exception as e:
            self.image.clear()
            self.counter.set_label(f"não foi possível abrir: {e}")

    def _prev(self, *_):
        if self._images:
            self._index = (self._index - 1) % len(self._images)
            self._show_current()

    def _next(self, *_):
        if self._images:
            self._index = (self._index + 1) % len(self._images)
            self._show_current()


if __name__ == "__main__":
    PineapplePhotos().run(None)
