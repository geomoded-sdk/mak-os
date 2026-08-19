#!/usr/bin/env python3
# =============================================================================
#  Pineapple Music — player de música simples (GLib playbin)
# =============================================================================
import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, GLib, Gst  # noqa: E402

APP_ID = "org.pineappleos.music"
AUDIO_EXTS = (".mp3", ".ogg", ".flac", ".wav", ".m4a", ".opus")


class PineappleMusic(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        Gst.init(None)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MusicWindow(application=self)
        win.present()


class MusicWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Pineapple Music")
        self.set_default_size(860, 520)
        self._playlist = []
        self._index = -1

        self.player = Gst.ElementFactory.make("playbin", "player")
        self.player.set_property("volume", 0.8)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # barra de título / pasta
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)
        open_btn = Gtk.Button(label="Abrir pasta")
        open_btn.connect("clicked", self._pick_folder)
        self.title_label = Gtk.Label(label="", xalign=0.0, hexpand=True)
        self.title_label.add_css_class("pineapple-path")
        toolbar.append(self.title_label)
        toolbar.append(open_btn)
        root.append(toolbar)

        # lista de faixas
        self.list = Gtk.ListBox()
        self.list.connect("row-activated", self._on_row)
        scroller = Gtk.ScrolledWindow()
        scroller.set_child(self.list)
        scroller.set_vexpand(True)
        root.append(scroller)

        # controles
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls.set_halign(Gtk.Align.CENTER)
        controls.set_margin_top(10)
        controls.set_margin_bottom(10)

        self.prev_btn = Gtk.Button.new_from_icon_name("media-skip-backward-symbolic")
        self.play_btn = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        self.next_btn = Gtk.Button.new_from_icon_name("media-skip-forward-symbolic")
        self.prev_btn.connect("clicked", self._prev)
        self.play_btn.connect("clicked", self._toggle)
        self.next_btn.connect("clicked", self._next)

        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.slider.set_hexpand(True)
        self.slider.set_draw_value(False)
        self.slider.connect("value-changed", self._seek)

        controls.append(self.prev_btn)
        controls.append(self.play_btn)
        controls.append(self.next_btn)
        controls.append(self.slider)

        volume = Gtk.VolumeButton()
        volume.connect("value-changed", self._volume)
        controls.append(volume)

        controls.set_margin_start(8)
        controls.set_margin_end(8)
        root.append(controls)

        self.set_child(root)
        GLib.timeout_add_seconds(1, self._update_slider)

    # ---------------- playlist ----------------
    def _pick_folder(self, *_):
        dialog = Gtk.FileDialog()
        dialog.select_folder(None, None, self._on_folder, None)

    def _on_folder(self, _dialog, result):
        try:
            folder = _dialog.select_folder_finish(result).get_path()
        except Exception:
            return
        self._playlist = sorted(
            f for f in os.listdir(folder) if f.lower().endswith(AUDIO_EXTS)
        )
        self._folder = folder
        self.title_label.set_label(folder)
        while (row := self.list.get_first_child()) is not None:
            self.list.remove(row)
        for name in self._playlist:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=name, xalign=0.0)
            lbl.set_margin_top(8)
            lbl.set_margin_bottom(8)
            lbl.set_margin_start(8)
            row.set_child(lbl)
            self.list.append(row)
        self._index = -1

    def _on_row(self, _list, row):
        self._index = row.get_index()
        self._play()

    # ---------------- playback ----------------
    def _play(self):
        if self._index < 0 or self._index >= len(self._playlist):
            return
        path = os.path.join(self._folder, self._playlist[self._index])
        self.player.set_property("uri", f"file://{path}")
        self.player.set_state(Gst.State.PLAYING)
        self.play_btn.set_icon_name("media-playback-pause-symbolic")
        self.set_title(f"Pineapple Music — {self._playlist[self._index]}")

    def _stop(self):
        self.player.set_state(Gst.State.NULL)
        self.play_btn.set_icon_name("media-playback-start-symbolic")

    def _toggle(self, *_):
        state = self.player.get_state(0)[1]
        if state == Gst.State.PLAYING:
            self._stop()
        else:
            self._play()

    def _prev(self, *_):
        self._index = (self._index - 1) % len(self._playlist)
        self._play()

    def _next(self, *_):
        self._index = (self._index + 1) % len(self._playlist)
        self._play()

    def _seek(self, slider):
        duration = self.player.query_duration(Gst.Format.TIME)[1]
        if duration > 0:
            self.player.seek_simple(
                Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                int(slider.get_value() / 100.0 * duration),
            )

    def _volume(self, btn):
        self.player.set_property("volume", btn.get_value())

    def _update_slider(self):
        duration = self.player.query_duration(Gst.Format.TIME)[1]
        position = self.player.query_position(Gst.Format.TIME)[1]
        if duration > 0 and not self.slider.is_focus():
            self.slider.set_value(position / duration * 100.0)
        # fim da faixa: avança
        if duration > 0 and position > 0 and duration - position < 200_000_000:
            self._next()
        return True


if __name__ == "__main__":
    PineappleMusic().run(None)
