// =============================================================================
//  Indicador de Áreas de Trabalho Virtuais — Pineapple OS
//
//  Mostra pontos na barra (uma por área). O compositor/labwc pode publicar a
//  área ativa em um arquivo de estado; na ausência dele, apenas renderiza as
//  áreas configuradas.
// =============================================================================

use glib::clone;
use gtk::prelude::*;
use gtk::{Box as GtkBox, Label, Orientation};

const DEFAULT_WORKSPACES: u32 = 4;
const STATE_FILE: &str = "/run/user/";

/// Lê o número de áreas configuradas.
fn workspace_count() -> u32 {
    std::fs::read_to_string("/etc/pineappleos/workspaces.conf")
        .ok()
        .and_then(|s| s.trim().parse().ok())
        .unwrap_or(DEFAULT_WORKSPACES)
}

/// Lê a área ativa a partir do arquivo de estado do compositor.
fn active_workspace() -> Option<u32> {
    let uid = unsafe { libc::getuid() };
    let path = format!("{STATE_FILE}{uid}/pineappleos-workspace");
    std::fs::read_to_string(path)
        .ok()?
        .trim()
        .parse::<u32>()
        .ok()
}

/// Cria o indicador: um label com pontos (●/○) por área.
pub fn indicator() -> Label {
    let count = workspace_count();
    let label = Label::new(None);
    label.set_markup(&render(count, None));
    label.set_css_classes(&["pineapple-workspace-indicator"]);
    label.set_tooltip_text(Some("Áreas de trabalho: Super+1..4"));

    // atualiza periodicamente a partir do estado do compositor
    glib::timeout_add_local(
        std::time::Duration::from_millis(1000),
        clone!(@strong label => move || {
            let active = active_workspace();
            let count = workspace_count();
            label.set_markup(&render(count, active));
            glib::ControlFlow::Continue
        }),
    );

    label
}

/// Caixa central da barra: indicador + reserva.
pub fn center_widget() -> GtkBox {
    let box_ = GtkBox::new(Orientation::Horizontal, 8);
    box_.set_halign(gtk::Align::Center);
    box_.append(&indicator());
    box_
}

fn render(count: u32, active: Option<u32>) -> String {
    (1..=count.max(1))
        .map(|n| {
            let act = active == Some(n);
            let on = if act { "●" } else { "○" };
            format!("<span size='small' foreground='{}'>{on}</span>",
                if act { "#4f9dde" } else { "#5a6170" })
        })
        .collect::<Vec<_>>()
        .join(" ")
}
