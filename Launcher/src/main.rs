use gtk::prelude::*;
use gtk::{
    Application, ApplicationWindow, IconTheme, Image, Label, ListBox, ListBoxRow, Orientation,
    SearchEntry,
};

/// Um aplicativo descoberto pelo launcher.
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

/// Cria uma linha do launcher para um app.
fn row_for(app: &AppItem) -> ListBoxRow {
    let hbox = gtk::Box::new(Orientation::Horizontal, 12);
    hbox.set_margin_top(6);
    hbox.set_margin_bottom(6);
    hbox.set_margin_start(10);
    hbox.set_margin_end(10);

    let icon = Image::from_icon_name(&app.icon);
    icon.set_pixel_size(36);
    hbox.append(&icon);

    let vbox = gtk::Box::new(Orientation::Vertical, 0);
    let name = Label::new(Some(&app.name));
    name.set_xalign(0.0);
    name.set_css_classes(&["pineapple-launcher-name"]);
    vbox.append(&name);

    if !app.comment.is_empty() {
        let comment = Label::new(Some(&app.comment));
        comment.set_xalign(0.0);
        comment.set_css_classes(&["pineapple-launcher-comment"]);
        vbox.append(&comment);
    }
    hbox.append(&vbox);

    let row = ListBoxRow::new();
    row.set_child(Some(&hbox));
    row.set_activatable(true);
    row
}

/// Executa um comando de sistema no plano de fundo.
fn spawn(cmd: &str) {
    let _ = std::process::Command::new("sh").arg("-c").arg(cmd).spawn();
}

/// Cria um botão de ação do sistema (bloquear/suspender/reiniciar/desligar).
fn system_button(icon: &str, tooltip: &str, cmd: &str) -> gtk::Button {
    let btn = gtk::Button::from_icon_name(icon);
    btn.set_tooltip_text(Some(tooltip));
    btn.set_hexpand(true);
    let cmd = cmd.to_string();
    btn.connect_clicked(move |_| spawn(&cmd));
    btn
}

/// Constrói a interface do launcher.
pub fn build(app: &Application) -> ApplicationWindow {
    let win = ApplicationWindow::new(app);
    win.set_decorated(false);
    win.set_title(Some("Pineapple Launcher"));
    win.set_css_classes(&["pineapple-launcher-window"]);

    let vbox = gtk::Box::new(Orientation::Vertical, 6);
    vbox.set_css_classes(&["pineapple-launcher"]);

    let entry = SearchEntry::new();
    entry.set_placeholder_text(Some("Pesquisar aplicativos, arquivos, comandos..."));
    entry.set_hexpand(true);
    entry.set_css_classes(&["pineapple-launcher-entry"]);
    vbox.append(&entry);

    let list = ListBox::new();
    list.set_css_classes(&["pineapple-launcher-list"]);
    list.set_selection_mode(gtk::SelectionMode::Single);

    let all = discover_apps();
    for app in &all {
        list.append(&row_for(app));
    }
    list.set_filter_func({
        let entry = entry.clone();
        move |row| {
            let text = entry.text();
            if text.is_empty() {
                return true;
            }
            if let Some(child) = row.child() {
                if let Ok(hbox) = child.downcast::<gtk::Box>() {
                    if let Some(vbox) = hbox.first_child().and_then(|c| c.next_sibling()) {
                        if let Some(name) =
                            vbox.first_child().and_then(|n| n.downcast::<Label>().ok())
                        {
                            return name.text().to_lowercase().contains(&text.to_lowercase());
                        }
                    }
                }
            }
            true
        }
    });

    entry.connect_search_changed({
        let list = list.clone();
        move |_| {
            list.invalidate_filter();
        }
    });

    list.connect_row_activated(move |_, row| {
        if let Some(child) = row.child() {
            if let Ok(hbox) = child.downcast::<gtk::Box>() {
                if let Some(vbox) = hbox.first_child().and_then(|c| c.next_sibling()) {
                    if let Some(name) = vbox.first_child().and_then(|n| n.downcast::<Label>().ok())
                    {
                        let name = name.text();
                        if let Some(app) = all.iter().find(|a| a.name.as_str() == name.as_str()) {
                            let _ = std::process::Command::new("sh")
                                .arg("-c")
                                .arg(&app.exec)
                                .spawn();
                        }
                    }
                }
            }
        }
    });

    let scroller = gtk::ScrolledWindow::new();
    scroller.set_child(Some(&list));
    scroller.set_vexpand(true);
    vbox.append(&scroller);

    // ---- ações de sistema ----
    let sep = gtk::Separator::new(Orientation::Horizontal);
    vbox.append(&sep);

    let sysbar = gtk::Box::new(Orientation::Horizontal, 4);
    sysbar.set_margin_top(6);
    sysbar.set_margin_bottom(6);
    sysbar.set_margin_start(10);
    sysbar.set_margin_end(10);
    sysbar.append(&system_button(
        "system-lock-screen-symbolic",
        "Bloquear tela",
        "loginctl lock-session",
    ));
    sysbar.append(&system_button(
        "media-playback-pause-symbolic",
        "Suspender",
        "systemctl suspend",
    ));
    sysbar.append(&system_button(
        "view-refresh-symbolic",
        "Reiniciar",
        "systemctl reboot",
    ));
    sysbar.append(&system_button(
        "system-shutdown-symbolic",
        "Desligar",
        "systemctl poweroff",
    ));
    vbox.append(&sysbar);

    win.set_child(Some(&vbox));

    // Fecha com Esc
    let key_controller = gtk::EventControllerKey::new();
    key_controller.connect_key_pressed({
        let win = win.clone();
        move |_, keyval, _, _| {
            if keyval == gtk::gdk::Key::Escape {
                win.close();
                glib::Propagation::Stop
            } else {
                glib::Propagation::Proceed
            }
        }
    });
    win.add_controller(key_controller);

    // fallback para tema de ícones
    let _ = IconTheme::for_display(&gtk::gdk::Display::default().unwrap());

    win
}

fn main() -> glib::ExitCode {
    let hidden = std::env::args().any(|a| a == "--hidden");
    let app = Application::builder()
        .application_id("org.pineappleos.launcher")
        .build();

    app.connect_activate(move |app| {
        let win = build(app);
        if !hidden {
            win.present();
        }
    });

    app.run()
}
