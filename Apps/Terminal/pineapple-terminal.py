#!/usr/bin/env python3
# =============================================================================
#  Pineapple Terminal — terminal nativo do Pineapple OS (VTE + GTK4) com multi-abas
# =============================================================================
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Vte", "3.91")
from gi.repository import Gtk, Gdk, Vte, GLib  # noqa: E402

APP_ID = "org.pineappleos.terminal"


class PineappleTerminal(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = TerminalWindow(application=self)
        win.present()


class TerminalTab:
    """Uma aba do terminal: um VTE + rótulo de título."""

    def __init__(self, label):
        self.term = Vte.Terminal()
        self.term.set_font_scale(1.0)
        self.term.set_scrollback_lines(5000)
        self.label = label
        self.term.connect("window-title-changed", self._on_title)
        self.term.connect("child-exited", self._on_child_exited)
        self.spawn()

    def _on_title(self, _term):
        title = self.term.get_window_title()
        if title:
            self.label.set_text(title[:24])

    def _on_child_exited(self, _term, _status):
        self.label.set_text("encerrado")

    def spawn(self):
        self.term.spawn_async(
            Vte.PtyFlags.DEFAULT,
            GLib.get_home_dir(),
            ["/bin/bash", "-l"],
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            None,
            -1,
            None,
            None,
        )


class TerminalWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Pineapple Terminal")
        self.set_default_size(900, 600)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_show_border(False)
        self.notebook.connect("switch-page", self._on_switch)
        self.set_child(self.notebook)

        plus = Gtk.Button.new_from_icon_name("list-add-symbolic")
        plus.set_has_frame(False)
        plus.set_tooltip_text("Nova aba (Ctrl+Shift+T)")
        plus.connect("clicked", lambda *_: self.new_tab())
        self.notebook.set_action_widget(plus, Gtk.PackType.END)

        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key)
        self.add_controller(ctrl)

        self.connect("close-request", self._on_close)

        self.new_tab()

    # ---------------- abas ----------------
    def new_tab(self):
        label = Gtk.Label(label="Terminal")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic")
        close_btn.set_has_frame(False)
        close_btn.set_size_request(20, 20)
        box.append(label)
        box.append(close_btn)

        tab = TerminalTab(label)
        close_btn.connect("clicked", self._close_tab_at, tab.term)
        box.show()

        self.notebook.append_page(tab.term, box)
        self.notebook.set_current_page(-1)
        tab.term.grab_focus()
        return tab

    def _close_tab_at(self, _btn, term):
        page_num = self.notebook.page_num(term)
        if page_num == -1:
            return
        term.kill_shell()
        self.notebook.remove_page(page_num)
        self._after_close()

    def close_current_tab(self):
        page_num = self.notebook.get_current_page()
        if page_num == -1:
            return
        child = self.notebook.get_nth_page(page_num)
        if isinstance(child, Vte.Terminal):
            child.kill_shell()
        self.notebook.remove_page(page_num)
        self._after_close()

    def _after_close(self):
        if self.notebook.get_n_pages() == 0:
            self.close()

    def _on_switch(self, _nb, page, _idx):
        if isinstance(page, Vte.Terminal):
            page.grab_focus()

    # ---------------- atalhos ----------------
    def _on_key(self, _ctrl, keyval, _keycode, state):
        mods = state & Gtk.accelerator_get_default_mod_mask()
        ctrl = bool(mods & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(mods & Gdk.ModifierType.SHIFT_MASK)

        if ctrl and shift:
            if keyval == Gdk.KEY_T:
                self.new_tab()
                return True
            if keyval == Gdk.KEY_W:
                self.close_current_tab()
                return True
        if ctrl and not shift:
            if keyval == Gdk.KEY_plus:
                self._zoom(1.15)
                return True
            if keyval == Gdk.KEY_minus:
                self._zoom(0.87)
                return True
            if keyval in (Gdk.KEY_1, Gdk.KEY_2, Gdk.KEY_3, Gdk.KEY_4, Gdk.KEY_5,
                          Gdk.KEY_6, Gdk.KEY_7, Gdk.KEY_8, Gdk.KEY_9):
                idx = keyval - Gdk.KEY_1
                if idx < self.notebook.get_n_pages():
                    self.notebook.set_current_page(idx)
                    return True
        return False

    def _zoom(self, factor):
        child = self.notebook.get_nth_page(self.notebook.get_current_page())
        if isinstance(child, Vte.Terminal):
            child.set_font_scale(child.get_font_scale() * factor)

    def _on_close(self, *_):
        for page in range(self.notebook.get_n_pages()):
            child = self.notebook.get_nth_page(page)
            if isinstance(child, Vte.Terminal):
                child.kill_shell()


if __name__ == "__main__":
    PineappleTerminal().run(None)
