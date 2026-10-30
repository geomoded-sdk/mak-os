/// Eventos de entrada entregues à UI a cada frame.
#[derive(Debug, Clone, PartialEq)]
pub enum Event {
    MouseMove { x: f64, y: f64 },
    MouseDown { x: f64, y: f64, button: u8 },
    MouseUp { x: f64, y: f64, button: u8 },
    /// Tecla pressionada; `text` contém o caractere quando for imprimível.
    KeyDown { key: String, text: Option<String> },
    KeyUp { key: String },
    Resize { width: u32, height: u32 },
    Tick,
}

impl Event {
    /// Posição do mouse, se houver.
    pub fn mouse_pos(&self) -> Option<(f64, f64)> {
        match self {
            Event::MouseMove { x, y }
            | Event::MouseDown { x, y, .. }
            | Event::MouseUp { x, y, .. } => Some((*x, *y)),
            _ => None,
        }
    }
}
