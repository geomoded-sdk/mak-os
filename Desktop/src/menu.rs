use gtk4::prelude::*;
use gtk4::Button;

/// Anexa um menu popover ao botão de logo.
pub fn attach(logo: &Button) {
    let popover = gtk4::Popover::new();
    let menu = menu_box();
    popover.set_child(Some(&menu));
    popover.set_position(gtk4::PositionType::Bottom);
    logo.set_popover(Some(&popover));
}

fn menu_box() -> gtk4::Box {
    let box_ = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
    box_.set_css_classes(&["mak-menu"]);

    for (label, cmd) in [
        ("Sobre o Mak OS", "mak-about"),
        ("Preferências do Sistema", "mak-settings"),
        ("Terminal", "mak-terminal"),
        ("Bloquear", "mak-lock"),
        ("Sair...", "mak-logout"),
    ] {
        let btn = gtk4::Button::new_with_label(label);
        btn.set_css_classes(&["mak-menu-item"]);
        btn.set_hexpand(true);
        let cmd = cmd.to_string();
        btn.connect_clicked(move |_| {
            let _ = std::process::Command::new(&cmd).spawn();
        });
        box_.append(&btn);
    }

    box_
}
