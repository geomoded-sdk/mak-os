#!/usr/bin/env python3
# =============================================================================
#  Mak Calculator — app GTK4 (a lógica vive em mak_calculator.py)
# =============================================================================
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from mak_calculator import evaluate  # noqa: E402

APP_ID = "org.makos.calculator"


class MakCalculator(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self._expr = ""

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = CalculatorWindow(application=self)
        win.present()


class CalculatorWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Mak Calculator")
        self.set_default_size(320, 460)
        self.add_css_class("mak-calc-window")

        self.display = Gtk.Entry()
        self.display.set_hexpand(True)
        self.display.set_alignment(1.0)
        self.display.set_css_classes(["mak-calc-display"])
        self.display.set_editable(False)
        self.display.set_text("0")
        self.display.set_size_request(-1, 90)

        grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)

        buttons = [
            ["C", "±", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "−"],
            ["1", "2", "3", "+"],
            ["0", ".", "⌫", "="],
        ]
        for r, row in enumerate(buttons):
            for c, label in enumerate(row):
                btn = Gtk.Button(label=label)
                btn.set_css_classes(self._css_for(label))
                btn.connect("clicked", self.on_key, label)
                grid.attach(btn, c, r, 1, 1)
        # "0" ocupa duas colunas
        zero = grid.get_child_at(0, 4)
        if zero is not None:
            grid.remove(zero)
        big = Gtk.Button(label="0")
        big.set_css_classes(self._css_for("0"))
        big.connect("clicked", self.on_key, "0")
        grid.attach(big, 0, 4, 2, 1)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.append(self.display)
        vbox.append(grid)
        self.set_child(vbox)

    @staticmethod
    def _css_for(label):
        if label in ("=",):
            return ["mak-calc-accent"]
        if label in ("C", "⌫", "±", "%"):
            return ["mak-calc-fn"]
        if label in ("÷", "×", "−", "+"):
            return ["mak-calc-op"]
        return ["mak-calc-num"]

    def on_key(self, _btn, key):
        if key == "C":
            self._expr = ""
            self.display.set_text("0")
            return
        if key == "⌫":
            self._expr = self._expr[:-1]
            self.display.set_text(self._expr or "0")
            return
        if key == "=":
            self._evaluate()
            return
        if key == "±":
            if self._expr.startswith("-"):
                self._expr = self._expr[1:]
            else:
                self._expr = "-" + self._expr
            self.display.set_text(self._expr or "0")
            return
        if key == "%":
            self._expr += "/100"
            self._evaluate()
            return
        # normaliza caracteres de operação
        repl = {"×": "*", "−": "-", "÷": "/"}
        key = repl.get(key, key)
        self._expr += key
        self.display.set_text(self._expr)

    def _evaluate(self):
        expr = self._expr
        if not expr:
            return
        text = evaluate(expr)
        self.display.set_text(text)
        self._expr = "" if text == "Erro" else text


if __name__ == "__main__":
    MakCalculator().run(None)
