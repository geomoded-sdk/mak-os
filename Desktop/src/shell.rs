use std::rc::Rc;

use crate::{menu, status};
use glib::clone;
use gtk::prelude::*;
use gtk::{gdk, Box as GtkBox, CenterBox, Label, Orientation, Widget};
use gtk4_layer_shell::{Edge, Layer, LayerShell};

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

        // ---- lado esquerdo: logo + menus (estilo macOS) ----
        let left = GtkBox::new(Orientation::Horizontal, 0);
        let logo = gtk::Button::new();
        logo.set_css_classes(&["mak-logo-button"]);
        let logo_image = gtk::Image::from_icon_name("mak-logo");
        logo_image.set_pixel_size(16);
        logo.set_child(Some(&logo_image));
        logo.set_tooltip_text(Some("MaK"));
        menu::attach(&logo);

        let title = Label::new(Some("MaK"));
        title.set_css_classes(&["mak-brand"]);

        left.append(&logo);
        left.append(&title);

        for name in ["Arquivo", "Editar", "Exibir", "Ir", "Janela", "Ajuda"] {
            let item = gtk::Button::with_label(name);
            item.set_css_classes(&["mak-menubar-item"]);
            left.append(&item);
        }

        // ---- lado direito: status (som, rede, bateria, relógio) ----
        let clock_label = status::clock_label();
        let right = status::build_status_area(&clock_label);

        container.set_start_widget(Some(&left));
        container.set_end_widget(Some(&right));

        Rc::new(Self {
            container,
            clock_label,
        })
    }

    /// Aplica a camada de janela no topo da tela (Layer Shell).
    pub fn place_as_top(&self, window: &gtk::ApplicationWindow) {
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
pub fn shell_window(app: &gtk::Application) -> gtk::ApplicationWindow {
    let window = gtk::ApplicationWindow::new(app);
    window.set_decorated(false);
    window
}

#[allow(dead_code)]
fn _keep_gdk_dep(_w: Option<&Widget>) -> Option<gdk::Display> {
    gdk::Display::default()
}
