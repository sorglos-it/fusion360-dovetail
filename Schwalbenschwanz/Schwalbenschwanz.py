# -*- coding: utf-8 -*-
"""
Schwalbenschwanz / Dovetail - Fusion 360 Add-In

Erzeugt aus einer gewaehlten Skizzenlinie eine Verzahnung: eine Nennkontur
(Tasche / Negativ) direkt auf der Linie und eine um die Toleranz verkleinerte
Gegenkontur (Zapfen / Positiv) darin.

Die Oberflaeche folgt der in Fusion eingestellten Sprache. Die Texte liegen
in lang/<code>.xml, fehlende Schluessel fallen auf lang/en.xml zurueck.
"""

import os
import math
import traceback
import xml.etree.ElementTree as ElementTree

import adsk.core
import adsk.fusion

CMD_ID = 'thwSchwalbenschwanzCmd'

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_IDS = ('SketchCreatePanel', 'SketchModifyPanel', 'SolidCreatePanel')

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_APP_DIR, 'resources')
LANG_DIR = os.path.join(_APP_DIR, 'lang')
RESOURCE_FOLDER = os.path.join(_RES, 'Schwalbenschwanz')
ICON_LEFT = os.path.join(_RES, 'nudge_left')
ICON_CENTER = os.path.join(_RES, 'nudge_center')
ICON_RIGHT = os.path.join(_RES, 'nudge_right')

FALLBACK_LANGUAGE = 'en'
SUPPORTED_LANGUAGES = ('de', 'en', 'es', 'fr', 'it')

# Fusion-Spracheinstellung -> Sprachcode. Namen werden per getattr geholt,
# damit ein in dieser Fusion-Version unbekannter Wert nichts kaputt macht.
FUSION_LANGUAGE_MAP = {
    'GermanLanguage': 'de',
    'EnglishLanguage': 'en',
    'SpanishLanguage': 'es',
    'FrenchLanguage': 'fr',
    'ItalianLanguage': 'it',
}

# Eingabe-IDs
IN_LINE = 'ssLine'
IN_COUNT = 'ssCount'
IN_SHAPE = 'ssShape'
IN_WIDTH = 'ssWidth'
IN_DEPTH = 'ssDepth'
IN_ANGLE = 'ssAngle'
IN_SPACING = 'ssSpacing'
IN_SHIFT = 'ssShift'
IN_STEP = 'ssStep'
IN_NUDGE = 'ssNudge'
IN_TOL = 'ssTol'
IN_FLIP = 'ssFlip'
IN_REPLACE = 'ssReplace'
IN_MATE = 'ssMate'

# Formen. Die Reihenfolge ist zugleich die Reihenfolge im Dropdown, der
# gespeicherte Wert ist der Index - unabhaengig von der Sprache.
SHAPE_TRAPEZ = 0
SHAPE_TRIANGLE = 1
SHAPE_RECT = 2
SHAPE_KEYS = ('shape.trapez', 'shape.triangle', 'shape.rect')

NUDGE_LEFT = 0
NUDGE_CENTER = 1
NUDGE_RIGHT = 2

EPS = 1e-9
MAX_FLANK_ANGLE = math.radians(89.0)

_handlers = []
_control = None
_updating = False       # Re-Entrancy-Schutz fuer inputChanged

# Zuletzt benutzte Werte (bleiben innerhalb der Fusion-Sitzung erhalten).
# Laengen in cm (Fusion-Innenmass), Winkel in Radiant.
# Die Verschiebung wird bewusst NICHT gemerkt - sie gehoert zur jeweiligen Linie.
_last = {
    IN_COUNT: 1,
    IN_SHAPE: SHAPE_TRAPEZ,
    IN_WIDTH: 1.0,          # 10 mm
    IN_DEPTH: 0.6,          # 6 mm
    IN_ANGLE: math.radians(15.0),
    IN_SPACING: 2.0,        # 20 mm
    IN_STEP: 0.1,           # 1 mm
    IN_TOL: 0.025,          # 0,25 mm
    IN_FLIP: False,
    IN_REPLACE: True,
    IN_MATE: True,
}


# ------------------------------------------------------------------ Sprache --

class Strings(object):
    """Textkatalog aus lang/<code>.xml mit Rueckfall auf Englisch."""

    def __init__(self):
        self.code = FALLBACK_LANGUAGE
        self._current = {}
        self._fallback = {}

    @staticmethod
    def _read(code):
        path = os.path.join(LANG_DIR, '%s.xml' % code)
        if not os.path.isfile(path):
            return {}
        try:
            root = ElementTree.parse(path).getroot()
        except Exception:
            return {}
        out = {}
        for node in root.findall('string'):
            key = node.get('key')
            if key:
                out[key] = node.text or ''
        return out

    def load(self, code):
        if code not in SUPPORTED_LANGUAGES:
            code = FALLBACK_LANGUAGE
        if not self._fallback:
            self._fallback = self._read(FALLBACK_LANGUAGE)
        self._current = self._fallback if code == FALLBACK_LANGUAGE else self._read(code)
        self.code = code
        return self.code

    def get(self, key, *args):
        text = self._current.get(key) or self._fallback.get(key) or key
        if args:
            try:
                return text.format(*args)
            except (IndexError, KeyError, ValueError):
                return text
        return text


S = Strings()


def T(key, *args):
    return S.get(key, *args)


def detect_language():
    """Sprachcode aus der Fusion-Einstellung, sonst aus dem Betriebssystem."""
    try:
        prefs = adsk.core.Application.get().preferences.generalPreferences
        current = prefs.userLanguage
        languages = adsk.core.UserLanguages
        for name, code in FUSION_LANGUAGE_MAP.items():
            value = getattr(languages, name, None)
            if value is not None and current == value:
                return code
    except Exception:
        pass

    for env in ('LANG', 'LANGUAGE', 'LC_ALL'):
        value = os.environ.get(env) or ''
        code = value.replace('-', '_').split('_')[0].lower()
        if code in SUPPORTED_LANGUAGES:
            return code
    try:
        import locale
        value = locale.getdefaultlocale()[0] or ''
        code = value.replace('-', '_').split('_')[0].lower()
        if code in SUPPORTED_LANGUAGES:
            return code
    except Exception:
        pass
    return FALLBACK_LANGUAGE


S.load(FALLBACK_LANGUAGE)


# ---------------------------------------------------------------- Geometrie --

class GeometryError(Exception):
    """Eingaben ergeben keine sinnvolle Geometrie.

    key haelt den sprachunabhaengigen Grund fest, die Meldung selbst kommt
    uebersetzt aus dem Textkatalog.
    """

    def __init__(self, key, *args):
        self.key = key
        self.params = args
        super(GeometryError, self).__init__(T(key, *args))


def _line_intersection(p, d, q, e):
    """Schnittpunkt der Geraden (p + t*d) und (q + s*e). None wenn parallel."""
    denom = d[0] * e[1] - d[1] * e[0]
    if abs(denom) < 1e-12:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / denom
    return (p[0] + d[0] * t, p[1] + d[1] * t)


def _dedupe(points):
    out = [points[0]]
    for p in points[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-7:
            out.append(p)
    return out


def _offset_polyline(points, dist):
    """Versetzt einen offenen Polygonzug um dist nach rechts (Blickrichtung
    entlang des Zuges). Gehrungsecken durch Schnitt der versetzten Segmente."""
    pts = _dedupe(points)
    if len(pts) < 2:
        raise GeometryError('err.degenerate')

    segs = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        d = (dx / ln, dy / ln)
        r = (d[1], -d[0])                     # Rechts-Normale
        segs.append(((a[0] + r[0] * dist, a[1] + r[1] * dist), d, r))

    out = [segs[0][0]]
    for i in range(len(segs) - 1):
        p, d, r = segs[i]
        q, e, _ = segs[i + 1]
        ip = _line_intersection(p, d, q, e)
        vtx = pts[i + 1]
        if ip is None:
            ip = (vtx[0] + r[0] * dist, vtx[1] + r[1] * dist)
        elif math.hypot(ip[0] - vtx[0], ip[1] - vtx[1]) > abs(dist) * 12.0 + 1e-6:
            raise GeometryError('err.miter')
        out.append(ip)

    _p_end, d_end, r_end = segs[-1]
    end = pts[-1]
    out.append((end[0] + r_end[0] * dist, end[1] + r_end[1] * dist))
    return out


def _top_half(width, depth, angle, shape):
    """Halbe Kopfbreite des Zahns.

    Rechteck  -> gleich der halben Basis (gerader Zapfen)
    Dreieck   -> 0, der Zahn laeuft auf eine Spitze zu
    Trapez    -> weitet sich mit dem Flankenwinkel auf (Hinterschnitt)
    """
    half = width / 2.0
    if shape == SHAPE_RECT:
        return half
    if shape == SHAPE_TRIANGLE:
        return 0.0
    if abs(angle) >= MAX_FLANK_ANGLE:
        raise GeometryError('err.angle_range')
    th = half + depth * math.tan(angle)
    if th <= EPS:
        raise GeometryError('err.angle_neg')
    return th


def max_shift(length, count, spacing, width, depth, angle, shape):
    """Groesstmoegliche Verschiebung, bei der die Verzahnung noch komplett
    auf der Linie liegt. 0.0 wenn sie ohnehin nicht passt."""
    try:
        th = _top_half(width, depth, angle, shape)
    except GeometryError:
        return 0.0
    outer = max(width / 2.0, th)
    span = (max(count, 1) - 1) / 2.0 * spacing + outer
    return max(0.0, length / 2.0 - span)


def build_contours(length, count, spacing, width, depth, angle, tol, shape,
                   shift=0.0):
    """Baut Nenn- und Toleranzkontur in lokalen Koordinaten (s entlang der
    Linie ab Startpunkt, h senkrecht dazu in Zahnrichtung)."""
    if length <= EPS:
        raise GeometryError('err.no_length')
    if width <= EPS:
        raise GeometryError('err.width')
    if depth <= EPS:
        raise GeometryError('err.depth')
    if tol < 0:
        raise GeometryError('err.tol_neg')
    if count < 1:
        raise GeometryError('err.count')

    half = width / 2.0
    top_half = _top_half(width, depth, angle, shape)
    outer = max(half, top_half)

    # Mittenpositionen, symmetrisch um die Linienmitte plus Verschiebung
    centers = [length / 2.0 + shift + (i - (count - 1) / 2.0) * spacing
               for i in range(count)]

    if count > 1:
        if spacing <= EPS:
            raise GeometryError('err.spacing_pos')
        if spacing < 2 * outer + 2 * tol:
            raise GeometryError('err.spacing_small',
                                '%.2f' % ((2 * outer + 2 * tol) * 10.0))
    if centers[0] - outer < -EPS or centers[-1] + outer > length + EPS:
        ms = max_shift(length, count, spacing, width, depth, angle, shape)
        if ms > EPS and abs(shift) > ms:
            raise GeometryError('err.shift_range', '%.2f' % (ms * 10.0))
        raise GeometryError('err.too_long', '%.2f' % (length * 10.0))

    nominal = [(0.0, 0.0)]
    for sc in centers:
        nominal.append((sc - half, 0.0))
        if top_half <= EPS:
            nominal.append((sc, depth))
        else:
            nominal.append((sc - top_half, depth))
            nominal.append((sc + top_half, depth))
        nominal.append((sc + half, 0.0))
    nominal.append((length, 0.0))

    if tol <= EPS:
        return nominal, None

    mate = _offset_polyline(nominal, tol)

    # Plausibilitaet: der Zahn muss ueber der versetzten Grundlinie (h = -tol)
    # noch stehen bleiben und darf sich nicht selbst durchdringen.
    peak = max(p[1] for p in mate)
    if peak <= -tol + EPS:
        raise GeometryError('err.tol_eats')
    if (peak + tol) < 0.05 * depth:
        raise GeometryError('err.tol_depth')
    if 2 * tol >= width:
        raise GeometryError('err.tol_width')

    return nominal, mate


# ------------------------------------------------------------------ Zeichnen --

def _to_world(pt, origin, u, n):
    return adsk.core.Point3D.create(
        origin[0] + u[0] * pt[0] + n[0] * pt[1],
        origin[1] + u[1] * pt[0] + n[1] * pt[1],
        0.0)


def _draw_polyline(sketch, points, origin, u, n):
    lines = sketch.sketchCurves.sketchLines
    prev = None
    for i in range(len(points) - 1):
        p_end = _to_world(points[i + 1], origin, u, n)
        if prev is None:
            prev = lines.addByTwoPoints(_to_world(points[i], origin, u, n), p_end)
        else:
            prev = lines.addByTwoPoints(prev.endSketchPoint, p_end)


def _tooth_segments(points):
    """Nur die Zahnkonturen ohne die auf der Linie liegenden Grundstuecke."""
    chunks = []
    current = []
    for p in points:
        if abs(p[1]) <= EPS:
            if current:
                current.append(p)
                chunks.append(current)
                current = []
            current = [p]
        else:
            current.append(p)
    return [c for c in chunks if len(c) > 2]


def line_length(line):
    p0 = line.startSketchPoint.geometry
    p1 = line.endSketchPoint.geometry
    return math.hypot(p1.x - p0.x, p1.y - p0.y)


def create_geometry(line, count, spacing, width, depth, angle, tol, flip,
                    shape, shift, replace_line, make_mate, delete_original):
    sketch = line.parentSketch
    p0 = line.startSketchPoint.geometry
    p1 = line.endSketchPoint.geometry
    origin = (p0.x, p0.y)
    dx, dy = p1.x - p0.x, p1.y - p0.y
    length = math.hypot(dx, dy)
    if length <= EPS:
        raise GeometryError('err.no_length')

    u = (dx / length, dy / length)
    n = (-u[1], u[0])
    if flip:
        n = (-n[0], -n[1])

    nominal, mate = build_contours(length, count, spacing, width, depth,
                                   angle, tol, shape, shift)

    sketch.isComputeDeferred = True
    try:
        if replace_line:
            if delete_original:
                line.deleteMe()
            _draw_polyline(sketch, nominal, origin, u, n)
        else:
            for chunk in _tooth_segments(nominal):
                _draw_polyline(sketch, chunk, origin, u, n)

        if make_mate and mate:
            _draw_polyline(sketch, mate, origin, u, n)
    finally:
        sketch.isComputeDeferred = False


# ------------------------------------------------------------------ Handlers --

def _read_inputs(inputs):
    shape_item = inputs.itemById(IN_SHAPE).selectedItem
    return dict(
        count=inputs.itemById(IN_COUNT).value,
        shape=shape_item.index if shape_item else SHAPE_TRAPEZ,
        width=inputs.itemById(IN_WIDTH).value,
        depth=inputs.itemById(IN_DEPTH).value,
        angle=inputs.itemById(IN_ANGLE).value,
        spacing=inputs.itemById(IN_SPACING).value,
        shift=inputs.itemById(IN_SHIFT).value,
        step=inputs.itemById(IN_STEP).value,
        tol=inputs.itemById(IN_TOL).value,
        flip=inputs.itemById(IN_FLIP).value,
        replace_line=inputs.itemById(IN_REPLACE).value,
        make_mate=inputs.itemById(IN_MATE).value,
    )


def _selected_line(inputs):
    sel = inputs.itemById(IN_LINE)
    if sel.selectionCount != 1:
        return None
    entity = sel.selection(0).entity
    if entity and entity.objectType == adsk.fusion.SketchLine.classType():
        return entity
    return None


def _run(inputs, delete_original):
    line = _selected_line(inputs)
    if not line:
        raise GeometryError('err.no_line')
    v = _read_inputs(inputs)
    create_geometry(line, v['count'], v['spacing'], v['width'], v['depth'],
                    v['angle'], v['tol'], v['flip'], v['shape'], v['shift'],
                    v['replace_line'], v['make_mate'], delete_original)
    return v


class ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            v = _run(args.firingEvent.sender.commandInputs, delete_original=True)
            _last.update({
                IN_COUNT: v['count'], IN_SHAPE: v['shape'], IN_WIDTH: v['width'],
                IN_DEPTH: v['depth'], IN_ANGLE: v['angle'], IN_SPACING: v['spacing'],
                IN_STEP: v['step'], IN_TOL: v['tol'], IN_FLIP: v['flip'],
                IN_REPLACE: v['replace_line'], IN_MATE: v['make_mate'],
            })
        except GeometryError as err:
            adsk.core.Application.get().userInterface.messageBox(str(err), T('cmd.name'))
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(
                T('msg.exec_failed', traceback.format_exc()), T('cmd.name'))


class PreviewHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            # Die Originallinie wird in der Vorschau nicht geloescht, damit die
            # Auswahl gueltig bleibt.
            _run(args.firingEvent.sender.commandInputs, delete_original=False)
            args.isValidResult = False
        except GeometryError:
            pass
        except Exception:
            pass


class ValidateHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            line = _selected_line(inputs)
            if not line:
                args.areInputsValid = False
                return
            v = _read_inputs(inputs)
            build_contours(line_length(line), v['count'], v['spacing'], v['width'],
                           v['depth'], v['angle'], v['tol'], v['shape'], v['shift'])
            args.areInputsValid = True
        except GeometryError:
            args.areInputsValid = False
        except Exception:
            args.areInputsValid = False


def _apply_nudge(inputs, row):
    """Wertet die gedrueckten Verschieben-Buttons aus und setzt sie zurueck."""
    global _updating
    delta = 0.0
    reset = False
    for i in range(row.listItems.count):
        if not row.listItems.item(i).isSelected:
            continue
        if i == NUDGE_LEFT:
            delta -= 1.0
        elif i == NUDGE_RIGHT:
            delta += 1.0
        else:
            reset = True

    _updating = True
    try:
        for i in range(row.listItems.count):
            row.listItems.item(i).isSelected = False

        shift_in = inputs.itemById(IN_SHIFT)
        if reset:
            shift_in.value = 0.0
            return
        if delta == 0.0:
            return

        target = shift_in.value + delta * inputs.itemById(IN_STEP).value
        line = _selected_line(inputs)
        if line:
            v = _read_inputs(inputs)
            ms = max_shift(line_length(line), v['count'], v['spacing'],
                           v['width'], v['depth'], v['angle'], v['shape'])
            if ms > EPS:
                target = max(-ms, min(ms, target))
        shift_in.value = target
    finally:
        _updating = False


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        if _updating:
            return
        try:
            changed = args.input
            inputs = changed.parentCommand.commandInputs

            if changed.id == IN_NUDGE:
                _apply_nudge(inputs, changed)
                return

            shape_item = inputs.itemById(IN_SHAPE).selectedItem
            shape = shape_item.index if shape_item else SHAPE_TRAPEZ
            inputs.itemById(IN_ANGLE).isEnabled = shape == SHAPE_TRAPEZ
            inputs.itemById(IN_SPACING).isEnabled = inputs.itemById(IN_COUNT).value > 1
        except Exception:
            pass


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            ui = adsk.core.Application.get().userInterface
            cmd = args.command
            cmd.isRepeatable = True
            inputs = cmd.commandInputs

            preselected = []
            for i in range(ui.activeSelections.count):
                ent = ui.activeSelections.item(i).entity
                if ent and ent.objectType == adsk.fusion.SketchLine.classType():
                    preselected.append(ent)

            sel = inputs.addSelectionInput(IN_LINE, T('in.line'), T('in.line.prompt'))
            sel.addSelectionFilter('SketchLines')
            sel.setSelectionLimits(1, 1)

            inputs.addIntegerSpinnerCommandInput(
                IN_COUNT, T('in.count'), 1, 500, 1, _last[IN_COUNT])

            shape = inputs.addDropDownCommandInput(
                IN_SHAPE, T('in.shape'), adsk.core.DropDownStyles.TextListDropDownStyle)
            for index, key in enumerate(SHAPE_KEYS):
                shape.listItems.add(T(key), index == _last[IN_SHAPE])

            inputs.addValueInput(IN_WIDTH, T('in.width'), 'mm',
                                 adsk.core.ValueInput.createByReal(_last[IN_WIDTH]))
            inputs.addValueInput(IN_DEPTH, T('in.depth'), 'mm',
                                 adsk.core.ValueInput.createByReal(_last[IN_DEPTH]))
            angle = inputs.addValueInput(IN_ANGLE, T('in.angle'), 'deg',
                                         adsk.core.ValueInput.createByReal(_last[IN_ANGLE]))
            angle.isEnabled = _last[IN_SHAPE] == SHAPE_TRAPEZ

            spacing = inputs.addValueInput(IN_SPACING, T('in.spacing'), 'mm',
                                           adsk.core.ValueInput.createByReal(_last[IN_SPACING]))
            spacing.isEnabled = _last[IN_COUNT] > 1

            inputs.addValueInput(IN_SHIFT, T('in.shift'), 'mm',
                                 adsk.core.ValueInput.createByReal(0.0))
            inputs.addValueInput(IN_STEP, T('in.step'), 'mm',
                                 adsk.core.ValueInput.createByReal(_last[IN_STEP]))

            nudge = inputs.addButtonRowCommandInput(IN_NUDGE, T('in.nudge'), True)
            nudge.listItems.add(T('nudge.left'), False, ICON_LEFT)
            nudge.listItems.add(T('nudge.center'), False, ICON_CENTER)
            nudge.listItems.add(T('nudge.right'), False, ICON_RIGHT)
            nudge.tooltip = T('nudge.tooltip')

            inputs.addValueInput(IN_TOL, T('in.tol'), 'mm',
                                 adsk.core.ValueInput.createByReal(_last[IN_TOL]))

            inputs.addBoolValueInput(IN_FLIP, T('in.flip'), True, '', _last[IN_FLIP])
            inputs.addBoolValueInput(IN_MATE, T('in.mate'), True, '', _last[IN_MATE])
            inputs.addBoolValueInput(IN_REPLACE, T('in.replace'), True, '',
                                     _last[IN_REPLACE])

            if preselected and sel.selectionCount == 0:
                sel.addSelection(preselected[0])

            on_exec = ExecuteHandler()
            cmd.execute.add(on_exec)
            _handlers.append(on_exec)

            on_preview = PreviewHandler()
            cmd.executePreview.add(on_preview)
            _handlers.append(on_preview)

            on_validate = ValidateHandler()
            cmd.validateInputs.add(on_validate)
            _handlers.append(on_validate)

            on_changed = InputChangedHandler()
            cmd.inputChanged.add(on_changed)
            _handlers.append(on_changed)
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(
                T('msg.dialog_failed', traceback.format_exc()), T('cmd.name'))


# ------------------------------------------------------------- Start / Stopp --

def _find_panel(ui):
    ws = ui.workspaces.itemById(WORKSPACE_ID)
    for pid in PANEL_IDS:
        if ws:
            panel = ws.toolbarPanels.itemById(pid)
            if panel:
                return panel
        panel = ui.allToolbarPanels.itemById(pid)
        if panel:
            return panel
    return None


def run(context):
    global _control
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        S.load(detect_language())

        cmd_def = ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            cmd_def.deleteMe()

        icons = RESOURCE_FOLDER if os.path.isdir(RESOURCE_FOLDER) else ''
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, T('cmd.name'), T('cmd.tooltip'), icons)

        on_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        panel = _find_panel(ui)
        if not panel:
            ui.messageBox(T('msg.panel_missing'), T('cmd.name'))
            return

        existing = panel.controls.itemById(CMD_ID)
        if existing:
            existing.deleteMe()
        _control = panel.controls.addCommand(cmd_def)
        _control.isPromoted = True
        _control.isPromotedByDefault = True
    except Exception:
        if ui:
            ui.messageBox(T('msg.run_failed', traceback.format_exc()), T('cmd.name'))


def stop(context):
    global _control
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        panel = _find_panel(ui)
        if panel:
            ctrl = panel.controls.itemById(CMD_ID)
            if ctrl:
                ctrl.deleteMe()
        _control = None

        cmd_def = ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            cmd_def.deleteMe()

        del _handlers[:]
    except Exception:
        if ui:
            ui.messageBox(T('msg.stop_failed', traceback.format_exc()), T('cmd.name'))
