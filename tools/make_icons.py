# -*- coding: utf-8 -*-
"""Generate the toolbar icon for the Dovetail add-in (standard library only)."""
import os
import math
import zlib
import struct

_HERE = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.environ.get('DOVETAIL_ADDIN_DIR') or os.path.join(
    os.path.dirname(_HERE), 'apps', 'desktop', 'Dovetail')
OUT = os.path.join(ADDIN, 'resources', 'Dovetail')

# Contours in normalised coordinates (0..1, y pointing up)
NOMINAL = [(0.06, 0.38), (0.36, 0.38), (0.28, 0.72), (0.72, 0.72),
           (0.64, 0.38), (0.94, 0.38)]
MATE = [(0.06, 0.32), (0.4357, 0.32), (0.3557, 0.66), (0.6443, 0.66),
        (0.5643, 0.32), (0.94, 0.32)]

DARK = (0x2E, 0x3A, 0x45)
ACCENT = (0xE8, 0x8A, 0x1E)

SS = 4  # supersampling factor


def dist_to_segment(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    length2 = vx * vx + vy * vy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / length2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def stroke_coverage(px, py, path, half_width):
    d = min(dist_to_segment(px, py, path[i][0], path[i][1],
                            path[i + 1][0], path[i + 1][1])
            for i in range(len(path) - 1))
    return 1.0 if d <= half_width else 0.0


def render(size):
    half_main = max(1.35, 0.062 * size) / 2.0
    half_mate = max(1.15, 0.048 * size) / 2.0
    scaled_nominal = [(a * size, b * size) for a, b in NOMINAL]
    scaled_mate = [(a * size, b * size) for a, b in MATE]
    buffer = bytearray(size * size * 4)

    for y in range(size):
        for x in range(size):
            hits_dark = hits_accent = 0
            for sy in range(SS):
                for sx in range(SS):
                    # image space has y pointing down, the contours point up
                    px = x + (sx + 0.5) / SS
                    py = size - (y + (sy + 0.5) / SS)
                    hits_dark += stroke_coverage(px, py, scaled_nominal, half_main)
                    hits_accent += stroke_coverage(px, py, scaled_mate, half_mate)

            samples = SS * SS
            alpha_dark = hits_dark / samples
            alpha_accent = (hits_accent / samples) * (1.0 - alpha_dark)
            alpha = alpha_dark + alpha_accent
            if alpha <= 0.0:
                continue
            r = (DARK[0] * alpha_dark + ACCENT[0] * alpha_accent) / alpha
            g = (DARK[1] * alpha_dark + ACCENT[1] * alpha_accent) / alpha
            b = (DARK[2] * alpha_dark + ACCENT[2] * alpha_accent) / alpha
            i = (y * size + x) * 4
            buffer[i] = int(round(r))
            buffer[i + 1] = int(round(g))
            buffer[i + 2] = int(round(b))
            buffer[i + 3] = int(round(alpha * 255))
    return bytes(buffer)


def write_png(path, size, rgba):
    raw = b''.join(b'\x00' + rgba[y * size * 4:(y + 1) * size * 4]
                   for y in range(size))

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as handle:
        handle.write(png)


def main():
    os.makedirs(OUT, exist_ok=True)
    for size in (16, 32, 64):
        path = os.path.join(OUT, '%dx%d.png' % (size, size))
        write_png(path, size, render(size))
        print('written:', path)


if __name__ == '__main__':
    main()
