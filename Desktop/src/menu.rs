use gtk::prelude::*;
use gtk::Button;

/// Anexa um menu popover ao botão de logo.
pub fn attach(logo: &Button) {
    let popover = gtk::Popover::new();
    let menu = menu_box();
    popover.set_child(Some(&menu));
    popover.set_position(gtk::PositionType::Bottom);
    popover.set_parent(logo);

    logo.connect_clicked(move |_| {
        if popover.is_visible() {
            popover.popdown();
        } else {
            popover.popup();
        }
    });
}

fn menu_box() -> gtk::Box {
    let box_ = gtk::Box::new(gtk::Orientation::Vertical, 0);
    box_.set_css_classes(&["pineapple-menu"]);

    for (label, cmd) in [
        ("Sobre o Pineapple OS", "pineapple-about"),
        ("Preferências do Sistema", "pineapple-settings"),
        ("Terminal", "pineapple-terminal"),
        ("Bloquear", "pineapple-lock"),
        ("Sair...", "pineapple-logout"),
    ] {
        let btn = gtk::Button::with_label(label);
        btn.set_css_classes(&["pineapple-menu-item"]);
        btn.set_hexpand(true);
        let cmd = cmd.to_string();
        btn.connect_clicked(move |_| {
            let _ = std::process::Command::new(&cmd).spawn();
        });
        box_.append(&btn);
    }

    box_
}
