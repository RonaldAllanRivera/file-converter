# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2025-09-12
### Removed
- Commit helper UI from `main.py` at the user's request.

### Docs
- README updated to remove mention of the Commit panel.

## [0.2.0] - 2025-09-12
### Added
- Fast-first MP4 → GIF conversion strategy in `converter.py`:
  - Probes video with ffprobe to estimate duration.
  - Predicts width/fps/colors to hit size cap quickly.
  - Limits palette generation to first ~6 seconds for performance.
  - Caps attempts to 2 per file (predicted + fallback).
- Default output directory now `E:\Sites\<YYYY-MM-DD>` and auto-created on startup.
- Top-right "Convert to GIF" and "Cancel" buttons for better visibility.
- Commit helper panel in the UI with prefilled commit message and "Copy to Clipboard".
- README updated with .exe build/run commands using PyInstaller.

### Changed
- Reduced total attempts from exhaustive grid search to fast-first (significant speedup on long videos).

### Notes
- If the 5 MB target cannot be reached even at lowest settings, the smallest result is kept and a warning is logged.

## [0.1.0] - 2025-09-12
### Added
- Initial Tkinter GUI app for batch MP4 → GIF conversion.
- Web-optimized GIF pipeline (palettegen + paletteuse, lanczos scaling, sierra2_4a dithering).
- Iterative compression to meet a target size (default 5 MB).
- Multi-file selection, output selection, progress, and logs.
