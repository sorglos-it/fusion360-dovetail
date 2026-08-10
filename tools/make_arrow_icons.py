# -*- coding: utf-8 -*-
"""Generate the arrow icons for the move buttons (standard library only)."""
import os
import zlib
import struct

_HERE = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.environ.get('DOVETAIL_ADDIN_DIR') or os.path.join(
    os.path.dirname(_HERE), 'Dovetail')
BASE = os.path.join(ADDIN, 'resources')

DARK = (0x2E, 0x3A, 0x45)
SS = 4  # supersampling factor

# Polygons in normalised coordinates (0..1, y pointing up)
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


def point_in_polygon(x, y, polygon):
    inside = False
    count = len(polygon)
    j = count - 1
    for i in range(count):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y):
            crossing = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < crossing:
                inside = not inside
        j = i
    return inside


def render(polygons, size):
    buffer = bytearray(size * size * 4)
    for py in range(size):
        for px in range(size):
            hits = 0
            for sy in range(SS):
                for sx in range(SS):
                    gx = (px + (sx + 0.5) / SS) / size
                    gy = 1.0 - (py + (sy + 0.5) / SS) / size
                    if any(point_in_polygon(gx, gy, p) for p in polygons):
                        hits += 1
            if not hits:
                continue
            i = (py * size + px) * 4
            buffer[i] = DARK[0]
            buffer[i + 1] = DARK[1]
            buffer[i + 2] = DARK[2]
            buffer[i + 3] = int(round(255 * hits / (SS * SS)))
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
    for name, polygons in ICONS.items():
        folder = os.path.join(BASE, name)
        os.makedirs(folder, exist_ok=True)
        for size in (16, 32, 64):
            write_png(os.path.join(folder, '%dx%d.png' % (size, size)),
                      size, render(polygons, size))
        print('written:', folder)


if __name__ == '__main__':
    main()
