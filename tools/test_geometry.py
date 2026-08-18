# -*- coding: utf-8 -*-
"""Test the geometry maths and the language files without running Fusion."""
import os
import re
import sys
import math
import types
import xml.etree.ElementTree as ElementTree

# --- adsk stubs so the add-in can be imported outside of Fusion -------------
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
ADDIN = os.environ.get('DOVETAIL_ADDIN_DIR') or os.path.join(
    os.path.dirname(_HERE), 'Dovetail')
sys.path.insert(0, ADDIN)
import Dovetail as dt  # noqa: E402

MM = 0.1  # 1 mm expressed in cm, Fusion's internal unit
failures = []


def check(condition, message):
    if condition:
        print('  ok   ', message)
    else:
        print('  FAIL ', message)
        failures.append(message)


def expect_error(key, args, label):
    try:
        dt.build_contours(*args)
        check(False, '%s -> should have raised "%s"' % (label, key))
    except dt.GeometryError as err:
        check(err.key == key, '%s -> %s  "%s"' % (label, err.key, err))


def segment_directions(points):
    out = []
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        length = math.hypot(dx, dy)
        out.append((dx / length, dy / length))
    return out


def verify_offset(nominal, mate, tolerance):
    """Every mate segment must be parallel to its nominal segment and sit
    exactly the tolerance to the right of it."""
    dn = segment_directions(nominal)
    dm = segment_directions(mate)
    check(len(dn) == len(dm), 'same segment count (%d/%d)' % (len(dn), len(dm)))
    worst_parallel = worst_distance = 0.0
    for i in range(min(len(dn), len(dm))):
        worst_parallel = max(worst_parallel,
                             abs(dn[i][0] * dm[i][1] - dn[i][1] * dm[i][0]))
        ax, ay = nominal[i]
        r = (dn[i][1], -dn[i][0])
        vx, vy = mate[i][0] - ax, mate[i][1] - ay
        worst_distance = max(worst_distance, abs((vx * r[0] + vy * r[1]) - tolerance))
    check(worst_parallel < 1e-9,
          'all segments parallel (max cross product %.2e)' % worst_parallel)
    check(worst_distance < 1e-9,
          'offset equals the tolerance everywhere (max error %.2e cm)' % worst_distance)


def tooth_centres(nominal, count, shape):
    per_tooth = 3 if shape == dt.SHAPE_TRIANGLE else 4
    return [(nominal[1 + per_tooth * i][0] + nominal[per_tooth * i + per_tooth][0]) / 2.0
            for i in range(count)]


print('1) Trapezoid is the default shape')
check(dt._last[dt.IN_SHAPE] == dt.SHAPE_TRAPEZOID, 'default is trapezoid')
check((dt.SHAPE_TRAPEZOID, dt.SHAPE_TRIANGLE, dt.SHAPE_RECTANGLE) == (0, 1, 2),
      'drop-down order: trapezoid, triangle, rectangle')
check(len(dt.SHAPE_KEYS) == 3, 'three shapes with a text key')

print('2) Trapezoid 15 deg, 3 teeth, L=200mm W=12mm D=8mm spacing=25mm')
nominal, mate = dt.build_contours(200 * MM, 3, 25 * MM, 12 * MM, 8 * MM,
                                  math.radians(15), 0.25 * MM, dt.SHAPE_TRAPEZOID, 0.0, dt.REF_POCKET)
check(len(nominal) == 2 + 3 * 4, 'nominal contour has %d points (expected 14)' % len(nominal))
top_half = 6 * MM + 8 * MM * math.tan(math.radians(15))
check(abs((nominal[1][0] - nominal[2][0]) - (top_half - 6 * MM)) < 1e-12,
      'undercut present: tip %.3f mm wider per side' % ((top_half - 6 * MM) * 10))
centres = tooth_centres(nominal, 3, dt.SHAPE_TRAPEZOID)
check(all(abs((centres[i + 1] - centres[i]) - 25 * MM) < 1e-12 for i in range(2)),
      'centre to centre spacing is 25 mm')
check(abs(sum(centres) / 3 - 100 * MM) < 1e-12, 'group centred on the line')
verify_offset(nominal, mate, 0.25 * MM)

print('3) Triangle, 1 tooth, L=100mm W=10mm D=6mm tolerance=0.25mm')
nominal, mate = dt.build_contours(100 * MM, 1, 20 * MM, 10 * MM, 6 * MM,
                                  math.radians(15), 0.25 * MM, dt.SHAPE_TRIANGLE, 0.0, dt.REF_POCKET)
check(len(nominal) == 5, 'nominal contour has 5 points (%d)' % len(nominal))
check(abs(nominal[2][0] - 50 * MM) < 1e-12 and abs(nominal[2][1] - 6 * MM) < 1e-12,
      'tip centred at 50/6 mm')
check(abs(nominal[1][0] - 45 * MM) < 1e-12 and abs(nominal[3][0] - 55 * MM) < 1e-12,
      'base spans 45..55 mm (width 10 mm)')
check(all(abs(p[1] + 0.25 * MM) < 1e-12 for p in (mate[0], mate[-1])),
      'mate base line sits 0.25 mm below the line')
check(mate[2][1] < nominal[2][1], 'mate tip %.4f mm < nominal tip %.4f mm'
      % (mate[2][1] * 10, nominal[2][1] * 10))
verify_offset(nominal, mate, 0.25 * MM)

print('4) Rectangle (box joint), 4 teeth')
nominal, mate = dt.build_contours(200 * MM, 4, 30 * MM, 12 * MM, 8 * MM,
                                  math.radians(15), 0.25 * MM, dt.SHAPE_RECTANGLE, 0.0, dt.REF_POCKET)
check(len(nominal) == 2 + 4 * 4, 'nominal contour has %d points (expected 18)' % len(nominal))
check(abs(nominal[1][0] - nominal[2][0]) < 1e-12
      and abs(nominal[3][0] - nominal[4][0]) < 1e-12,
      'flanks exactly perpendicular, no undercut')
check(abs((nominal[3][0] - nominal[2][0]) - 12 * MM) < 1e-12,
      'tip width equals base width, 12 mm')
check(abs(nominal[2][1] - 8 * MM) < 1e-12, 'tip at the full depth of 8 mm')
check(abs(mate[1][0] - (nominal[1][0] + 0.25 * MM)) < 1e-12
      and abs(mate[2][1] - (8 * MM - 0.25 * MM)) < 1e-12,
      'pin is 0.25 mm smaller all round')
verify_offset(nominal, mate, 0.25 * MM)
check(abs(dt._top_half(12 * MM, 8 * MM, math.radians(80), dt.SHAPE_RECTANGLE)
          - 6 * MM) < 1e-12, 'flank angle is ignored for the rectangle')

print('5) Alignment: the group is always centred on the midpoint of the line')
length = 300 * MM
midpoint = length / 2
for count in (1, 2, 3, 4, 5):
    nominal, _ = dt.build_contours(length, count, 30 * MM, 10 * MM, 6 * MM, 0.0,
                                   0.25 * MM, dt.SHAPE_TRIANGLE, 0.0, dt.REF_POCKET)
    relative = [(x - midpoint) * 10
                for x in tooth_centres(nominal, count, dt.SHAPE_TRIANGLE)]
    check(abs(sum(relative)) < 1e-9,
          'n=%d: centre of gravity exactly on the midpoint' % count)
    if count % 2 == 1:
        check(any(abs(r) < 1e-9 for r in relative),
              'n=%d: a tooth sits on the midpoint  %s'
              % (count, [round(r, 3) for r in relative]))
    else:
        check(all(abs(r) > 1e-9 for r in relative),
              'n=%d: the gap sits on the midpoint  %s'
              % (count, [round(r, 3) for r in relative]))
    check(all(abs(relative[i] + relative[count - 1 - i]) < 1e-9 for i in range(count)),
          'n=%d: mirror symmetric about the midpoint' % count)

print('6) Offset (the left / right buttons)')
nominal, mate = dt.build_contours(length, 3, 30 * MM, 10 * MM, 6 * MM, 0.0,
                                  0.25 * MM, dt.SHAPE_TRIANGLE, reference=dt.REF_POCKET, offset=12 * MM)
check(abs(tooth_centres(nominal, 3, dt.SHAPE_TRIANGLE)[1] - (midpoint + 12 * MM)) < 1e-12,
      'offset of +12 mm moves the group')
check(abs(nominal[0][0]) < 1e-12 and abs(nominal[-1][0] - length) < 1e-12,
      'contour still starts and ends at the line ends')
verify_offset(nominal, mate, 0.25 * MM)
nominal_left, _ = dt.build_contours(length, 3, 30 * MM, 10 * MM, 6 * MM, 0.0,
                                    0.25 * MM, dt.SHAPE_TRIANGLE, reference=dt.REF_POCKET, offset=-12 * MM)
check(abs(tooth_centres(nominal_left, 3, dt.SHAPE_TRIANGLE)[1]
          - (midpoint - 12 * MM)) < 1e-12, 'offset of -12 mm moves the group')

limit = dt.max_offset(length, 3, 30 * MM, 10 * MM, 6 * MM, 0.0, dt.SHAPE_TRIANGLE)
check(abs(limit - (150 - 30 - 5) * MM) < 1e-12,
      'max_offset is 115 mm (%.3f mm)' % (limit * 10))
dt.build_contours(length, 3, 30 * MM, 10 * MM, 6 * MM, 0.0, 0.25 * MM,
                  dt.SHAPE_TRIANGLE, reference=dt.REF_POCKET, offset=limit)
check(True, 'an offset exactly at the limit is still valid')
expect_error('err.offset_range',
             (length, 3, 30 * MM, 10 * MM, 6 * MM, 0.0, 0.25 * MM,
              dt.SHAPE_TRIANGLE, limit + 0.1 * MM), 'beyond the limit')
limit_trapezoid = dt.max_offset(200 * MM, 1, 25 * MM, 12 * MM, 8 * MM,
                                math.radians(15), dt.SHAPE_TRAPEZOID)
check(abs(limit_trapezoid - (100 * MM - top_half)) < 1e-12,
      'max_offset uses the wide tip for the trapezoid (%.3f mm)' % (limit_trapezoid * 10))
limit_rectangle = dt.max_offset(200 * MM, 1, 25 * MM, 12 * MM, 8 * MM, 0.0,
                                dt.SHAPE_RECTANGLE)
check(abs(limit_rectangle - (100 - 6) * MM) < 1e-12,
      'max_offset for the rectangle is 94 mm')

print('7) Who pays for the clearance')
TOL = 0.25 * MM


def contours(reference):
    return dt.build_contours(100 * MM, 2, 30 * MM, 10 * MM, 6 * MM,
                             math.radians(15), TOL, dt.SHAPE_TRAPEZOID,
                             0.0, reference)


check(dt._last[dt.IN_REFERENCE] == dt.REF_CENTER,
      'the centred split is the default')
check(len(dt.REF_KEYS) == len(dt.REF_SPLIT) == 3, 'three entries with a text key')
for index, (grow, shrink) in enumerate(dt.REF_SPLIT):
    check(abs(grow + shrink - 1.0) < 1e-12,
          '%s: the two shares add up to the whole tolerance' % dt.REF_KEYS[index])

expected_base = {
    dt.REF_POCKET: (0.0, -TOL),         # line is the pocket, the pin gives way
    dt.REF_PIN: (TOL, 0.0),             # line is the pin, the pocket opens up
    dt.REF_CENTER: (TOL / 2, -TOL / 2),  # both give up half
}
for reference, (pocket_base, pin_base) in expected_base.items():
    pocket, pin = contours(reference)
    check(abs(pocket[0][1] - pocket_base) < 1e-12,
          '%s: pocket base at %+.3f mm' % (dt.REF_KEYS[reference], pocket[0][1] * 10))
    check(abs(pin[0][1] - pin_base) < 1e-12,
          '%s: pin base at %+.3f mm' % (dt.REF_KEYS[reference], pin[0][1] * 10))
    # Whatever the split, the gap between the two parts stays the tolerance.
    verify_offset(pocket, pin, TOL)

print('   the bug this fixes: two equal halves stay equal')
pocket, pin = contours(dt.REF_CENTER)
check(abs(pocket[0][1] + pin[0][1]) < 1e-12,
      'centred: the two bases are symmetric about the line (%+.4f / %+.4f mm)'
      % (pocket[0][1] * 10, pin[0][1] * 10))
pocket_off, pin_off = contours(dt.REF_POCKET)
check(abs(pocket_off[0][1]) < 1e-12 and abs(pin_off[0][1] + TOL) < 1e-12,
      'pocket edge: the whole 0.25 mm comes off the pin, as before this change')

print('   the two contours close into one band')
pocket, pin = contours(dt.REF_CENTER)
band = dt.closed_band(pocket, pin)
check(len(band) == len(pocket) + len(pin),
      'the band walks the pocket out and the pin back (%d points)' % len(band))
check(band[0] == pocket[0] and band[len(pocket) - 1] == pocket[-1],
      'first half is the pocket, in order')
check(band[len(pocket)] == pin[-1] and band[-1] == pin[0],
      'second half is the pin, reversed')
check(abs(band[len(pocket) - 1][0] - band[len(pocket)][0]) < 1e-12,
      'the far end cap is perpendicular to the line')
check(abs(band[-1][0] - band[0][0]) < 1e-12,
      'the near end cap is perpendicular to the line')
cap_far = abs(band[len(pocket) - 1][1] - band[len(pocket)][1])
cap_near = abs(band[-1][1] - band[0][1])
check(abs(cap_far - TOL) < 1e-12 and abs(cap_near - TOL) < 1e-12,
      'both caps are exactly the tolerance wide (%.3f / %.3f mm)'
      % (cap_far * 10, cap_near * 10))
check(len(set(band)) == len(band), 'no repeated point, so no zero-length segment')

print('   a tolerance of 0 has no band to enclose')
try:
    dt.build_contours(100 * MM, 1, 20 * MM, 10 * MM, 6 * MM,
                      math.radians(15), 0.0, dt.SHAPE_TRAPEZOID, 0.0, dt.REF_CENTER)
    check(False, 'tolerance 0 should have been refused')
except dt.GeometryError as err:
    check(err.key == 'err.tolerance_zero', 'tolerance 0 -> %s  "%s"' % (err.key, err))

print('8) Failures report the right key')
expect_error('err.spacing_too_small',
             (100 * MM, 3, 5 * MM, 12 * MM, 8 * MM, math.radians(15), 0.25 * MM,
              dt.SHAPE_TRAPEZOID), 'spacing too small')
expect_error('err.does_not_fit',
             (20 * MM, 3, 25 * MM, 12 * MM, 8 * MM, math.radians(15), 0.25 * MM,
              dt.SHAPE_TRIANGLE), 'wider than the line')
expect_error('err.tolerance_vs_width',
             (100 * MM, 1, 20 * MM, 10 * MM, 6 * MM, math.radians(15), 6 * MM,
              dt.SHAPE_TRIANGLE), 'tolerance too large')
expect_error('err.width',
             (100 * MM, 1, 20 * MM, 0.0, 6 * MM, math.radians(15), 0.25 * MM,
              dt.SHAPE_TRIANGLE), 'width of 0')
expect_error('err.depth',
             (100 * MM, 1, 20 * MM, 10 * MM, 0.0, math.radians(15), 0.25 * MM,
              dt.SHAPE_TRIANGLE), 'depth of 0')
expect_error('err.zero_length',
             (0.0, 1, 20 * MM, 10 * MM, 6 * MM, math.radians(15), 0.25 * MM,
              dt.SHAPE_TRIANGLE), 'line without length')
expect_error('err.tolerance_zero',
             (100 * MM, 1, 20 * MM, 10 * MM, 6 * MM, math.radians(15), -0.1 * MM,
              dt.SHAPE_TRIANGLE), 'negative tolerance')
expect_error('err.angle_range',
             (100 * MM, 1, 20 * MM, 10 * MM, 6 * MM, math.radians(89.9), 0.25 * MM,
              dt.SHAPE_TRAPEZOID), 'flank angle of 89.9 deg')
expect_error('err.angle_negative',
             (100 * MM, 1, 20 * MM, 10 * MM, 6 * MM, math.radians(-60), 0.25 * MM,
              dt.SHAPE_TRAPEZOID), 'flank angle of -60 deg')

print('10b) Every drop-down entry has a text of its own')
_en = ElementTree.parse(os.path.join(ADDIN, 'lang', 'en.xml')).getroot()
_en_keys = set(node.get('key') for node in _en.findall('string'))
for label, keys in (('shape', dt.SHAPE_KEYS), ('reference', dt.REF_KEYS)):
    missing = [k for k in keys if k not in _en_keys]
    check(not missing, '%s: all %d entries present%s'
          % (label, len(keys), '' if not missing else ' - missing %s' % missing))
for key in ('in.reference', 'reference.tooltip', 'construction.tooltip',
            'in.construction', 'err.tolerance_zero'):
    check(key in _en_keys, '%s present' % key)

print('11) Language files')
lang_dir = os.path.join(ADDIN, 'lang')
reference = {}
for node in ElementTree.parse(os.path.join(lang_dir, 'en.xml')).getroot().findall('string'):
    reference[node.get('key')] = node.text or ''
check(len(reference) > 30, 'en.xml holds %d keys' % len(reference))

for code in dt.SUPPORTED_LANGUAGES:
    path = os.path.join(lang_dir, '%s.xml' % code)
    check(os.path.isfile(path), '%s.xml exists' % code)
    root = ElementTree.parse(path).getroot()
    check(root.get('language') == code,
          '%s.xml declares language="%s"' % (code, code))
    strings = {}
    for node in root.findall('string'):
        strings[node.get('key')] = node.text or ''
    missing = sorted(set(reference) - set(strings))
    unknown = sorted(set(strings) - set(reference))
    check(not missing, '%s.xml complete%s'
          % (code, '' if not missing else ' - missing: %s' % missing))
    check(not unknown, '%s.xml has no unknown keys%s'
          % (code, '' if not unknown else ' - unknown: %s' % unknown))
    mismatched = [key for key in reference
                  if set(re.findall(r'\{\d+\}', reference[key]))
                  != set(re.findall(r'\{\d+\}', strings.get(key, '')))]
    check(not mismatched, '%s.xml keeps every placeholder%s'
          % (code, '' if not mismatched else ' - differing: %s' % mismatched))
    check(all(value.strip() for value in strings.values()),
          '%s.xml has no empty texts' % code)

print('12) Text catalogue and language detection')
for code in dt.SUPPORTED_LANGUAGES:
    dt.S.load(code)
    check(dt.S.code == code and dt.T('cmd.name') != 'cmd.name',
          '%s: cmd.name = "%s"' % (code, dt.T('cmd.name')))
dt.S.load('de')
check('115.00' in dt.T('err.offset_range', '115.00'), 'placeholders are filled in')
check(dt.S.load('klingon') == 'en', 'an unknown language falls back to English')
check(dt.T('does.not.exist') == 'does.not.exist',
      'a missing key returns the key itself')
dt.S.load('fr')
error = None
try:
    dt.build_contours(0.0, 1, 1.0, 1.0, 1.0, 0.0, 0.0, dt.SHAPE_TRAPEZOID, 0.0, dt.REF_POCKET)
except dt.GeometryError as exc:
    error = exc
check(error is not None and error.key == 'err.zero_length' and 'longueur' in str(error),
      'error messages follow the language: "%s"' % error)
check(dt.detect_language() in dt.SUPPORTED_LANGUAGES,
      'detect_language() returns "%s" without Fusion' % dt.detect_language())
dt.S.load('en')

print()
if failures:
    print('%d FAILURES' % len(failures))
    sys.exit(1)
print('all tests passed')
