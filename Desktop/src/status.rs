use chrono::Local;
use gtk4::prelude::*;
use gtk4::{Box as GtkBox, Button, Image, Label, Orientation};

/// Cria o label do relógio (horas:minutos, dia da semana e data curta).
pub fn clock_label() -> Label {
    let label = Label::new(Some(&now_string()));
    label.set_css_classes(&["mak-clock"]);
    label
}

pub fn now_string() -> String {
    Local::now().format("%H:%M  •  %a %d/%m").to_string()
}

/// Constrói a área de status à direita: som, rede, energia e relógio.
pub fn build_status_area(clock: &Label) -> GtkBox {
    let box_ = GtkBox::new(Orientation::Horizontal, 4);
    box_.set_css_classes(&["mak-status-area"]);

    let sound = status_button("mak-volume-high-symbolic", "Volume");
    let net = status_button("mak-wifi-symbolic", "Rede");
    let power = status_button("mak-battery-symbolic", "Energia");
    let ctrl = status_button("mak-control-center-symbolic", "Central de Controle");

    // Clique abre a Central de Controle via D-Bus
    ctrl.connect_clicked(|_| {
        let _ = std::process::Command::new("mak-control-center").spawn();
    });

    box_.append(&sound);
    box_.append(&net);
    box_.append(&power);
    box_.append(&ctrl);
    box_.append(clock);

    box_
}

fn status_button(icon: &str, tip: &str) -> Button {
    let btn = Button::new();
    btn.set_css_classes(&["mak-status-button"]);
    let img = Image::from_icon_name(icon);
    img.set_pixel_size(16);
    btn.set_child(Some(&img));
    btn.set_tooltip_text(tip);
    btn
}
