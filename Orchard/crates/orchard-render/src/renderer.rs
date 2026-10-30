/// Cor RGBA em float (0.0–1.0), usada pelo GLS Render e pelo Gtk4.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Color {
    pub r: f32,
    pub g: f32,
    pub b: f32,
    pub a: f32,
}

impl Color {
    pub const fn new(r: f32, g: f32, b: f32, a: f32) -> Self {
        Self { r, g, b, a }
    }

    pub const fn rgb(r: f32, g: f32, b: f32) -> Self {
        Self::new(r, g, b, 1.0)
    }

    /// Cores da identidade Pineapple (boot/login lavanda escuro ~9%).
    pub const BG: Color = Color::rgb(0.149, 0.141, 0.149); // #262426
    pub const FG: Color = Color::rgb(0.604, 0.588, 0.604); // #9a969a
    pub const TEXT: Color = Color::rgb(0.925, 0.918, 0.925); // #eceaed
    pub const ACCENT: Color = Color::rgb(0.761, 0.745, 0.761); // #c2bec2
    pub const DIM: Color = Color::rgb(0.235, 0.224, 0.235); // #3c393c
    pub const WHITE: Color = Color::rgb(1.0, 1.0, 1.0);
    pub const BLACK: Color = Color::rgb(0.0, 0.0, 0.0);

    pub fn with_alpha(mut self, a: f32) -> Self {
        self.a = a;
        self
    }

    /// Hex "#rrggbb" → Color (ignora alpha).
    pub fn from_hex(hex: &str) -> Self {
        let h = hex.trim_start_matches('#');
        let v = u32::from_str_radix(h, 16).unwrap_or(0);
        Self::rgb(
            ((v >> 16) & 0xff) as f32 / 255.0,
            ((v >> 8) & 0xff) as f32 / 255.0,
            (v & 0xff) as f32 / 255.0,
        )
    }
}

/// Retângulo em pixels (origem no canto superior esquerdo).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Rect {
    pub x: f32,
    pub y: f32,
    pub w: f32,
    pub h: f32,
}

impl Rect {
    pub const fn new(x: f32, y: f32, w: f32, h: f32) -> Self {
        Self { x, y, w, h }
    }

    /// Retângulo centralizado horizontalmente com largura `w`.
    pub fn centered_x(w: f32, y: f32, h: f32, screen_w: f32) -> Self {
        Self::new((screen_w - w) / 2.0, y, w, h)
    }

    pub fn contains(&self, px: f64, py: f64) -> bool {
        px >= self.x as f64
            && px <= (self.x + self.w) as f64
            && py >= self.y as f64
            && py <= (self.y + self.h) as f64
    }
}

/// Interface de desenho imediato implementada pelos backends (Gtk4 e GLS).
pub trait Renderer {
    /// Largura da janela em pixels.
    fn width(&self) -> f32;
    /// Altura da janela em pixels.
    fn height(&self) -> f32;

    /// Preenche a janela inteira com `color`.
    fn clear(&mut self, color: Color);

    /// Preenche um retângulo.
    fn fill_rect(&mut self, rect: Rect, color: Color);

    /// Contorna um retângulo com espessura `thickness`.
    fn stroke_rect(&mut self, rect: Rect, color: Color, thickness: f32);

    /// Desenha texto; `(x, y)` é a base superior esquerda do texto.
    fn text(&mut self, x: f32, y: f32, size: f32, color: Color, content: &str);

    /// Mede a largura aproximada do texto no tamanho dado.
    fn text_width(&self, size: f32, content: &str) -> f32;

    /// Apresenta o frame (no Gtk4 é no-op; no GLS Render faz o swap).
    fn present(&mut self);
}
