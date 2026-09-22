# Changelog

## Unreleased – 2026-09-22

- Layout after the project standard: the add-in lives in `apps/desktop/Dovetail/`, unchanged inside (Fusion needs
  folder, `.py` and `.manifest` under one name). Its version is also in `apps/desktop/VERSION`.
- The tests moved to `apps/desktop/tests/test_geometry.py`. `tools/make_icons.py` and `tools/make_arrow_icons.py`
  stay in `tools/` and write the icons into `apps/desktop/Dovetail/resources/`; `DOVETAIL_ADDIN_DIR` works as before.
- Compatibility: `python tools/test_geometry.py` still works and runs the moved tests.
- README rewritten: start in 3 steps, shorter sections, every path after the new layout.
- README no longer claims the dialog says which value or line is at fault — it only greys out OK and draws nothing.
- New `CHANGELOG.md`; `.gitignore` after the project standard.

Earlier versions: [Releases](https://github.com/sorglos-it/fusion360-dovetail/releases).
