#!/usr/bin/env python3
# =============================================================================
#  gen-backgrounds.py — gera os PNGs de boot e login do Pineapple OS
#
#  Estilo Apple: fundo cinza-claro #c2bec2 + abacaxi de contorno no centro
#  (como a maçã no boot do macOS). O abacaxi é desenhado como contorno
#  #7a767a com o centro transparente (mostra a cor do fundo), com uma
#  mordida no lado direito e levemente inclinado.
#
#  Imagens geradas:
#    Installer/grub/theme/background.png     fundo #c2bec2 do GRUB (invisível)
#    Installer/plymouth/theme/background.png fundo #c2bec2 do boot
#    Installer/plymouth/theme/pineapple.png  abacaxi de contorno (RGBA)
#    Installer/sddm/theme/background.png     fundo escuro do login (fallback)
#    Installer/sddm/theme/avatar.png         avatar de usuário estilo macOS
#
#  Sem dependências externas (PNG escrito na mão com zlib).
# =============================================================================
import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
#  Helpers de PNG
# ---------------------------------------------------------------------------
def lerp(a, b, t):
    return int(a + (b - a) * t)


def write_png(path, width, height, pixel_fn):
    """Escreve um PNG RGB8. pixel_fn(t) -> (r, g, b), t = 0..1 (topo->base)."""
    rows = []
    for y in range(height):
        t = y / max(height - 1, 1)
        r, g, b = pixel_fn(t)
        row = b"\x00" + bytes((r, g, b) * width)
        rows.append(row)

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
    png += chunk(b"IEND", b"")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    print("gerado:", os.path.relpath(path, ROOT))


def write_rgba_png(path, width, height, pixel_fn):
    """Escreve um PNG RGBA8. pixel_fn(x, y) -> (r, g, b, a)."""
    rows = []
    for y in range(height):
        row = bytearray(b"\x00")
        for x in range(width):
            r, g, b, a = pixel_fn(x, y)
            row += bytes((r, g, b, a))
        rows.append(bytes(row))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
    png += chunk(b"IEND", b"")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    print("gerado:", os.path.relpath(path, ROOT))


# ---------------------------------------------------------------------------
#  Fundos (cor sólida #c2bec2)
# ---------------------------------------------------------------------------
BOOT_BG = (0xC2, 0xBE, 0xC2)   # fundo do boot/GRUB (estilo Apple)


def gradient_apple_boot(t):
    return BOOT_BG


def gradient_apple_grub(t):
    return BOOT_BG


def gradient_sddm(t):
    # Fundo do login: azul-ardósia profundo (fallback quando não há wallpaper).
    return (lerp(0x10, 0x18, t), lerp(0x18, 0x24, t), lerp(0x20, 0x32, t))


# ---------------------------------------------------------------------------
#  Logo do abacaxi (contorno estilo Apple, com mordida)
# ---------------------------------------------------------------------------
def dist_seg(px, py, ax, ay, bx, by):
    """Distância do ponto (px,py) ao segmento AB."""
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx * vx + vy * vy
    if vv == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    tt = max(0.0, min(1.0, (wx * vx + wy * vy) / vv))
    qx, qy = ax + tt * vx, ay + tt * vy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


def pineapple_logo(size=320, tilt=0.105, contour=(0x7A, 0x76, 0x7A)):
    """Renderiza o abacaxi de boot do Pineapple OS (PNG RGBA transparente).

    Desenhado como *contorno* (cor #7a767a) com o interior transparente — o
    fundo #c2bec2 aparece no centro —, com uma mordida no lado direito e
    leve inclinação, no mesmo espírito do logo de boot do macOS.

    Geometria virtual em um canvas de 1000x1000; o pixel final é calculado
    com supersampling 4x4 (anti-aliasing) e rotação aplicada sobre o centro.
    """
    S = 1000.0
    cx = cy = S / 2.0
    hw = 9.0                       # meia-largura do traço (unidades virtuais)

    # ---- corpo: elipse vertical (centro ligeiramente abaixo do canvas) ----
    b_cx, b_cy = cx, 600.0
    b_rx, b_ry = 185.0, 225.0      # topo=375, base=825

    # ---- mordida: círculo que corta a borda direita do corpo ----
    bite_cx = b_cx + 1.22 * b_rx
    bite_cy = b_cy + 0.02 * b_ry
    bite_r = 0.51 * b_rx

    # ---- coroa: folhas como triângulos finos (contorno) sobre o topo ----
    # (ápice, base-esquerda, base-direita)
    leaves = [
        ((cx - 80, 250), (cx - 72, 388), (cx - 50, 368)),
        ((cx - 42, 220), (cx - 36, 392), (cx - 12, 372)),
        ((cx + 0, 205), (cx - 12, 396), (cx + 12, 376)),
        ((cx + 42, 220), (cx + 14, 374), (cx + 36, 392)),
        ((cx + 80, 250), (cx + 50, 370), (cx + 72, 388)),
    ]

    # rotação do desenho (sample é rotacionado para avaliar a geometria)
    s, c = math.sin(tilt), math.cos(tilt)

    def _rot(x, y):
        dx, dy = x - cx, y - cy
        return (cx + dx * c + dy * s, cy - dx * s + dy * c)

    def _dist_ellipse(u, v):
        """Distância aproximada até a borda da elipse do corpo."""
        dx = (u - b_cx) / b_rx
        dy = (v - b_cy) / b_ry
        f = dx * dx + dy * dy - 1.0
        grad = 2.0 * math.hypot(dx / b_rx, dy / b_ry)
        return abs(f) / max(grad, 1e-9)

    def _dist_tri(u, v, tri):
        (ax, ay), (bx, by), (cx2, cy2) = tri
        return min(
            dist_seg(u, v, ax, ay, bx, by),
            dist_seg(u, v, bx, by, cx2, cy2),
            dist_seg(u, v, cx2, cy2, ax, ay),
        )

    def _stroke(u, v):
        """True se o ponto está sobre o contorno do abacaxi."""
        # corpo (ignorando a mordida)
        if 310 <= u <= 690 and 370 <= v <= 830:
            if _dist_ellipse(u, v) < hw:
                if math.hypot(u - bite_cx, v - bite_cy) >= bite_r:
                    return True
        # folhas (acima da metade do corpo)
        if v < 430:
            for tri in leaves:
                if _dist_tri(u, v, tri) < hw:
                    return True
        return False

    scale = S / float(size)

    def pixel(x, y):
        hits = 0
        for i in range(4):
            for j in range(4):
                px = (x + (i + 0.5) / 4.0) * scale
                py = (y + (j + 0.5) / 4.0) * scale
                u, v = _rot(px, py)
                if _stroke(u, v):
                    hits += 1
        a = round(hits * 255 / 16)
        if a == 0:
            return (0, 0, 0, 0)
        return (contour[0], contour[1], contour[2], a)

    return pixel


# ---------------------------------------------------------------------------
#  Avatar de usuário (estilo macOS)
# ---------------------------------------------------------------------------
def avatar(size=256):
    """Renderiza o avatar padrão estilo macOS: círculo + silhueta de pessoa."""
    c = size / 2.0

    def pixel(x, y):
        # círculo do avatar
        d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
        if d > c * 0.98:
            return (0, 0, 0, 0)
        # gradiente do círculo (azul-acinzentado claro)
        t = y / size
        r = lerp(0xC9, 0x8F, t)
        g = lerp(0xD1, 0x98, t)
        b = lerp(0xDD, 0xA5, t)
        # cabeça
        hd = ((x - c) ** 2 + (y - c * 0.38) ** 2) ** 0.5
        if hd < c * 0.13:
            return (0x3A, 0x40, 0x4C, 255)
        # ombros (meia elipse)
        dx = (x - c) / (c * 0.36)
        dy = (y - c * 0.88) / (c * 0.26)
        if y > c * 0.62 and dx * dx + dy * dy <= 1.0:
            return (0x3A, 0x40, 0x4C, 255)
        return (r, g, b, 255)

    return pixel


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    grub_dir = os.path.join(ROOT, "Installer", "grub", "theme")
    plymouth_dir = os.path.join(ROOT, "Installer", "plymouth", "theme")
    sddm_dir = os.path.join(ROOT, "Installer", "sddm", "theme")

    write_png(os.path.join(grub_dir, "background.png"), 1920, 1080, gradient_apple_grub)
    write_png(os.path.join(plymouth_dir, "background.png"), 1920, 1080, gradient_apple_boot)
    write_png(os.path.join(sddm_dir, "background.png"), 1920, 1080, gradient_sddm)

    write_rgba_png(
        os.path.join(plymouth_dir, "pineapple.png"),
        320, 320,
        pineapple_logo(320),
    )

    write_rgba_png(
        os.path.join(sddm_dir, "avatar.png"),
        256, 256,
        avatar(256),
    )