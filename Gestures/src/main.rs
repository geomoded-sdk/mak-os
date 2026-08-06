// =============================================================================
//  mak-gestures — daemon de gestos no touchpad (libinput)
//
//  Lê os dispositivos de entrada via libinput (independente do compositor) e
//  dispara comandos do Mak OS quando um gesto é reconhecido:
//   - swipe up com 3 dedos → mak-launchpad
//
//  O eixo Y do libinput cresce para baixo; um swipe "para cima" acumula dy
//  negativo. As deltas são normalizadas para um dispositivo de 1000dpi.
// =============================================================================

use std::fs::{File, OpenOptions};
use std::os::fd::OwnedFd;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::process::Command;
use std::thread;
use std::time::Duration;

use input::event::gesture::{GestureEndEvent, GestureEventCoordinates, GestureEventTrait};
use input::event::{Event, GestureEvent, GestureSwipeEvent};
use input::{Libinput, LibinputInterface};
use libc::{O_ACCMODE, O_RDONLY, O_RDWR, O_WRONLY};

/// Número de dedos do gesto que abre o Launchpad (como no macOS).
const GESTURE_FINGERS: i32 = 3;
/// Deslocamento mínimo (em unidades normalizadas 1000dpi) para validar o swipe.
const SWIPE_THRESHOLD: f64 = 60.0;

/// Abre/fecha dispositivos de entrada para o libinput.
struct Interface;

impl LibinputInterface for Interface {
    fn open_restricted(&mut self, path: &Path, flags: i32) -> Result<OwnedFd, i32> {
        OpenOptions::new()
            .custom_flags(flags)
            .read((flags & O_ACCMODE) == O_RDONLY || (flags & O_ACCMODE) == O_RDWR)
            .write((flags & O_ACCMODE) == O_WRONLY || (flags & O_ACCMODE) == O_RDWR)
            .open(path)
            .map(|file| file.into())
            .map_err(|err| err.raw_os_error().unwrap_or(1))
    }

    fn close_restricted(&mut self, fd: OwnedFd) {
        drop(File::from(fd));
    }
}

/// Estado de um swipe em andamento.
#[derive(Default)]
struct SwipeState {
    fingers: i32,
    dx: f64,
    dy: f64,
}

/// Processa um evento; retorna o comando a executar se um gesto for reconhecido.
fn handle_event(event: Event, state: &mut SwipeState) -> Option<&'static str> {
    let Event::Gesture(gesture) = event else { return None };
    let GestureEvent::Swipe(swipe) = gesture else { return None };

    match swipe {
        GestureSwipeEvent::Begin(begin) => {
            state.fingers = begin.finger_count();
            state.dx = 0.0;
            state.dy = 0.0;
        }
        GestureSwipeEvent::Update(update) => {
            state.dx += update.dx();
            state.dy += update.dy();
        }
        GestureSwipeEvent::End(end) => {
            if end.cancelled() {
                return None;
            }
            // swipe predominantemente para cima (dy negativo) com 3 dedos
            if state.fingers == GESTURE_FINGERS
                && state.dy < -SWIPE_THRESHOLD
                && state.dy.abs() > state.dx.abs() * 1.2
            {
                return Some("mak-launchpad");
            }
        }
        _ => {}
    }
    None
}

/// Executa um comando de sistema no plano de fundo.
fn spawn(cmd: &str) {
    let _ = Command::new("sh").arg("-c").arg(cmd).spawn();
}

fn main() {
    let seat = std::env::var("MAK_GESTURES_SEAT").unwrap_or_else(|_| "seat0".to_string());

    let mut input = Libinput::new_with_udev(Interface);
    if input.udev_assign_seat(&seat).is_err() {
        eprintln!("[mak-gestures] falha ao atribuir o seat '{seat}'");
        std::process::exit(1);
    }
    println!("[mak-gestures] aguardando gestos no seat '{seat}' ({GESTURE_FINGERS} dedos p/ cima = Launchpad)");

    let mut state = SwipeState::default();
    loop {
        if let Err(err) = input.dispatch() {
            eprintln!("[mak-gestures] erro de dispatch: {err}");
            thread::sleep(Duration::from_millis(100));
            continue;
        }
        for event in &mut input {
            if let Some(cmd) = handle_event(event, &mut state) {
                spawn(cmd);
            }
        }
    }
}
