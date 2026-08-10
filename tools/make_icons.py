# -*- coding: utf-8 -*-
"""Erzeugt die PNG-Icons fuer das Schwalbenschwanz-Add-In (nur stdlib)."""
import os
import math
import zlib
import struct

_HERE = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.environ.get('SS_ADDIN_DIR') or os.path.join(
    os.path.dirname(_HERE), 'Schwalbenschwanz')
OUT = os.path.join(ADDIN, 'resources', 'Schwalbenschwanz')

# Konturen in normierten Koordinaten (0..1, y nach oben)
NOMINAL = [(0.06, 0.38), (0.36, 0.38), (0.28, 0.72), (0.72, 0.72),
           (0.64, 0.38), (0.94, 0.38)]
MATE = [(0.06, 0.32), (0.4357, 0.32), (0.3557, 0.66), (0.6443, 0.66),
        (0.5643, 0.32), (0.94, 0.32)]

DARK = (0x2E, 0x3A, 0x45)
ACCENT = (0xE8, 0x8A, 0x1E)

SS = 4  # Supersampling


def dist_to_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    ln2 = vx * vx + vy * vy
    t = 0.0 if ln2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / ln2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def stroke_coverage(px, py, path, half_w):
    d = min(dist_to_seg(px, py, path[i][0], path[i][1],
                        path[i + 1][0], path[i + 1][1])
            for i in range(len(path) - 1))
    return 1.0 if d <= half_w else 0.0


def render(size):
    w_main = max(1.35, 0.062 * size) / 2.0
    w_mate = max(1.15, 0.048 * size) / 2.0
    buf = bytearray(size * size * 4)

    for y in range(size):
        for x in range(size):
            acc_d = acc_a = 0
            for sy in range(SS):
                for sx in range(SS):
                    px = x + (sx + 0.5) / SS
                    py = y + (sy + 0.5) / SS
                    # in Icon-Koordinaten: y nach oben
                    gx = px / size
                    gy = 1.0 - py / size
                    p = (gx * size, gy * size)
                    scaled_nom = [(a * size, b * size) for a, b in NOMINAL]
                    scaled_mate = [(a * size, b * size) for a, b in MATE]
                    acc_d += stroke_coverage(p[0], p[1], scaled_nom, w_main)
                    acc_a += stroke_coverage(p[0], p[1], scaled_mate, w_mate)
            n = SS * SS
            a_dark = acc_d / n
            a_acc = acc_a / n
            # dunkle Kontur liegt oben
            a_acc *= (1.0 - a_dark)
            alpha = a_dark + a_acc
            if alpha <= 0.0:
                continue
            r = (DARK[0] * a_dark + ACCENT[0] * a_acc) / alpha
            g = (DARK[1] * a_dark + ACCENT[1] * a_acc) / alpha
            b = (DARK[2] * a_dark + ACCENT[2] * a_acc) / alpha
            i = (y * size + x) * 4
            buf[i] = int(round(r))
            buf[i + 1] = int(round(g))
            buf[i + 2] = int(round(b))
            buf[i + 3] = int(round(alpha * 255))
    return bytes(buf)


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
    with open(path, 'wb') as fh:
        fh.write(png)


def main():
    os.makedirs(OUT, exist_ok=True)
    for size in (16, 32, 64):
        write_png(os.path.join(OUT, '%dx%d.png' % (size, size)), size,
                  render(size))
        print('geschrieben:', os.path.join(OUT, '%dx%d.png' % (size, size)))


if __name__ == '__main__':
    main()
