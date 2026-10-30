// =============================================================================
//  GLS Render — backend GPU próprio do Pineapple OS (orchard-render).
//
//  GLS (Graphics Layer System) foi projetado para superar o Metal da Apple:
//  wgpu (Vulkan/Metal/DX12/WebGPU) por baixo, pipeline próprio e API de
//  desenho imediato feita para a UI Pineapple. Texto rasterizado com a fonte
//  bitmap font8x8 (cada pixel do glifo vira um quad). Independente de GTK —
//  a UI final do sistema pode ser desenhada 100% por aqui.
// =============================================================================

use crate::events::Event;
use crate::renderer::{Color, Rect, Renderer};
use bytemuck::{Pod, Zeroable};
use font8x8::UnicodeFonts;
use std::sync::{Arc, Mutex};
use winit::application::ApplicationHandler;
use winit::dpi::LogicalSize;
use winit::event::{ElementState, MouseButton, WindowEvent};
use winit::event_loop::{ActiveEventLoop, EventLoop};
use winit::window::{Window, WindowId};

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct Vertex {
    pos: [f32; 2],
    color: [f32; 4],
}

struct GpuState {
    window: Arc<Window>,
    surface: wgpu::Surface<'static>,
    device: wgpu::Device,
    queue: wgpu::Queue,
    config: wgpu::SurfaceConfiguration,
    pipeline: wgpu::RenderPipeline,
    vbuf: wgpu::Buffer,
    bind: wgpu::BindGroup,
}

struct Shared {
    frame: Box<dyn FnMut(&mut dyn Renderer, &[Event]) -> bool>,
    events: Vec<Event>,
    mouse: (f64, f64),
    quit: bool,
}

struct App {
    shared: Arc<Mutex<Shared>>,
    gpu: Option<GpuState>,
    title: String,
}

impl App {
    fn new(title: String, shared: Arc<Mutex<Shared>>) -> Self {
        Self {
            shared,
            gpu: None,
            title,
        }
    }

    fn init_gpu(&mut self, event_loop: &ActiveEventLoop) {
        let window = Arc::new(
            event_loop
                .create_window(
                    Window::default_attributes()
                        .with_title(self.title.clone())
                        .with_inner_size(LogicalSize::new(1024.0, 640.0)),
                )
                .expect("criar janela"),
        );

        let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
            backends: wgpu::Backends::PRIMARY,
            ..Default::default()
        });
        let surface = instance
            .create_surface(window.clone())
            .expect("criar surface");
        let size = window.inner_size();

        let adapter = pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            compatible_surface: Some(&surface),
            force_fallback_adapter: false,
        }))
        .expect("adapter GPU");

        let (device, queue) = pollster::block_on(adapter.request_device(
            &wgpu::DeviceDescriptor {
                label: Some("gls-render"),
                required_features: wgpu::Features::empty(),
                required_limits: wgpu::Limits::default(),
                memory_hints: Default::default(),
            },
            None,
        ))
        .expect("device GPU");

        let caps = surface.get_capabilities(&adapter);
        let format = caps
            .formats
            .iter()
            .copied()
            .find(|f| f.is_srgb())
            .unwrap_or(caps.formats[0]);
        let config = wgpu::SurfaceConfiguration {
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            format,
            width: size.width.max(1),
            height: size.height.max(1),
            present_mode: wgpu::PresentMode::AutoVsync,
            alpha_mode: caps.alpha_modes[0],
            view_formats: vec![],
            desired_maximum_frame_latency: 2,
        };
        surface.configure(&device, &config);

        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("orchard-shader"),
            source: wgpu::ShaderSource::Wgsl(SHADER.into()),
        });

        let uniform = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("ortho"),
            contents: bytemuck::cast_slice(&ortho(config.width, config.height)),
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        });
        let bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("ortho-bind"),
            layout: &device
                .create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                    label: Some("layout"),
                    bind_group_layouts: &[&device.create_bind_group_layout(
                        &wgpu::BindGroupLayoutDescriptor {
                            label: Some("ortho-layout"),
                            entries: &[wgpu::BindGroupLayoutEntry {
                                binding: 0,
                                visibility: wgpu::ShaderStages::VERTEX,
                                ty: wgpu::BindingType::Buffer {
                                    ty: wgpu::BufferBindingType::Uniform,
                                    has_dynamic_offset: false,
                                    min_binding_size: None,
                                },
                                count: None,
                            }],
                        },
                    )],
                    push_constant_ranges: &[],
                }),
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: uniform.as_entire_binding(),
            }],
        });

        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("orchard-pipeline"),
            layout: Some(&device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("pl"),
                bind_group_layouts: &[bind.get_layout()],
                push_constant_ranges: &[],
            })),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: Some("vs"),
                compilation_options: Default::default(),
                buffers: &[wgpu::VertexBufferLayout {
                    array_stride: std::mem::size_of::<Vertex>() as wgpu::BufferAddress,
                    step_mode: wgpu::VertexStepMode::Vertex,
                    attributes: &wgpu::vertex_attr_array![0 => Float32x2, 1 => Float32x4],
                }],
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: Some("fs"),
                compilation_options: Default::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format,
                    blend: Some(wgpu::BlendState::ALPHA_BLENDING),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState::default(),
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
            cache: None,
        });

        let vbuf = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("verts"),
            size: 4 * 1024 * 1024,
            usage: wgpu::BufferUsages::VERTEX | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        self.gpu = Some(GpuState {
            window,
            surface,
            device,
            queue,
            config,
            pipeline,
            vbuf,
            bind,
        });
    }
}

/// Renderer imediato do GLS Render: acumula vértices e desenha no `present`.
struct GlsRenderer {
    width: f32,
    height: f32,
    verts: Vec<Vertex>,
    pending_present: bool,
}

impl GlsRenderer {
    fn push_quad(&mut self, x: f32, y: f32, w: f32, h: f32, c: Color) {
        let x0 = x;
        let y0 = y;
        let x1 = x + w;
        let y1 = y + h;
        let col = [c.r, c.g, c.b, c.a];
        let a = Vertex { pos: [x0, y0], color: col };
        let b = Vertex { pos: [x1, y0], color: col };
        let d = Vertex { pos: [x1, y1], color: col };
        let e = Vertex { pos: [x0, y1], color: col };
        // dois triângulos: a-b-d, a-d-e
        self.verts.extend_from_slice(&[a, b, d, a, d, e]);
    }
}

impl Renderer for GlsRenderer {
    fn width(&self) -> f32 {
        self.width
    }
    fn height(&self) -> f32 {
        self.height
    }

    fn clear(&mut self, color: Color) {
        self.verts.clear();
        self.push_quad(0.0, 0.0, self.width, self.height, color);
    }

    fn fill_rect(&mut self, rect: Rect, color: Color) {
        self.push_quad(rect.x, rect.y, rect.w, rect.h, color);
    }

    fn stroke_rect(&mut self, rect: Rect, color: Color, thickness: f32) {
        let t = thickness;
        self.push_quad(rect.x, rect.y, rect.w, t, color);
        self.push_quad(rect.x, rect.y + rect.h - t, rect.w, t, color);
        self.push_quad(rect.x, rect.y, t, rect.h, color);
        self.push_quad(rect.x + rect.w - t, rect.y, t, rect.h, color);
    }

    fn text(&mut self, x: f32, y: f32, size: f32, color: Color, content: &str) {
        let px = size / 8.0; // font8x8: 8x8 por glifo
        let fallback: &[u8; 8] = &[0; 8];
        let mut cx = x;
        for ch in content.chars() {
            let glyph = font8x8::BASIC_FONTS
                .get(ch)
                .or_else(|| font8x8::BASIC_FONTS.get('?'))
                .unwrap_or(fallback);
            for (row, bits) in glyph.iter().enumerate() {
                for col in 0..8u32 {
                    if bits & (1 << col) != 0 {
                        self.push_quad(
                            cx + col as f32 * px,
                            y + row as f32 * px,
                            px,
                            px,
                            color,
                        );
                    }
                }
            }
            cx += px * 8.0;
        }
    }

    fn text_width(&self, size: f32, content: &str) -> f32 {
        content.chars().count() as f32 * (size / 8.0) * 8.0
    }

    fn present(&mut self) {
        self.pending_present = true;
    }
}

/// Matriz ortográfica 3x2 (2D) coluna-maior para wgpu.
fn ortho(w: u32, h: u32) -> [[f32; 4]; 4] {
    let w = w as f32;
    let h = h as f32;
    [
        [2.0 / w, 0.0, 0.0, 0.0],
        [0.0, -2.0 / h, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [-1.0, 1.0, 0.0, 1.0],
    ]
}

const SHADER: &str = r#"
struct Uniforms { mvp: mat4x4<f32>, };
@group(0) @binding(0) var<uniform> u: Uniforms;

struct VsIn {
    @location(0) pos: vec2<f32>,
    @location(1) color: vec4<f32>,
};
struct VsOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) color: vec4<f32>,
};

@vertex
fn vs(in: VsIn) -> VsOut {
    var out: VsOut;
    out.clip = u.mvp * vec4<f32>(in.pos, 0.0, 1.0);
    out.color = in.color;
    return out;
}

@fragment
fn fs(in: VsOut) -> @location(0) vec4<f32> {
    return in.color;
}
"#;

impl ApplicationHandler for App {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        if self.gpu.is_none() {
            self.init_gpu(event_loop);
        }
    }

    fn window_event(
        &mut self,
        event_loop: &ActiveEventLoop,
        _id: WindowId,
        event: WindowEvent,
    ) {
        let Some(gpu) = self.gpu.as_ref() else { return };
        match event {
            WindowEvent::CloseRequested => event_loop.exit(),
            WindowEvent::Resized(size) => {
                gpu.surface.configure(
                    &gpu.device,
                    &wgpu::SurfaceConfiguration {
                        width: size.width.max(1),
                        height: size.height.max(1),
                        ..gpu.config.clone()
                    },
                );
                let mut sh = self.shared.lock().unwrap();
                sh.events.push(Event::Resize {
                    width: size.width,
                    height: size.height,
                });
            }
            WindowEvent::CursorMoved { position, .. } => {
                let mut sh = self.shared.lock().unwrap();
                sh.mouse = (position.x, position.y);
                sh.events.push(Event::MouseMove {
                    x: position.x,
                    y: position.y,
                });
            }
            WindowEvent::MouseInput { state, button, .. } => {
                let btn = match button {
                    MouseButton::Left => 1,
                    MouseButton::Right => 2,
                    MouseButton::Middle => 3,
                    _ => 0,
                };
                let (x, y) = self.shared.lock().unwrap().mouse;
                let ev = match state {
                    ElementState::Pressed => Event::MouseDown { x, y, button: btn },
                    ElementState::Released => Event::MouseUp { x, y, button: btn },
                };
                self.shared.lock().unwrap().events.push(ev);
            }
            WindowEvent::KeyboardInput { event: ke, .. } => {
                if let Some(txt) = ke.text.as_ref() {
                    let ev = Event::KeyDown {
                        key: txt.to_string(),
                        text: Some(txt.to_string()),
                    };
                    self.shared.lock().unwrap().events.push(ev);
                }
            }
            WindowEvent::RedrawRequested => {
                let mut sh = self.shared.lock().unwrap();
                let evs: Vec<Event> = sh.events.drain(..).collect();
                let (w, h) = (gpu.config.width as f32, gpu.config.height as f32);
                let mut renderer = GlsRenderer {
                    width: w,
                    height: h,
                    verts: Vec::with_capacity(4096),
                    pending_present: false,
                };
                let alive = (sh.frame)(&mut renderer, &evs);
                if !alive {
                    sh.quit = true;
                }
                drop(sh);

                if !renderer.verts.is_empty() {
                    let bytes: &[u8] = bytemuck::cast_slice(&renderer.verts);
                    let len = bytes.len().min(4 * 1024 * 1024) as u64;
                    gpu.queue
                        .write_buffer(&gpu.vbuf, 0, &bytes[..len as usize]);

                    let frame = match gpu.surface.get_current_texture() {
                        Ok(f) => f,
                        Err(_) => return,
                    };
                    let view = frame
                        .texture
                        .create_view(&wgpu::TextureViewDescriptor::default());
                    let mut enc = gpu
                        .device
                        .create_command_encoder(&wgpu::CommandEncoderDescriptor::default());
                    {
                        let mut pass = enc.begin_render_pass(&wgpu::RenderPassDescriptor {
                            label: Some("main"),
                            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                                view: &view,
                                resolve_target: None,
                                ops: wgpu::Operations {
                                    load: wgpu::LoadOp::Clear(wgpu::Color::BLACK),
                                    store: wgpu::StoreOp::Store,
                                },
                            })],
                            depth_stencil_attachment: None,
                            timestamp_writes: None,
                            occlusion_query_set: None,
                        });
                        pass.set_pipeline(&gpu.pipeline);
                        pass.set_bind_group(0, &gpu.bind, &[]);
                        pass.set_vertex_buffer(0, gpu.vbuf.slice(..));
                        pass.draw(0..renderer.verts.len() as u32, 0..1);
                    }
                    gpu.queue.submit(Some(enc.finish()));
                    frame.present();
                }
                gpu.window.request_redraw();
            }
            _ => {}
        }

        if self.shared.lock().unwrap().quit {
            event_loop.exit();
        }
    }

    fn about_to_wait(&mut self, _event_loop: &ActiveEventLoop) {
        if let Some(gpu) = self.gpu.as_ref() {
            {
                let mut sh = self.shared.lock().unwrap();
                sh.events.push(Event::Tick);
            }
            gpu.window.request_redraw();
        }
        if self.shared.lock().unwrap().quit {
            _event_loop.exit();
        }
    }
}

/// Roda a UI no GLS Render (renderer GPU próprio do Pineapple OS).
pub fn run<F>(title: &str, frame: F) -> Result<(), String>
where
    F: FnMut(&mut dyn Renderer, &[Event]) -> bool + 'static,
{
    let shared = Arc::new(Mutex::new(Shared {
        frame: Box::new(frame),
        events: Vec::new(),
        mouse: (0.0, 0.0),
        quit: false,
    }));
    let event_loop = EventLoop::new().map_err(|e| e.to_string())?;
    let mut app = App::new(title.to_string(), shared);
    event_loop
        .run_app(&mut app)
        .map_err(|e| e.to_string())?;
    Ok(())
}
