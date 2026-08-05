#!/usr/bin/env python3
# =============================================================================
#  gen-backgrounds.py — gera PNGs de fundo (GRUB/Plymouth) sem dependências
# =============================================================================
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lerp(a, b, t):
    return int(a + (b - a) * t)


def write_png(path, width, height, pixel_fn):
    """Escreve um PNG RGB8 com um gradiente vertical definido por pixel_fn(t)."""
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


def gradient_bottom(t):
    # #17181c (topo) -> #1d2a38 (base)
    return (lerp(0x17, 0x1D, t), lerp(0x18, 0x2A, t), lerp(0x1C, 0x38, t))


def gradient_top(t):
    # #101820 (topo) -> #16232e (base) — mais escuro para o Plymouth
    return (lerp(0x10, 0x16, t), lerp(0x18, 0x23, t), lerp(0x20, 0x2E, t))


def write_rgba_png(path, width, height, pixel_fn):
    """Escreve um PNG RGBA8 com pixel_fn(x, y) -> (r, g, b, a)."""
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


def mak_m_logo(size=200):
    """Renderiza a marca 'M' do Mak OS em PNG RGBA (fundo transparente)."""
    c = size / 2.0
    t = c / 2.6  # espessura das linhas

    def dist_seg(px, py, ax, ay, bx, by):
        vx, vy = bx - ax, by - ay
        wx, wy = px - ax, py - ay
        vv = vx * vx + vy * vy
        if vv == 0:
            return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        tt = max(0.0, min(1.0, (wx * vx + wy * vy) / vv))
        qx, qy = ax + tt * vx, ay + tt * vy
        return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5

    ring_r = c * 0.78
    thickness = t * 0.9

    def accent(y):
        tt = (y / size)
        return (lerp(0x4F, 0xE2, tt), lerp(0x9D, 0x77, tt), lerp(0xDE, 0x6F, tt))

    def pixel(x, y):
        d_center = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
        # anel externo + anel interno
        ring = abs(d_center - ring_r) < thickness
        ring2 = abs(d_center - c * 0.62) < thickness * 0.55
        # barras verticais do "M"
        bar1 = x > c - t * 1.3 and x < c - t * 0.3 and y > c * 0.3 and y < c * 1.7
        bar2 = x > c + t * 0.3 and x < c + t * 1.3 and y > c * 0.3 and y < c * 1.7
        # chevrons (segmentos)
        chev_t = t * 0.9
        seg1 = dist_seg(x, y, c - t, c * 0.3, c, c * 0.85) < chev_t
        seg2 = dist_seg(x, y, c, c * 0.85, c + t, c * 0.3) < chev_t
        seg3 = dist_seg(x, y, c - t, c * 1.7, c, c * 1.15) < chev_t
        seg4 = dist_seg(x, y, c, c * 1.15, c + t, c * 1.7) < chev_t

        if ring or ring2 or bar1 or bar2 or seg1 or seg2 or seg3 or seg4:
            r, g, b = accent(y)
            return (r, g, b, 255)
        return (0, 0, 0, 0)

    return pixel


def gradient_sddm(t):
    # mais profundo, com leve tom azulado para a tela de login
    return (lerp(0x10, 0x18, t), lerp(0x18, 0x24, t), lerp(0x20, 0x32, t))


if __name__ == "__main__":
    grub_dir = os.path.join(ROOT, "Installer", "grub", "theme")
    plymouth_dir = os.path.join(ROOT, "Installer", "plymouth", "theme")
    sddm_dir = os.path.join(ROOT, "Installer", "sddm", "theme")

    write_png(os.path.join(grub_dir, "background.png"), 1920, 1080, gradient_bottom)
    write_png(os.path.join(plymouth_dir, "background.png"), 1920, 1080, gradient_top)
    write_png(os.path.join(sddm_dir, "background.png"), 1920, 1080, gradient_sddm)
    write_rgba_png(
        os.path.join(plymouth_dir, "mak-m.png"),
        200, 200,
        mak_m_logo(200),
    )
