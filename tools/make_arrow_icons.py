# -*- coding: utf-8 -*-
"""Erzeugt die Pfeil-Icons fuer die Verschieben-Buttons (nur stdlib)."""
import os
import zlib
import struct

_HERE = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.environ.get('SS_ADDIN_DIR') or os.path.join(
    os.path.dirname(_HERE), 'Schwalbenschwanz')
BASE = os.path.join(ADDIN, 'resources')

DARK = (0x2E, 0x3A, 0x45)
SS = 4

# Polygone in normierten Koordinaten (0..1, y nach oben)
ICONS = {
    'nudge_left': [
        [(0.26, 0.50), (0.66, 0.82), (0.66, 0.18)],
        [(0.70, 0.18), (0.82, 0.18), (0.82, 0.82), (0.70, 0.82)],
    ],
    'nudge_right': [
        [(0.74, 0.50), (0.34, 0.82), (0.34, 0.18)],
        [(0.18, 0.18), (0.30, 0.18), (0.30, 0.82), (0.18, 0.82)],
    ],
    'nudge_center': [
        [(0.455, 0.10), (0.545, 0.10), (0.545, 0.90), (0.455, 0.90)],
        [(0.40, 0.50), (0.14, 0.76), (0.14, 0.24)],
        [(0.60, 0.50), (0.86, 0.76), (0.86, 0.24)],
    ],
}


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xc = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < xc:
                inside = not inside
        j = i
    return inside


def render(polys, size):
    buf = bytearray(size * size * 4)
    for py in range(size):
        for px in range(size):
            hits = 0
            for sy in range(SS):
                for sx in range(SS):
                    gx = (px + (sx + 0.5) / SS) / size
                    gy = 1.0 - (py + (sy + 0.5) / SS) / size
                    if any(point_in_poly(gx, gy, p) for p in polys):
                        hits += 1
            if not hits:
                continue
            i = (py * size + px) * 4
            buf[i] = DARK[0]
            buf[i + 1] = DARK[1]
            buf[i + 2] = DARK[2]
            buf[i + 3] = int(round(255 * hits / (SS * SS)))
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
    for name, polys in ICONS.items():
        folder = os.path.join(BASE, name)
        os.makedirs(folder, exist_ok=True)
        for size in (16, 32, 64):
            write_png(os.path.join(folder, '%dx%d.png' % (size, size)),
                      size, render(polys, size))
        print('geschrieben:', folder)


if __name__ == '__main__':
    main()
