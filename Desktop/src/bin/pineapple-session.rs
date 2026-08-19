// =============================================================================
//  pineapple-session — gerenciador de sessão do Pineapple OS
//
//  Responsabilidades:
//   - iniciar o compositor Wayland (labwc/wayfire)
//   - subir os componentes da interface (shell, dock, launcher, control center)
//   - iniciar os serviços (notificações, IA)
//   - gerenciar Áreas de Trabalho Virtuais via IPC do compositor
//   - desligar/limpar a sessão no encerramento
// =============================================================================

use std::collections::HashMap;
use std::process::{Child, Command};
use std::thread;
use std::time::Duration;

use gtk::prelude::*;

const COMPOSITOR: &str = "labwc";
const DEFAULT_WORKSPACES: u32 = 4;

/// Um processo gerenciado pela sessão.
struct Managed {
    child: Child,
}

impl Managed {
    fn launch(cmd: &str, args: &[&str], envs: &[(&str, &str)]) -> Option<Self> {
        let mut c = Command::new(cmd);
        c.args(args);
        for (k, v) in envs {
            c.env(k, v);
        }
        c.spawn().ok().map(|child| Self { child })
    }
}

/// Configura a sessão: componentes a iniciar.
fn session_components() -> Vec<(&'static str, Vec<&'static str>)> {
    vec![
        ("pineapple-shell", vec![]),
        ("pineapple-dock", vec![]),
        ("pineapple-launcher", vec!["--hidden"]),
        ("pineapple-launchpad", vec!["--hidden"]),
        ("pineapple-mission", vec!["--hidden"]),
        ("pineapple-gestures", vec![]),
        ("pineapple-control-center", vec!["--daemon"]),
        ("pineapple-notifyd", vec![]),
        ("pineapple-ai", vec!["--daemon"]),
    ]
}

/// Lê o número de áreas de trabalho da configuração.
fn workspace_count() -> u32 {
    std::fs::read_to_string("/etc/pineappleos/workspaces.conf")
        .ok()
        .and_then(|s| s.trim().parse().ok())
        .unwrap_or(DEFAULT_WORKSPACES)
}

#[allow(dead_code)]
/// Simula o IPC de troca de workspace. Em produção, use o IPC do compositor
/// (ex.: `swaymsg workspace N` no sway, ou a API wlroots equivalente).
fn switch_workspace(n: u32) {
    let _ = Command::new(COMPOSITOR).arg(format!("workspace {n}")).spawn();
}

/// Inicia o compositor em primeiro plano. Retorna seu PID.
fn start_compositor() {
    // labwc não suporta "workspace N" via CLI; a troca de áreas é feita por
    // atalhos do próprio compositor. Registramos os atalhos em rc.xml.
    println!("[pineapple-session] compositor: {COMPOSITOR} (áreas virtuais via rc.xml)");
}

fn main() -> glib::ExitCode {
    println!("== Pineapple OS Session Manager ==");

    let envs: Vec<(&str, &str)> = vec![
        ("XDG_CURRENT_DESKTOP", "PineappleOS"),
        ("XDG_SESSION_TYPE", "wayland"),
        ("GDK_BACKEND", "wayland"),
        ("GTK_THEME", "Pineapple-HighSierra"),
    ];

    let mut procs: HashMap<&'static str, Managed> = HashMap::new();

    // inicia o compositor como processo supervisor
    let _compositor = Managed::launch("labwc", &["-c", "/usr/share/pineappleos/Desktop/data/labwc/rc.xml"], &[]);

    // pequena espera pelo compositor
    thread::sleep(Duration::from_millis(1200));

    // inicia os componentes da interface
    for (name, args) in session_components() {
        match Managed::launch(name, &args, &envs) {
            Some(p) => {
                println!("[pineapple-session] iniciado: {name}");
                procs.insert(name, p);
            }
            None => eprintln!("[pineapple-session] falhou ao iniciar: {name}"),
        }
    }

    let workspaces = workspace_count();
    println!("[pineapple-session] {workspaces} áreas de trabalho virtuais");

    // Interface gráfica de status da sessão (voltar a chamar app::run? Não:
    // este binário é um daemon; mantém-se vivo monitorando os filhos.)
    keep_alive_for(procs)
}

/// Mantém a sessão viva até que o compositor saia.
fn keep_alive_for(_procs: HashMap<&'static str, Managed>) -> glib::ExitCode {
    let app = gtk::Application::builder()
        .application_id("org.pineappleos.session")
        .flags(gtk::gio::ApplicationFlags::NON_UNIQUE)
        .build();

    // roda o loop GTK para receber sinais de encerramento de forma limpa
    app.connect_activate(|_| {});
    app.run()
}

#[allow(dead_code)]
fn _unused(clone: &glib::Object) -> bool {
    let _ = clone;
    false
}