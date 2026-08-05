use std::cell::RefCell;
use std::path::{Path, PathBuf};
use std::rc::Rc;

use gio::prelude::*;
use gtk::prelude::*;
use gtk::{
    Application, ApplicationWindow, Button, Image, Label, ListBox, ListBoxRow,
    Orientation, Popover, ScrolledWindow, SearchEntry, Stack,
};

struct FinderState {
    current: PathBuf,
    history: Vec<PathBuf>,
    forward: Vec<PathBuf>,
    clipboard: Option<PathBuf>,
}

impl FinderState {
    fn new() -> Self {
        Self {
            current: home_dir(),
            history: Vec::new(),
            forward: Vec::new(),
            clipboard: None,
        }
    }

    fn go(&mut self, path: PathBuf) {
        if path == self.current {
            return;
        }
        self.history.push(self.current.clone());
        self.forward.clear();
        self.current = path;
    }

    fn back(&mut self) -> bool {
        if let Some(p) = self.history.pop() {
            self.forward.push(self.current.clone());
            self.current = p;
            true
        } else {
            false
        }
    }

    fn forward(&mut self) -> bool {
        if let Some(p) = self.forward.pop() {
            self.history.push(self.current.clone());
            self.current = p;
            true
        } else {
            false
        }
    }
}

fn home_dir() -> PathBuf {
    std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/"))
}

fn icon_for(path: &Path) -> String {
    if path.is_dir() {
        return "folder".to_string();
    }
    match path.extension().and_then(|e| e.to_str()) {
        Some("png") | Some("jpg") | Some("jpeg") | Some("gif") | Some("svg") | Some("webp") => {
            "image-x-generic".to_string()
        }
        Some("mp3") | Some("ogg") | Some("flac") | Some("wav") => "audio-x-generic".to_string(),
        Some("mp4") | Some("mkv") | Some("webm") => "video-x-generic".to_string(),
        Some("pdf") => "application-pdf".to_string(),
        Some("txt") | Some("md") | Some("rs") | Some("py") | Some("c") => "text-x-generic".to_string(),
        Some("deb") => "application-x-deb".to_string(),
        _ => "text-x-generic".to_string(),
    }
}

fn human_size(bytes: u64) -> String {
    const UNITS: [&str; 5] = ["B", "KiB", "MiB", "GiB", "TiB"];
    let mut v = bytes as f64;
    let mut i = 0;
    while v >= 1024.0 && i < 4 {
        v /= 1024.0;
        i += 1;
    }
    if i == 0 {
        format!("{bytes} B")
    } else {
        format!("{v:.1} {}", UNITS[i])
    }
}

fn make_row(path: &Path, name: &str, size: u64) -> ListBoxRow {
    let hbox = gtk::Box::new(Orientation::Horizontal, 12);
    hbox.set_margin_top(4);
    hbox.set_margin_bottom(4);
    hbox.set_margin_start(10);
    hbox.set_margin_end(10);

    let icon = Image::from_icon_name(&icon_for(path));
    icon.set_pixel_size(28);
    hbox.append(&icon);

    let vbox = gtk::Box::new(Orientation::Vertical, 0);
    let name_label = Label::new(Some(name));
    name_label.set_xalign(0.0);
    name_label.set_css_classes(&["mak-file-name"]);
    vbox.append(&name_label);

    let sub_text = if path.is_dir() {
        "Pasta".to_string()
    } else {
        human_size(size)
    };
    let sub = Label::new(Some(&sub_text));
    sub.set_xalign(0.0);
    sub.set_css_classes(&["mak-file-meta"]);
    vbox.append(&sub);

    hbox.append(&vbox);
    hbox.set_hexpand(true);

    let row = ListBoxRow::new();
    row.set_child(Some(&hbox));
    row.set_activatable(true);
    unsafe {
        row.set_data("path", path.to_path_buf());
    }
    row
}

/// Abre um caminho: pastas entram, arquivos abrem com o app padrão.
fn open_path(state: &mut FinderState, target: PathBuf, refresh: &dyn Fn()) {
    if target.is_dir() {
        state.go(target);
        refresh();
    } else {
        let file = gio::File::for_path(&target);
        let _ = gio::AppInfo::launch_default_for_uri(&file.uri(), None::<&gio::AppLaunchContext>);
    }
}

/// Janela modal simples para digitar um nome (renomear / nova pasta).
fn input_window(
    parent: &impl IsA<gtk::Window>,
    title: &str,
    initial: &str,
    on_submit: impl FnOnce(String) + 'static,
) {
    let win = gtk::Window::new();
    win.set_title(Some(title));
    win.set_default_size(400, 140);
    win.set_transient_for(Some(parent));
    win.set_modal(true);
    win.set_resizable(false);

    let vbox = gtk::Box::new(Orientation::Vertical, 12);
    vbox.set_margin_top(16);
    vbox.set_margin_bottom(16);
    vbox.set_margin_start(16);
    vbox.set_margin_end(16);

    let entry = gtk::Entry::new();
    entry.set_text(initial);
    entry.set_activates_default(true);
    vbox.append(&entry);

    let hbox = gtk::Box::new(Orientation::Horizontal, 8);
    hbox.set_halign(gtk::Align::End);

    let cancel = Button::with_label("Cancelar");
    let ok = Button::with_label("OK");
    ok.add_css_class("suggested-action");
    hbox.append(&cancel);
    hbox.append(&ok);
    vbox.append(&hbox);

    win.set_child(Some(&vbox));
    win.set_default_widget(Some(&ok));

    let close_win = win.clone();
    cancel.connect_clicked(move |_| close_win.close());

    let ok_close = win.clone();
    let entry2 = entry.clone();
    let on_submit = RefCell::new(Some(on_submit));
    ok.connect_clicked(move |_| {
        if let Some(f) = on_submit.borrow_mut().take() {
            f(entry2.text().to_string());
        }
        ok_close.close();
    });

    win.present();
    entry.grab_focus();
}

/// Cria um botão com ícone + rótulo para o menu de contexto.
fn menu_button(label: &str, icon: &str, on_click: impl Fn() + 'static) -> Button {
    let btn = Button::new();
    let hbox = gtk::Box::new(Orientation::Horizontal, 8);
    hbox.set_margin_top(2);
    hbox.set_margin_bottom(2);
    hbox.set_margin_start(4);
    hbox.set_margin_end(12);
    let img = Image::from_icon_name(icon);
    img.set_pixel_size(16);
    let lbl = Label::new(Some(label));
    lbl.set_xalign(0.0);
    hbox.append(&img);
    hbox.append(&lbl);
    btn.set_child(Some(&hbox));
    btn.connect_clicked(move |_| on_click());
    btn
}

/// Menu de contexto (clique direito): abrir, renomear, copiar, colar, excluir, nova pasta.
fn build_context_menu(
    selected: Rc<RefCell<Option<PathBuf>>>,
    state: Rc<RefCell<FinderState>>,
    refresh: Rc<dyn Fn()>,
    win: &ApplicationWindow,
) -> Popover {
    let pop = Popover::new();
    let vbox = gtk::Box::new(Orientation::Vertical, 2);
    vbox.set_margin_top(6);
    vbox.set_margin_bottom(6);

    // Abrir
    {
        let selected = selected.clone();
        let state = state.clone();
        let refresh = refresh.clone();
        let pop2 = pop.clone();
        vbox.append(&menu_button("Abrir", "document-open-symbolic", move || {
            if let Some(p) = (*selected.borrow()).clone() {
                open_path(&mut state.borrow_mut(), p, &*refresh);
            }
            pop2.popdown();
        }));
    }

    // Renomear
    {
        let selected = selected.clone();
        let state = state.clone();
        let refresh = refresh.clone();
        let win2 = win.clone();
        let pop2 = pop.clone();
        vbox.append(&menu_button("Renomear", "edit-rename-symbolic", move || {
            let target = (*selected.borrow()).clone();
            pop2.popdown();
            if let Some(path) = target {
                let current = state.borrow().current.clone();
                let initial = path
                    .file_name()
                    .map(|f| f.to_string_lossy().to_string())
                    .unwrap_or_default();
                input_window(&win2, "Renomear", &initial, move |new_name| {
                    let new_name = new_name.trim().to_string();
                    if new_name.is_empty() || new_name == initial {
                        return;
                    }
                    let dest = current.join(&new_name);
                    let _ = std::fs::rename(&path, &dest);
                    refresh();
                });
            }
        }));
    }

    // Copiar
    {
        let selected = selected.clone();
        let state = state.clone();
        let pop2 = pop.clone();
        vbox.append(&menu_button("Copiar", "edit-copy-symbolic", move || {
            if let Some(p) = (*selected.borrow()).clone() {
                state.borrow_mut().clipboard = Some(p);
            }
            pop2.popdown();
        }));
    }

    // Colar
    {
        let state = state.clone();
        let refresh = refresh.clone();
        let pop2 = pop.clone();
        vbox.append(&menu_button("Colar", "edit-paste-symbolic", move || {
            let src = state.borrow().clipboard.clone();
            let dest_dir = state.borrow().current.clone();
            if let Some(src) = src {
                let name = src
                    .file_name()
                    .map(|f| f.to_string_lossy().to_string())
                    .unwrap_or_else(|| "arquivo".to_string());
                let dest = dest_dir.join(&name);
                if src.is_dir() {
                    let _ = std::process::Command::new("cp")
                        .args(["-r", src.to_string_lossy().as_ref(), dest.to_string_lossy().as_ref()])
                        .spawn();
                } else {
                    let _ = std::fs::copy(&src, &dest);
                }
                refresh();
            }
            pop2.popdown();
        }));
    }

    // Excluir (vai para a lixeira)
    {
        let selected = selected.clone();
        let refresh = refresh.clone();
        let pop2 = pop.clone();
        vbox.append(&menu_button("Mover para a Lixeira", "user-trash-symbolic", move || {
            if let Some(p) = (*selected.borrow()).clone() {
                let _ = std::process::Command::new("gio")
                    .args(["trash", p.to_string_lossy().as_ref()])
                    .spawn();
                refresh();
            }
            pop2.popdown();
        }));
    }

    // Nova pasta
    {
        let state = state.clone();
        let refresh = refresh.clone();
        let win2 = win.clone();
        let pop2 = pop.clone();
        vbox.append(&menu_button("Nova pasta", "folder-new-symbolic", move || {
            let dest_dir = state.borrow().current.clone();
            pop2.popdown();
            input_window(&win2, "Nova pasta", "Nova pasta", move |name| {
                let name = name.trim().to_string();
                if name.is_empty() {
                    return;
                }
                let _ = std::fs::create_dir(dest_dir.join(&name));
                refresh();
            });
        }));
    }

    pop.set_child(Some(&vbox));
    pop
}

fn load_directory(state: &FinderState, list: &ListBox, stack: &Stack, search: &SearchEntry) {
    while let Some(child) = list.first_child() {
        list.remove(&child);
    }

    let dir = &state.current;
    let Ok(entries) = std::fs::read_dir(dir) else {
        stack.set_visible_child_name("empty");
        return;
    };

    let mut items: Vec<(PathBuf, u64, String)> = Vec::new();
    for entry in entries.flatten() {
        let path = entry.path();
        let meta = entry.metadata().ok();
        let size = meta.as_ref().map(|m| m.len()).unwrap_or(0);
        let name = entry.file_name().to_string_lossy().to_string();
        items.push((path, size, name));
    }
    items.sort_by(|a, b| {
        let a_dir = a.0.is_dir();
        let b_dir = b.0.is_dir();
        b_dir.cmp(&a_dir).then_with(|| {
            a.2.to_lowercase().cmp(&b.2.to_lowercase())
        })
    });

    let q = search.text().to_lowercase();
    let mut count = 0;
    for (path, size, name) in items {
        if !q.is_empty() && !name.to_lowercase().contains(&q) {
            continue;
        }
        list.append(&make_row(&path, &name, size));
        count += 1;
    }

    if count == 0 {
        stack.set_visible_child_name("empty");
    } else {
        stack.set_visible_child_name("view");
    }
}

fn main() -> glib::ExitCode {
    let app = Application::builder()
        .application_id("org.makos.finder")
        .build();

    app.connect_activate(build_ui);
    app.run()
}

fn build_ui(app: &Application) {
    let state = Rc::new(RefCell::new(FinderState::new()));
    let selected = Rc::new(RefCell::new(None::<PathBuf>));

    let win = ApplicationWindow::new(app);
    win.set_title(Some("Mak Finder"));
    win.set_default_size(960, 620);
    win.set_css_classes(&["mak-finder-window"]);

    let root = gtk::Box::new(Orientation::Vertical, 0);

    // ---- barra de ações ----
    let actions = gtk::Box::new(Orientation::Horizontal, 4);
    actions.set_margin_start(8);
    actions.set_margin_end(8);
    actions.set_margin_top(6);
    actions.set_margin_bottom(6);

    let back = gtk::Button::from_icon_name("go-previous-symbolic");
    back.set_tooltip_text(Some("Voltar"));
    let fwd = gtk::Button::from_icon_name("go-next-symbolic");
    fwd.set_tooltip_text(Some("Avançar"));
    let up = gtk::Button::from_icon_name("go-up-symbolic");
    up.set_tooltip_text(Some("Subir um nível"));

    let path_label = Label::new(Some("/"));
    path_label.set_xalign(0.0);
    path_label.set_hexpand(true);
    path_label.set_css_classes(&["mak-path"]);

    let search = SearchEntry::new();
    search.set_placeholder_text(Some("Pesquisar..."));

    actions.append(&back);
    actions.append(&fwd);
    actions.append(&up);
    actions.append(&path_label);
    actions.append(&search);
    root.append(&actions);

    // ---- conteúdo ----
    let content = gtk::Box::new(Orientation::Horizontal, 0);

    let sidebar = ListBox::new();
    sidebar.set_css_classes(&["mak-sidebar"]);
    sidebar.set_width_request(180);
    let places: [(&str, &str); 4] = [
        ("folder-home-symbolic", "Início"),
        ("folder-documents-symbolic", "Documentos"),
        ("folder-download-symbolic", "Downloads"),
        ("folder-pictures-symbolic", "Imagens"),
    ];
    let mut place_rows: Vec<PathBuf> = Vec::new();
    for (icon, name) in places {
        let row = ListBoxRow::new();
        let box_ = gtk::Box::new(Orientation::Horizontal, 8);
        box_.set_margin_top(8);
        box_.set_margin_bottom(8);
        box_.set_margin_start(8);
        let img = Image::from_icon_name(icon);
        img.set_pixel_size(16);
        let lbl = Label::new(Some(name));
        box_.append(&img);
        box_.append(&lbl);
        row.set_child(Some(&box_));
        sidebar.append(&row);
        let base = if name == "Início" {
            home_dir()
        } else {
            home_dir().join(name.to_lowercase())
        };
        place_rows.push(base);
    }

    // lista de arquivos
    let list = ListBox::new();
    list.set_css_classes(&["mak-file-list"]);

    let scroller = ScrolledWindow::new();
    scroller.set_child(Some(&list));
    scroller.set_vexpand(true);

    let empty = gtk::Box::new(Orientation::Vertical, 4);
    empty.set_vexpand(true);
    let msg = Label::new(Some("Pasta vazia"));
    msg.set_css_classes(&["mak-empty"]);
    empty.append(&msg);

    let stack = Stack::new();
    stack.add_named(&scroller, Some("view"));
    stack.add_named(&empty, Some("empty"));
    stack.set_visible_child_name("view");
    stack.set_vexpand(true);

    content.append(&sidebar);
    content.append(&stack);
    root.append(&content);
    win.set_child(Some(&root));

    // ---- navegação ----
    let refresh = {
        let state = state.clone();
        let list = list.clone();
        let stack = stack.clone();
        let search = search.clone();
        move || {
            let s = state.borrow();
            path_label.set_label(s.current.to_str().unwrap_or("/"));
            load_directory(&s, &list, &stack, &search);
        }
    };
    let refresh = Rc::new(refresh);

    // ---- menu de contexto ----
    let context = build_context_menu(selected.clone(), state.clone(), refresh.clone(), &win);
    context.set_parent(&list);

    let gesture = gtk::GestureClick::new();
    gesture.set_button(3);
    let selected_g = selected.clone();
    let context_g = context.clone();
    gesture.connect_pressed(move |_g, _n, x, y| {
        if let Some(row) = list.row_at_y(y as i32) {
            if let Some(path) = unsafe { row.data::<PathBuf>("path") } {
                *selected_g.borrow_mut() = Some(unsafe { path.as_ref() }.clone());
                let rect = gtk::gdk::Rectangle::new(x as i32, y as i32, 1, 1);
                context_g.set_pointing_to(Some(&rect));
                context_g.popup();
            }
        }
    });
    list.add_controller(gesture);

    back.connect_clicked({
        let state = state.clone();
        let refresh = refresh.clone();
        move |_| {
            if state.borrow_mut().back() {
                refresh();
            }
        }
    });
    fwd.connect_clicked({
        let state = state.clone();
        let refresh = refresh.clone();
        move |_| {
            if state.borrow_mut().forward() {
                refresh();
            }
        }
    });
    up.connect_clicked({
        let state = state.clone();
        let refresh = refresh.clone();
        move |_| {
            let parent = state.borrow().current.parent().map(|p| p.to_path_buf());
            if let Some(p) = parent {
                state.borrow_mut().go(p);
                refresh();
            }
        }
    });

    sidebar.connect_row_activated({
        let state = state.clone();
        let refresh = refresh.clone();
        let place_rows = place_rows.clone();
        move |_, row| {
            if let Some(p) = place_rows.get(row.index() as usize) {
                state.borrow_mut().go(p.clone());
                refresh();
            }
        }
    });

    list.connect_row_activated({
        let state = state.clone();
        let refresh = refresh.clone();
        move |_, row| {
            if let Some(path) = unsafe { row.data::<PathBuf>("path") } {
                open_path(&mut state.borrow_mut(), unsafe { path.as_ref() }.clone(), &*refresh);
            }
        }
    });

    search.connect_search_changed({
        let refresh = refresh.clone();
        move |_| refresh()
    });

    win.present();
    refresh();
}
