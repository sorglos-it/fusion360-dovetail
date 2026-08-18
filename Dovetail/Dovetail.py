# -*- coding: utf-8 -*-
"""
Dovetail - Fusion 360 add-in

Turns a selected sketch line into a joint: a pocket contour and a pin contour
that clear each other by the tolerance everywhere. Which part pays for that
clearance - both by half, or one of them in full - is what the line stands for.

The interface follows the language Fusion is set to. All display text lives in
lang/<code>.xml; a key missing from a file falls back to lang/en.xml.
"""

import os
import math
import traceback
import xml.etree.ElementTree as ElementTree

import adsk.core
import adsk.fusion

CMD_ID = 'thwDovetailCmd'

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_IDS = ('SketchCreatePanel', 'SketchModifyPanel', 'SolidCreatePanel')

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_APP_DIR, 'resources')
LANG_DIR = os.path.join(_APP_DIR, 'lang')
RESOURCE_FOLDER = os.path.join(_RES, 'Dovetail')
ICON_LEFT = os.path.join(_RES, 'nudge_left')
ICON_CENTER = os.path.join(_RES, 'nudge_center')
ICON_RIGHT = os.path.join(_RES, 'nudge_right')

FALLBACK_LANGUAGE = 'en'
SUPPORTED_LANGUAGES = ('de', 'en', 'es', 'fr', 'it')

# Fusion language preference -> language code. The enum members are looked up
# with getattr so a value this Fusion version does not know cannot break us.
FUSION_LANGUAGE_MAP = {
    'GermanLanguage': 'de',
    'EnglishLanguage': 'en',
    'SpanishLanguage': 'es',
    'FrenchLanguage': 'fr',
    'ItalianLanguage': 'it',
}

# Command input ids
IN_LINE = 'dtLine'
IN_COUNT = 'dtCount'
IN_SHAPE = 'dtShape'
IN_WIDTH = 'dtWidth'
IN_DEPTH = 'dtDepth'
IN_ANGLE = 'dtAngle'
IN_SPACING = 'dtSpacing'
IN_OFFSET = 'dtOffset'
IN_STEP = 'dtStep'
IN_NUDGE = 'dtNudge'
IN_TOLERANCE = 'dtTolerance'
IN_REFERENCE = 'dtReference'
IN_FLIP = 'dtFlip'
IN_CONSTRUCTION = 'dtConstruction'

# Tooth shapes. The order is also the order in the drop-down, and the stored
# value is the index - independent of the display language.
SHAPE_TRAPEZOID = 0
SHAPE_TRIANGLE = 1
SHAPE_RECTANGLE = 2
SHAPE_KEYS = ('shape.trapezoid', 'shape.triangle', 'shape.rectangle')

# What the selected line stands for, and therefore which part pays for the
# clearance. The pair is (how far the pocket grows, how far the pin shrinks),
# as a fraction of the tolerance; the two always add up to 1.
REF_CENTER = 0
REF_POCKET = 1
REF_PIN = 2
REF_KEYS = ('reference.center', 'reference.pocket', 'reference.pin')
REF_SPLIT = ((0.5, 0.5), (0.0, 1.0), (1.0, 0.0))

NUDGE_LEFT = 0
NUDGE_CENTER = 1
NUDGE_RIGHT = 2

EPS = 1e-9
MAX_FLANK_ANGLE = math.radians(89.0)

_handlers = []
_control = None
_updating = False       # re-entrancy guard for inputChanged

# Last used values, kept for the duration of the Fusion session.
# Lengths in cm (Fusion's internal unit), angles in radians.
# The offset is deliberately NOT remembered - it belongs to the line at hand.
_last = {
    IN_COUNT: 1,
    IN_SHAPE: SHAPE_TRAPEZOID,
    IN_WIDTH: 1.0,          # 10 mm
    IN_DEPTH: 0.6,          # 6 mm
    IN_ANGLE: math.radians(15.0),
    IN_SPACING: 2.0,        # 20 mm
    IN_STEP: 0.1,           # 1 mm
    IN_TOLERANCE: 0.025,    # 0.25 mm
    IN_REFERENCE: REF_CENTER,
    IN_FLIP: False,
    IN_CONSTRUCTION: True,
}


# ------------------------------------------------------------------ Language --

class Strings(object):
    """Text catalogue read from lang/<code>.xml, falling back to English."""

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
    """Language code from the Fusion preference, else from the environment."""
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


# ------------------------------------------------------------------ Geometry --

class GeometryError(Exception):
    """The inputs do not describe usable geometry.

    key holds the language-independent reason; the message itself is looked up
    in the text catalogue.
    """

    def __init__(self, key, *args):
        self.key = key
        self.params = args
        super(GeometryError, self).__init__(T(key, *args))


def _line_intersection(p, d, q, e):
    """Intersection of the lines (p + t*d) and (q + s*e). None if parallel."""
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
    """Offset an open polyline by dist to the right, looking along the run.

    Corners are mitred by intersecting the two offset segments that meet there.
    """
    pts = _dedupe(points)
    if len(pts) < 2:
        raise GeometryError('err.degenerate')

    segments = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        d = (dx / length, dy / length)
        r = (d[1], -d[0])                     # right-hand normal
        segments.append(((a[0] + r[0] * dist, a[1] + r[1] * dist), d, r))

    out = [segments[0][0]]
    for i in range(len(segments) - 1):
        p, d, r = segments[i]
        q, e, _ = segments[i + 1]
        corner = _line_intersection(p, d, q, e)
        vertex = pts[i + 1]
        if corner is None:
            corner = (vertex[0] + r[0] * dist, vertex[1] + r[1] * dist)
        elif math.hypot(corner[0] - vertex[0],
                        corner[1] - vertex[1]) > abs(dist) * 12.0 + 1e-6:
            raise GeometryError('err.miter_runaway')
        out.append(corner)

    _last_point, _last_dir, last_normal = segments[-1]
    end = pts[-1]
    out.append((end[0] + last_normal[0] * dist, end[1] + last_normal[1] * dist))
    return out


def _top_half(width, depth, angle, shape):
    """Half the width of the tooth at its tip.

    Rectangle -> same as half the base, a straight tenon
    Triangle  -> 0, the tooth runs to a point
    Trapezoid -> widens with the flank angle, giving the undercut
    """
    half = width / 2.0
    if shape == SHAPE_RECTANGLE:
        return half
    if shape == SHAPE_TRIANGLE:
        return 0.0
    if abs(angle) >= MAX_FLANK_ANGLE:
        raise GeometryError('err.angle_range')
    top = half + depth * math.tan(angle)
    if top <= EPS:
        raise GeometryError('err.angle_negative')
    return top


def max_offset(length, count, spacing, width, depth, angle, shape):
    """Largest offset that still keeps every tooth on the line.

    Returns 0.0 when the teeth do not fit in the first place.
    """
    try:
        top = _top_half(width, depth, angle, shape)
    except GeometryError:
        return 0.0
    outer = max(width / 2.0, top)
    span = (max(count, 1) - 1) / 2.0 * spacing + outer
    return max(0.0, length / 2.0 - span)


def build_contours(length, count, spacing, width, depth, angle, tolerance,
                   shape, offset=0.0, reference=REF_CENTER):
    """Build the pocket and the pin contour in local coordinates.

    s runs along the line from its start point, h is perpendicular to it in
    the direction the teeth point.

    The nominal outline is the zero-clearance boundary the two parts share. The
    tolerance is then split between them according to `reference`: the pocket
    grows outwards by its share, the pin shrinks inwards by the rest, and the
    gap between the two is the full tolerance either way. Centred means both
    parts give up half, which keeps two equal halves equal.
    """
    if length <= EPS:
        raise GeometryError('err.zero_length')
    if width <= EPS:
        raise GeometryError('err.width')
    if depth <= EPS:
        raise GeometryError('err.depth')
    if tolerance <= EPS:
        raise GeometryError('err.tolerance_zero')
    if count < 1:
        raise GeometryError('err.count')

    half = width / 2.0
    top_half = _top_half(width, depth, angle, shape)
    outer = max(half, top_half)

    # Tooth centres, symmetric about the midpoint of the line plus the offset
    centres = [length / 2.0 + offset + (i - (count - 1) / 2.0) * spacing
               for i in range(count)]

    if count > 1:
        if spacing <= EPS:
            raise GeometryError('err.spacing_positive')
        if spacing < 2 * outer + 2 * tolerance:
            raise GeometryError('err.spacing_too_small',
                                '%.2f' % ((2 * outer + 2 * tolerance) * 10.0))
    if centres[0] - outer < -EPS or centres[-1] + outer > length + EPS:
        limit = max_offset(length, count, spacing, width, depth, angle, shape)
        if limit > EPS and abs(offset) > limit:
            raise GeometryError('err.offset_range', '%.2f' % (limit * 10.0))
        raise GeometryError('err.does_not_fit', '%.2f' % (length * 10.0))

    nominal = [(0.0, 0.0)]
    for centre in centres:
        nominal.append((centre - half, 0.0))
        if top_half <= EPS:
            nominal.append((centre, depth))
        else:
            nominal.append((centre - top_half, depth))
            nominal.append((centre + top_half, depth))
        nominal.append((centre + half, 0.0))
    nominal.append((length, 0.0))

    grow, shrink = REF_SPLIT[reference]
    outward = tolerance * grow          # how far the pocket opens up
    inward = tolerance * shrink         # how far the pin is pulled back

    # A negative distance offsets to the left of the run, which is away from
    # the teeth - that is the direction the pocket has to open in.
    pocket = _offset_polyline(nominal, -outward) if outward > EPS else nominal
    pin = _offset_polyline(nominal, inward) if inward > EPS else nominal

    # Sanity: the tooth has to survive above its own base line (h = -inward)
    # and must not run into itself.
    peak = max(p[1] for p in pin)
    if peak <= -inward + EPS:
        raise GeometryError('err.tolerance_eats_tooth')
    if (peak + inward) < 0.05 * depth:
        raise GeometryError('err.tolerance_vs_depth')
    if 2 * tolerance >= width:
        raise GeometryError('err.tolerance_vs_width')

    return pocket, pin


def closed_band(pocket, pin):
    """Join the two contours into one closed loop.

    Runs along the pocket, drops across at the far end, comes back along the
    pin and closes at the near end. What it encloses is the clearance itself:
    a band of exactly the tolerance following the tooth outline, so cutting it
    out of one solid leaves two parts that fit.
    """
    if len(pocket) != len(pin):
        raise GeometryError('err.degenerate')
    return list(pocket) + list(reversed(pin))


# ------------------------------------------------------------------- Drawing --

def _to_world(point, origin, u, n):
    return adsk.core.Point3D.create(
        origin[0] + u[0] * point[0] + n[0] * point[1],
        origin[1] + u[1] * point[0] + n[1] * point[1],
        0.0)


def _draw_polyline(sketch, points, origin, u, n):
    lines = sketch.sketchCurves.sketchLines
    previous = None
    for i in range(len(points) - 1):
        end = _to_world(points[i + 1], origin, u, n)
        if previous is None:
            previous = lines.addByTwoPoints(_to_world(points[i], origin, u, n), end)
        else:
            previous = lines.addByTwoPoints(previous.endSketchPoint, end)


def _draw_closed_polyline(sketch, points, origin, u, n):
    """Draw points as a closed loop, the last segment tying back to the first."""
    lines = sketch.sketchCurves.sketchLines
    first = previous = None
    for i in range(len(points) - 1):
        end = _to_world(points[i + 1], origin, u, n)
        if previous is None:
            first = previous = lines.addByTwoPoints(
                _to_world(points[i], origin, u, n), end)
        else:
            previous = lines.addByTwoPoints(previous.endSketchPoint, end)
    if first is not None:
        lines.addByTwoPoints(previous.endSketchPoint, first.startSketchPoint)


def line_length(line):
    start = line.startSketchPoint.geometry
    end = line.endSketchPoint.geometry
    return math.hypot(end.x - start.x, end.y - start.y)


def create_geometry(line, count, spacing, width, depth, angle, tolerance, flip,
                    shape, offset, reference, to_construction, modify_original):
    sketch = line.parentSketch
    start = line.startSketchPoint.geometry
    end = line.endSketchPoint.geometry
    origin = (start.x, start.y)
    dx, dy = end.x - start.x, end.y - start.y
    length = math.hypot(dx, dy)
    if length <= EPS:
        raise GeometryError('err.zero_length')

    u = (dx / length, dy / length)
    n = (-u[1], u[0])
    if flip:
        n = (-n[0], -n[1])

    pocket, pin = build_contours(length, count, spacing, width, depth,
                                 angle, tolerance, shape, offset, reference)
    band = closed_band(pocket, pin)

    sketch.isComputeDeferred = True
    try:
        # The original line runs straight through the band and would cut it
        # into two profiles. Turning it into construction geometry stops it
        # creating profiles while keeping its dimensions and constraints,
        # which deleting it would throw away.
        if to_construction and modify_original and not line.isConstruction:
            line.isConstruction = True
        _draw_closed_polyline(sketch, band, origin, u, n)
    finally:
        sketch.isComputeDeferred = False


# ------------------------------------------------------------------ Handlers --

def _read_inputs(inputs):
    shape_item = inputs.itemById(IN_SHAPE).selectedItem
    reference_item = inputs.itemById(IN_REFERENCE).selectedItem
    return dict(
        reference=reference_item.index if reference_item else REF_CENTER,
        count=inputs.itemById(IN_COUNT).value,
        shape=shape_item.index if shape_item else SHAPE_TRAPEZOID,
        width=inputs.itemById(IN_WIDTH).value,
        depth=inputs.itemById(IN_DEPTH).value,
        angle=inputs.itemById(IN_ANGLE).value,
        spacing=inputs.itemById(IN_SPACING).value,
        offset=inputs.itemById(IN_OFFSET).value,
        step=inputs.itemById(IN_STEP).value,
        tolerance=inputs.itemById(IN_TOLERANCE).value,
        flip=inputs.itemById(IN_FLIP).value,
        to_construction=inputs.itemById(IN_CONSTRUCTION).value,
    )


def _selected_line(inputs):
    selection = inputs.itemById(IN_LINE)
    if selection.selectionCount != 1:
        return None
    entity = selection.selection(0).entity
    if entity and entity.objectType == adsk.fusion.SketchLine.classType():
        return entity
    return None


def _run(inputs, modify_original):
    line = _selected_line(inputs)
    if not line:
        raise GeometryError('err.no_line')
    values = _read_inputs(inputs)
    create_geometry(line, values['count'], values['spacing'], values['width'],
                    values['depth'], values['angle'], values['tolerance'],
                    values['flip'], values['shape'], values['offset'],
                    values['reference'], values['to_construction'],
                    modify_original)
    return values


class ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            values = _run(args.firingEvent.sender.commandInputs,
                          modify_original=True)
            _last.update({
                IN_COUNT: values['count'], IN_SHAPE: values['shape'],
                IN_WIDTH: values['width'], IN_DEPTH: values['depth'],
                IN_ANGLE: values['angle'], IN_SPACING: values['spacing'],
                IN_STEP: values['step'], IN_TOLERANCE: values['tolerance'],
                IN_REFERENCE: values['reference'],
                IN_CONSTRUCTION: values['to_construction'],
                IN_FLIP: values['flip'],
            })
        except GeometryError as err:
            adsk.core.Application.get().userInterface.messageBox(str(err), T('cmd.name'))
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(
                T('msg.exec_failed', traceback.format_exc()), T('cmd.name'))


class PreviewHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            # The original line is left alone during the preview so the
            # selection cannot be invalidated underneath the dialog.
            _run(args.firingEvent.sender.commandInputs, modify_original=False)
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
            values = _read_inputs(inputs)
            build_contours(line_length(line), values['count'], values['spacing'],
                           values['width'], values['depth'], values['angle'],
                           values['tolerance'], values['shape'], values['offset'],
                           values['reference'])
            args.areInputsValid = True
        except GeometryError:
            args.areInputsValid = False
        except Exception:
            args.areInputsValid = False


def _apply_nudge(inputs, row):
    """Act on the pressed move buttons and release them again."""
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

        offset_input = inputs.itemById(IN_OFFSET)
        if reset:
            offset_input.value = 0.0
            return
        if delta == 0.0:
            return

        target = offset_input.value + delta * inputs.itemById(IN_STEP).value
        line = _selected_line(inputs)
        if line:
            values = _read_inputs(inputs)
            limit = max_offset(line_length(line), values['count'],
                               values['spacing'], values['width'],
                               values['depth'], values['angle'], values['shape'])
            if limit > EPS:
                target = max(-limit, min(limit, target))
        offset_input.value = target
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
            shape = shape_item.index if shape_item else SHAPE_TRAPEZOID
            inputs.itemById(IN_ANGLE).isEnabled = shape == SHAPE_TRAPEZOID
            inputs.itemById(IN_SPACING).isEnabled = inputs.itemById(IN_COUNT).value > 1

        except Exception:
            pass


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            ui = adsk.core.Application.get().userInterface
            command = args.command
            command.isRepeatable = True
            inputs = command.commandInputs

            preselected = []
            for i in range(ui.activeSelections.count):
                entity = ui.activeSelections.item(i).entity
                if entity and entity.objectType == adsk.fusion.SketchLine.classType():
                    preselected.append(entity)

            selection = inputs.addSelectionInput(IN_LINE, T('in.line'),
                                                 T('in.line.prompt'))
            selection.addSelectionFilter('SketchLines')
            selection.setSelectionLimits(1, 1)

            inputs.addIntegerSpinnerCommandInput(
                IN_COUNT, T('in.count'), 1, 500, 1, _last[IN_COUNT])

            shape = inputs.addDropDownCommandInput(
                IN_SHAPE, T('in.shape'),
                adsk.core.DropDownStyles.TextListDropDownStyle)
            for index, key in enumerate(SHAPE_KEYS):
                shape.listItems.add(T(key), index == _last[IN_SHAPE])

            inputs.addValueInput(IN_WIDTH, T('in.width'), 'mm',
                                 adsk.core.ValueInput.createByReal(_last[IN_WIDTH]))
            inputs.addValueInput(IN_DEPTH, T('in.depth'), 'mm',
                                 adsk.core.ValueInput.createByReal(_last[IN_DEPTH]))
            angle = inputs.addValueInput(IN_ANGLE, T('in.angle'), 'deg',
                                         adsk.core.ValueInput.createByReal(_last[IN_ANGLE]))
            angle.isEnabled = _last[IN_SHAPE] == SHAPE_TRAPEZOID

            spacing = inputs.addValueInput(IN_SPACING, T('in.spacing'), 'mm',
                                           adsk.core.ValueInput.createByReal(_last[IN_SPACING]))
            spacing.isEnabled = _last[IN_COUNT] > 1

            inputs.addValueInput(IN_OFFSET, T('in.offset'), 'mm',
                                 adsk.core.ValueInput.createByReal(0.0))
            inputs.addValueInput(IN_STEP, T('in.step'), 'mm',
                                 adsk.core.ValueInput.createByReal(_last[IN_STEP]))

            nudge = inputs.addButtonRowCommandInput(IN_NUDGE, T('in.nudge'), True)
            nudge.listItems.add(T('nudge.left'), False, ICON_LEFT)
            nudge.listItems.add(T('nudge.center'), False, ICON_CENTER)
            nudge.listItems.add(T('nudge.right'), False, ICON_RIGHT)
            nudge.tooltip = T('nudge.tooltip')

            inputs.addValueInput(IN_TOLERANCE, T('in.tolerance'), 'mm',
                                 adsk.core.ValueInput.createByReal(_last[IN_TOLERANCE]))

            reference = inputs.addDropDownCommandInput(
                IN_REFERENCE, T('in.reference'),
                adsk.core.DropDownStyles.TextListDropDownStyle)
            for index, key in enumerate(REF_KEYS):
                reference.listItems.add(T(key), index == _last[IN_REFERENCE])
            reference.tooltip = T('reference.tooltip')

            inputs.addBoolValueInput(IN_FLIP, T('in.flip'), True, '', _last[IN_FLIP])
            construction = inputs.addBoolValueInput(
                IN_CONSTRUCTION, T('in.construction'), True, '',
                _last[IN_CONSTRUCTION])
            construction.tooltip = T('construction.tooltip')

            if preselected and selection.selectionCount == 0:
                selection.addSelection(preselected[0])

            on_execute = ExecuteHandler()
            command.execute.add(on_execute)
            _handlers.append(on_execute)

            on_preview = PreviewHandler()
            command.executePreview.add(on_preview)
            _handlers.append(on_preview)

            on_validate = ValidateHandler()
            command.validateInputs.add(on_validate)
            _handlers.append(on_validate)

            on_changed = InputChangedHandler()
            command.inputChanged.add(on_changed)
            _handlers.append(on_changed)
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(
                T('msg.dialog_failed', traceback.format_exc()), T('cmd.name'))


# --------------------------------------------------------------- Start / stop --

def _find_panel(ui):
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    for panel_id in PANEL_IDS:
        if workspace:
            panel = workspace.toolbarPanels.itemById(panel_id)
            if panel:
                return panel
        panel = ui.allToolbarPanels.itemById(panel_id)
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

        definition = ui.commandDefinitions.itemById(CMD_ID)
        if definition:
            definition.deleteMe()

        icons = RESOURCE_FOLDER if os.path.isdir(RESOURCE_FOLDER) else ''
        definition = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, T('cmd.name'), T('cmd.tooltip'), icons)

        on_created = CommandCreatedHandler()
        definition.commandCreated.add(on_created)
        _handlers.append(on_created)

        panel = _find_panel(ui)
        if not panel:
            ui.messageBox(T('msg.panel_missing'), T('cmd.name'))
            return

        existing = panel.controls.itemById(CMD_ID)
        if existing:
            existing.deleteMe()
        _control = panel.controls.addCommand(definition)
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
            control = panel.controls.itemById(CMD_ID)
            if control:
                control.deleteMe()
        _control = None

        definition = ui.commandDefinitions.itemById(CMD_ID)
        if definition:
            definition.deleteMe()

        del _handlers[:]
    except Exception:
        if ui:
            ui.messageBox(T('msg.stop_failed', traceback.format_exc()), T('cmd.name'))
