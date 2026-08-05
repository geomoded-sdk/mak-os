#!/usr/bin/env python3
# =============================================================================
#  Mak Monitor — monitor de recursos (CPU, RAM, disco, rede) + processos
# =============================================================================
import os
import signal
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, GLib, cairo  # noqa: E402

APP_ID = "org.makos.monitor"


class MakMonitor(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MonitorWindow(application=self)
        win.present()


def read_stat():
    with open("/proc/stat") as f:
        line = f.readline().split()
    idle = int(line[4]) + int(line[5])
    total = sum(int(v) for v in line[1:8])
    return total, idle


def read_mem():
    fields = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v, *_ = line.split()
            fields[k] = int(v)
    total = fields.get("MemTotal", 0) / 1024.0
    avail = fields.get("MemAvailable", total) / 1024.0
    return total, avail


class MonitorWindow(Gtk.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("Mak Monitor")
        self.set_default_size(860, 640)

        self.prev_total, self.prev_idle = read_stat()
        self._prev_proc = {}
        self._prev_time = time.monotonic()
        self._procs = []
        self._cpu_hist = []
        self._ram_hist = []

        self.cpu_bar = Gtk.ProgressBar(show_text=False)
        self.mem_bar = Gtk.ProgressBar()
        self.mem_bar.set_show_text(True)
        self.uptime_label = Gtk.Label(label="", xalign=0.0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(24)
        vbox.set_margin_bottom(24)
        vbox.set_margin_start(24)
        vbox.set_margin_end(24)

        title = Gtk.Label(label="Monitor de recursos", xalign=0.0)
        title.add_css_class("mak-settings-title")
        vbox.append(title)

        vbox.append(self._row("CPU", self.cpu_bar, "mak-cpu"))
        vbox.append(self._row("Memória", self.mem_bar, "mak-mem"))
        vbox.append(self.uptime_label)

        # gráfico de CPU + RAM
        self.chart = Gtk.DrawingArea()
        self.chart.set_vexpand(True)
        self.chart.set_hexpand(True)
        self.chart.set_draw_func(self._draw_chart)
        self.chart.add_css_class("mak-chart")
        vbox.append(self.chart)

        # ---- lista de processos ----
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.append(sep)

        proc_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        proc_title = Gtk.Label(label="Processos", xalign=0.0)
        proc_title.add_css_class("mak-settings-subtitle")
        kill_btn = Gtk.Button(label="Terminar selecionado")
        kill_btn.connect("clicked", self._kill_selected)
        self.proc_status = Gtk.Label(label="", xalign=1.0)
        proc_head.append(proc_title)
        proc_head.append(self.proc_status)
        proc_head.append(kill_btn)
        vbox.append(proc_head)

        self.proc_list = Gtk.ListBox()
        self.proc_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        proc_scroll = Gtk.ScrolledWindow()
        proc_scroll.set_child(self.proc_list)
        proc_scroll.set_size_request(-1, 180)
        proc_scroll.set_vexpand(True)
        vbox.append(proc_scroll)

        self.set_child(vbox)
        GLib.timeout_add_seconds(1, self._tick)
        GLib.timeout_add_seconds(2, self._refresh_procs)
        self._tick()
        self._refresh_procs()

    def _row(self, title, widget, css):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl = Gtk.Label(label=title, xalign=0.0)
        box.append(lbl)
        widget.set_size_request(-1, 16)
        widget.add_css_class(css)
        box.append(widget)
        return box

    # ---------------- medições ----------------
    def _tick(self):
        total, idle = read_stat()
        dt = total - self.prev_total
        di = idle - self.prev_idle
        if dt > 0:
            usage = max(min((dt - di) / dt, 1.0), 0.0)
        else:
            usage = 0.0
        self.cpu_bar.set_fraction(usage)
        self.prev_total, self.prev_idle = total, idle

        mem_total, mem_avail = read_mem()
        frac = max(min((mem_total - mem_avail) / mem_total, 1.0), 0.0)
        self.mem_bar.set_fraction(frac)
        self.mem_bar.set_text(f"{mem_total - mem_avail:.0f} MB / {mem_total:.0f} MB")

        with open("/proc/uptime") as f:
            secs = float(f.readline().split()[0])
        h, m = int(secs // 3600), int((secs % 3600) // 60)
        self.uptime_label.set_label(f"Ativo há {h}h {m}m")

        self._cpu_hist.append(usage)
        self._ram_hist.append(frac)
        if len(self._cpu_hist) > 80:
            self._cpu_hist.pop(0)
            self._ram_hist.pop(0)
        self.chart.queue_draw()
        return True

    def _refresh_procs(self):
        hz = os.sysconf("SC_CLK_TCK")
        nproc = os.cpu_count() or 1
        now = time.monotonic()
        dt_sec = max(now - self._prev_time, 0.1)
        cur = {}
        procs = []
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            p = int(pid)
            try:
                with open(f"/proc/{p}/stat", "rb") as f:
                    data = f.read()
                rpar = data.rfind(b")")
                fields = data[rpar + 2:].split()
                utime = int(fields[11])
                stime = int(fields[12])
            except (OSError, ValueError, IndexError):
                continue
            cur[p] = utime + stime
            cpu = 0.0
            if p in self._prev_proc:
                cpu = max((utime + stime - self._prev_proc[p]) / hz / dt_sec * 100.0, 0.0)
            rss = 0
            name = "?"
            try:
                with open(f"/proc/{p}/status") as f:
                    for line in f:
                        if line.startswith("Name:"):
                            name = line.split(":", 1)[1].strip()
                        elif line.startswith("VmRSS:"):
                            rss = int(line.split()[1])  # kB
            except OSError:
                pass
            procs.append({"pid": p, "cpu": cpu, "rss": rss, "name": name})

        self._prev_proc = cur
        self._prev_time = now
        self._procs = sorted(procs, key=lambda x: x["cpu"], reverse=True)[:30]

        # rebuild da lista
        while (child := self.proc_list.get_first_child()) is not None:
            self.proc_list.remove(child)
        for pr in self._procs:
            self.proc_list.append(self._proc_row(pr))
        self.proc_status.set_label(f"{len(self._procs)} processos")
        return True

    def _proc_row(self, pr):
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)

        pid_lbl = Gtk.Label(label=str(pr["pid"]), xalign=0.0)
        pid_lbl.add_css_class("mak-mono")
        cpu_lbl = Gtk.Label(label=f'{pr["cpu"]:5.1f}%', xalign=0.0)
        cpu_lbl.add_css_class("mak-mono")
        cpu_lbl.set_css_classes(["mak-mono", "mak-proc-cpu"])
        mem_lbl = Gtk.Label(label=f'{pr["rss"] / 1024.0:6.1f} MB', xalign=0.0)
        mem_lbl.add_css_class("mak-mono")
        name_lbl = Gtk.Label(label=pr["name"], xalign=0.0, ellipsize=True)
        name_lbl.set_hexpand(True)

        hbox.append(pid_lbl)
        hbox.append(cpu_lbl)
        hbox.append(mem_lbl)
        hbox.append(name_lbl)
        row.set_child(hbox)
        row.set_data("pid", pr["pid"])
        return row

    def _kill_selected(self, *_):
        row = self.proc_list.get_selected_row()
        if row is None:
            return
        pid = row.get_data("pid")
        if pid is None:
            return
        try:
            os.kill(pid, signal.SIGTERM)
            self.proc_status.set_label(f"Enviado SIGTERM para {pid}")
        except (OSError, PermissionError) as exc:
            self.proc_status.set_label(f"Falha: {exc}")

    # ---------------- gráfico ----------------
    def _draw_chart(self, _area, cr: cairo.Context, _w, _h):
        w = float(self.chart.get_width())
        h = float(self.chart.get_height())
        if w < 2 or h < 2:
            return
        self._draw_series(cr, self._cpu_hist, w, h, (0.31, 0.62, 0.87, 0.85))
        self._draw_series(cr, self._ram_hist, w, h, (0.89, 0.47, 0.44, 0.75))

    def _draw_series(self, cr: cairo.Context, hist, w, h, color):
        n = len(hist)
        if n < 2:
            return
        step = w / (n - 1)
        cr.save()
        cr.set_source_rgba(*color)
        cr.move_to(0, h)
        for i, v in enumerate(hist):
            cr.line_to(i * step, h * (1.0 - v))
        cr.line_to((n - 1) * step, h)
        cr.close_path()
        cr.fill()
        cr.set_line_width(1.5)
        cr.move_to(0, h * (1.0 - hist[0]))
        for i, v in enumerate(hist):
            cr.line_to(i * step, h * (1.0 - v))
        cr.stroke()
        cr.restore()


if __name__ == "__main__":
    MakMonitor().run(None)
