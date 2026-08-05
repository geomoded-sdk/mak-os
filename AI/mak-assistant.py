#!/usr/bin/env python3
# =============================================================================
#  Mak Assistant — interface do assistente local (Ollama)
# =============================================================================
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "AI"))
from mak_ai import Agent, OllamaClient  # noqa: E402

APP_ID = "org.makos.assistant"


class MakAssistant(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = AssistantWindow(application=self)
        win.present()


class AssistantWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Mak Assistant")
        self.set_default_size(760, 560)
        self.set_css_classes(["mak-assistant-window"])

        self.agent = Agent(OllamaClient())

        # ---- histórico da conversa ----
        self.buffer = Gtk.TextBuffer()
        self.view = Gtk.TextView(buffer=self.buffer)
        self.view.set_editable(False)
        self.view.set_cursor_visible(False)
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.view.set_css_classes(["mak-chat-view"])
        self.view.set_left_margin(12)
        self.view.set_right_margin(12)
        self.view.set_top_margin(8)
        self.view.set_bottom_margin(8)

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(self.view)
        scroller.set_vexpand(True)

        # ---- input ----
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Pergunte algo ou peça: abrir apps, pesquisar arquivos, resumir...")
        self.entry.connect("activate", self._send)
        self.entry.set_css_classes(["mak-chat-input"])

        send = Gtk.Button.new_from_icon_name("send-symbolic")
        send.connect("clicked", self._send)

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_row.set_margin_top(6)
        input_row.set_margin_bottom(8)
        input_row.set_margin_start(8)
        input_row.set_margin_end(8)
        input_row.append(self.entry)
        input_row.append(send)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header = Gtk.Label(label="Mak Assistant  —  assistente local (Ollama)")
        header.set_css_classes(["mak-assistant-header"])
        header.set_margin_top(8)
        header.set_margin_bottom(4)
        root.append(header)
        root.append(scroller)
        root.append(input_row)
        self.set_child(root)

        self._append("sistema", "Olá! Sou o assistente do Mak OS. Posso abrir apps, "
                                 "pesquisar arquivos, resumir documentos e responder perguntas.")
        if not self.agent.client.available():
            self._append("sistema", "Aviso: Ollama não detectado. Para respostas com IA, execute `ollama serve`.")

        GLib.timeout_add_seconds(10, self._check_ollama)

    def _check_ollama(self):
        if self.agent.client.available():
            self.entry.set_sensitive(True)
            return False
        return True

    def _append(self, who, text):
        end = self.buffer.get_end_iter()
        tag = self.buffer.create_tag(None, **{"weight": 700})
        self.buffer.insert_with_tags(end, {"sistema": "Mak", "user": "Você", "assistente": "Mak"}[who] + ": ", tag)
        end = self.buffer.get_end_iter()
        self.buffer.insert(end, text + "\n\n")
        self.view.scroll_to_iter(self.buffer.get_end_iter(), 0.0, False, 0, 0)

    def _send(self, *_):
        text = self.entry.get_text().strip()
        if not text:
            return
        self.entry.set_text("")
        self.entry.set_sensitive(False)
        self._append("user", text)

        def worker():
            try:
                reply = self.agent.handle(text)
            except Exception as e:
                reply = f"erro: {e}"
            GLib.idle_add(self._on_reply, reply)

        threading.Thread(target=worker, daemon=True).start()

    def _on_reply(self, reply):
        self._append("assistente", reply)
        self.entry.set_sensitive(True)
        self.entry.grab_focus()


if __name__ == "__main__":
    MakAssistant().run(None)
