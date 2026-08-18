# fusion360-dovetail

[![Fusion 360](https://img.shields.io/badge/Autodesk-Fusion%20360-F60?logo=autodesk&logoColor=white)](#requirements)
[![Type](https://img.shields.io/badge/type-add--in-0b7285.svg)](#installation)
[![Languages](https://img.shields.io/badge/UI-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR%20%7C%20IT-4c1.svg)](#languages)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-0078D6?logo=windows&logoColor=white)](#requirements)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Donate](https://img.shields.io/badge/Donate-PayPal-00457C.svg?logo=paypal)](https://www.paypal.com/donate/?hosted_button_id=6CDEVZGJWTNQQ)

A Fusion 360 add-in that turns **one sketch line into a finished joint**. Pick a line, press the button, and you get a single closed profile: the **clearance itself**, a band of exactly the tolerance following the tooth outline. Cut that band out of one solid and you are left with two parts that fit.

The tolerance is not a guess applied to one edge. Both sides of the band are **true parallel offsets of the same outline**, so the clearance is identical on the base face, on both flanks and over the tip.

You decide which part pays for it. Centred is the default and takes half from each, which keeps two equal halves equal; the other two settings take the whole tolerance out of one part and leave the other exactly on the line.

Three tooth shapes ship with it: the **trapezoid** dovetail with a real undercut (the default), a **triangle**, and a **rectangle** for box joints. The interface follows whatever language Fusion is set to.

See also **[fusion360-sketch-grid](https://github.com/sorglos-it/fusion360-sketch-grid)** — grids of shapes around a sketch point — and **[fusion360-addin-template](https://github.com/sorglos-it/fusion360-addin-template)**, the scaffolding this add-in was extracted into. One command gives you the same translated interface, live preview, validation and offline test harness as a starting point for your own add-in.

## Features

- **One line in, one closed profile out** — the clearance band, ready to extrude-cut in a single operation
- **Uniform clearance** — a real parallel offset, verified to the last floating-point digit by the test suite
- **You choose who pays** — half from each part, or all of it from one
- **Mirror geometry** — one symmetric cut, two identical parts: model once, print twice
- **Three shapes** — trapezoid with flank angle (undercut, holds under load), triangle, rectangle (box / finger joint)
- **Always centred on the line** — odd counts put a tooth on the midpoint, even counts put the gap there
- **Nudge buttons** — ◀ / centre / ▶ shift the whole set along the line and stop themselves at the point where it would run off the end
- **Live preview** — every field updates the sketch while the dialog is open
- **Explained refusals** — impossible combinations disable OK and say which value is the problem, in your language
- **Five languages** — German, English, Spanish, French, Italian, picked from the Fusion setting, XML files you can edit
- **No dependencies** — pure Python standard library, nothing to install

## Requirements

- Autodesk Fusion 360 (Windows or macOS), any recent version
- Nothing else — the add-in uses only Python modules that ship with Fusion

## Installation

1. Copy the `Dovetail` folder into the Fusion add-ins directory:

   | OS | Path |
   |---|---|
   | Windows | `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` |
   | macOS | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` |

2. In Fusion: **Utilities → ADD-INS → Add-Ins**, select the entry, tick *Run on Startup*, press **Run**.
3. The button appears on the **SKETCH** tab in the **CREATE** panel, with the installed version in brackets after its name — *Dovetail (1.4.1)* — so the dialog title says which version you are on.

Keep the folder name and the file names in sync — Fusion requires `<Folder>/<Folder>.py` and `<Folder>/<Folder>.manifest` to match.

## Usage

1. Open or edit a sketch.
2. Click a line.
3. Click the dovetail icon — the line you clicked is already filled into the dialog.
4. Set the values, watch the preview, press **OK**.

## Dialog

| Field | Meaning |
|---|---|
| **Line** | The sketch line the teeth sit on. Pre-filled from the current selection. |
| **Count** | Number of teeth, 1 – 500, centred on the line. |
| **Mirror geometry** | Makes the two parts identical. Rounds the count up to even and pins the split to the centre line with no offset. |
| **Shape** | `Trapezoid` (default, real dovetail with undercut), `Triangle`, `Rectangle` (box joint). |
| **Width (base)** | Width of the tooth where it meets the line. |
| **Depth** | How far the tooth stands off the line. |
| **Flank angle** | Trapezoid only: how much the tooth widens towards its tip. Default 15°, range ±89°. At 0° it becomes a rectangle. |
| **Spacing** | Two teeth or more: centre-to-centre distance. |
| **Offset** | Shift of the whole set along the line. 0 = centred. Type a value or use the buttons. |
| **Step size** | How far one click of ◀ / ▶ moves. Default 1 mm. |
| **Move ◀ ▮ ▶** | ◀ towards the start point, ▶ towards the end point, the middle button resets to the centre. |
| **Tolerance** | Clearance between the two parts. Default **0.25 mm**, and it has to be above 0 — the band is made of it. |
| **The line is** | `Centre line` (default, half the tolerance each side), `Pocket edge` (all of it on the pin), `Pin edge` (all of it on the pocket). |
| **Flip direction** | Teeth to the other side of the line. |
| **Turn the original line into construction geometry** | On by default. The band spans across the line, so leaving the line as normal geometry cuts the band into two profiles. |

## Alignment

The set is always symmetric about the **midpoint of the selected line**:

| Count | Position relative to the midpoint (spacing 30 mm) |
|---|---|
| 1 | `0` |
| 2 | `−15 / +15` |
| 3 | `−30 / 0 / +30` |
| 4 | `−45 / −15 / +15 / +45` |
| 5 | `−60 / −30 / 0 / +30 / +60` |

An odd count puts a tooth on the midpoint, an even count puts the gap there, and the centre of gravity of the group lands exactly on the midpoint either way.

**Offset** moves away from that. The ◀ / ▶ buttons clamp themselves to the range in which the teeth still fit entirely on the line, so holding one down parks the set against the end instead of producing an invalid sketch. The offset resets to 0 on every invocation — it belongs to the line at hand, not to the settings.

## How the tolerance works

Two contours are built from the same zero-clearance outline: the **pocket**, offset outwards, and the **pin**, offset inwards. They are joined at both ends into one closed loop — the band between them is the clearance, and it is the full tolerance everywhere: base face, both flanks, over the tip.

**The line is** decides how that tolerance is split. With a 0.25 mm tolerance:

| Setting | Pocket sits at | Pin sits at | Gap |
|---|---|---|---|
| `Centre line` (default) | +0.125 mm | −0.125 mm | 0.25 mm |
| `Pocket edge` | on the line | −0.25 mm | 0.25 mm |
| `Pin edge` | +0.25 mm | on the line | 0.25 mm |

Centred is what you want when the line is the middle of the joint and both halves should stay the size you drew them. The other two are for when the line *is* one part's edge and only the other may lose material.

## Mirror geometry

Tick it and half the teeth point one way, half the other, arranged so that turning the contour 180° about the midpoint of the line maps it onto itself. Both parts of the cut then come out **identical** — model once, export once, print twice and turn the second one round.

```
   ___                 ___
  /   \               /   \        4 teeth, mirrored
──┘     └───┬───┬───┴─┘     └──
            │   │
            └───┘
```

Three things break that symmetry, so the dialog sets them for you and greys them out:

| Needs | Why |
|---|---|
| An **even** count | A tooth on the midpoint would have to point both ways at once. |
| The **centre line** split | Only there do both parts give up the same amount; on an edge split one part stays nominal and the other loses everything. |
| **No offset** | Shifting the group moves the symmetry point off the midpoint of the line. |

The test suite checks the real invariant: turning the pocket contour 180° produces the pin contour exactly, for 2, 4, 6 and 8 teeth.

## Turning the band into two parts

1. Draw the outline of the whole piece, with the joint line running across it.
2. Run the command on that line.
3. Extrude the outline into a solid.
4. Extrude-cut the band through it.

What is left are two bodies that mate with the tolerance you asked for. The original line becomes construction geometry so it does not cut the band in half — its dimensions and constraints survive, which deleting it would not.

## Languages

The UI language comes from **Preferences → General → User Language** in Fusion. German, English, Spanish, French and Italian are included; anything else falls back to English.

The strings live in `Dovetail/lang/<code>.xml`, one file per language:

```xml
<string key="in.width">Width (base)</string>
```

`en.xml` is the reference — every key exists there, and a key missing from another file falls back to it. To add a language, copy `en.xml`, translate the values, name it after the two-letter code and add the code to `SUPPORTED_LANGUAGES` and `FUSION_LANGUAGE_MAP` in `Dovetail.py`. The placeholders `{0}` must survive translation; `tools/test_geometry.py` checks that for every file.

Nothing outside these files is translated. Identifiers, comments and keys are English throughout, so a translator never has to touch the code.

## How it works

1. The selected line gives an origin (its start point), a direction `u` and a normal `n`. Everything is computed in that 2D frame, `s` along the line and `h` perpendicular to it, then transformed back into sketch space. The line's own orientation therefore does not matter, and *flip direction* is simply `n → −n`.
2. `build_contours()` places the tooth centres symmetrically around `length / 2 + offset` and walks the outline: base point, tip (one point for a triangle, two for a trapezoid or rectangle), base point, for every tooth, joined by the flat stretches that lie on the line.
3. `_offset_polyline()` moves every segment sideways by the tolerance and intersects consecutive offset segments to get the mitred corners. A corner whose mitre runs more than twelve times the offset distance away from the original vertex is rejected rather than drawn — that is a tooth so sharp that the offset has nowhere sensible to go.
4. The result is checked before anything is drawn: teeth inside the line, no overlap, a tooth that survives the tolerance. Failures raise a `GeometryError` carrying a language-independent key, which `validateInputs` turns into a disabled OK button and the message under the dialog.
5. Drawing happens with `isComputeDeferred` set, and each segment reuses the previous segment's end point, so the polyline comes out connected rather than as loose lines.

## Notes & caveats

- **The band needs a tolerance above 0.** At zero the two contours coincide and there is no area to enclose, so the command refuses rather than drawing a degenerate loop.
- **The line has to stop making profiles.** Fusion detects profiles geometrically, so a normal line crossing the band splits it in two. Converting it to construction geometry is the fix, and it keeps the dimensions and constraints that deleting the line would throw away.
- **A triangle is not a dovetail.** It has no undercut; it is a wedge and will pull apart under load. It is included because it is the simplest shape that indexes two parts against each other, not because it holds. Use the trapezoid where the joint has to resist tension.
- **The preview does not delete the original line.** Deleting the selected entity during `executePreview` risks invalidating the selection, so the preview draws the contour over the line and only `execute` removes it. The preview therefore looks marginally busier than the result.
- **Tolerance is clearance, not shrinkage compensation.** For FDM prints, 0.2 – 0.3 mm is a reasonable start; elephant's foot and over-extrusion on the first layers come on top and are not modelled here.
- **Upgrading from 1.1.x means deleting the old folder.** Up to 1.1.0 the add-in was called `Schwalbenschwanz`. Stop it in Fusion first, remove the old folder from the add-ins directory, then install `Dovetail` — otherwise both register and you get two buttons.

## Development

The geometry is pure mathematics with no Fusion dependency, so it can be tested from a normal Python installation. The test stubs the `adsk` modules, imports the add-in and checks point positions, the parallel-offset property, alignment, offset limits, every error key and all five language files:

```bash
python tools/test_geometry.py
```

The icons are generated, not drawn by hand — PNG writing via `zlib` and `struct`, no third-party imaging library:

```bash
python tools/make_icons.py
```

```bash
python tools/make_arrow_icons.py
```

All three scripts resolve paths relative to the repository. Set `DOVETAIL_ADDIN_DIR` to point them at an installed copy instead.

## Support this project ❤️

If this add-in saved you time, you can support further development:

[![Donate with PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate/?hosted_button_id=6CDEVZGJWTNQQ)

**[➡️ Donate via PayPal](https://www.paypal.com/donate/?hosted_button_id=6CDEVZGJWTNQQ)**

## License

This project is licensed under the [MIT License](LICENSE) — © 2026 Thomas Weirich.
