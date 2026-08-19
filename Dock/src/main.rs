// =============================================================================
//  pineapple-dock — dock inferior do Pineapple OS
//
//  Ícones de atalhos + bandeja de janelas minimizadas (estilo macOS):
//   - via wlr-foreign-toplevel-management-v1 rastreia as janelas abertas;
//   - janelas minimizadas (Cmd+M / Iconify) aparecem na bandeja após o
//     separador, animando o "colapso" para o Dock;
//   - clicar em uma miniatura restaura a janela (activate + foco);
//   - magnificação suave dos ícones próximos ao centro.
//
//  Degradação graciosa: sem conexão Wayland o dock continua com os atalhos,
//  apenas sem a bandeja de minimizadas.
// =============================================================================

use std::sync::{Arc, Mutex};
use std::time::Duration;

use gtk::prelude::*;
use gtk::{Button, Image, Label, Orientation};
use gtk4_layer_shell::{Edge, Layer, LayerShell};

use wayland_client::event_created_child;
use wayland_client::globals::{registry_queue_init, GlobalListContents};
use wayland_client::protocol::wl_registry;
use wayland_client::protocol::wl_seat;
use wayland_client::{delegate_noop, Connection, Dispatch, QueueHandle};

use wayland_protocols_wlr::foreign_toplevel::v1::client::zwlr_foreign_toplevel_handle_v1::{
    self, Event as ToplevelEvent, State as ToplevelState, ZwlrForeignToplevelHandleV1,
};
use wayland_protocols_wlr::foreign_toplevel::v1::client::zwlr_foreign_toplevel_manager_v1::{
    self, Event as ToplevelManagerEvent, ZwlrForeignToplevelManagerV1,
};

// ------------------------------------------------------------------ estado

/// Uma janela aberta (descoberta via wlr-foreign-toplevel).
struct WindowEntry {
    app_id: String,
    title: String,
    minimized: bool,
    handle: ZwlrForeignToplevelHandleV1,
}

/// Estado compartilhado entre a thread Wayland e a thread da UI (GTK).
#[derive(Default)]
struct Shared {
    windows: Vec<WindowEntry>,
    seat: Option<wl_seat::WlSeat>,
    toplevel_manager: Option<ZwlrForeignToplevelManagerV1>,
    /// Incrementado a cada mudança; a UI só reconstrói quando muda.
    version: u64,
}

/// Estado da thread de despacho do Wayland.
struct WaylandState {
    shared: Arc<Mutex<Shared>>,
}

// ------------------------------------------------------------------ Wayland

impl Dispatch<wl_registry::WlRegistry, GlobalListContents> for WaylandState {
    fn event(
        _state: &mut Self,
        _proxy: &wl_registry::WlRegistry,
        _event: wl_registry::Event,
        _data: &GlobalListContents,
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
    }
}

impl Dispatch<ZwlrForeignToplevelManagerV1, ()> for WaylandState {
    fn event(
        state: &mut Self,
        _proxy: &ZwlrForeignToplevelManagerV1,
        event: ToplevelManagerEvent,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        if let ToplevelManagerEvent::Toplevel { toplevel } = event {
            let mut shared = state.shared.lock().unwrap();
            shared.windows.push(WindowEntry {
                app_id: String::new(),
                title: String::new(),
                minimized: false,
                handle: toplevel,
            });
            shared.version += 1;
        }
    }

    event_created_child!(WaylandState, ZwlrForeignToplevelManagerV1, [
        zwlr_foreign_toplevel_manager_v1::EVT_TOPLEVEL_OPCODE => (ZwlrForeignToplevelHandleV1, ())
    ]);
}

impl Dispatch<ZwlrForeignToplevelHandleV1, ()> for WaylandState {
    fn event(
        state: &mut Self,
        proxy: &ZwlrForeignToplevelHandleV1,
        event: ToplevelEvent,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        match event {
            ToplevelEvent::Closed => {
                let mut shared = state.shared.lock().unwrap();
                if let Some(pos) = shared.windows.iter().position(|w| w.handle == *proxy) {
                    let entry = shared.windows.remove(pos);
                    let _ = entry.handle.destroy();
                    shared.version += 1;
                }
            }
            other => {
                let mut shared = state.shared.lock().unwrap();
                let Some(entry) = shared.windows.iter_mut().find(|w| w.handle == *proxy) else {
                    return;
                };
                match other {
                    ToplevelEvent::AppId { app_id } => entry.app_id = app_id,
                    ToplevelEvent::Title { title } => entry.title = title,
                    ToplevelEvent::State { state } => {
                        // O evento State traz a lista completa de estados.
                        entry.minimized = false;
                        for word in state.chunks_exact(4) {
                            let v = u32::from_le_bytes([word[0], word[1], word[2], word[3]]);
                            if v == ToplevelState::Minimized as u32 {
                                entry.minimized = true;
                            }
                        }
                    }
                    _ => {}
                }
                shared.version += 1;
            }
        }
    }

    event_created_child!(WaylandState, ZwlrForeignToplevelHandleV1, [
        zwlr_foreign_toplevel_handle_v1::EVT_PARENT_OPCODE => (ZwlrForeignToplevelHandleV1, ())
    ]);
}

delegate_noop!(WaylandState: ignore wl_seat::WlSeat);

/// Conecta-se ao compositor, liga os protocolos e sobe a thread de eventos.
fn setup_wayland() -> Option<Arc<Mutex<Shared>>> {
    let conn = Connection::connect_to_env().ok()?;
    let (globals, mut queue) = registry_queue_init::<WaylandState>(&conn).ok()?;
    let qh = queue.handle();

    let toplevel_manager = globals
        .bind::<ZwlrForeignToplevelManagerV1, _, _>(&qh, 1..=3, ())
        .ok();
    let seat = globals.bind::<wl_seat::WlSeat, _, _>(&qh, 1..=8, ()).ok();

    let shared = Arc::new(Mutex::new(Shared {
        seat,
        toplevel_manager,
        ..Shared::default()
    }));

    // Roundtrip inicial: recebe as janelas já existentes.
    let mut init = WaylandState {
        shared: shared.clone(),
    };
    let _ = queue.roundtrip(&mut init);

    let for_thread = shared.clone();
    std::thread::spawn(move || {
        let mut state = WaylandState { shared: for_thread };
        loop {
            if queue.blocking_dispatch(&mut state).is_err() {
                break;
            }
        }
    });

    Some(shared)
}

// ------------------------------------------------------------------ helpers

/// Deriva um nome de ícone a partir do app_id.
fn icon_for(app_id: &str) -> String {
    let id = app_id.to_lowercase();
    if id.is_empty() {
        return "application-x-executable".to_string();
    }
    if let Some(rest) = id.strip_prefix("org.pineappleos.") {
        return format!("pineapple-{}", rest.replace('.', "-"));
    }
    id
}

fn place_dock(window: &gtk::ApplicationWindow) {
    window.init_layer_shell();
    window.set_layer(Layer::Bottom);
    window.set_anchor(Edge::Bottom, true);
    window.set_anchor(Edge::Left, true);
    window.set_anchor(Edge::Right, true);
    window.set_margin(Edge::Bottom, 8);
    window.set_exclusive_zone(64);
    window.set_default_size(1, 64);
    window.set_css_classes(&["pineapple-dock-window"]);
}

fn default_icons() -> Vec<(&'static str, &'static str, &'static str)> {
    vec![
        ("pineapple-canopy", "Pineapple Canopy", "pineapple-canopy"),
        ("pineapple-launchpad", "Launchpad", "pineapple-launchpad"),
        ("pineapple-mission", "Mission Control", "pineapple-mission"),
        (
            "pineapple-terminal",
            "Pineapple Terminal",
            "pineapple-terminal",
        ),
        (
            "pineapple-browser",
            "Pineapple Browser",
            "pineapple-browser",
        ),
        ("pineapple-music", "Pineapple Music", "pineapple-music"),
        ("pineapple-photos", "Pineapple Photos", "pineapple-photos"),
        ("pineapple-notes", "Pineapple Notes", "pineapple-notes"),
        ("pineapple-store", "Pineapple Store", "pineapple-store"),
        (
            "pineapple-settings",
            "Pineapple Settings",
            "pineapple-settings",
        ),
        ("pineapple-calc", "Pineapple Calculator", "pineapple-calc"),
    ]
}

fn make_icon_button(icon: &str, label: &str, exec: &str) -> Button {
    let image = Image::from_icon_name(icon);
    image.set_pixel_size(48);

    let button = Button::new();
    button.set_child(Some(&image));
    button.set_tooltip_text(Some(label));
    button.set_css_classes(&["pineapple-dock-icon"]);

    let exec = exec.to_string();
    button.connect_clicked(move |_| {
        let _ = std::process::Command::new("sh")
            .arg("-c")
            .arg(&exec)
            .spawn();
    });

    button
}

/// Miniatura de uma janela minimizada na bandeja do Dock.
fn make_minimized_tile(entry: &WindowEntry, seat: Option<wl_seat::WlSeat>) -> Button {
    let mut title = entry.title.clone();
    if title.is_empty() {
        title = entry.app_id.clone();
    }
    if title.is_empty() {
        title = "Janela".to_string();
    }

    let image = Image::from_icon_name(&icon_for(&entry.app_id));
    image.set_pixel_size(36);

    let button = Button::new();
    button.set_child(Some(&image));
    button.set_tooltip_text(Some(&title));
    button.set_css_classes(&["pineapple-dock-tile"]);
    button.set_opacity(0.0);

    // Clique restaura a janela (desminimiza e traz para o foco).
    let handle = entry.handle.clone();
    button.connect_clicked(move |_| {
        if let Some(seat) = &seat {
            let _ = handle.activate(seat);
        }
    });

    // Animação de entrada: a janela "colapsa" para o Dock, aparecendo
    // crescendo e esmaecendo em (efeito de minimizar do macOS).
    let img = image.clone();
    let btn = button.clone();
    let mut step = 0u32;
    glib::timeout_add_local(Duration::from_millis(16), move || {
        step += 1;
        let t = (step as f64 / 12.0).min(1.0);
        let eased = 1.0 - (1.0 - t) * (1.0 - t);
        img.set_pixel_size((24.0 + 12.0 * eased) as i32);
        btn.set_opacity(eased);
        if t >= 1.0 {
            glib::ControlFlow::Break
        } else {
            glib::ControlFlow::Continue
        }
    });

    button
}

/// Reconstrói a bandeja de minimizadas (separador + miniaturas).
fn rebuild_tray(tray: &gtk::Box, shared: &Shared) {
    while let Some(child) = tray.first_child() {
        tray.remove(&child);
    }
    let minimized: Vec<&WindowEntry> = shared.windows.iter().filter(|w| w.minimized).collect();
    if minimized.is_empty() {
        tray.set_visible(false);
        return;
    }
    let sep = Label::new(None);
    sep.set_css_classes(&["pineapple-dock-sep"]);
    tray.append(&sep);
    for w in minimized {
        tray.append(&make_minimized_tile(w, shared.seat.clone()));
    }
    tray.set_visible(true);
}

/// Magnificação suave: ícones próximos ao centro ficam maiores.
fn start_magnification(container: &gtk::Box) {
    let children_box = container.clone();
    glib::timeout_add_local(Duration::from_millis(16), move || {
        let mut total = 0i32;
        let mut c = children_box.first_child();
        while let Some(child) = c {
            if child.is_visible() {
                total += 1;
            }
            c = child.next_sibling();
        }
        let total = total.max(1) as f64;

        let mut index = 0i32;
        let mut c = children_box.first_child();
        while let Some(child) = c {
            let next = child.next_sibling();
            if child.is_visible() {
                let dist = (index as f64 - (total - 1.0) / 2.0).abs();
                let scale = 1.0 + (1.0 - (dist / total).min(1.0)) * 0.35;
                let size = (48.0 * scale) as i32;
                if let Ok(btn) = child.downcast::<Button>() {
                    if let Some(image) = btn.child().and_then(|c| c.downcast::<Image>().ok()) {
                        image.set_pixel_size(size);
                    }
                }
                index += 1;
            }
            c = next;
        }
        glib::ControlFlow::Continue
    });
}

fn main() -> glib::ExitCode {
    let shared = match setup_wayland() {
        Some(s) => s,
        None => {
            eprintln!(
                "[pineapple-dock] aviso: sem conexão Wayland — rodando sem bandeja de minimizadas"
            );
            Arc::new(Mutex::new(Shared::default()))
        }
    };

    let app = gtk::Application::builder()
        .application_id("org.pineappleos.dock")
        .build();

    app.connect_activate(move |app| {
        let window = gtk::ApplicationWindow::new(app);
        window.set_decorated(false);

        let container = gtk::Box::new(Orientation::Horizontal, 6);
        container.set_css_classes(&["pineapple-dock"]);
        container.set_halign(gtk::Align::Center);

        for (name, label, exec) in default_icons() {
            container.append(&make_icon_button(name, label, exec));
        }

        let tray = gtk::Box::new(Orientation::Horizontal, 6);
        tray.set_visible(false);
        container.append(&tray);

        // Acompanha o estado Wayland e reconstrói a bandeja quando muda.
        let shared2 = shared.clone();
        let tray2 = tray.clone();
        let mut last = {
            let guard = shared.lock().unwrap();
            rebuild_tray(&tray, &guard);
            guard.version
        };
        glib::timeout_add_local(Duration::from_millis(120), move || {
            let guard = shared2.lock().unwrap();
            if guard.version != last {
                last = guard.version;
                rebuild_tray(&tray2, &guard);
            }
            glib::ControlFlow::Continue
        });

        start_magnification(&container);

        window.set_child(Some(&container));
        place_dock(&window);
        window.present();
    });

    app.run()
}
