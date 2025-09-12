import os
import shutil
import subprocess
import tempfile
from typing import Callable, Optional, Tuple


def _log(logger: Optional[Callable[[str], None]], message: str) -> None:
    if logger:
        try:
            logger(message)
        except Exception:
            # Never let logging crash conversion
            pass


def check_ffmpeg_available() -> bool:
    """Return True if ffmpeg is available on PATH."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except FileNotFoundError:
        return False


def _even(value: int) -> int:
    return value if value % 2 == 0 else value - 1


def _filesize_mb(path: str) -> float:
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0.0


def _attempt_encode(
    src: str,
    dst: str,
    width: int,
    fps: int,
    max_colors: int,
    palette_sample_sec: Optional[float] = None,
    logger: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Run a single ffmpeg encode using palettegen/paletteuse pipeline for high-quality, web-optimized GIFs.
    Returns (success, error_message)
    """
    # Ensure even width as some codecs/filters require this
    width = _even(width)

    # Create a temp palette path
    with tempfile.TemporaryDirectory() as tmpdir:
        palette_path = os.path.join(tmpdir, "palette.png")

        # 1) Generate palette
        palette_cmd = [
            "ffmpeg", "-v", "error", "-stats",
            "-y",
        ]
        # Optionally limit palette sampling time for speed
        if palette_sample_sec and palette_sample_sec > 0:
            palette_cmd += ["-t", str(palette_sample_sec)]
        palette_cmd += [
            "-i", src,
            "-vf",
            f"fps={fps},scale={width}:-1:flags=lanczos,palettegen=stats_mode=full:reserve_transparent=0:max_colors={max_colors}",
            palette_path,
        ]
        _log(logger, f"Generating palette (fps={fps}, width={width}, colors={max_colors})...")
        pal = subprocess.run(palette_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if pal.returncode != 0 or not os.path.exists(palette_path):
            return False, f"Palette generation failed: {pal.stdout.strip()}"

        # 2) Use palette to create gif
        # Use sierra2_4a dithering for good perceptual quality
        gif_cmd = [
            "ffmpeg", "-v", "error", "-stats",
            "-y",
            "-i", src,
            "-i", palette_path,
            "-filter_complex",
            f"fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse=new=1:dither=sierra2_4a",
            "-gifflags", "-offsetting",
            "-loop", "0",
            dst,
        ]
        _log(logger, "Encoding GIF...")
        enc = subprocess.run(gif_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if enc.returncode != 0:
            return False, f"GIF encoding failed: {enc.stdout.strip()}"

    return True, None


def _probe_video(input_path: str) -> Tuple[Optional[int], Optional[int], Optional[float], Optional[float]]:
    """Return (width, height, fps, duration) if available, else Nones."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path,
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
        # Expecting: width, height, r_frame_rate, duration (order may vary across ffprobe versions)
        w = h = None
        fps = None
        dur = None
        # Heuristically parse by looking for non-fraction ints for width/height, fraction for fps, float for duration
        for l in lines:
            if "/" in l and fps is None:
                try:
                    num, den = l.split("/", 1)
                    num = float(num); den = float(den) if float(den) != 0 else 1.0
                    fps = num / den if den else None
                    continue
                except Exception:
                    pass
            if "." in l and dur is None:
                try:
                    dur = float(l)
                    continue
                except Exception:
                    pass
            if w is None:
                try:
                    w = int(l)
                    continue
                except Exception:
                    pass
            if h is None:
                try:
                    h = int(l)
                    continue
                except Exception:
                    pass
        return w, h, fps, dur
    except Exception:
        return None, None, None, None


def convert_mp4_to_gif(
    input_path: str,
    output_path: str,
    max_size_mb: float = 5.0,
    initial_width: int = 480,
    initial_fps: int = 12,
    fast_first: bool = True,
    max_attempts: int = 3,
    palette_sample_sec: float = 6.0,
    logger: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Convert MP4 to GIF optimized for web. Iteratively compress to not exceed max_size_mb.

    Returns the path to the generated GIF.
    Raises RuntimeError on failure.
    """
    if not os.path.isfile(input_path):
        raise RuntimeError(f"Input file not found: {input_path}")

    if not check_ffmpeg_available():
        raise RuntimeError("FFmpeg is not available on PATH. Please install FFmpeg and ensure 'ffmpeg' and 'ffprobe' commands are accessible.")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Parameter search strategy (fast-first):
    # 0. Probe video to estimate reasonable starting parameters for the size cap.
    # 1. Try a single predicted encode aimed at the cap.
    # 2. If still too large, try at most (max_attempts-1) fallback attempts reducing fps/width/colors.
    # This avoids dozens of attempts and returns a result much faster.

    # Predict initial params based on duration
    pred_width = initial_width
    pred_fps = initial_fps
    pred_colors = 128

    w0, h0, fps0, dur = _probe_video(input_path)
    if dur is None:
        dur = 8.0  # assume short clip if unknown

    # Frame budget scales roughly with size cap
    frame_budget = max(120, int(240 * (max_size_mb / 5.0)))
    pred_fps = max(6, min(12, int(frame_budget / max(dur, 1))))

    # Choose width based on duration buckets
    if dur <= 6:
        pred_width = min(480, w0 or 480)
        pred_colors = 128
    elif dur <= 12:
        pred_width = min(400, (w0 or 400))
        pred_colors = 128
    elif dur <= 20:
        pred_width = min(360, (w0 or 360))
        pred_colors = 96
    elif dur <= 35:
        pred_width = min(320, (w0 or 320))
        pred_colors = 96
    else:
        pred_width = min(272, (w0 or 272))
        pred_colors = 64

    widths = []
    w = initial_width
    while w >= 240:
        widths.append(_even(w))
        w = int(w * 0.85)
    if 240 not in widths:
        widths.append(240)

    fps_candidates = [initial_fps]
    for f in range(initial_fps - 2, 5, -2):
        if f >= 6:
            fps_candidates.append(f)
    if 6 not in fps_candidates:
        fps_candidates.append(6)

    color_candidates = [256, 192, 160, 128, 96, 64]

    last_error = None
    attempts_done = 0

    def try_encode(width: int, fps: int, colors: int) -> Optional[float]:
        nonlocal last_error, attempts_done
        if attempts_done >= max_attempts:
            return None
        attempts_done += 1
        _log(logger, f"Attempt: width={width}, fps={fps}, colors={colors}")
        success, err = _attempt_encode(
            src=input_path,
            dst=output_path,
            width=width,
            fps=fps,
            max_colors=colors,
            palette_sample_sec=palette_sample_sec,
            logger=logger,
        )
        if not success:
            last_error = err
            _log(logger, f"Encode failed: {err}")
            return None
        size_mb = _filesize_mb(output_path)
        _log(logger, f"Result size: {size_mb:.2f} MB (limit {max_size_mb:.2f} MB)")
        return size_mb

    # Fast first attempt
    if fast_first:
        size_mb = try_encode(pred_width, pred_fps, pred_colors)
        if size_mb is not None and size_mb <= max_size_mb:
            _log(logger, "Success within size limit.")
            return output_path

    # Fallback attempts (at most max_attempts total)
    # 1) Reduce fps then width, with colors min at 64
    for (wf, ff, cf) in [
        (int(pred_width * 0.85), max(6, pred_fps - 2), max(64, pred_colors // 2)),
        (240, 6, 64),
    ]:
        size_mb = try_encode(max(240, _even(wf)), ff, cf)
        if size_mb is not None and size_mb <= max_size_mb:
            _log(logger, "Success within size limit.")
            return output_path

    # If we reach here, best we could do still exceeds size; keep the smallest result if any, else error
    if os.path.exists(output_path):
        _log(logger, "Warning: Could not reach size target. Keeping the most compressed version.")
        return output_path

    raise RuntimeError(last_error or "Failed to encode GIF.")
