// =============================================================================
//  pineapple-mission — Mission Control e Spaces do Pineapple OS
//
//  Visão geral em tela cheia estilo macOS:
//   - faixa superior de Spaces (áreas de trabalho) via ext-workspace-v1;
//   - grade de janelas abertas via wlr-foreign-toplevel-management-v1;
//   - clique em um card foca a janela; clique em um Space troca a área.
//
//  Degradação graciosa: sem ext-workspace mostra um aviso e depende dos
//  atalhos Super+1..4; sem foreign-toplevel mostra apenas a faixa de Spaces.
// =============================================================================

use std::cell::{Cell, RefCell};
use std::rc::Rc;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use gtk::prelude::*;
use gtk::{Box, FlowBox, Image, Label, Orientation, ScrolledWindow};
use gtk4_layer_shell::{Edge, KeyboardMode, Layer, LayerShell};

use wayland_backend::protocol::WEnum;
use wayland_client::event_created_child;
use wayland_client::globals::{registry_queue_init, GlobalListContents};
use wayland_client::protocol::wl_registry;
use wayland_client::protocol::wl_seat;
use wayland_client::{delegate_noop, Connection, Dispatch, QueueHandle};

use wayland_protocols::ext::workspace::v1::client::ext_workspace_handle_v1::{
    self, Event as WorkspaceEvent, State as WorkspaceState, WorkspaceCapabilities,
    ExtWorkspaceHandleV1,
};
use wayland_protocols::ext::workspace::v1::client::ext_workspace_group_handle_v1::{
    self, Event as WorkspaceGroupEvent, ExtWorkspaceGroupHandleV1,
};
use wayland_protocols::ext::workspace::v1::client::ext_workspace_manager_v1::{
    self, Event as WorkspaceManagerEvent, ExtWorkspaceManagerV1,
};
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
    active: bool,
    minimized: bool,
    handle: ZwlrForeignToplevelHandleV1,
}

/// Uma área de trabalho (Space), via ext-workspace-v1.
struct WorkspaceEntry {
    name: String,
    active: bool,
    can_activate: bool,
    handle: ExtWorkspaceHandleV1,
}

/// Estado compartilhado entre a thread Wayland e a thread da UI (GTK).
#[derive(Default)]
struct Shared {
    windows: Vec<WindowEntry>,
    workspaces: Vec<WorkspaceEntry>,
    seat: Option<wl_seat::WlSeat>,
    toplevel_manager: Option<ZwlrForeignToplevelManagerV1>,
    workspace_manager: Option<ExtWorkspaceManagerV1>,
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
                active: false,
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
                        entry.active = false;
                        entry.minimized = false;
                        for word in state.chunks_exact(4) {
                            let v = u32::from_le_bytes([word[0], word[1], word[2], word[3]]);
                            if v == ToplevelState::Activated as u32 {
                                entry.active = true;
                            } else if v == ToplevelState::Minimized as u32 {
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

impl Dispatch<ExtWorkspaceManagerV1, ()> for WaylandState {
    fn event(
        state: &mut Self,
        _proxy: &ExtWorkspaceManagerV1,
        event: WorkspaceManagerEvent,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        match event {
            WorkspaceManagerEvent::Workspace { workspace } => {
                let mut shared = state.shared.lock().unwrap();
                shared.workspaces.push(WorkspaceEntry {
                    name: String::new(),
                    active: false,
                    can_activate: true,
                    handle: workspace,
                });
                shared.version += 1;
            }
            _ => {}
        }
    }

    event_created_child!(WaylandState, ExtWorkspaceManagerV1, [
        ext_workspace_manager_v1::EVT_WORKSPACE_OPCODE => (ExtWorkspaceHandleV1, ()),
        ext_workspace_manager_v1::EVT_WORKSPACE_GROUP_OPCODE => (ExtWorkspaceGroupHandleV1, ())
    ]);
}

impl Dispatch<ExtWorkspaceHandleV1, ()> for WaylandState {
    fn event(
        state: &mut Self,
        proxy: &ExtWorkspaceHandleV1,
        event: WorkspaceEvent,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        match event {
            WorkspaceEvent::Removed => {
                let mut shared = state.shared.lock().unwrap();
                if let Some(pos) = shared.workspaces.iter().position(|w| w.handle == *proxy) {
                    let entry = shared.workspaces.remove(pos);
                    let _ = entry.handle.destroy();
                    shared.version += 1;
                }
            }
            other => {
                let mut shared = state.shared.lock().unwrap();
                let Some(entry) = shared.workspaces.iter_mut().find(|w| w.handle == *proxy) else {
                    return;
                };
                match other {
                    WorkspaceEvent::Name { name } => entry.name = name,
                    WorkspaceEvent::State { state } => {
                        if let WEnum::Value(st) = state {
                            entry.active = st.contains(WorkspaceState::Active);
                        }
                    }
                    WorkspaceEvent::Capabilities { capabilities } => {
                        if let WEnum::Value(caps) = capabilities {
                            entry.can_activate = caps.contains(WorkspaceCapabilities::Activate);
                        }
                    }
                    _ => {}
                }
                shared.version += 1;
            }
        }
    }
}

impl Dispatch<ExtWorkspaceGroupHandleV1, ()> for WaylandState {
    fn event(
        _state: &mut Self,
        _proxy: &ExtWorkspaceGroupHandleV1,
        _event: WorkspaceGroupEvent,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
    }
}

delegate_noop!(WaylandState: ignore wl_seat::WlSeat);

/// Conecta-se ao compositor, liga os protocolos e sobe a thread de eventos.
fn setup_wayland() -> Option<Arc<Mutex<Shared>>> {
    let conn = Connection::connect_to_env().ok()?;
    let (globals, mut queue) = registry_queue_init::<WaylandState>(&conn).ok()?;
    let qh = queue.handle();

    let toplevel_manager =
        globals.bind::<ZwlrForeignToplevelManagerV1, _, _>(&qh, 1..=3, ()).ok();
    let workspace_manager = globals.bind::<ExtWorkspaceManagerV1, _, _>(&qh, 1..=1, ()).ok();
    let seat = globals.bind::<wl_seat::WlSeat, _, _>(&qh, 1..=8, ()).ok();

    let shared = Arc::new(Mutex::new(Shared {
        seat,
        toplevel_manager,
        workspace_manager,
        ..Shared::default()
    }));

    // Roundtrip inicial: recebe as janelas e áreas já existentes.
    let mut init = WaylandState { shared: shared.clone() };
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

/// Cria um card (ícone + título) para uma janela.
fn card_for(entry: &WindowEntry) -> gtk::Button {
    let vbox = Box::new(Orientation::Vertical, 8);
    vbox.set_halign(gtk::Align::Center);

    let image = Image::from_icon_name(&icon_for(&entry.app_id));
    image.set_pixel_size(56);
    vbox.append(&image);

    let mut title = entry.title.clone();
    if title.is_empty() {
        title = entry.app_id.clone();
    }
    if title.is_empty() {
        title = "Janela".to_string();
    }

    let label = Label::new(Some(&title));
    label.set_css_classes(&["pineapple-mission-card-title"]);
    label.set_max_width_chars(18);
    label.set_ellipsize(gtk::pango::EllipsizeMode::End);
    label.set_xalign(0.5);
    vbox.append(&label);

    let button = gtk::Button::new();
    button.set_child(Some(&vbox));
    button.set_css_classes(&["pineapple-mission-card"]);
    button.set_tooltip_text(Some(&title));
    button
}

/// Reconstrói a faixa de Spaces e a grade de janelas a partir do estado.
fn rebuild(
    shared: &Shared,
    win: &gtk::ApplicationWindow,
    spaces: &Box,
    flow: &FlowBox,
    empty: &Label,
) {
    while let Some(child) = spaces.first_child() {
        spaces.remove(&child);
    }
    match &shared.workspace_manager {
        None => {
            let hint = Label::new(Some("Áreas de trabalho: use os atalhos Super+1..4"));
            hint.set_css_classes(&["pineapple-mission-hint"]);
            spaces.append(&hint);
        }
        Some(manager) => {
            let mgr = manager.clone();
            for ws in &shared.workspaces {
                let name = if ws.name.is_empty() {
                    "…".to_string()
                } else {
                    ws.name.clone()
                };
                let button = gtk::Button::with_label(&name);
                button.set_css_classes(&["pineapple-mission-space"]);
                if ws.active {
                    button.add_css_class("pineapple-mission-space-active");
                }
                if ws.can_activate {
                    let handle = ws.handle.clone();
                    let mgr = mgr.clone();
                    let win = win.clone();
                    button.connect_clicked(move |_| {
                        let _ = handle.activate();
                        let _ = mgr.commit();
                        win.set_visible(false);
                    });
                }
                spaces.append(&button);
            }
        }
    }

    while let Some(child) = flow.first_child() {
        flow.remove(&child);
    }
    for w in &shared.windows {
        let card = card_for(w);
        let handle = w.handle.clone();
        let seat = shared.seat.clone();
        let win = win.clone();
        card.connect_clicked(move |_| {
            if let Some(seat) = &seat {
                let _ = handle.activate(seat);
            }
            win.set_visible(false);
        });
        flow.insert(&card, -1);
    }

    match &shared.toplevel_manager {
        None => {
            empty.set_text("Visualização de janelas não suportada neste compositor");
            empty.set_visible(true);
        }
        Some(_) => {
            empty.set_text("Nenhuma janela aberta");
            empty.set_visible(shared.windows.is_empty());
        }
    }
}

// ------------------------------------------------------------------ UI

/// Estado da janela (mantido vivo entre ativações).
struct Ui {
    win: gtk::ApplicationWindow,
    flow: FlowBox,
    spaces: Box,
    empty: Label,
    shared: Arc<Mutex<Shared>>,
    last_version: u64,
}

impl Ui {
    /// Reconstrói a UI apenas quando o estado Wayland mudou.
    fn refresh(&mut self) {
        let shared = self.shared.lock().unwrap();
        if shared.version == self.last_version {
            return;
        }
        self.last_version = shared.version;
        rebuild(&shared, &self.win, &self.spaces, &self.flow, &self.empty);
    }
}

fn place(window: &gtk::ApplicationWindow) {
    window.init_layer_shell();
    window.set_namespace("pineappleos-mission");
    window.set_layer(Layer::Overlay);
    window.set_anchor(Edge::Top, true);
    window.set_anchor(Edge::Bottom, true);
    window.set_anchor(Edge::Left, true);
    window.set_anchor(Edge::Right, true);
    window.set_exclusive_zone(-1);
    window.set_keyboard_mode(KeyboardMode::OnDemand);
}

fn build(app: &gtk::Application, shared: Arc<Mutex<Shared>>) -> Ui {
    let win = gtk::ApplicationWindow::new(app);
    win.set_decorated(false);
    win.set_title(Some("Pineapple Mission Control"));
    win.set_css_classes(&["pineapple-mission-window"]);
    place(&win);

    let root = Box::new(Orientation::Vertical, 18);
    root.set_css_classes(&["pineapple-mission"]);
    root.set_margin_top(70);
    root.set_margin_bottom(70);
    root.set_margin_start(90);
    root.set_margin_end(90);

    let title = Label::new(Some("Mission Control"));
    title.set_css_classes(&["pineapple-mission-title"]);
    title.set_halign(gtk::Align::Center);
    root.append(&title);

    let spaces = Box::new(Orientation::Horizontal, 10);
    spaces.set_css_classes(&["pineapple-mission-spaces"]);
    spaces.set_halign(gtk::Align::Center);
    root.append(&spaces);

    let flow = FlowBox::new();
    flow.set_css_classes(&["pineapple-mission-grid"]);
    flow.set_min_children_per_line(5);
    flow.set_max_children_per_line(5);
    flow.set_homogeneous(true);
    flow.set_selection_mode(gtk::SelectionMode::None);
    flow.set_row_spacing(18);
    flow.set_column_spacing(18);
    flow.set_vexpand(true);

    let scroller = ScrolledWindow::new();
    scroller.set_child(Some(&flow));
    scroller.set_vexpand(true);
    root.append(&scroller);

    let empty = Label::new(Some("Nenhuma janela aberta"));
    empty.set_css_classes(&["pineapple-mission-empty"]);
    empty.set_halign(gtk::Align::Center);
    empty.set_visible(false);
    root.append(&empty);

    win.set_child(Some(&root));

    // Esc oculta o Mission Control
    let key_controller = gtk::EventControllerKey::new();
    key_controller.connect_key_pressed({
        let win = win.clone();
        move |_, keyval, _, _| {
            if keyval == gtk::gdk::Key::Escape {
                win.set_visible(false);
                glib::Propagation::Stop
            } else {
                glib::Propagation::Proceed
            }
        }
    });
    win.add_controller(key_controller);

    // Atualização periódica: janelas e Spaces mudam sem a nossa interação.
    let last_version = Rc::new(Cell::new(u64::MAX));
    let lv = last_version.clone();
    let shared2 = shared.clone();
    let win2 = win.clone();
    let spaces2 = spaces.clone();
    let flow2 = flow.clone();
    let empty2 = empty.clone();
    let _ = glib::timeout_add_local(Duration::from_millis(120), move || {
        let guard = shared2.lock().unwrap();
        if guard.version != lv.get() {
            lv.set(guard.version);
            rebuild(&guard, &win2, &spaces2, &flow2, &empty2);
        }
        glib::ControlFlow::Continue
    });

    Ui {
        win,
        flow,
        spaces,
        empty,
        shared,
        last_version: u64::MAX,
    }
}

fn main() -> glib::ExitCode {
    let hidden = std::env::args().any(|a| a == "--hidden");

    let shared = match setup_wayland() {
        Some(s) => s,
        None => {
            eprintln!(
                "[pineapple-mission] aviso: sem conexão Wayland — rodando sem dados de janelas"
            );
            Arc::new(Mutex::new(Shared::default()))
        }
    };

    let app = gtk::Application::builder()
        .application_id("org.pineappleos.mission")
        .build();

    // A janela é mantida viva entre ativações: cada F3 alterna mostrar/ocultar.
    let state: Rc<RefCell<Option<Ui>>> = Rc::new(RefCell::new(None));

    app.connect_activate(move |app| {
        let mut st = state.borrow_mut();
        if st.as_ref().is_some_and(|ui| ui.win.is_visible()) {
            st.as_ref().unwrap().win.set_visible(false);
        } else if let Some(ui) = st.as_mut() {
            // Força a reconstrução ao abrir (o estado pode ter mudado).
            ui.refresh();
            ui.win.present();
        } else {
            let ui = build(app, shared.clone());
            if !hidden {
                ui.win.present();
            }
            *st = Some(ui);
        }
    });

    app.run()
}
