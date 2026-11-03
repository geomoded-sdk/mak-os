// =============================================================================
//  Backend GTK4 do orchard-render — cairo + DrawingArea, loop a 60 fps.
// =============================================================================

use crate::events::Event;
use crate::renderer::{Color, Rect, Renderer};
use gtk4::prelude::*;
use gtk4::{Application, ApplicationWindow, DrawingArea};
use std::cell::RefCell;
use std::rc::Rc;

/// Renderer imediato sobre um contexto cairo.
struct Gtk4Renderer<'a> {
    cr: &'a gtk4::cairo::Context,
    width: f32,
    height: f32,
}

impl<'a> Gtk4Renderer<'a> {
    fn set_source(cr: &'a gtk4::cairo::Context, c: Color) {
        cr.set_source_rgba(c.r as f64, c.g as f64, c.b as f64, c.a as f64);
    }
}

impl Renderer for Gtk4Renderer<'_> {
    fn width(&self) -> f32 {
        self.width
    }
    fn height(&self) -> f32 {
        self.height
    }

    fn clear(&mut self, color: Color) {
        Self::set_source(self.cr, color);
        self.cr.paint().ok();
    }

    fn fill_rect(&mut self, rect: Rect, color: Color) {
        Self::set_source(self.cr, color);
        self.cr
            .rectangle(rect.x as f64, rect.y as f64, rect.w as f64, rect.h as f64);
        self.cr.fill().ok();
    }

    fn stroke_rect(&mut self, rect: Rect, color: Color, thickness: f32) {
        Self::set_source(self.cr, color);
        self.cr.set_line_width(thickness as f64);
        self.cr
            .rectangle(rect.x as f64, rect.y as f64, rect.w as f64, rect.h as f64);
        self.cr.stroke().ok();
    }

    fn text(&mut self, x: f32, y: f32, size: f32, color: Color, content: &str) {
        Self::set_source(self.cr, color);
        self.cr.select_font_face(
            "Inter",
            gtk4::cairo::FontSlant::Normal,
            gtk4::cairo::FontWeight::Normal,
        );
        self.cr.set_font_size(size as f64);
        self.cr.move_to(x as f64, (y + size * 0.8) as f64);
        self.cr.show_text(content).ok();
    }

    fn text_width(&self, size: f32, content: &str) -> f32 {
        self.cr.select_font_face(
            "Inter",
            gtk4::cairo::FontSlant::Normal,
            gtk4::cairo::FontWeight::Normal,
        );
        self.cr.set_font_size(size as f64);
        self.cr
            .text_extents(content)
            .map(|e| e.width() as f32)
            .unwrap_or(content.len() as f32 * size * 0.6)
    }

    fn present(&mut self) {
        // GTK desenha via sinal draw; nada a apresentar.
    }
}

type FrameFn = dyn FnMut(&mut dyn Renderer, &[Event]) -> bool;

/// Roda a UI GTK4 com o loop de frames a ~60 fps.
pub fn run<F>(title: &str, frame: F) -> Result<(), String>
where
    F: FnMut(&mut dyn Renderer, &[Event]) -> bool + 'static,
{
    let app = Application::builder()
        .application_id("org.pineappleos.orchard")
        .build();

    let frame_rc: Rc<RefCell<F>> = Rc::new(RefCell::new(frame));
    let events_rc: Rc<RefCell<Vec<Event>>> = Rc::new(RefCell::new(Vec::new()));
    let mouse_rc: Rc<RefCell<(f64, f64)>> = Rc::new(RefCell::new((0.0, 0.0)));
    let size_rc: Rc<RefCell<(f32, f32)>> = Rc::new(RefCell::new((1024.0, 640.0)));

    app.connect_activate(move |app| {
        let window = ApplicationWindow::builder()
            .application(app)
            .title(title)
            .default_width(1024)
            .default_height(640)
            .build();

        let da = DrawingArea::new();
        da.set_hexpand(true);
        da.set_vexpand(true);

        // ---- tamanho ----
        {
            let size_rc = size_rc.clone();
            let da2 = da.clone();
            da.connect_resize(move |_, w, h| {
                *size_rc.borrow_mut() = (w as f32, h as f32);
                da2.queue_draw();
            });
        }

        // ---- eventos de mouse ----
        {
            let events = events_rc.clone();
            let mouse = mouse_rc.clone();
            let da2 = da.clone();
            let gesture = gtk4::EventControllerMotion::new();
            gesture.connect_motion(move |_, x, y| {
                *mouse.borrow_mut() = (x, y);
                events.borrow_mut().push(Event::MouseMove { x, y });
                da2.queue_draw();
            });
            da.add_controller(gesture);
        }
        {
            let events = events_rc.clone();
            let mouse = mouse_rc.clone();
            let da2 = da.clone();
            let click = gtk4::GestureClick::new();
            click.connect_pressed(move |_, _n, x, y| {
                events.borrow_mut().push(Event::MouseDown {
                    x,
                    y,
                    button: 1,
                });
                da2.queue_draw();
            });
            click.connect_released(move |_, _n, x, y| {
                events.borrow_mut().push(Event::MouseUp {
                    x,
                    y,
                    button: 1,
                });
                da2.queue_draw();
            });
            da.add_controller(click);
        }

        // ---- teclado ----
        {
            let events = events_rc.clone();
            let da2 = da.clone();
            let key = gtk4::EventControllerKey::new();
            key.connect_key_pressed(move |_, keyval, _keycode, _mods| {
                let name = keyval.name().map(|n| n.to_string()).unwrap_or_default();
                let text = keyval.to_unicode().map(|c| c.to_string());
                events.borrow_mut().push(Event::KeyDown {
                    key: name,
                    text,
                });
                da2.queue_draw();
                glib::Propagation::Proceed
            });
            da.add_controller(key);
        }

        // ---- desenho ----
        {
            let frame_rc = frame_rc.clone();
            let events = events_rc.clone();
            let size_rc = size_rc.clone();
            da.set_draw_func(move |_, cr, w, h| {
                let mut renderer = Gtk4Renderer {
                    cr,
                    width: w as f32,
                    height: h as f32,
                };
                *size_rc.borrow_mut() = (w as f32, h as f32);
                let evs: Vec<Event> = events.borrow_mut().drain(..).collect();
                let mut f = frame_rc.borrow_mut();
                let _alive = f(&mut renderer, &evs);
            });
        }

        // ---- timer 60 fps: coleta Tick e redesenha ----
        {
            let events = events_rc.clone();
            let da2 = da.clone();
            glib::timeout_add_local(std::time::Duration::from_millis(16), move || {
                events.borrow_mut().push(Event::Tick);
                da2.queue_draw();
                glib::ControlFlow::Continue
            });
        }

        window.set_child(Some(&da));
        window.present();
    });

    // Argumentos do app (para não brigar com flags).
    let argv: Vec<String> = std::env::args().collect();
    let argv_refs: Vec<&str> = argv.iter().map(String::as_str).collect();
    let exit = app.run_with_args(&argv_refs);
    if exit == glib::ExitCode::SUCCESS {
        Ok(())
    } else {
        Err("orchard GTK4 fechou com erro".into())
    }
}
