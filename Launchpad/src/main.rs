use std::cell::RefCell;
use std::rc::Rc;

use gtk::prelude::*;
use gtk::{FlowBox, Image, Label, Orientation, SearchEntry};
use gtk4_layer_shell::{Edge, KeyboardMode, Layer, LayerShell};

/// Um aplicativo descoberto pelo launchpad.
#[derive(Debug, Clone)]
pub struct AppItem {
    pub name: String,
    pub comment: String,
    pub icon: String,
    pub exec: String,
}

const APP_DIRS: [&str; 2] = ["/usr/share/applications", "/usr/share/applications/org.gtk"];
const HOME_DIRS: [&str; 2] = [".local/share/applications", ".config/applications"];

/// Descobre aplicativos em .desktop files (sistema + usuário).
pub fn discover_apps() -> Vec<AppItem> {
    use std::fs;

    let mut apps: Vec<AppItem> = Vec::new();
    let mut seen: std::collections::HashSet<String> = Default::default();

    let mut dirs: Vec<std::path::PathBuf> = Vec::new();
    for d in APP_DIRS {
        dirs.push(std::path::PathBuf::from(d));
    }
    if let Ok(home) = std::env::var("HOME") {
        for d in HOME_DIRS {
            dirs.push(std::path::Path::new(&home).join(d));
        }
    }

    for dir in dirs {
        let Ok(entries) = fs::read_dir(&dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let Some(ext) = path.extension() else {
                continue;
            };
            if ext != "desktop" {
                continue;
            }
            let content = fs::read_to_string(&path).unwrap_or_default();
            if !content.contains("[Desktop Entry]") {
                continue;
            }
            let mut name = String::new();
            let mut comment = String::new();
            let mut icon = "application-x-executable".to_string();
            let mut exec = String::new();
            let mut no_display = false;

            for line in content.lines() {
                if let Some(v) = line.strip_prefix("Name=") {
                    name = v.to_string();
                } else if let Some(v) = line.strip_prefix("Comment=") {
                    comment = v.to_string();
                } else if let Some(v) = line.strip_prefix("Icon=") {
                    icon = v.to_string();
                } else if let Some(v) = line.strip_prefix("Exec=") {
                    exec = v.trim().trim_end_matches('%').to_string();
                } else if line == "NoDisplay=true" || line == "Hidden=true" {
                    no_display = true;
                }
            }

            if no_display || name.is_empty() || exec.is_empty() {
                continue;
            }
            if !seen.insert(format!("{name}|{exec}")) {
                continue;
            }
            apps.push(AppItem {
                name,
                comment,
                icon,
                exec,
            });
        }
    }

    apps.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    apps
}

/// Define a posição da janela: overlay em tela cheia sobre o compositor.
fn place(window: &gtk::ApplicationWindow) {
    window.init_layer_shell();
    window.set_namespace("pineappleos-launchpad");
    window.set_layer(Layer::Overlay);
    window.set_anchor(Edge::Top, true);
    window.set_anchor(Edge::Bottom, true);
    window.set_anchor(Edge::Left, true);
    window.set_anchor(Edge::Right, true);
    window.set_exclusive_zone(-1);
    window.set_keyboard_mode(KeyboardMode::OnDemand);
}

/// Executa um comando de sistema no plano de fundo.
fn spawn(cmd: &str) {
    let _ = std::process::Command::new("sh").arg("-c").arg(cmd).spawn();
}

/// Verifica se um app corresponde ao texto de busca.
fn matches(app: &AppItem, text: &str) -> bool {
    let t = text.trim().to_lowercase();
    if t.is_empty() {
        return true;
    }
    app.name.to_lowercase().contains(&t) || app.comment.to_lowercase().contains(&t)
}

/// Cria um tile (ícone + nome) do launchpad, como no macOS.
fn tile_for(app: &AppItem, index: usize) -> gtk::Button {
    let vbox = gtk::Box::new(Orientation::Vertical, 6);
    vbox.set_halign(gtk::Align::Center);

    let image = Image::from_icon_name(&app.icon);
    image.set_pixel_size(88);
    vbox.append(&image);

    let name = Label::new(Some(&app.name));
    name.set_css_classes(&["pineapple-launchpad-name"]);
    name.set_max_width_chars(14);
    name.set_ellipsize(gtk::pango::EllipsizeMode::End);
    name.set_xalign(0.5);
    vbox.append(&name);

    let button = gtk::Button::new();
    button.set_child(Some(&vbox));
    button.set_css_classes(&["pineapple-launchpad-tile"]);
    button.set_widget_name(&format!("lp-{index}"));
    button
}

/// Estado retido entre ativações (mantém a janela viva no modo oculto).
struct Ui {
    win: gtk::ApplicationWindow,
    entry: SearchEntry,
}

/// Constrói a interface do launchpad.
fn build(app: &gtk::Application) -> Ui {
    let win = gtk::ApplicationWindow::new(app);
    win.set_decorated(false);
    win.set_title(Some("Pineapple Launchpad"));
    win.set_css_classes(&["pineapple-launchpad-window"]);
    place(&win);

    let root = gtk::Box::new(Orientation::Vertical, 18);
    root.set_css_classes(&["pineapple-launchpad"]);
    root.set_margin_top(90);
    root.set_margin_bottom(70);
    root.set_margin_start(90);
    root.set_margin_end(90);

    let entry = SearchEntry::new();
    entry.set_placeholder_text(Some("Pesquisar"));
    entry.set_halign(gtk::Align::Center);
    entry.set_width_request(360);
    entry.set_css_classes(&["pineapple-launchpad-search"]);
    root.append(&entry);

    let flow = FlowBox::new();
    flow.set_css_classes(&["pineapple-launchpad-grid"]);
    flow.set_min_children_per_line(7);
    flow.set_max_children_per_line(7);
    flow.set_homogeneous(true);
    flow.set_selection_mode(gtk::SelectionMode::None);
    flow.set_row_spacing(18);
    flow.set_column_spacing(18);
    flow.set_vexpand(true);

    let apps = discover_apps();
    for (i, app) in apps.iter().enumerate() {
        let tile = tile_for(app, i);
        let cmd = app.exec.clone();
        let win = win.clone();
        tile.connect_clicked(move |_| {
            spawn(&cmd);
            win.set_visible(false);
        });
        flow.insert(&tile, -1);
    }

    flow.set_filter_func({
        let apps = apps.clone();
        let entry = entry.clone();
        move |child| {
            let Some(button) = child.child().and_then(|c| c.downcast::<gtk::Button>().ok()) else {
                return true;
            };
            let Ok(index) = button
                .widget_name()
                .strip_prefix("lp-")
                .unwrap_or("")
                .parse::<usize>()
            else {
                return true;
            };
            apps.get(index)
                .map_or(true, |app| matches(app, &entry.text()))
        }
    });

    entry.connect_search_changed({
        let flow = flow.clone();
        move |_| {
            flow.invalidate_filter();
        }
    });

    // Enter abre o primeiro resultado
    entry.connect_activate({
        let apps = apps.clone();
        let win = win.clone();
        move |entry| {
            let text = entry.text();
            if let Some(app) = apps.iter().find(|a| matches(a, &text)) {
                spawn(&app.exec);
                win.set_visible(false);
            }
        }
    });

    let scroller = gtk::ScrolledWindow::new();
    scroller.set_child(Some(&flow));
    scroller.set_vexpand(true);
    root.append(&scroller);

    win.set_child(Some(&root));

    // Esc oculta o launchpad
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

    // Foca a busca sempre que o launchpad aparece
    win.connect_show({
        let entry = entry.clone();
        move |_| {
            entry.grab_focus();
        }
    });

    Ui { win, entry }
}

fn main() -> glib::ExitCode {
    let hidden = std::env::args().any(|a| a == "--hidden");
    let app = gtk::Application::builder()
        .application_id("org.pineappleos.launchpad")
        .build();

    // A janela é mantida viva entre ativações: cada F4 alterna mostrar/ocultar.
    let state: Rc<RefCell<Option<Ui>>> = Rc::new(RefCell::new(None));

    app.connect_activate(move |app| {
        let mut st = state.borrow_mut();
        if let Some(ui) = st.as_ref() {
            if ui.win.is_visible() {
                ui.win.set_visible(false);
            } else {
                ui.entry.set_text("");
                ui.win.present();
            }
        } else {
            let ui = build(app);
            if !hidden {
                ui.win.present();
            }
            *st = Some(ui);
        }
    });

    app.run()
}
