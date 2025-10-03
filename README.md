# Multi File Converter (Video & Image)

A lightweight Python Tkinter app to batch-convert video and images:
- MP4/MOV → GIF with a configurable size cap (default 5 MB)
- WEBP/ICO → PNG
Built for speed, small outputs, and simple batch workflows.

Currently implemented:
- MP4 -> GIF batch conversion
- MOV -> GIF batch conversion
- WEBP -> PNG image conversion
- ICO -> PNG image conversion
- Multi-file selection and progress display
- Web-optimized GIF pipeline (palettegen + paletteuse, lanczos scaling, sierra2_4a dithering)
- Fast-first strategy to meet a target size (default 5 MB)
- Output folder selection and quick open

Planned next:
- Additional formats and presets

## Requirements
- Python 3.9+
- Tkinter (ships with most Python installers)
- FFmpeg on PATH (only needed for MP4/MOV -> GIF)
- Pillow (image conversions)
- Optional: PyInstaller to build a Windows .exe

Install Python deps:
```powershell
python -m pip install -r requirements.txt
```
 

### Install FFmpeg (Windows)
1. Download a build from: https://www.gyan.dev/ffmpeg/builds/
2. Extract the archive and locate the `bin/` folder containing `ffmpeg.exe` and `ffprobe.exe`.
3. Add that `bin/` folder to your System PATH.
4. Restart your terminal/IDE.

### Verify FFmpeg
```bash
ffmpeg -version
ffprobe -version
```

## Setup
Clone or copy this folder, then simply run:

```bash
python main.py
```

## Usage
1. Pick a Conversion type from the dropdown (MP4 -> GIF, MOV -> GIF, WEBP -> PNG, ICO -> PNG).
2. Click "Add Files" to select one or more inputs.
   - The file dialog only allows the extension for the current type (e.g., `*.webp` when WEBP -> PNG is selected).
   - Optionally click "Add Folder" to import all matching files from a folder (recursively) according to the selected type.
3. Choose an output folder (defaults to `E:\\Sites\\<YYYY-MM-DD>`; it is created on first run).
4. If using MP4/MOV -> GIF, set the "Max GIF size (MB)" (defaults to 5.0).
5. Click "Convert" (label changes depending on the type).
6. Watch the log and progress. Click "Open" to open the output folder.



## How size limiting works
The converter uses a fast-first strategy to hit your size cap quickly:
- Probes the input with ffprobe to estimate duration.
- Predicts width, fps, and palette size to meet the cap.
- Generates the color palette from only the first ~6 seconds for speed.
- Attempts a maximum of 2 encodes per file (1 predicted + 1 fallback).

If needed, it may still trade visual fidelity for size using these levers:
- Scale down width (starting at 480 px, in ~15% steps; minimum 240 px)
- Lower frame rate (starting at 12 fps, down to 6 fps)
- Reduce color palette (256 → 192 → 160 → 128 → 96 → 64 colors)
- Use palettegen/paletteuse for high perceptual quality at small sizes
- Use `lanczos` scaling and `sierra2_4a` dithering for crisp yet small outputs

If the cap cannot be reached even at the lowest settings, the smallest produced GIF is kept and a warning is logged.

## Notes
- GIFs are looped by default (`-loop 0`).
- The palette pipeline avoids color banding and yields smaller files than naive encodes.
- Some inputs with very high motion/details may not reach extremely small sizes without aggressive downscaling.

## Troubleshooting
- If you see "FFmpeg is not available on PATH", install FFmpeg and restart your terminal/IDE.
- If the UI freezes, ensure you have not forcibly closed the window while a conversion is ongoing; the app runs conversions in a background thread to keep the UI responsive.

## Project Structure
- `main.py`: Tkinter GUI with batch controls, mode selector, and logging
- `converter.py`: Converters for MP4 → GIF (FFmpeg) and WEBP/ICO → PNG
- Default destination: `E:\\Sites\\<YYYY-MM-DD>` (created on first run)

---

## Build a Windows .exe (PyInstaller)
Install PyInstaller and build:

```powershell
# Install PyInstaller in your (activated) venv
python -m pip install pyinstaller

# Build a single-file, windowed executable (no icon)
py -m PyInstaller --name FileConverter --windowed --onefile main.py
```

### Build with a custom icon
1. Place your icon at `assets\\app.ico`. If you have a PNG, you can create an ICO with Pillow:
   ```powershell
   # Convert a PNG to multi-size ICO (requires Pillow, already in requirements)
   python -c "from PIL import Image; Image.open('assets\\app.png').save('assets\\app.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
   ```
2. Build the .exe with the icon:
   ```powershell
   py -m PyInstaller --name FileConverter --windowed --onefile --icon assets\\app.ico main.py
   ```

#### No icon (use default)
- If you don't specify `--icon`, PyInstaller embeds its default generic app icon. Use:
  ```powershell
  py -m PyInstaller --name FileConverter --windowed --onefile main.py
  ```

#### Generate a simple icon without uploading assets
Create a tiny script to produce an ICO (blue background with "FC" text) using Pillow:

1) Save as `tools\\gen_icon.py`:
```python
import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs('assets', exist_ok=True)
sizes = [16, 32, 48, 64, 128, 256]
images = []
for s in sizes:
    img = Image.new('RGBA', (s, s), '#1D4ED8')  # blue
    d = ImageDraw.Draw(img)
    text = 'FC'
    try:
        font = ImageFont.truetype('arial.ttf', int(s * 0.5))
    except Exception:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((s - w) / 2, (s - h) / 2), text, font=font, fill='white')
    images.append(img)

images[0].save('assets/app.ico', sizes=[(s, s) for s in sizes])
print('Wrote assets/app.ico')
```

2) Run the generator, then build with the new icon:
```powershell
python tools\gen_icon.py
py -m PyInstaller --name FileConverter --windowed --onefile --icon assets\app.ico main.py
```

#### Troubleshooting: icon not updating
- **Clean rebuild with icon**
  ```powershell
  # From project root
  Remove-Item -Recurse -Force build, dist -ErrorAction Ignore
  Remove-Item -Force FileConverter.spec -ErrorAction Ignore

  py -m PyInstaller --clean -y --name FileConverter --windowed --onefile --icon assets\app.ico main.py
  ```

- **Build under a new name (bypass cache)**
  ```powershell
  py -m PyInstaller --clean -y --name FileConverter_Icon --windowed --onefile --icon assets\app.ico main.py
  ```

- **Refresh Explorer’s icon cache** (if the file still shows the old icon)
  ```powershell
  ie4uinit.exe -ClearIconCache
  taskkill /IM explorer.exe /F
  Start-Process explorer.exe
  ```

- **Verify the .ico is valid (not a PNG renamed)**
  ```powershell
  # Recreate a proper multi-size ICO from a PNG (if you have one)
  $code = @'
  from PIL import Image
  Image.open("assets/app.png").save("assets/app.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
  '@
  $code | python -
  ```

#### Quick one-liner (no script, no PNG)
Generate a fresh simple icon directly from Python, then rebuild:

```powershell
# Create a random-color 'FC' icon and build the exe
python - <<'PY'
from PIL import Image, ImageDraw, ImageFont
import os, random
os.makedirs('assets', exist_ok=True)
sizes = [16,32,48,64,128,256]
bg = random.choice(['#1D4ED8','#047857','#DC2626','#7C3AED','#EA580C','#0EA5E9'])
imgs = []
for s in sizes:
    im = Image.new('RGBA', (s, s), bg)
    d = ImageDraw.Draw(im)
    text = 'FC'
    try:
        font = ImageFont.truetype('arial.ttf', int(s*0.55))
    except Exception:
        font = ImageFont.load_default()
    try:
        bbox = d.textbbox((0,0), text, font=font)
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    except Exception:
        w, h = d.textlength(text, font=font), int(s*0.6)
    d.text(((s-w)/2, (s-h)/2), text, font=font, fill='white')
    imgs.append(im)
imgs[0].save('assets/app.ico', sizes=[(s,s) for s in sizes])
print('Wrote assets/app.ico with bg', bg)
PY

py -m PyInstaller --name FileConverter --windowed --onefile --icon assets\app.ico main.py
```

You will get:
- `dist\\FileConverter.exe`

Notes:
- The .exe expects FFmpeg (`ffmpeg`, `ffprobe`) to be available on PATH.

### Run the .exe
```powershell
./dist/FileConverter.exe
```

## Commands quick reference
```powershell
# 1) Create and activate venv
python -m venv .venv
. .\\.venv\\Scripts\\Activate

# 2) Install requirements
python -m pip install -r requirements.txt

# 3) Install FFmpeg (winget example)
winget install --id=Gyan.FFmpeg -e

# 4) Run the GUI (Python)
python main.py

# 5) Build Windows .exe
python -m pip install pyinstaller
py -m PyInstaller --name FileConverter --windowed --onefile main.py

# 6) Run the .exe
./dist/FileConverter.exe
```
