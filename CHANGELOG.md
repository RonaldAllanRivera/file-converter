# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2025-09-12
### Removed
- Commit helper UI from `main.py` at the user's request.

### Docs
- README updated to remove mention of the Commit panel.

## [0.3.0] - 2025-09-17
### Added
- Image converters and UI mode selector:
  - WEBP → PNG (Pillow)
  - ICO → PNG (Pillow; selects largest icon size)
  - SVG → PNG (CairoSVG if installed; fallback to Inkscape CLI on PATH)
- Updated `requirements.txt` to include Pillow; documented optional CairoSVG.
- README updated with new features, usage steps, and commands.

## [0.3.1] - 2025-09-17
### Added
- Strict file picker filtering: the "Add Files" dialog now only allows the extension matching the selected conversion type (no "All files").
- "Add Folder" button: import all matching files recursively from a selected folder based on the current conversion type.

### Changed
- Conversion run filters the selected list to the current mode and logs skipped non-matching files if the mode was changed later.

## [0.3.2] - 2025-09-17
### Docs
- README title and overview updated to reflect multi-format support (Video & Image).
- Added detailed SVG conversion notes: CairoSVG vs Inkscape, verification commands, and PyInstaller bundling guidance.
- Project structure section updated to mention image converters and mode selector.

## [0.3.3] - 2025-10-03
### Added
- MOV -> GIF conversion mode using the same FFmpeg-based GIF pipeline as MP4.
- File picker and folder import now support `*.mov` when MOV -> GIF is selected.
- "Max GIF size" control applies to both MP4 and MOV modes.

## [0.3.4] - 2025-10-03
### Removed
- SVG -> PNG converter and all SVG-related dependencies/notes to simplify setup on Windows.

### Changed
- Cleaned up UI and logs to remove CairoSVG/Inkscape checks.
- README and requirements trimmed accordingly.

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
