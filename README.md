# fusion360-dovetail

[![Fusion 360](https://img.shields.io/badge/Autodesk-Fusion%20360-F60?logo=autodesk&logoColor=white)](#requirements)
[![Type](https://img.shields.io/badge/type-add--in-0b7285.svg)](#installation)
[![Languages](https://img.shields.io/badge/UI-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR%20%7C%20IT-4c1.svg)](#languages)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-0078D6?logo=windows&logoColor=white)](#requirements)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Donate](https://img.shields.io/badge/Donate-PayPal-00457C.svg?logo=paypal)](https://www.paypal.com/donate/?hosted_button_id=6CDEVZGJWTNQQ)

A Fusion 360 add-in that turns **one sketch line into a finished joint**. Pick a line, press the button, and you get the nominal contour sitting on the line plus a second contour shrunk by the tolerance — the pocket and the pin, both ready to extrude, in a single sketch.

The tolerance is not a guess applied to one edge. The mating contour is a **true parallel offset of the whole outline**, so the clearance is identical on the base face, on both flanks and over the tip.

Three tooth shapes ship with it: the **trapezoid** dovetail with a real undercut (the default), a **triangle**, and a **rectangle** for box joints. The interface follows whatever language Fusion is set to.

## Features

- **One line in, two contours out** — nominal (pocket) and mating (pin), correct relative to each other by construction
- **Uniform clearance** — a real parallel offset, verified to the last floating-point digit by the test suite
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

1. Copy the `Schwalbenschwanz` folder into the Fusion add-ins directory:

   | OS | Path |
   |---|---|
   | Windows | `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` |
   | macOS | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` |

2. In Fusion: **Utilities → ADD-INS → Add-Ins**, select the entry, tick *Run on Startup*, press **Run**.
3. The button appears on the **SKETCH** tab in the **CREATE** panel.

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
| **Shape** | `Trapezoid` (default, real dovetail with undercut), `Triangle`, `Rectangle` (box joint). |
| **Width (base)** | Width of the tooth where it meets the line. |
| **Depth** | How far the tooth stands off the line. |
| **Flank angle** | Trapezoid only: how much the tooth widens towards its tip. Default 15°, range ±89°. At 0° it becomes a rectangle. |
| **Spacing** | Two teeth or more: centre-to-centre distance. |
| **Offset** | Shift of the whole set along the line. 0 = centred. Type a value or use the buttons. |
| **Step size** | How far one click of ◀ / ▶ moves. Default 1 mm. |
| **Move ◀ ▮ ▶** | ◀ towards the start point, ▶ towards the end point, the middle button resets to the centre. |
| **Tolerance** | Clearance between the two parts. Default **0.25 mm**. 0 skips the mating contour. |
| **Flip direction** | Teeth to the other side of the line. |
| **Create mating contour** | Draw the second, smaller contour. |
| **Replace the original line** | On: the line is deleted and the nominal contour runs end to end. Off: the line stays and only the tooth outlines are drawn. |

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

The mating contour is the nominal contour offset by the tolerance towards the pin side. That means, simultaneously:

- the base line drops by the tolerance below the selected line,
- both flanks move inwards by the tolerance,
- the tip loses the corresponding height.

Which gives the assignment:

- **Nominal contour** (on the line) → the part with the **pocket**
- **Mating contour** (the smaller one) → the part with the **pin**

Triangle, 10 mm wide, 6 mm deep, 0.25 mm tolerance: the mating tip sits at 5.609 mm instead of 6.000 mm, and the gap measured perpendicular to any flank is 0.25 mm.

## Languages

The UI language comes from **Preferences → General → User Language** in Fusion. German, English, Spanish, French and Italian are included; anything else falls back to English.

The strings live in `Schwalbenschwanz/lang/<code>.xml`, one file per language:

```xml
<string key="in.width">Width (base)</string>
```

`en.xml` is the reference — every key exists there, and a key missing from another file falls back to it. To add a language, copy `en.xml`, translate the values, name it after the two-letter code and add the code to `SUPPORTED_LANGUAGES` and `FUSION_LANGUAGE_MAP` in `Schwalbenschwanz.py`. The placeholders `{0}` must survive translation; `tools/test_geometry.py` checks that for every file.

## How it works

1. The selected line gives an origin (its start point), a direction `u` and a normal `n`. Everything is computed in that 2D frame, `s` along the line and `h` perpendicular to it, then transformed back into sketch space. The line's own orientation therefore does not matter, and *flip direction* is simply `n → −n`.
2. `build_contours()` places the tooth centres symmetrically around `length / 2 + offset` and walks the outline: base point, tip (one point for a triangle, two for a trapezoid or rectangle), base point, for every tooth, joined by the flat stretches that lie on the line.
3. `_offset_polyline()` moves every segment sideways by the tolerance and intersects consecutive offset segments to get the mitred corners. A corner whose mitre runs more than twelve times the offset distance away from the original vertex is rejected rather than drawn — that is a tooth so sharp that the offset has nowhere sensible to go.
4. The result is checked before anything is drawn: teeth inside the line, no overlap, a tooth that survives the tolerance. Failures raise a `GeometryError` carrying a language-independent key, which `validateInputs` turns into a disabled OK button and the message under the dialog.
5. Drawing happens with `isComputeDeferred` set, and each segment reuses the previous segment's end point, so the polyline comes out connected rather than as loose lines.

## Notes & caveats

- **Replacing the line drops its constraints.** Dimensions and relations attached to the original line die with it. The new contour starts and ends on the exact old endpoints, so adjacent geometry still closes into a profile — Fusion detects profiles geometrically, not from constraints.
- **A triangle is not a dovetail.** It has no undercut; it is a wedge and will pull apart under load. It is included because it is the simplest shape that indexes two parts against each other, not because it holds. Use the trapezoid where the joint has to resist tension.
- **The preview does not delete the original line.** Deleting the selected entity during `executePreview` risks invalidating the selection, so the preview draws the contour over the line and only `execute` removes it. The preview therefore looks marginally busier than the result.
- **Both contours land in the same sketch.** That is the point — they are two halves of one joint — but it does mean the sketch contains overlapping profiles. Extrude the outer one for the pocket part and the inner one for the pin part.
- **Tolerance is clearance, not shrinkage compensation.** For FDM prints, 0.2 – 0.3 mm is a reasonable start; elephant's foot and over-extrusion on the first layers come on top and are not modelled here.
- **The add-in folder is named `Schwalbenschwanz`.** That is only the identifier Fusion loads; the interface itself is translated. Renaming it means renaming the folder, the `.py` and the `.manifest` together.

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

All three scripts resolve paths relative to the repository. Set `SS_ADDIN_DIR` to point them at an installed copy instead.

## Support this project ❤️

If this add-in saved you time, you can support further development:

[![Donate with PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate/?hosted_button_id=6CDEVZGJWTNQQ)

**[➡️ Donate via PayPal](https://www.paypal.com/donate/?hosted_button_id=6CDEVZGJWTNQQ)**

## License

This project is licensed under the [MIT License](LICENSE) — © 2026 Thomas Weirich.
