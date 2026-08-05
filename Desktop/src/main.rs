mod menu;
mod shell;
mod status;

use std::rc::Rc;

use gtk4::prelude::*;

fn main() -> glib::ExitCode {
    let app = gtk4::Application::builder()
        .application_id("org.makos.shell")
        .build();

    app.connect_activate(build_ui);
    app.run()
}

fn build_ui(app: &gtk4::Application) {
    let window = shell::shell_window(app);
    let bar = Rc::new(shell::ShellBar::new());

    window.set_child(Some(&bar.container));
    bar.place_as_top(&window);
    shell::start_clock_loop(bar.clock_label.clone());

    window.present();
}
