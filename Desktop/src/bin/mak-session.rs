// =============================================================================
//  mak-session — gerenciador de sessão do Mak OS
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
        ("mak-shell", vec![]),
        ("mak-dock", vec![]),
        ("mak-launcher", vec!["--hidden"]),
        ("mak-launchpad", vec!["--hidden"]),
        ("mak-mission", vec!["--hidden"]),
        ("mak-gestures", vec![]),
        ("mak-control-center", vec!["--daemon"]),
        ("mak-notifyd", vec![]),
        ("mak-ai", vec!["--daemon"]),
    ]
}

/// Lê o número de áreas de trabalho da configuração.
fn workspace_count() -> u32 {
    std::fs::read_to_string("/etc/makos/workspaces.conf")
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
    println!("[mak-session] compositor: {COMPOSITOR} (áreas virtuais via rc.xml)");
}

fn main() -> glib::ExitCode {
    println!("== Mak OS Session Manager ==");

    let envs: Vec<(&str, &str)> = vec![
        ("XDG_CURRENT_DESKTOP", "MakOS"),
        ("XDG_SESSION_TYPE", "wayland"),
        ("GDK_BACKEND", "wayland"),
        ("GTK_THEME", "Mak-HighSierra"),
    ];

    let mut procs: HashMap<&'static str, Managed> = HashMap::new();

    // inicia o compositor como processo supervisor
    let _compositor = Managed::launch("labwc", &["-c", "/usr/share/makos/Desktop/data/labwc/rc.xml"], &[]);

    // pequena espera pelo compositor
    thread::sleep(Duration::from_millis(1200));

    // inicia os componentes da interface
    for (name, args) in session_components() {
        match Managed::launch(name, &args, &envs) {
            Some(p) => {
                println!("[mak-session] iniciado: {name}");
                procs.insert(name, p);
            }
            None => eprintln!("[mak-session] falhou ao iniciar: {name}"),
        }
    }

    let workspaces = workspace_count();
    println!("[mak-session] {workspaces} áreas de trabalho virtuais");

    // Interface gráfica de status da sessão (voltar a chamar app::run? Não:
    // este binário é um daemon; mantém-se vivo monitorando os filhos.)
    keep_alive_for(procs)
}

/// Mantém a sessão viva até que o compositor saia.
fn keep_alive_for(_procs: HashMap<&'static str, Managed>) -> glib::ExitCode {
    let app = gtk::Application::builder()
        .application_id("org.makos.session")
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