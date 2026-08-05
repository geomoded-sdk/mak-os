#!/usr/bin/env python3
# =============================================================================
#  Mak Notes — notas com armazenamento local (JSON) e pesquisa
# =============================================================================
import json
import os
import uuid
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from mak_notes_io import note_from_markdown, note_to_markdown  # noqa: E402

APP_ID = "org.makos.notes"
DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "makos", "notes")
HAS_FILE_DIALOG = hasattr(Gtk, "FileDialog")  # GTK >= 4.10


class MakNotes(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        os.makedirs(DATA_DIR, exist_ok=True)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = NotesWindow(application=self)
        win.present()


class NotesWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Mak Notes")
        self.set_default_size(900, 600)

        self._current_id = None
        self._search_text = ""

        # ---- sidebar: lista de notas ----
        self.list = Gtk.ListBox()
        self.list.set_css_classes(["mak-notes-list"])
        self.list.connect("row-selected", self._on_select)

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(self.list)
        scroller.set_width_request(240)

        # ---- editor ----
        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Título")
        self.title_entry.set_css_classes(["mak-notes-title"])
        self.title_entry.connect("changed", lambda *_: self._save())

        self.buffer = Gtk.TextBuffer()
        self.buffer.connect("changed", lambda *_: self._save())
        self.text_view = Gtk.TextView(buffer=self.buffer)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_css_classes(["mak-notes-editor"])

        editor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        editor.set_margin_top(8)
        editor.set_margin_bottom(8)
        editor.set_margin_start(8)
        editor.set_margin_end(8)
        editor.append(self.title_entry)
        editor.append(self.text_view)
        self.text_view.set_vexpand(True)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        new_btn = Gtk.Button(label="Nova")
        new_btn.connect("clicked", self._new_note)
        del_btn = Gtk.Button(label="Excluir")
        del_btn.connect("clicked", self._delete_note)
        export_btn = Gtk.Button(label="Exportar")
        export_btn.connect("clicked", self._export_note)
        import_btn = Gtk.Button(label="Importar")
        import_btn.connect("clicked", self._import_note)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Pesquisar notas...")
        self.search.connect("search-changed", self._on_search)
        toolbar.append(new_btn)
        toolbar.append(del_btn)
        toolbar.append(export_btn)
        toolbar.append(import_btn)
        toolbar.append(self.search)

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main.append(scroller)
        main.append(editor)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(toolbar)
        root.append(main)
        self.set_child(root)

        self._refresh_list()
        self._new_note()

    # ---- persistência ----
    def _path(self, note_id):
        return os.path.join(DATA_DIR, f"{note_id}.json")

    def _save(self):
        if not self._current_id:
            return
        data = {
            "id": self._current_id,
            "title": self.title_entry.get_text(),
            "body": self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), True),
            "updated": datetime.now().isoformat(),
        }
        with open(self._path(self._current_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    # ---- ações ----
    def _fallback_message(self, msg):
        print(f"[mak-notes] {msg}", flush=True)

    def _current_body(self):
        return self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), True)

    def _export_note(self, *_):
        if not self._current_id:
            return
        if not HAS_FILE_DIALOG:
            self._fallback_message("Exportar nota exige GTK 4.10+")
            return
        title = self.title_entry.get_text() or "(sem título)"
        body = self._current_body()

        fd = Gtk.FileDialog()
        fd.set_title("Exportar nota")
        fd.set_initial_name(f"{title.replace('/', '-')}.md")
        fd.save(self, None, lambda d, r: self._on_export_saved(d, r, title, body))

    def _on_export_saved(self, dialog, result, title, body):
        try:
            file = dialog.save_finish(result)
        except GLib.Error:
            return
        path = file.get_path()
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(note_to_markdown(title, body))

    def _import_note(self, *_):
        if not HAS_FILE_DIALOG:
            self._fallback_message("Importar nota exige GTK 4.10+")
            return
        fd = Gtk.FileDialog()
        fd.set_title("Importar nota")
        fd.open(self, None, self._on_import_opened)

    def _on_import_opened(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        path = file.get_path()
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return
        title, body = note_from_markdown(content)
        self._new_note()
        self.title_entry.set_text(title)
        self.buffer.set_text(body)
        self._save()

    def _new_note(self, *_):
        note_id = str(uuid.uuid4())
        self._current_id = note_id
        self.title_entry.set_text("")
        self.buffer.set_text("")
        with open(self._path(note_id), "w", encoding="utf-8") as f:
            json.dump({"id": note_id, "title": "", "body": "", "updated": datetime.now().isoformat()}, f)
        self._refresh_list()
        self.title_entry.grab_focus()

    def _delete_note(self, *_):
        if not self._current_id:
            return
        try:
            os.remove(self._path(self._current_id))
        except FileNotFoundError:
            pass
        self._current_id = None
        self._refresh_list()
        self._new_note()

    def _on_select(self, _list, row):
        if row is None:
            return
        note = row.get_data("note")
        if note is None:
            return
        if self._current_id and self._current_id != note["id"]:
            self._save()
        self._current_id = note["id"]
        self.title_entry.set_text(note.get("title", ""))
        self.buffer.set_text(note.get("body", ""))

    def _on_search(self, entry):
        self._search_text = entry.get_text().lower()
        self._refresh_list()

    def _refresh_list(self):
        while (row := self.list.get_first_child()) is not None:
            self.list.remove(row)

        files = sorted(
            (f for f in os.listdir(DATA_DIR) if f.endswith(".json")),
            key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)),
            reverse=True,
        )
        for fname in files:
            try:
                with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
                    note = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            title = note.get("title") or "(sem título)"
            if self._search_text and self._search_text not in title.lower():
                continue
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=title, xalign=0.0)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            row.set_child(label)
            row.set_data("note", note)
            self.list.append(row)


if __name__ == "__main__":
    MakNotes().run(None)
