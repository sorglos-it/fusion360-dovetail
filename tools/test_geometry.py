# -*- coding: utf-8 -*-
"""Testet Geometrie-Mathematik und Sprachdateien des Add-Ins ohne Fusion."""
import os
import re
import sys
import math
import types
import xml.etree.ElementTree as ET

# --- adsk-Stubs, damit das Modul ausserhalb von Fusion importierbar ist -----
adsk = types.ModuleType('adsk')
core = types.ModuleType('adsk.core')
fusion = types.ModuleType('adsk.fusion')
for name in ('CommandEventHandler', 'ValidateInputsEventHandler',
             'InputChangedEventHandler', 'CommandCreatedEventHandler'):
    setattr(core, name, type(name, (object,), {}))
adsk.core = core
adsk.fusion = fusion
sys.modules['adsk'] = adsk
sys.modules['adsk.core'] = core
sys.modules['adsk.fusion'] = fusion

_HERE = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.environ.get('SS_ADDIN_DIR') or os.path.join(
    os.path.dirname(_HERE), 'Schwalbenschwanz')
sys.path.insert(0, ADDIN)
import Schwalbenschwanz as ss  # noqa: E402

MM = 0.1  # 1 mm in cm
fails = []


def check(cond, msg):
    if cond:
        print('  ok   ', msg)
    else:
        print('  FAIL ', msg)
        fails.append(msg)


def expect_error(key, args, label):
    try:
        ss.build_contours(*args)
        check(False, '%s -> haette "%s" liefern muessen' % (label, key))
    except ss.GeometryError as err:
        check(err.key == key, '%s -> %s  "%s"' % (label, err.key, err))


def seg_dirs(pts):
    out = []
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        ln = math.hypot(dx, dy)
        out.append((dx / ln, dy / ln))
    return out


def verify_offset(nom, mate, tol):
    """Jedes Mate-Segment muss parallel zum Nenn-Segment und um tol nach
    rechts versetzt sein."""
    dn, dm = seg_dirs(nom), seg_dirs(mate)
    check(len(dn) == len(dm), 'gleiche Segmentanzahl (%d/%d)' % (len(dn), len(dm)))
    worst_par = worst_off = 0.0
    for i in range(min(len(dn), len(dm))):
        worst_par = max(worst_par, abs(dn[i][0] * dm[i][1] - dn[i][1] * dm[i][0]))
        ax, ay = nom[i]
        r = (dn[i][1], -dn[i][0])
        vx, vy = mate[i][0] - ax, mate[i][1] - ay
        worst_off = max(worst_off, abs((vx * r[0] + vy * r[1]) - tol))
    check(worst_par < 1e-9, 'alle Segmente parallel (max Kreuzprodukt %.2e)' % worst_par)
    check(worst_off < 1e-9, 'Versatz ueberall = Toleranz (max Abw. %.2e cm)' % worst_off)


def centers_of(nom, count, shape):
    per = 3 if shape == ss.SHAPE_TRIANGLE else 4
    return [(nom[1 + per * i][0] + nom[per * i + per][0]) / 2.0
            for i in range(count)]


print('1) Standardform ist Trapez')
check(ss._last[ss.IN_SHAPE] == ss.SHAPE_TRAPEZ, 'Voreinstellung = Trapez')
check((ss.SHAPE_TRAPEZ, ss.SHAPE_TRIANGLE, ss.SHAPE_RECT) == (0, 1, 2),
      'Reihenfolge im Dropdown: Trapez, Dreieck, Rechteck')
check(len(ss.SHAPE_KEYS) == 3, 'drei Formen mit Textschluessel')

print('2) Trapez 15 Grad, 3 Zaehne, L=200mm B=12mm T=8mm A=25mm')
nom, mate = ss.build_contours(200 * MM, 3, 25 * MM, 12 * MM, 8 * MM,
                              math.radians(15), 0.25 * MM, ss.SHAPE_TRAPEZ)
check(len(nom) == 2 + 3 * 4, 'Nennkontur hat %d Punkte (erwartet 14)' % len(nom))
top_half = 6 * MM + 8 * MM * math.tan(math.radians(15))
check(abs((nom[1][0] - nom[2][0]) - (top_half - 6 * MM)) < 1e-12,
      'Hinterschnitt vorhanden: Kopf %.3f mm breiter je Seite'
      % ((top_half - 6 * MM) * 10))
mids = centers_of(nom, 3, ss.SHAPE_TRAPEZ)
check(all(abs((mids[i + 1] - mids[i]) - 25 * MM) < 1e-12 for i in range(2)),
      'Abstand Mitte-Mitte = 25 mm')
check(abs(sum(mids) / 3 - 100 * MM) < 1e-12, 'Gruppe mittig auf der Linie')
verify_offset(nom, mate, 0.25 * MM)

print('3) Dreieck, 1 Zahn, L=100mm B=10mm T=6mm Tol=0,25mm')
nom, mate = ss.build_contours(100 * MM, 1, 20 * MM, 10 * MM, 6 * MM,
                              math.radians(15), 0.25 * MM, ss.SHAPE_TRIANGLE)
check(len(nom) == 5, 'Nennkontur hat 5 Punkte (%d)' % len(nom))
check(abs(nom[2][0] - 50 * MM) < 1e-12 and abs(nom[2][1] - 6 * MM) < 1e-12,
      'Spitze mittig bei 50/6 mm')
check(abs(nom[1][0] - 45 * MM) < 1e-12 and abs(nom[3][0] - 55 * MM) < 1e-12,
      'Basis 45..55 mm (Breite 10 mm)')
check(all(abs(p[1] + 0.25 * MM) < 1e-12 for p in (mate[0], mate[-1])),
      'Grundlinie der Gegenkontur liegt 0,25 mm unter der Linie')
check(mate[2][1] < nom[2][1], 'Gegen-Spitze %.4f mm < Nenn-Spitze %.4f mm'
      % (mate[2][1] * 10, nom[2][1] * 10))
verify_offset(nom, mate, 0.25 * MM)

print('4) Rechteck (Fingerzinken), 4 Zaehne')
nom, mate = ss.build_contours(200 * MM, 4, 30 * MM, 12 * MM, 8 * MM,
                              math.radians(15), 0.25 * MM, ss.SHAPE_RECT)
check(len(nom) == 2 + 4 * 4, 'Nennkontur hat %d Punkte (erwartet 18)' % len(nom))
check(abs(nom[1][0] - nom[2][0]) < 1e-12 and abs(nom[3][0] - nom[4][0]) < 1e-12,
      'Flanken exakt senkrecht, kein Hinterschnitt')
check(abs((nom[3][0] - nom[2][0]) - 12 * MM) < 1e-12,
      'Kopfbreite = Basisbreite = 12 mm')
check(abs(nom[2][1] - 8 * MM) < 1e-12, 'Kopf auf voller Tiefe 8 mm')
check(abs(mate[1][0] - (nom[1][0] + 0.25 * MM)) < 1e-12
      and abs(mate[2][1] - (8 * MM - 0.25 * MM)) < 1e-12,
      'Zapfen ringsum 0,25 mm kleiner')
verify_offset(nom, mate, 0.25 * MM)
check(abs(ss._top_half(12 * MM, 8 * MM, math.radians(80), ss.SHAPE_RECT)
          - 6 * MM) < 1e-12, 'Flankenwinkel wird beim Rechteck ignoriert')

print('5) Ausrichtung: Gruppe immer auf den Linienmittelpunkt zentriert')
L = 300 * MM
mid = L / 2
for cnt in (1, 2, 3, 4, 5):
    nom, _ = ss.build_contours(L, cnt, 30 * MM, 10 * MM, 6 * MM, 0.0,
                               0.25 * MM, ss.SHAPE_TRIANGLE)
    rel = [(x - mid) * 10 for x in centers_of(nom, cnt, ss.SHAPE_TRIANGLE)]
    check(abs(sum(rel)) < 1e-9, 'n=%d: Schwerpunkt exakt auf der Linienmitte' % cnt)
    if cnt % 2 == 1:
        check(any(abs(r) < 1e-9 for r in rel),
              'n=%d: ein Zahn genau auf der Mitte  %s' % (cnt, [round(r, 3) for r in rel]))
    else:
        check(all(abs(r) > 1e-9 for r in rel),
              'n=%d: Mitte liegt zwischen zwei Zaehnen  %s'
              % (cnt, [round(r, 3) for r in rel]))
    check(all(abs(rel[i] + rel[cnt - 1 - i]) < 1e-9 for i in range(cnt)),
          'n=%d: spiegelsymmetrisch zur Mitte' % cnt)

print('6) Verschiebung (Links-/Rechts-Buttons)')
nom, mate = ss.build_contours(L, 3, 30 * MM, 10 * MM, 6 * MM, 0.0,
                              0.25 * MM, ss.SHAPE_TRIANGLE, shift=12 * MM)
check(abs(centers_of(nom, 3, ss.SHAPE_TRIANGLE)[1] - (mid + 12 * MM)) < 1e-12,
      'Verschiebung +12 mm wandert mit')
check(abs(nom[0][0]) < 1e-12 and abs(nom[-1][0] - L) < 1e-12,
      'Kontur beginnt/endet weiterhin an den Linienenden')
verify_offset(nom, mate, 0.25 * MM)
nom_l, _ = ss.build_contours(L, 3, 30 * MM, 10 * MM, 6 * MM, 0.0,
                             0.25 * MM, ss.SHAPE_TRIANGLE, shift=-12 * MM)
check(abs(centers_of(nom_l, 3, ss.SHAPE_TRIANGLE)[1] - (mid - 12 * MM)) < 1e-12,
      'Verschiebung -12 mm wandert mit')

ms = ss.max_shift(L, 3, 30 * MM, 10 * MM, 6 * MM, 0.0, ss.SHAPE_TRIANGLE)
check(abs(ms - (150 - 30 - 5) * MM) < 1e-12, 'max_shift = 115 mm (%.3f mm)' % (ms * 10))
ss.build_contours(L, 3, 30 * MM, 10 * MM, 6 * MM, 0.0, 0.25 * MM,
                  ss.SHAPE_TRIANGLE, shift=ms)
check(True, 'Verschiebung genau am Limit ist noch gueltig')
expect_error('err.shift_range',
             (L, 3, 30 * MM, 10 * MM, 6 * MM, 0.0, 0.25 * MM,
              ss.SHAPE_TRIANGLE, ms + 0.1 * MM), 'ueber dem Limit')
ms_trap = ss.max_shift(200 * MM, 1, 25 * MM, 12 * MM, 8 * MM,
                       math.radians(15), ss.SHAPE_TRAPEZ)
check(abs(ms_trap - (100 * MM - top_half)) < 1e-12,
      'max_shift beim Trapez rechnet mit der breiten Kopfseite (%.3f mm)'
      % (ms_trap * 10))
ms_rect = ss.max_shift(200 * MM, 1, 25 * MM, 12 * MM, 8 * MM, 0.0, ss.SHAPE_RECT)
check(abs(ms_rect - (100 - 6) * MM) < 1e-12, 'max_shift beim Rechteck = 94 mm')

print('7) Fehlerfaelle liefern den richtigen Schluessel')
expect_error('err.spacing_small', (100 * MM, 3, 5 * MM, 12 * MM, 8 * MM,
                                   math.radians(15), 0.25 * MM, ss.SHAPE_TRAPEZ),
             'Abstand zu klein')
expect_error('err.too_long', (20 * MM, 3, 25 * MM, 12 * MM, 8 * MM,
                              math.radians(15), 0.25 * MM, ss.SHAPE_TRIANGLE),
             'breiter als Linie')
expect_error('err.tol_width', (100 * MM, 1, 20 * MM, 10 * MM, 6 * MM,
                               math.radians(15), 6 * MM, ss.SHAPE_TRIANGLE),
             'Toleranz zu gross')
expect_error('err.width', (100 * MM, 1, 20 * MM, 0.0, 6 * MM,
                           math.radians(15), 0.25 * MM, ss.SHAPE_TRIANGLE),
             'Breite 0')
expect_error('err.depth', (100 * MM, 1, 20 * MM, 10 * MM, 0.0,
                           math.radians(15), 0.25 * MM, ss.SHAPE_TRIANGLE),
             'Tiefe 0')
expect_error('err.no_length', (0.0, 1, 20 * MM, 10 * MM, 6 * MM,
                               math.radians(15), 0.25 * MM, ss.SHAPE_TRIANGLE),
             'Linie ohne Laenge')
expect_error('err.tol_neg', (100 * MM, 1, 20 * MM, 10 * MM, 6 * MM,
                             math.radians(15), -0.1 * MM, ss.SHAPE_TRIANGLE),
             'negative Toleranz')
expect_error('err.angle_range', (100 * MM, 1, 20 * MM, 10 * MM, 6 * MM,
                                 math.radians(89.9), 0.25 * MM, ss.SHAPE_TRAPEZ),
             'Flankenwinkel 89,9 Grad')
expect_error('err.angle_neg', (100 * MM, 1, 20 * MM, 10 * MM, 6 * MM,
                               math.radians(-60), 0.25 * MM, ss.SHAPE_TRAPEZ),
             'Flankenwinkel -60 Grad')

print('8) Toleranz 0 liefert nur die Nennkontur')
_n0, m0 = ss.build_contours(100 * MM, 1, 20 * MM, 10 * MM, 6 * MM,
                            math.radians(15), 0.0, ss.SHAPE_TRIANGLE)
check(m0 is None, 'keine Gegenkontur bei Toleranz 0')

print('9) Zahnkonturen ohne Grundstuecke (Modus "Linie behalten")')
nom, _ = ss.build_contours(200 * MM, 3, 25 * MM, 12 * MM, 8 * MM,
                           math.radians(15), 0.25 * MM, ss.SHAPE_TRAPEZ)
chunks = ss._tooth_segments(nom)
check(len(chunks) == 3 and all(len(c) == 4 for c in chunks),
      '3 Trapezzaehne mit je 4 Punkten')
nom_t, _ = ss.build_contours(100 * MM, 2, 30 * MM, 10 * MM, 6 * MM, 0.0,
                             0.25 * MM, ss.SHAPE_TRIANGLE)
check(len(ss._tooth_segments(nom_t)) == 2
      and all(len(c) == 3 for c in ss._tooth_segments(nom_t)),
      '2 Dreieckszaehne mit je 3 Punkten')

print('10) Sprachdateien')
lang_dir = os.path.join(ADDIN, 'lang')
en_path = os.path.join(lang_dir, 'en.xml')
en_keys = {}
for node in ET.parse(en_path).getroot().findall('string'):
    en_keys[node.get('key')] = node.text or ''
check(len(en_keys) > 30, 'en.xml enthaelt %d Schluessel' % len(en_keys))

for code in ss.SUPPORTED_LANGUAGES:
    path = os.path.join(lang_dir, '%s.xml' % code)
    check(os.path.isfile(path), '%s.xml vorhanden' % code)
    root = ET.parse(path).getroot()
    check(root.get('language') == code, '%s.xml deklariert language="%s"' % (code, code))
    keys = {}
    for node in root.findall('string'):
        keys[node.get('key')] = node.text or ''
    missing = sorted(set(en_keys) - set(keys))
    extra = sorted(set(keys) - set(en_keys))
    check(not missing, '%s.xml vollstaendig%s'
          % (code, '' if not missing else ' - fehlt: %s' % missing))
    check(not extra, '%s.xml ohne unbekannte Schluessel%s'
          % (code, '' if not extra else ' - unbekannt: %s' % extra))
    bad = [k for k in en_keys
           if set(re.findall(r'\{\d+\}', en_keys[k])) != set(re.findall(r'\{\d+\}', keys.get(k, '')))]
    check(not bad, '%s.xml mit passenden Platzhaltern%s'
          % (code, '' if not bad else ' - abweichend: %s' % bad))
    check(all(v.strip() for v in keys.values()), '%s.xml ohne leere Texte' % code)

print('11) Textkatalog und Spracherkennung')
for code in ss.SUPPORTED_LANGUAGES:
    ss.S.load(code)
    check(ss.S.code == code and ss.T('cmd.name') != 'cmd.name',
          '%s: cmd.name = "%s"' % (code, ss.T('cmd.name')))
ss.S.load('de')
check('115.00' in ss.T('err.shift_range', '115.00'), 'Platzhalter wird gefuellt')
check(ss.S.load('klingon') == 'en', 'unbekannte Sprache faellt auf Englisch zurueck')
check(ss.T('gibt.es.nicht') == 'gibt.es.nicht', 'fehlender Schluessel liefert den Schluessel')
ss.S.load('fr')
err = None
try:
    ss.build_contours(0.0, 1, 1.0, 1.0, 1.0, 0.0, 0.0, ss.SHAPE_TRAPEZ)
except ss.GeometryError as exc:
    err = exc
check(err is not None and err.key == 'err.no_length' and 'longueur' in str(err),
      'Fehlermeldung folgt der Sprache: "%s"' % err)
check(ss.detect_language() in ss.SUPPORTED_LANGUAGES,
      'detect_language() liefert ohne Fusion "%s"' % ss.detect_language())
ss.S.load('en')

print()
if fails:
    print('%d FEHLER' % len(fails))
    sys.exit(1)
print('alle Tests bestanden')
