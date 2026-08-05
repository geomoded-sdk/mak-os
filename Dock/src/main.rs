use gtk::prelude::*;
use gtk::{Button, Image, Orientation};
use gtk4_layer_shell::{Edge, Layer, LayerShell};

fn place_dock(window: &gtk::ApplicationWindow) {
    window.init_layer_shell();
    window.set_layer(Layer::Bottom);
    window.set_anchor(Edge::Bottom, true);
    window.set_anchor(Edge::Left, true);
    window.set_anchor(Edge::Right, true);
    window.set_margin(Edge::Bottom, 8);
    window.set_exclusive_zone(64);
    window.set_default_size(1, 64);
    window.set_css_classes(&["mak-dock-window"]);
}

fn default_icons() -> Vec<(&'static str, &'static str, &'static str)> {
    vec![
        ("mak-finder", "Mak Finder", "mak-finder"),
        ("mak-terminal", "Mak Terminal", "mak-terminal"),
        ("mak-browser", "Mak Browser", "mak-browser"),
        ("mak-music", "Mak Music", "mak-music"),
        ("mak-photos", "Mak Photos", "mak-photos"),
        ("mak-notes", "Mak Notes", "mak-notes"),
        ("mak-store", "Mak Store", "mak-store"),
        ("mak-settings", "Mak Settings", "mak-settings"),
        ("mak-calc", "Mak Calculator", "mak-calc"),
    ]
}

fn make_icon_button(icon: &str, label: &str, exec: &str) -> Button {
    let image = Image::from_icon_name(icon);
    image.set_pixel_size(48);

    let button = Button::new();
    button.set_child(Some(&image));
    button.set_tooltip_text(Some(label));
    button.set_css_classes(&["mak-dock-icon"]);

    let exec = exec.to_string();
    button.connect_clicked(move |_| {
        let _ = std::process::Command::new("sh").arg("-c").arg(&exec).spawn();
    });

    button
}

fn populate_dock(box_: &gtk::Box) {
    for (name, label, exec) in default_icons() {
        box_.append(&make_icon_button(name, label, exec));
    }

    // Magnificação suave: ícones próximos ao centro ficam maiores.
    let children_box = box_.clone();
    glib::timeout_add_local(std::time::Duration::from_millis(16), move || {
        let children = children_box.children();
        let total = children.len().max(1) as f64;
        for (i, child) in children.iter().enumerate() {
            let dist = (i as f64 - (total - 1.0) / 2.0).abs();
            let scale = 1.0 + (1.0 - (dist / total).min(1.0)) * 0.35;
            let size = (48.0 * scale) as i32;
            if let Ok(btn) = child.clone().downcast::<Button>() {
                if let Some(image) = btn.child().and_then(|c| c.and_downcast::<Image>().ok()) {
                    image.set_pixel_size(size);
                }
            }
        }
        glib::ControlFlow::Continue
    });
}

fn main() -> glib::ExitCode {
    let app = gtk::Application::builder()
        .application_id("org.makos.dock")
        .build();

    app.connect_activate(|app| {
        let window = gtk::ApplicationWindow::new(app);
        window.set_decorated(false);

        let container = gtk::Box::new(Orientation::Horizontal, 6);
        container.set_css_classes(&["mak-dock"]);
        container.set_halign(gtk::Align::Center);
        populate_dock(&container);

        window.set_child(Some(&container));
        place_dock(&window);
        window.present();
    });

    app.run()
}
