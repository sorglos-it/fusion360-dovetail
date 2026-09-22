# fusion360-dovetail

[![Fusion 360](https://img.shields.io/badge/Autodesk-Fusion%20360-F60?logo=autodesk&logoColor=white)](#start-in-3-steps)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-0078D6?logo=windows&logoColor=white)](#start-in-3-steps)
[![Languages](https://img.shields.io/badge/UI-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR%20%7C%20IT-4c1.svg)](#languages)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Donate](https://img.shields.io/badge/Donate-PayPal-00457C.svg?logo=paypal)](https://www.paypal.com/donate/?hosted_button_id=6CDEVZGJWTNQQ)

A Fusion 360 add-in that turns **sketch lines into finished joints** — dovetail, triangle or box joint. Pick a line,
press the button, and you get one closed band exactly as wide as the clearance. Cut that band out of a solid and you
are left with two parts that fit.

| Folder | Purpose | Language | Start | Build |
|---|---|---|---|---|
| `apps/desktop/Dovetail` | the add-in: joints on sketch lines | Python 3 (the one inside Fusion) | copy into Fusion's add-ins folder, then *Run* | – (runs as is) |

## Start in 3 steps

1. Download the latest `Dovetail-*.zip` from **[Releases](https://github.com/sorglos-it/fusion360-dovetail/releases)**
   — or clone this repository and take the folder `apps/desktop/Dovetail`.
2. Unpack or copy it into Fusion's add-ins folder, so that `Dovetail\Dovetail.py` ends up one level below it:

   | OS | Path |
   |---|---|
   | Windows | `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` |
   | macOS | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` |

3. In Fusion: **Utilities → ADD-INS → Add-Ins**, select the entry, tick *Run on Startup*, press **Run**. The button
   appears on the **SKETCH** tab in the **CREATE** panel, with the version in brackets — *Dovetail (1.5.0)*.

You need Autodesk Fusion 360 (Windows or macOS), any recent version — nothing else to install.

## Update

- Stop the add-in in Fusion first, otherwise the running one stays in memory. Then replace the folder.
- Keep the folder name and the file names in sync — Fusion requires `<Folder>/<Folder>.py` and
  `<Folder>/<Folder>.manifest` to match.
- Coming from 1.1.x or older, when the add-in was called `Schwalbenschwanz`: stop it, delete the old folder from the
  add-ins folder, then install `Dovetail` — otherwise both register and you get two buttons.

## Usage

1. Open or edit a sketch.
2. Click a line, or several — hold the usual modifier to add to the selection.
3. Click the dovetail icon — the selection is already in the dialog.
4. Set the values, watch the preview, press **OK**.

To get two parts: draw the outline of the whole piece with the joint line running across it, run the command on that
line, extrude the outline into a solid, then extrude-cut the band through it. Two bodies remain that mate with the
tolerance you asked for.

What you get:

- **Uniform clearance** — both sides of the band are true parallel offsets of the same outline, so the gap is the same
  on the base, both flanks and the tip.
- **You choose who pays** — half from each part, or all of it from one.
- **Three shapes** — the trapezoid dovetail with a real undercut (default), a triangle, a rectangle for box joints.
- **Many lines at once** — up to 100, each gets its own joint from the same settings.
- **Mirror geometry** — one symmetric cut, two identical parts: model once, print twice.
- **Live preview, explained refusals** — impossible values disable OK and the dialog says which one, in your language.

## Dialog

| Field | Meaning |
|---|---|
| **Lines** | The sketch lines the teeth sit on, 1 to 100. Pre-filled from the current selection. |
| **Count** | Number of teeth, 1 – 500, centred on each line. |
| **Mirror geometry** | Makes the two parts identical. Rounds the count up to even and pins the split to the centre line with no offset. |
| **Shape** | `Trapezoid` (default, real dovetail with undercut), `Triangle`, `Rectangle` (box joint). |
| **Width (base)** | Width of the tooth where it meets the line. |
| **Depth** | How far the tooth stands off the line. |
| **Flank angle** | Trapezoid only: how much the tooth widens towards its tip. Default 15°, range ±89°; at 0° it becomes a rectangle. |
| **Spacing** | Two teeth or more: centre-to-centre distance. |
| **Offset** | Shift of the whole set along the line; 0 = centred. Type a value or use the buttons. |
| **Step size** | How far one click of ◀ / ▶ moves. Default 1 mm. |
| **Move ◀ ▮ ▶** | ◀ towards the start point, ▶ towards the end point, the middle button resets to the centre. |
| **Tolerance** | Clearance between the two parts. Default **0.25 mm**; it must be above 0 — the band is made of it. |
| **The line is** | `Centre line` (default, half the tolerance each side), `Pocket edge` (all of it on the pin), `Pin edge` (all of it on the pocket). |
| **Flip direction** | Teeth to the other side of the line. |
| **Turn the original line into construction geometry** | On by default. A normal line would cut the band into two profiles. |

## Alignment

The teeth are always symmetric about the **midpoint of the line they sit on** — with several lines, each is measured
and centred on its own:

| Count | Position relative to the midpoint (spacing 30 mm) |
|---|---|
| 1 | `0` |
| 2 | `−15 / +15` |
| 3 | `−30 / 0 / +30` |
| 4 | `−45 / −15 / +15 / +45` |
| 5 | `−60 / −30 / 0 / +30 / +60` |

An odd count puts a tooth on the midpoint, an even count puts the gap there. **Offset** moves the set away from that;
◀ / ▶ stop where the teeth would run off the line — with several lines, the shortest sets the limit. The offset starts
at 0 every time: it belongs to the line at hand, not to the settings.

## Tolerance

The band is built from two contours of the same zero-clearance outline: the **pocket**, offset outwards, and the
**pin**, offset inwards. **The line is** decides how the tolerance is split — here with 0.25 mm:

| Setting | Pocket sits at | Pin sits at | Gap |
|---|---|---|---|
| `Centre line` (default) | +0.125 mm | −0.125 mm | 0.25 mm |
| `Pocket edge` | on the line | −0.25 mm | 0.25 mm |
| `Pin edge` | +0.25 mm | on the line | 0.25 mm |

Centred keeps two halves the size you drew them. The other two are for a line that *is* one part's edge, where only
the other part may lose material.

## Several lines at once

Every selected line gets its own joint, measured on its own; lines of different lengths are fine as long as the teeth
fit on each. That makes parts with gaps between the pieces easy: select every cut line, press OK once.

If one line cannot take the settings, nothing is drawn and the message names it — *Line 2 of 3: the teeth are wider
than the selected line (30.00 mm)*. The teeth stand on the side each line's own start-to-end direction decides, so
lines drawn in opposite directions get them on opposite sides; **Flip direction** turns them all over together.

## Mirror geometry

Half the teeth point one way, half the other, so turning the contour 180° about the midpoint of the line maps it onto
itself — both parts come out identical. With several lines, each is mirrored about its own midpoint. Three things
would break that, so the dialog sets them for you:

| Needs | Why |
|---|---|
| An **even** count | A tooth on the midpoint would have to point both ways at once. |
| The **centre line** split | Only there do both parts give up the same amount. |
| **No offset** | Shifting the set moves the symmetry point off the midpoint. |

## Languages

The interface follows **Preferences → General → User Language** in Fusion: German, English, Spanish, French or
Italian, anything else falls back to English. The texts live in `apps/desktop/Dovetail/lang/<code>.xml`:

```xml
<string key="in.width">Width (base)</string>
```

`en.xml` is the reference — every key exists there, and a key missing from another file falls back to it. To add a
language, copy `en.xml`, translate the values, name it after the two-letter code and add the code to
`SUPPORTED_LANGUAGES` and `FUSION_LANGUAGE_MAP` in `Dovetail.py`. Placeholders like `{0}` must survive translation;
the tests check that for every file.

## Notes & caveats

- **The band needs a tolerance above 0.** At zero both contours coincide and there is no area, so the command refuses.
- **The line has to stop making profiles.** A normal line across the band splits it in two. Turning it into
  construction geometry fixes that and keeps its dimensions and constraints, which deleting it would not.
- **A triangle is not a dovetail.** It has no undercut and pulls apart under load. Use the trapezoid where the joint
  has to hold under tension.
- **The preview does not remove the original line** — only OK does, because deleting the selection during the preview
  can break it. The preview therefore looks a little busier than the result.
- **Tolerance is clearance, not shrinkage compensation.** For FDM prints 0.2 – 0.3 mm is a good start; elephant's foot
  and over-extrusion on the first layers come on top.

## Development

The geometry is pure maths without Fusion, so everything runs in a normal Python 3 (standard library only):

```bash
python apps/desktop/tests/test_geometry.py   # tests: points, parallel offset, alignment, limits, error keys, languages
python tools/make_icons.py                   # toolbar icon
python tools/make_arrow_icons.py             # icons of the move buttons
```

The scripts find the add-in in `apps/desktop/Dovetail`; set `DOVETAIL_ADDIN_DIR` to point them at an installed copy
instead. `python tools/test_geometry.py` still works and runs the same tests.

How it works, in short: the selected line gives an origin, a direction and a normal; `build_contours()` lays out the
teeth around `length / 2 + offset` in that frame; `_offset_polyline()` offsets every segment by the tolerance and
mitres the corners, refusing a corner that would run more than twelve times the offset away; everything is checked
before drawing, and failures raise a `GeometryError` with a language-independent key that the dialog shows. Drawing
runs with `isComputeDeferred` set and chains the segments, so the outline comes out connected.

## Related

[fusion360-sketch-grid](https://github.com/sorglos-it/fusion360-sketch-grid) builds grids of shapes around a sketch
point. [fusion360-addin-template](https://github.com/sorglos-it/fusion360-addin-template) is the scaffolding this
add-in was extracted into — the same translated interface, live preview, validation and offline tests as a starting
point for your own add-in.

## License

MIT — see [LICENSE](LICENSE). © 2026 Thomas Weirich.

## Donate via PayPal

If this add-in saved you time, a donation supports further development. Thank you!

**[➡️ Donate via PayPal](https://www.paypal.com/donate/?hosted_button_id=6CDEVZGJWTNQQ)**
