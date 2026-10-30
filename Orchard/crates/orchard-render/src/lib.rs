// =============================================================================
//  orchard-render — framework de UI do Orchard com DOIS renderizadores:
//
//   * Gtk4Backend (padrão) — cairo via GTK4, texto nativo.
//   * GLSRender   (feature gls-backend) — renderer GPU PRÓPRIO do Pineapple
//     OS, desenvolvido para superar o Metal da Apple: wgpu (Vulkan/Metal/
//     DX12/WebGPU) por baixo, pipeline e API pensados para a UI Pineapple.
//
//  A UI é imediata: a cada frame a app desenha via trait Renderer e recebe
//  os eventos (mouse/teclado) do frame anterior. O backend é selecionado por
//  feature de build — a API não muda.
// =============================================================================

pub mod events;
pub mod renderer;

#[cfg(feature = "gtk4-backend")]
pub mod gtk4_backend;

#[cfg(feature = "gls-backend")]
pub mod gls_backend;

pub use events::Event;
pub use renderer::{Color, Rect, Renderer};

/// Executa o loop da UI com o backend disponível (Gtk4 por padrão).
///
/// `frame` é chamada a cada frame com o renderer e os eventos; retorne
/// `false` para encerrar. Retorna quando a janela é fechada.
#[cfg(feature = "gtk4-backend")]
pub fn run_ui<F>(title: &str, mut frame: F) -> Result<(), String>
where
    F: FnMut(&mut dyn Renderer, &[Event]) -> bool + 'static,
{
    gtk4_backend::run(title, move |r, ev| frame(r, ev))
}

/// Executa com o GLS Render (quando a feature gls-backend está ativa e o
/// Gtk4 não está).
#[cfg(all(feature = "gls-backend", not(feature = "gtk4-backend")))]
pub fn run_ui<F>(title: &str, frame: F) -> Result<(), String>
where
    F: FnMut(&mut dyn Renderer, &[Event]) -> bool + 'static,
{
    gls_backend::run(title, frame)
}
