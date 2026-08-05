use std::rc::Rc;

use glib::clone;
use gtk4::prelude::*;
use gtk4::{gdk, Box as GtkBox, Button, CenterBox, Label, Orientation, Widget};
use gtk4_layer_shell::{Edge, Layer, LayerShell};

mod status;
mod menu;
mod workspace;

/// Cria a barra superior do Mak OS.
pub struct ShellBar {
    pub container: CenterBox,
    pub clock_label: Label,
}

impl ShellBar {
    pub fn new() -> Rc<Self> {
        let container = CenterBox::new();
        container.set_hexpand(true);
        container.set_orientation(Orientation::Horizontal);
        container.set_css_classes(&["mak-bar"]);

        // ---- lado esquerdo: logo + menu ----
        let left = GtkBox::new(Orientation::Horizontal, 0);
        let logo = Button::new();
        logo.set_css_classes(&["mak-logo-button"]);
        logo.set_icon_name("mak-logo");
        logo.set_tooltip_text("Mak OS");
        menu::attach(logo);

        let title = Label::new(Some("MaK"));
        title.set_css_classes(&["mak-brand"]);

        left.append(&logo);
        left.append(&title);

        // ---- centro: indicador de áreas de trabalho ----
        let center = workspace::center_widget();

        // ---- lado direito: status (som, rede, bateria, relógio) ----
        let clock_label = status::clock_label();
        let right = status::build_status_area(&clock_label);

        container.set_start_widget(Some(&left));
        container.set_center_widget(Some(&center));
        container.set_end_widget(Some(&right));

        Rc::new(Self {
            container,
            clock_label,
        })
    }

    /// Aplica a camada de janela no topo da tela (Layer Shell).
    pub fn place_as_top(&self, window: &gtk4::ApplicationWindow) {
        window.init_layer_shell();
        window.set_layer(Layer::Top);
        window.set_anchor(Edge::Top, true);
        window.set_anchor(Edge::Left, true);
        window.set_anchor(Edge::Right, true);
        window.set_margin(Edge::Top, 0);
        window.set_exclusive_zone(40);
        window.set_default_size(1, 40);
        window.set_css_classes(&["mak-shell-window"]);
    }
}

/// Mantém o relógio atualizado (a cada segundo).
pub fn start_clock_loop(clock_label: Label) {
    glib::timeout_add_seconds_local(1, clone!(@strong clock_label => move || {
        clock_label.set_label(&status::now_string());
        glib::ControlFlow::Continue
    }));
}

/// Cria uma janela GTK sem decoração para o shell.
pub fn shell_window(app: &gtk4::Application) -> gtk4::ApplicationWindow {
    let window = gtk4::ApplicationWindow::new(app);
    window.set_decorated(false);
    window
}

#[allow(dead_code)]
fn _keep_gdk_dep(_w: Option<&Widget>) -> Option<gdk::Display> {
    gdk::Display::default()
}
