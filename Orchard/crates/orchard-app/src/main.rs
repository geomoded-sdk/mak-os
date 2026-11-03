// =============================================================================
//  pineapple-orchard — instalador do Pineapple OS (Rust nativo + GTK4)
//
//  UI nativa estilo macOS (fiel a ui.html): sem HTML/JS/WebKit.
//  Motor: orchard-core — apaga/grava disco de verdade (sfdisk, mkfs, rsync…).
//
//  Uso:
//    pineapple-orchard              # modo real (pede sudo)
//    pineapple-orchard --dry-run    # não toca disco (demo/teste)
// =============================================================================

use gtk4::prelude::*;
use gtk4::{
    Application, ApplicationWindow, Align, Box as GtkBox, Button, Entry, Label, ListBox,
    ListBoxRow, Orientation, ProgressBar, ScrolledWindow, SelectionMode,
};
use orchard_core::{human_size, list_disks, InstallConfig, Installer, PartitionMode};
use std::cell::{Cell, RefCell};
use std::rc::Rc;

const APP_ID: &str = "com.pineappleos.orchard";

// ---------------------------------------------------------------------------
//  CSS — fiel ao mockup ui.html
// ---------------------------------------------------------------------------
const CSS: &str = r#"
* { font-family: "Cantarell", "DejaVu Sans", sans-serif; }
window { background: #1e3a4a; }
.app {
  background: #f6f6f6;
  border-radius: 8px;
}
.titlebar {
  background: linear-gradient(#fafafa, #e9e9e9);
  border-bottom: 1px solid #c8c8c8;
  border-radius: 8px 8px 0 0;
  min-height: 38px;
}
.titlebar label { color: #555; font-size: 13px; }
.dot {
  min-width: 12px; min-height: 12px;
  padding: 0;
  border-radius: 6px;
  border: 1px solid rgba(0,0,0,0.12);
  background: #ccc;
}
.dot.red { background: #ff6058; }
.dot.yellow { background: #ffbd2e; }
.dot.green { background: #28c840; }
button.dot { min-width: 12px; min-height: 12px; }
.content {
  background: #f6f6f6;
  padding: 28px 40px 20px;
}
.content h1 { font-size: 22px; font-weight: 400; color: #292929; margin: 6px 0 10px; }
.content p { font-size: 13px; color: #555; }
.small { font-size: 11px; color: #888; }
.logo { font-size: 44px; color: #777; }
.list {
  background: white;
  border: 1px solid #ccc;
  border-radius: 5px;
  min-width: 320px;
  max-width: 460px;
}
.list row { padding: 9px 12px; min-height: 40px; border-bottom: 1px solid #e5e5e5; }
.list row:last-child { border-bottom: none; }
.list row:hover { background: #eef6ff; }
.list row:selected { background: #dceeff; }
.list row label { font-size: 13px; color: #292929; }
.list row .sub { font-size: 11px; color: #888; }
.btn {
  border: 1px solid #aaa; border-radius: 5px;
  padding: 7px 16px; min-width: 80px;
  background: linear-gradient(#fff, #e8e8e8);
  color: #333; font-size: 13px;
}
.btn:hover { background: linear-gradient(#fff, #dcecff); }
.btn.primary {
  color: white; border-color: #0872c8;
  background: linear-gradient(#45a5f4, #087bd5);
}
.btn.primary:hover { background: linear-gradient(#5ab0f8, #1a8adf); }
.footer {
  background: linear-gradient(#fafafa, #f0f0f0);
  border-top: 1px solid #d6d6d6;
  border-radius: 0 0 8px 8px;
  min-height: 58px;
  padding: 10px 20px;
}
.entry {
  border: 1px solid #aaa; border-radius: 4px;
  background: white; padding: 8px 10px;
  min-width: 300px; font-size: 13px;
}
.entry:focus { border-color: #0872c8; }
.progress trough { background: #d8d8d8; border-radius: 4px; min-height: 7px; }
.progress progress { background: #1685df; border-radius: 4px; min-height: 7px; }
"#;

// ---------------------------------------------------------------------------
//  Páginas
// ---------------------------------------------------------------------------
#[derive(Clone, PartialEq)]
enum Page {
    Language,
    Utilities,
    Installer,
    License,
    Agree,
    Disk,
    Installing,
    Country,
    Keyboard,
    Network,
    Migration,
    PineappleId,
    Terms,
    Account,
    Express,
    Complete,
    Desktop,
    DiskUtil,
    Help,
    TimeMachine,
}

struct App {
    dry_run: bool,
    page: Page,
    previous: Vec<Page>,
    language: String,
    disk_label: String,
    disk_path: String,
    country: String,
    keyboard: String,
    username: String,
    full_name: String,
    password: String,
    powerbook_id: String,
    install_progress: f64,
    install_running: Rc<Cell<bool>>,
    config: InstallConfig,
}

impl App {
    fn new(dry_run: bool) -> Self {
        Self {
            dry_run,
            page: Page::Language,
            previous: Vec::new(),
            language: "Português".into(),
            disk_label: String::new(),
            disk_path: String::new(),
            country: "Brasil".into(),
            keyboard: "Brasileiro".into(),
            username: String::new(),
            full_name: String::new(),
            password: String::new(),
            powerbook_id: String::new(),
            install_progress: 0.0,
            install_running: Rc::new(Cell::new(false)),
            config: InstallConfig::default(),
        }
    }

    fn go(&mut self, page: Page) {
        if self.page != page {
            self.previous.push(self.page.clone());
        }
        self.page = page;
    }

    fn back(&mut self) {
        self.page = self.previous.pop().unwrap_or(Page::Utilities);
    }

    fn locale(&self) -> &'static str {
        match self.language.as_str() {
            "English" => "en_US.UTF-8",
            "Español" => "es_ES.UTF-8",
            "Français" => "fr_FR.UTF-8",
            "Deutsch" => "de_DE.UTF-8",
            "Italiano" => "it_IT.UTF-8",
            "日本語" => "ja_JP.UTF-8",
            _ => "pt_BR.UTF-8",
        }
    }

    fn kb(&self) -> &'static str {
        match self.keyboard.as_str() {
            "ABC" | "U.S." => "us",
            "Português" => "pt",
            _ => "br",
        }
    }

    fn tz(&self) -> &'static str {
        match self.country.as_str() {
            "Estados Unidos" => "America/New_York",
            "Portugal" => "Europe/Lisbon",
            "Argentina" => "America/Argentina/Buenos_Aires",
            "Canadá" => "America/Toronto",
            "Alemanha" => "Europe/Berlin",
            "Japão" => "Asia/Tokyo",
            "Reino Unido" => "Europe/London",
            _ => "America/Sao_Paulo",
        }
    }
}

// ---------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------
fn label(text: &str, class: &str) -> Label {
    let l = Label::new(Some(text));
    for c in class.split_whitespace() {
        l.add_css_class(c);
    }
    l.set_wrap(true);
    l.set_xalign(0.5);
    l
}

fn button(text: &str, primary: bool) -> Button {
    let b = Button::with_label(text);
    b.add_css_class("btn");
    if primary {
        b.add_css_class("primary");
    }
    b
}

fn list_row(title: &str, sub: Option<&str>) -> ListBoxRow {
    let row = ListBoxRow::new();
    let b = GtkBox::new(Orientation::Vertical, 2);
    b.set_margin_top(6);
    b.set_margin_bottom(6);
    b.set_margin_start(12);
    b.set_margin_end(12);
    let t = Label::new(Some(title));
    t.set_xalign(0.0);
    b.append(&t);
    if let Some(s) = sub {
        let sl = Label::new(Some(s));
        sl.set_xalign(0.0);
        sl.add_css_class("sub");
        b.append(&sl);
    }
    row.set_child(Some(&b));
    row
}

fn list_box(items: &[(&str, Option<&str>)]) -> ListBox {
    let lb = ListBox::new();
    lb.add_css_class("list");
    lb.set_selection_mode(SelectionMode::Single);
    for (t, s) in items {
        lb.append(&list_row(t, *s));
    }
    lb
}

fn row_text(row: &ListBoxRow) -> String {
    row.child()
        .and_then(|c| c.downcast::<GtkBox>().ok())
        .and_then(|b| b.first_child())
        .and_then(|l| l.downcast::<Label>().ok())
        .map(|l| l.label().to_string())
        .unwrap_or_default()
}

fn footer(left: Option<&Button>, right: Option<&Button>) -> GtkBox {
    let f = GtkBox::new(Orientation::Horizontal, 9);
    f.add_css_class("footer");
    f.set_margin_top(8);
    f.set_margin_bottom(8);
    f.set_margin_start(20);
    f.set_margin_end(20);
    f.set_hexpand(true);
    if let Some(b) = left {
        f.append(b);
    }
    let sp = GtkBox::new(Orientation::Horizontal, 0);
    sp.set_hexpand(true);
    f.append(&sp);
    if let Some(b) = right {
        f.append(b);
    }
    f
}

fn content_vbox() -> GtkBox {
    let v = GtkBox::new(Orientation::Vertical, 8);
    v.add_css_class("content");
    v.set_hexpand(true);
    v.set_vexpand(true);
    v.set_halign(Align::Fill);
    v.set_valign(Align::Fill);
    v
}

fn logo() -> Label {
    let l = Label::new(Some("🍍"));
    l.add_css_class("logo");
    l.set_halign(Align::Center);
    l
}

// ---------------------------------------------------------------------------
//  Contexto de render (holder + navegação)
// ---------------------------------------------------------------------------
struct Ctx {
    app: Rc<RefCell<App>>,
    holder: GtkBox,
    window: ApplicationWindow,
}

impl Ctx {
    fn rebuild(&self) {
        while let Some(c) = self.holder.first_child() {
            self.holder.remove(&c);
        }
        let page = self.app.borrow().page.clone();
        match page {
            Page::Language => self.scr_language(),
            Page::Utilities => self.scr_utilities(),
            Page::Installer => self.scr_installer(),
            Page::License => self.scr_license(),
            Page::Agree => self.scr_agree(),
            Page::Disk => self.scr_disk(),
            Page::Installing => self.scr_installing(),
            Page::Country => self.scr_country(),
            Page::Keyboard => self.scr_keyboard(),
            Page::Network => self.scr_network(),
            Page::Migration => self.scr_migration(),
            Page::PineappleId => self.scr_pineapple_id(),
            Page::Terms => self.scr_terms(),
            Page::Account => self.scr_account(),
            Page::Express => self.scr_express(),
            Page::Complete => self.scr_complete(),
            Page::Desktop => self.scr_desktop(),
            Page::DiskUtil => self.scr_disk_util(),
            Page::Help => self.scr_help(),
            Page::TimeMachine => self.scr_time_machine(),
        }
    }

    fn go(&self, page: Page) {
        self.app.borrow_mut().go(page);
        self.rebuild();
    }

    fn back(&self) {
        self.app.borrow_mut().back();
        self.rebuild();
    }

    fn attach_nav(&self, back_btn: Option<&Button>, next_btn: Option<&Button>) {
        // bind botões — cada chamador conecta os handlers
        let _ = (back_btn, next_btn);
    }

    fn finish(&self, content: &GtkBox, left: Option<&Button>, right: Option<&Button>) {
        let f = footer(left, right);
        self.holder.append(content);
        self.holder.append(&f);
    }

    // --- Language ---
    fn scr_language(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Selecione seu idioma", "h1"));
        c.append(&label("Selecione o idioma principal que você deseja usar.", ""));

        let langs = ["Português", "English", "Español", "Français", "Deutsch", "Italiano", "日本語"];
        let items: Vec<(&str, Option<&str>)> = langs.iter().map(|l| (*l, None)).collect();
        let lb = list_box(&items);
        let cur = self.app.borrow().language.clone();
        for (i, lang) in langs.iter().enumerate() {
            if *lang == cur {
                if let Some(r) = lb.row_at_index(i as i32) {
                    lb.select_row(Some(&r));
                }
            }
        }
        let app = self.app.clone();
        lb.connect_row_selected(move |_, row| {
            if let Some(r) = row {
                app.borrow_mut().language = row_text(r);
            }
        });
        c.append(&lb);

        let next = button("Continuar", true);
        let ctx_next = CtxLike::from(self);
        next.connect_clicked(move |_| ctx_next.go(Page::Utilities));
        self.finish(&c, None, Some(&next));
    }

    // --- Utilities ---
    fn scr_utilities(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Utilitários do PineappleOS", "h1"));
        c.append(&label(
            "Para restaurar o sistema usando um backup, reinstalar o PineappleOS ou usar outras ferramentas, selecione uma das opções abaixo.",
            "",
        ));

        let grid = GtkBox::new(Orientation::Vertical, 10);
        grid.set_halign(Align::Center);
        let utils: [(&str, &str, &str, Page); 4] = [
            ("◷", "Restaurar de um backup do Time Machine", "Restaure o Mac usando um backup.", Page::TimeMachine),
            ("⬇", "Instalar PineappleOS", "Instale uma nova cópia do PineappleOS.", Page::Installer),
            ("◉", "Obter ajuda online", "Consulte informações sobre o PineappleOS.", Page::Help),
            ("▤", "Utilitário de Disco", "Repare ou apague discos.", Page::DiskUtil),
        ];
        for (icon, title, desc, page) in utils {
            let u = GtkBox::new(Orientation::Vertical, 2);
            u.set_margin_top(10);
            u.set_margin_bottom(10);
            u.set_margin_start(12);
            u.set_margin_end(12);
            let big = Label::new(Some(icon));
            big.add_css_class("title-1");
            big.set_halign(Align::Center);
            u.append(&big);
            let t = Label::new(Some(title));
            t.set_halign(Align::Center);
            t.set_wrap(true);
            u.append(&t);
            let d = Label::new(Some(desc));
            d.add_css_class("small");
            d.set_halign(Align::Center);
            u.append(&d);
            let ctx = CtxLike::from(self);
            let g = gtk4::GestureClick::new();
            g.connect_pressed(move |_, _, _, _| ctx.go(page.clone()));
            u.add_controller(g);
            grid.append(&u);
        }
        c.append(&grid);

        let restart = button("Reiniciar", false);
        let shutdown = button("Desligar", false);
        self.finish(&c, Some(&restart), Some(&shutdown));
    }

    // --- Installer intro ---
    fn scr_installer(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Instalar PineappleOS", "h1"));
        c.append(&label("Para configurar a instalação do PineappleOS, clique em Continuar.", ""));
        c.append(&label(
            "O PineappleOS oferece novas tecnologias e recursos que tornam seu Mac mais capaz, inteligente e responsivo.",
            "",
        ));
        c.append(&label("Versão 2.0 · Orchard", "small"));

        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::License));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- License ---
    fn scr_license(&self) {
        let c = content_vbox();
        c.append(&label("Contrato de licença de software", "h1"));
        c.append(&label("Leia os termos e condições antes de continuar.", ""));

        let scroll = ScrolledWindow::new();
        scroll.set_min_content_height(220);
        scroll.set_min_content_width(520);
        let text = Label::new(Some(
            "PineappleOS 2.0\n\n\
             Esta é a interface do instalador Orchard do PineappleOS.\n\n\
             As operações de partição e cópia são executadas no disco selecionado na etapa seguinte.\n\n\
             PineappleOS e 🍍 são marcas de seus respectivos titulares.",
        ));
        text.set_xalign(0.0);
        text.set_wrap(true);
        text.set_margin_top(12);
        text.set_margin_start(12);
        scroll.set_child(Some(&text));
        c.append(&scroll);

        let back = button("Voltar", false);
        let next = button("Concordar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::Agree));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Agree ---
    fn scr_agree(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Você concorda com os termos?", "h1"));
        c.append(&label(
            "Você deve concordar com o contrato de licença para continuar a instalação do PineappleOS.",
            "",
        ));
        let no = button("Não concordo", false);
        let yes = button("Concordo", true);
        let c1 = CtxLike::from(self);
        no.connect_clicked(move |_| c1.go(Page::License));
        let c2 = CtxLike::from(self);
        yes.connect_clicked(move |_| c2.go(Page::Disk));
        self.finish(&c, Some(&no), Some(&yes));
    }

    // --- Disk ---
    fn scr_disk(&self) {
        let c = content_vbox();
        c.append(&label("Selecione o disco onde deseja instalar o PineappleOS", "h1"));
        c.append(&label("Escolha o disco de destino para a instalação.", ""));

        let disks = list_disks().unwrap_or_default();
        let items: Vec<(String, Option<String>)> = disks
            .iter()
            .map(|d| {
                let sub = format!(
                    "{} · {}{}",
                    d.model,
                    human_size(d.size_bytes),
                    if d.is_removable { " · removível" } else { "" }
                );
                (d.path.rsplit('/').next().unwrap_or(&d.path).to_string(), Some(sub))
            })
            .collect();
        let refs: Vec<(&str, Option<&str>)> = items.iter().map(|(t, s)| (t.as_str(), s.as_deref())).collect();
        let lb = list_box(&refs);
        if !disks.is_empty() {
            if let Some(r) = lb.row_at_index(0) {
                lb.select_row(Some(&r));
            }
            let mut a = self.app.borrow_mut();
            a.disk_path = disks[0].path.clone();
            a.disk_label = disks[0].path.rsplit('/').next().unwrap_or(&disks[0].path).to_string();
        }
        let app = self.app.clone();
        lb.connect_row_selected(move |_, row| {
            if let Some(r) = row {
                let idx = r.index() as usize;
                if let Ok(disks) = list_disks() {
                    if let Some(d) = disks.get(idx) {
                        let mut a = app.borrow_mut();
                        a.disk_path = d.path.clone();
                        a.disk_label = d.path.rsplit('/').next().unwrap_or(&d.path).to_string();
                    }
                }
            }
        });
        c.append(&lb);
        c.append(&label("O disco selecionado será APAGADO por completo.", "small"));

        let back = button("Voltar", false);
        let next = button("Instalar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| {
            c2.prepare_install();
            c2.go(Page::Installing);
        });
        self.finish(&c, Some(&back), Some(&next));
    }

    fn prepare_install(&self) {
        let mut a = self.app.borrow_mut();
        a.config.disk = a.disk_path.clone();
        a.config.locale = a.locale().to_string();
        a.config.keyboard_layout = a.kb().to_string();
        a.config.timezone = a.tz().to_string();
        a.config.mode = PartitionMode::Erase;
        if a.config.username.is_empty() {
            a.config.username = "user".into();
        }
        if a.config.password.len() < 4 {
            a.config.password = "1234".into();
        }
        if a.config.hostname == "pineapple" {
            a.config.hostname = a.config.username.clone();
        }
        a.config.powerbook_id = if a.powerbook_id.is_empty() {
            std::env::var("POWERBOOK_ID").unwrap_or_else(|_| {
                if a.dry_run { "PB-DRYRUN".into() } else { "PB-UI".into() }
            })
        } else {
            a.powerbook_id.clone()
        };
        a.install_progress = 0.0;
    }

    // --- Installing ---
    fn scr_installing(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Instalando PineappleOS", "h1"));

        let disk_label = self.app.borrow().disk_label.clone();
        let msg = Label::new(Some(&format!("Preparando para instalar no disco {disk_label}…")));
        c.append(&msg);

        let bar = ProgressBar::new();
        bar.add_css_class("progress");
        bar.set_halign(Align::Center);
        bar.set_hexpand(true);
        bar.set_fraction(0.0);
        c.append(&bar);

        let pct = Label::new(Some("0% concluído"));
        c.append(&pct);
        c.append(&label("O computador será reiniciado após a conclusão da instalação.", "small"));

        // Inicia o motor uma única vez
        if !self.app.borrow().install_running.get() {
            let running = self.app.borrow().install_running.clone();
            running.set(true);
            let cfg = self.app.borrow().config.clone();
            let dry = self.app.borrow().dry_run;
            let bar2 = bar.clone();
            let pct2 = pct.clone();
            let msg2 = msg.clone();
            let ctx = CtxLike::from(self);

            let mut installer = Installer::new(cfg, dry);
            let result = installer.run(|p| {
                    let f = (p.percent as f64).clamp(0.0, 1.0);
                    let m = p.message.clone();
                    glib::MainContext::default().invoke_local(move || {
                        bar2.set_fraction(f);
                        pct2.set_text(&format!("{}% concluído", (f * 100.0) as u32));
                        msg2.set_text(&m);
                    });
            });
            glib::MainContext::default().invoke_local(move || {
                    running.set(false);
                    match result {
                        Ok(()) => ctx.go(Page::Country),
                        Err(_) => ctx.go(Page::Disk),
                    }
            });
        }

        let cancel = button("Cancelar", false);
        let c1 = CtxLike::from(self);
        cancel.connect_clicked(move |_| c1.go(Page::Disk));
        self.finish(&c, None, Some(&cancel));
    }

    // --- Country ---
    fn scr_country(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Selecione seu país ou região", "h1"));
        c.append(&label("Selecione seu país ou região para configurar o Mac.", ""));
        let countries = ["Brasil", "Estados Unidos", "Portugal", "Argentina", "Canadá", "Alemanha", "Japão", "Reino Unido"];
        let items: Vec<(&str, Option<&str>)> = countries.iter().map(|x| (*x, None)).collect();
        let lb = list_box(&items);
        let cur = self.app.borrow().country.clone();
        for (i, x) in countries.iter().enumerate() {
            if *x == cur {
                if let Some(r) = lb.row_at_index(i as i32) {
                    lb.select_row(Some(&r));
                }
            }
        }
        let app = self.app.clone();
        lb.connect_row_selected(move |_, row| {
            if let Some(r) = row {
                app.borrow_mut().country = row_text(r);
            }
        });
        c.append(&lb);
        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::Keyboard));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Keyboard ---
    fn scr_keyboard(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Selecione o layout do teclado", "h1"));
        c.append(&label("Selecione o layout que corresponde ao teclado conectado ao Mac.", ""));
        let layouts = ["Brasileiro", "Brasileiro - PC", "ABC", "U.S.", "Português"];
        let items: Vec<(&str, Option<&str>)> = layouts.iter().map(|x| (*x, None)).collect();
        let lb = list_box(&items);
        let cur = self.app.borrow().keyboard.clone();
        for (i, x) in layouts.iter().enumerate() {
            if *x == cur {
                if let Some(r) = lb.row_at_index(i as i32) {
                    lb.select_row(Some(&r));
                }
            }
        }
        let app = self.app.clone();
        lb.connect_row_selected(move |_, row| {
            if let Some(r) = row {
                app.borrow_mut().keyboard = row_text(r);
            }
        });
        c.append(&lb);
        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::Network));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Network ---
    fn scr_network(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Selecione sua rede Wi-Fi", "h1"));
        c.append(&label("Selecione uma rede para conectar o Mac à Internet.", ""));
        let nets = [
            ("📶 Minha Rede Wi-Fi", Some("WPA2")),
            ("📶 Rede de Convidados", None),
            ("📶 Outra Rede...", None),
        ];
        let lb = list_box(&nets);
        if let Some(r) = lb.row_at_index(0) {
            lb.select_row(Some(&r));
        }
        c.append(&lb);
        c.append(&label("Você também pode continuar sem conexão.", "small"));
        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::Migration));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Migration ---
    fn scr_migration(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Transferir informações para este Mac", "h1"));
        c.append(&label(
            "Você pode transferir informações de outro Mac, de um backup do Time Machine ou de um PC.",
            "",
        ));
        let choices = [
            "De um Mac, backup do Time Machine ou disco de inicialização",
            "De um PC com Windows",
            "Não transferir informações agora",
        ];
        let items: Vec<(&str, Option<&str>)> = choices.iter().map(|x| (*x, None)).collect();
        let lb = list_box(&items);
        if let Some(r) = lb.row_at_index(2) {
            lb.select_row(Some(&r));
        }
        c.append(&lb);
        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::PineappleId));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Pineapple ID ---
    fn scr_pineapple_id(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Inicie sessão com seu ID Pineapple", "h1"));
        c.append(&label(
            "Use seu ID Pineapple para configurar o iCloud, a App Store e outros serviços.",
            "",
        ));
        let email = Entry::new();
        email.add_css_class("entry");
        email.set_placeholder_text(Some("nome@exemplo.com"));
        email.set_halign(Align::Center);
        c.append(&email);
        let pass = Entry::new();
        pass.add_css_class("entry");
        pass.set_placeholder_text(Some("Senha"));
        pass.set_visibility(false);
        pass.set_halign(Align::Center);
        c.append(&pass);
        c.append(&label("Você pode configurar seu ID Pineapple mais tarde.", "small"));
        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::Terms));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Terms ---
    fn scr_terms(&self) {
        let c = content_vbox();
        c.append(&label("Termos e condições", "h1"));
        c.append(&label("Leia os termos e condições para utilizar o PineappleOS.", ""));
        let scroll = ScrolledWindow::new();
        scroll.set_min_content_height(180);
        scroll.set_min_content_width(500);
        let text = Label::new(Some(
            "Termos e condições\n\nEsta tela faz parte da configuração do PineappleOS 2.0.",
        ));
        text.set_xalign(0.0);
        text.set_wrap(true);
        text.set_margin_top(12);
        text.set_margin_start(12);
        scroll.set_child(Some(&text));
        c.append(&scroll);
        let back = button("Voltar", false);
        let next = button("Aceitar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::Account));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Account ---
    fn scr_account(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Crie uma conta de computador", "h1"));
        c.append(&label("Esta conta será usada para desbloquear o Mac e acessar seus arquivos.", ""));

        let full = Entry::new();
        full.add_css_class("entry");
        full.set_placeholder_text(Some("Nome completo"));
        full.set_halign(Align::Center);
        c.append(&full);

        let user = Entry::new();
        user.add_css_class("entry");
        user.set_placeholder_text(Some("Nome da conta"));
        user.set_halign(Align::Center);
        c.append(&user);

        let pass = Entry::new();
        pass.add_css_class("entry");
        pass.set_placeholder_text(Some("Senha"));
        pass.set_visibility(false);
        pass.set_halign(Align::Center);
        c.append(&pass);

        let app = self.app.clone();
        full.connect_changed(move |e| app.borrow_mut().full_name = e.text().to_string());
        let app = self.app.clone();
        user.connect_changed(move |e| app.borrow_mut().username = e.text().to_string());
        let app = self.app.clone();
        pass.connect_changed(move |e| app.borrow_mut().password = e.text().to_string());

        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| {
            let name = c2.app.borrow().full_name.trim().to_string();
            if name.is_empty() {
                return;
            }
            {
                let mut a = c2.app.borrow_mut();
                if a.username.is_empty() {
                    a.username = name.split_whitespace().next().unwrap_or("user").to_string();
                }
                a.config.hostname = a.username.clone();
            }
            c2.go(Page::Express);
        });
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Express ---
    fn scr_express(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Configurar seu Mac", "h1"));
        c.append(&label(
            "O PineappleOS pode configurar automaticamente serviços e funcionalidades.",
            "",
        ));
        let items = [
            ("✓ Ativar serviços de localização", None),
            ("✓ Compartilhar análises do Mac", None),
            ("✓ Ativar a Siri", None),
        ];
        let lb = list_box(&items);
        for i in 0..3 {
            if let Some(r) = lb.row_at_index(i) {
                lb.select_row(Some(&r));
            }
        }
        c.append(&lb);
        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::Complete));
        self.finish(&c, Some(&back), Some(&next));
    }

    // --- Complete ---
    fn scr_complete(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Seu Mac está configurado", "h1"));
        c.append(&label("O PineappleOS está pronto para uso.", ""));
        c.append(&label("Obrigado por usar esta demonstração.", ""));
        let next = button("Começar a usar", true);
        let c1 = CtxLike::from(self);
        next.connect_clicked(move |_| c1.go(Page::Desktop));
        self.finish(&c, None, Some(&next));
    }

    // --- Desktop ---
    fn scr_desktop(&self) {
        let c = content_vbox();
        c.set_valign(Align::Center);
        let w = Label::new(Some("Bem-vindo"));
        w.add_css_class("h1");
        c.append(&w);
        c.append(&label("PineappleOS 2.0", "small"));
        let quit = button("Fechar instalador", true);
        let win = self.window.clone();
        quit.connect_clicked(move |_| win.close());
        self.finish(&c, None, Some(&quit));
    }

    // --- Disk Util ---
    fn scr_disk_util(&self) {
        let c = content_vbox();
        c.append(&label("Utilitário de Disco", "h1"));
        let disks = list_disks().unwrap_or_default();
        let items: Vec<(String, Option<String>)> = disks
            .iter()
            .map(|d| {
                let sub = format!(
                    "{} · {}",
                    if d.is_removable { "USB" } else { "Volume interno" },
                    human_size(d.size_bytes)
                );
                (d.path.rsplit('/').next().unwrap_or(&d.path).to_string(), Some(sub))
            })
            .collect();
        let refs: Vec<(&str, Option<&str>)> = items.iter().map(|(t, s)| (t.as_str(), s.as_deref())).collect();
        let lb = list_box(&refs);
        if let Some(r) = lb.row_at_index(0) {
            lb.select_row(Some(&r));
        }
        c.append(&lb);
        c.append(&label("As operações são demonstrativas.", "small"));
        let back = button("Voltar", false);
        let done = button("Concluído", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        done.connect_clicked(move |_| c2.go(Page::Utilities));
        self.finish(&c, Some(&back), Some(&done));
    }

    // --- Help ---
    fn scr_help(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Ajuda do PineappleOS", "h1"));
        c.append(&label("Bem-vindo à ajuda do PineappleOS.", ""));
        let items = [
            ("Instalar o PineappleOS", None),
            ("Configurar seu Mac", None),
            ("Usar o Utilitário de Disco", None),
            ("Restaurar um backup", None),
        ];
        let lb = list_box(&items);
        c.append(&lb);
        let back = button("Voltar", false);
        let done = button("Concluído", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        done.connect_clicked(move |_| c2.go(Page::Utilities));
        self.finish(&c, Some(&back), Some(&done));
    }

    // --- Time Machine ---
    fn scr_time_machine(&self) {
        let c = content_vbox();
        c.append(&logo());
        c.append(&label("Restaurar de um backup do Time Machine", "h1"));
        c.append(&label("Selecione um backup para restaurar seu sistema.", ""));
        let items = [("Nenhum backup disponível", None)];
        let lb = list_box(&items);
        c.append(&lb);
        c.append(&label("Nenhuma restauração será executada nesta simulação.", "small"));
        let back = button("Voltar", false);
        let next = button("Continuar", true);
        let c1 = CtxLike::from(self);
        back.connect_clicked(move |_| c1.back());
        let c2 = CtxLike::from(self);
        next.connect_clicked(move |_| c2.go(Page::Utilities));
        self.finish(&c, Some(&back), Some(&next));
    }
}

/// Clone leve do contexto para closures (Rc + GtkBox + Window são Clone).
struct CtxLike {
    app: Rc<RefCell<App>>,
    holder: GtkBox,
    window: ApplicationWindow,
}

impl Clone for CtxLike {
    fn clone(&self) -> Self {
        Self {
            app: self.app.clone(),
            holder: self.holder.clone(),
            window: self.window.clone(),
        }
    }
}

impl From<&Ctx> for CtxLike {
    fn from(c: &Ctx) -> Self {
        Self {
            app: c.app.clone(),
            holder: c.holder.clone(),
            window: c.window.clone(),
        }
    }
}

impl CtxLike {
    fn prepare_install(&self) {
        let mut a = self.app.borrow_mut();
        a.config.disk = a.disk_path.clone();
        a.config.locale = a.locale().to_string();
        a.config.keyboard_layout = a.kb().to_string();
        a.config.timezone = a.tz().to_string();
        a.config.mode = PartitionMode::Erase;
        if a.config.username.is_empty() {
            a.config.username = "user".into();
        }
        if a.config.password.len() < 4 {
            a.config.password = "1234".into();
        }
        if a.config.hostname == "pineapple" {
            a.config.hostname = a.config.username.clone();
        }
        a.config.powerbook_id = if a.powerbook_id.is_empty() {
            std::env::var("POWERBOOK_ID").unwrap_or_else(|_| {
                if a.dry_run { "PB-DRYRUN".into() } else { "PB-UI".into() }
            })
        } else {
            a.powerbook_id.clone()
        };
        a.install_progress = 0.0;
    }

    fn go(&self, page: Page) {
        self.app.borrow_mut().go(page);
        self.rebuild();
    }
    fn back(&self) {
        self.app.borrow_mut().back();
        self.rebuild();
    }
    fn rebuild(&self) {
        while let Some(c) = self.holder.first_child() {
            self.holder.remove(&c);
        }
        let ctx = Ctx {
            app: self.app.clone(),
            holder: self.holder.clone(),
            window: self.window.clone(),
        };
        // Reusa o match de páginas do Ctx sem recursão (método separado)
        let page = ctx.app.borrow().page.clone();
        match page {
            Page::Language => ctx.scr_language(),
            Page::Utilities => ctx.scr_utilities(),
            Page::Installer => ctx.scr_installer(),
            Page::License => ctx.scr_license(),
            Page::Agree => ctx.scr_agree(),
            Page::Disk => ctx.scr_disk(),
            Page::Installing => ctx.scr_installing(),
            Page::Country => ctx.scr_country(),
            Page::Keyboard => ctx.scr_keyboard(),
            Page::Network => ctx.scr_network(),
            Page::Migration => ctx.scr_migration(),
            Page::PineappleId => ctx.scr_pineapple_id(),
            Page::Terms => ctx.scr_terms(),
            Page::Account => ctx.scr_account(),
            Page::Express => ctx.scr_express(),
            Page::Complete => ctx.scr_complete(),
            Page::Desktop => ctx.scr_desktop(),
            Page::DiskUtil => ctx.scr_disk_util(),
            Page::Help => ctx.scr_help(),
            Page::TimeMachine => ctx.scr_time_machine(),
        }
    }
}

// ---------------------------------------------------------------------------
//  main
// ---------------------------------------------------------------------------
fn main() {
    let dry_run = std::env::args().any(|a| a == "--dry-run");

    let app = Application::builder().application_id(APP_ID).build();

    app.connect_activate(move |app| {
        let provider = gtk4::CssProvider::new();
        provider.load_from_data(CSS);
        gtk4::StyleContext::add_provider_for_display(
            &gtk4::gdk::Display::default().expect("no display"),
            &provider,
            gtk4::STYLE_PROVIDER_PRIORITY_APPLICATION,
        );

        let window = ApplicationWindow::builder()
            .application(app)
            .title("PineappleOS  2.0")
            .default_width(820)
            .default_height(640)
            .decorated(false)
            .build();

        let app_state = Rc::new(RefCell::new(App::new(dry_run)));

        // Janela "app" centralizada com padding (simula o card do mockup)
        let card = GtkBox::new(Orientation::Vertical, 0);
        card.add_css_class("app");
        card.set_halign(Align::Fill);
        card.set_valign(Align::Fill);
        card.set_margin_top(20);
        card.set_margin_bottom(20);
        card.set_margin_start(30);
        card.set_margin_end(30);

        // Titlebar
        let titlebar = GtkBox::new(Orientation::Horizontal, 12);
        titlebar.add_css_class("titlebar");
        let traffic = GtkBox::new(Orientation::Horizontal, 7);
        traffic.set_valign(Align::Center);
        for cls in ["red", "yellow", "green"] {
            // Botão pequeno arredondado — CSS confiável (DrawingArea não pinta bg)
            let d = Button::new();
            d.set_size_request(12, 12);
            d.add_css_class("dot");
            d.add_css_class(cls);
            d.add_css_class("flat");
            let win = window.clone();
            let is_red = cls == "red";
            d.connect_clicked(move |_| {
                if is_red {
                    win.close();
                }
            });
            traffic.append(&d);
        }
        titlebar.append(&traffic);
        let title = Label::new(Some("PineappleOS  2.0"));
        title.set_halign(Align::Center);
        title.set_hexpand(true);
        titlebar.append(&title);
        card.append(&titlebar);

        // Holder de conteúdo
        let holder = GtkBox::new(Orientation::Vertical, 0);
        holder.set_hexpand(true);
        holder.set_vexpand(true);
        card.append(&holder);

        window.set_child(Some(&card));

        let ctx = Ctx {
            app: app_state,
            holder,
            window: window.clone(),
        };
        ctx.rebuild();

        window.present();
    });

    app.run();
}
