import os
import sys
import threading
import queue
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from converter import (
    convert_mp4_to_gif,
    check_ffmpeg_available,
    convert_webp_to_png,
    convert_ico_to_png,
)


APP_TITLE = "Multi File Converter"
DEFAULT_SIZE_MB = 5.0


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x600")
        self.minsize(800, 520)

        self.file_list = []  # list[str]
        base_sites = r"E:\\Sites"
        today_folder = time.strftime("%Y-%m-%d")
        self.output_dir = os.path.join(base_sites, today_folder)
        os.makedirs(self.output_dir, exist_ok=True)

        self.log_queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker_thread = None
        self.start_btns = []  # track multiple Convert buttons
        self.cancel_btns = []  # track multiple Cancel buttons

        self._build_ui()
        self._schedule_log_pump()

        if not check_ffmpeg_available():
            messagebox.showwarning(
                "FFmpeg not found",
                "FFmpeg is required. Please install FFmpeg and ensure 'ffmpeg' and 'ffprobe' are available on PATH.\n\n"
                "Windows quick steps:\n"
                "1) Download from https://www.gyan.dev/ffmpeg/builds/ (full or essentials).\n"
                "2) Extract and add the 'bin' folder to your System PATH.\n"
                "3) Restart your terminal/IDE."
            )
        # Log environment info (no SVG dependencies required)
        try:
            self.log(f"Python: {sys.version.split()[0]} @ {sys.executable}")
        except Exception:
            pass

    def _build_ui(self):
        # Top controls frame
        top = ttk.Frame(self, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        # File controls
        file_controls = ttk.LabelFrame(top, text="Files", padding=10)
        file_controls.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        btn_add = ttk.Button(file_controls, text="Add Files", command=self.add_files)
        btn_add.grid(row=0, column=0, sticky="w")

        btn_remove = ttk.Button(file_controls, text="Remove Selected", command=self.remove_selected)
        btn_remove.grid(row=0, column=1, padx=5, sticky="w")

        btn_clear = ttk.Button(file_controls, text="Clear List", command=self.clear_list)
        btn_clear.grid(row=0, column=2, sticky="w")

        btn_add_folder = ttk.Button(file_controls, text="Add Folder", command=self.add_folder)
        btn_add_folder.grid(row=0, column=3, padx=5, sticky="w")

        # Output controls
        out_controls = ttk.LabelFrame(top, text="Output", padding=10)
        out_controls.pack(side=tk.RIGHT, fill=tk.Y)

        # Conversion type selector
        ttk.Label(out_controls, text="Conversion type:").grid(row=0, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="MP4 -> GIF")
        mode_combo = ttk.Combobox(
            out_controls,
            textvariable=self.mode_var,
            values=["MP4 -> GIF", "MOV -> GIF", "WEBP -> PNG", "ICO -> PNG"],
            state="readonly",
            width=20,
        )
        mode_combo.grid(row=0, column=1, sticky="w", padx=(5, 0))
        mode_combo.bind("<<ComboboxSelected>>", lambda e: self.on_mode_change())

        ttk.Label(out_controls, text="Output folder:").grid(row=1, column=0, sticky="w")
        self.output_var = tk.StringVar(value=self.output_dir)
        out_entry = ttk.Entry(out_controls, textvariable=self.output_var, width=45)
        out_entry.grid(row=2, column=0, pady=2)
        ttk.Button(out_controls, text="Browse", command=self.choose_output_dir).grid(row=2, column=1, padx=5)
        ttk.Button(out_controls, text="Open", command=self.open_output_dir).grid(row=2, column=2)

        ttk.Label(out_controls, text="Max GIF size (MB):").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.size_var = tk.StringVar(value=str(DEFAULT_SIZE_MB))
        self.size_entry = ttk.Entry(out_controls, textvariable=self.size_var, width=10)
        self.size_entry.grid(row=4, column=0, sticky="w")

        # Extra controls (top-right) for visibility: Convert / Cancel
        top_buttons = ttk.Frame(out_controls)
        top_buttons.grid(row=5, column=0, columnspan=3, pady=(8, 0), sticky="e")
        top_cancel = ttk.Button(top_buttons, text="Cancel", command=self.cancel_conversion, state=tk.DISABLED)
        top_cancel.pack(side=tk.RIGHT, padx=5)
        top_convert = ttk.Button(top_buttons, text="Convert to GIF", command=self.start_conversion)
        top_convert.pack(side=tk.RIGHT)
        self.cancel_btns.append(top_cancel)
        self.start_btns.append(top_convert)

        # Middle lists/logs
        middle = ttk.Frame(self, padding=(10, 0, 10, 0))
        middle.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        files_frame = ttk.LabelFrame(middle, text="Selected Files", padding=10)
        files_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=5)

        self.files_listbox = tk.Listbox(files_frame, selectmode=tk.EXTENDED)
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        files_scroll = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        files_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.files_listbox.config(yscrollcommand=files_scroll.set)

        log_frame = ttk.LabelFrame(middle, text="Log", padding=10)
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        # Bottom actions
        bottom = ttk.Frame(self, padding=10)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)

        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_var = tk.StringVar(value="Idle")
        self.status_lbl = ttk.Label(bottom, textvariable=self.status_var)
        self.status_lbl.pack(side=tk.LEFT, padx=10)

        self.start_btn = ttk.Button(bottom, text="Convert to GIF", command=self.start_conversion)
        self.start_btn.pack(side=tk.RIGHT)
        self.start_btns.append(self.start_btn)

        self.cancel_btn = ttk.Button(bottom, text="Cancel", command=self.cancel_conversion, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.RIGHT, padx=5)
        self.cancel_btns.append(self.cancel_btn)

    # File operations
    def _allowed_exts(self, mode: str):
        return {
            "MP4 -> GIF": {".mp4"},
            "MOV -> GIF": {".mov"},
            "WEBP -> PNG": {".webp"},
            "ICO -> PNG": {".ico"},
        }.get(mode, set())

    def _mode_key(self) -> str:
        """Return one of: 'mp4', 'mov', 'webp', 'ico' based on current combobox text.
        This is resilient to minor label text changes.
        """
        val = (self.mode_var.get() or "").upper()
        if "MOV" in val:
            return "mov"
        if "WEBP" in val:
            return "webp"
        if "ICO" in val:
            return "ico"
        return "mp4"

    def add_files(self):
        mode = self.mode_var.get()
        key = self._mode_key()
        # Debug log to help user verify the active mode
        self.log(f"Add Files for mode: {mode}")
        if key == "mp4":
            filetypes = [("MP4 files", "*.mp4")]
        elif key == "mov":
            filetypes = [("MOV files", "*.mov")]
        elif key == "webp":
            filetypes = [("WEBP images", "*.webp")]
        else:  # ico
            filetypes = [("ICO files", "*.ico")]

        paths = filedialog.askopenfilenames(
            title="Select files",
            filetypes=filetypes,
        )
        if not paths:
            return
        added = 0
        allowed = {f".{key}"} if key in {"mp4", "mov", "webp", "ico"} else self._allowed_exts(mode)
        for p in paths:
            ext = os.path.splitext(p.lower())[1]
            if ext in allowed and p not in self.file_list:
                self.file_list.append(p)
                self.files_listbox.insert(tk.END, p)
                added += 1
        if added:
            self.log(f"Added {added} files.")

    def add_folder(self):
        """Add all files from a selected folder that match the current mode's extension.
        Recurses into subfolders.
        """
        d = filedialog.askdirectory(title="Select folder containing files")
        if not d:
            return
        mode = self.mode_var.get()
        allowed = {
            "MP4 -> GIF": {".mp4"},
            "MOV -> GIF": {".mov"},
            "WEBP -> PNG": {".webp"},
            "ICO -> PNG": {".ico"},
        }.get(mode, set())
        added = 0
        for root, _, files in os.walk(d):
            for name in files:
                ext = os.path.splitext(name.lower())[1]
                if ext in allowed:
                    p = os.path.join(root, name)
                    if p not in self.file_list:
                        self.file_list.append(p)
                        self.files_listbox.insert(tk.END, p)
                        added += 1
        if added:
            self.log(f"Added {added} files from folder.")

    def remove_selected(self):
        sel = list(self.files_listbox.curselection())
        if not sel:
            return
        sel.reverse()
        for idx in sel:
            path = self.files_listbox.get(idx)
            self.files_listbox.delete(idx)
            try:
                self.file_list.remove(path)
            except ValueError:
                pass
        self.log("Removed selected files.")

    def clear_list(self):
        self.files_listbox.delete(0, tk.END)
        self.file_list.clear()
        self.log("Cleared file list.")

    def choose_output_dir(self):
        d = filedialog.askdirectory(title="Choose output folder", initialdir=self.output_var.get())
        if d:
            self.output_var.set(d)
            self.output_dir = d
            os.makedirs(self.output_dir, exist_ok=True)

    def open_output_dir(self):
        d = self.output_var.get()
        if not os.path.isdir(d):
            messagebox.showerror("Error", "Output folder does not exist.")
            return
        if sys.platform.startswith("win"):
            os.startfile(d)
        elif sys.platform == "darwin":
            os.system(f"open '{d}'")
        else:
            os.system(f"xdg-open '{d}'")

    # Logging utilities
    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._append_log(f"[{ts}] {msg}\n")

    def _append_log(self, msg: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _schedule_log_pump(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._schedule_log_pump)

    def _logger_cb(self, message: str):
        self.log_queue.put(message + "\n")

    # Conversion workflow
    def start_conversion(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Busy", "A conversion is already running.")
            return
        if not self.file_list:
            messagebox.showwarning("No files", "Please add files to convert.")
            return
        mode = self.mode_var.get()
        max_mb = DEFAULT_SIZE_MB
        if mode in ("MP4 -> GIF", "MOV -> GIF"):
            try:
                max_mb = float(self.size_var.get())
                if max_mb <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid size", "Please enter a positive number for Max GIF size (MB).")
                return

        self.output_dir = self.output_var.get().strip() or self.output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Only process files matching the current mode in case the user changed modes after selecting
        allowed = self._allowed_exts(mode)
        files_to_process = [p for p in self.file_list if os.path.splitext(p.lower())[1] in allowed]
        skipped = len(self.file_list) - len(files_to_process)
        if skipped > 0:
            self.log(f"Skipping {skipped} non-matching file(s) for '{mode}'.")
        if not files_to_process:
            messagebox.showwarning("No valid files", f"No files match the selected type: {mode}.")
            return

        self.progress.configure(maximum=len(files_to_process), value=0)
        self.status_var.set("Starting...")
        self._set_buttons_state(start_state=tk.DISABLED, cancel_state=tk.NORMAL)
        self.cancel_event.clear()

        args = (files_to_process, self.output_dir, max_mb, mode)
        self.worker_thread = threading.Thread(target=self._run_conversion, args=args, daemon=True)
        self.worker_thread.start()

    def cancel_conversion(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.cancel_event.set()
            self.status_var.set("Cancelling...")
            self.log("Cancellation requested. Waiting for current file to finish...")

    def _run_conversion(self, files, out_dir, max_mb, mode):
        successes = 0
        for idx, src in enumerate(files, start=1):
            if self.cancel_event.is_set():
                break
            base = os.path.splitext(os.path.basename(src))[0]
            if mode in ("MP4 -> GIF", "MOV -> GIF"):
                dst = os.path.join(out_dir, f"{base}.gif")
                self.log_queue.put(f"Converting: {src} -> {dst}\n")
                try:
                    convert_mp4_to_gif(
                        input_path=src,
                        output_path=dst,
                        max_size_mb=max_mb,
                        fast_first=True,
                        max_attempts=2,
                        palette_sample_sec=6.0,
                        logger=self._logger_cb,
                    )
                    self.log_queue.put(f"Done: {dst}\n")
                    successes += 1
                except Exception as e:
                    self.log_queue.put(f"Error: {e}\n")
            elif mode == "WEBP -> PNG":
                dst = os.path.join(out_dir, f"{base}.png")
                self.log_queue.put(f"Converting: {src} -> {dst}\n")
                try:
                    convert_webp_to_png(src, dst, logger=self._logger_cb)
                    self.log_queue.put(f"Done: {dst}\n")
                    successes += 1
                except Exception as e:
                    self.log_queue.put(f"Error: {e}\n")
            else:  # ICO -> PNG
                dst = os.path.join(out_dir, f"{base}.png")
                self.log_queue.put(f"Converting: {src} -> {dst}\n")
                try:
                    convert_ico_to_png(src, dst, logger=self._logger_cb)
                    self.log_queue.put(f"Done: {dst}\n")
                    successes += 1
                except Exception as e:
                    self.log_queue.put(f"Error: {e}\n")

            # Progress update back on UI thread
            self.after(0, lambda v=idx: self.progress.configure(value=v))
            self.after(0, lambda s=f"Processed {idx}/{len(files)}": self.status_var.set(s))

        def finalize():
            self._set_buttons_state(start_state=tk.NORMAL, cancel_state=tk.DISABLED)
            if self.cancel_event.is_set():
                self.status_var.set(f"Cancelled. {successes}/{len(files)} completed")
            else:
                self.status_var.set(f"Finished. {successes}/{len(files)} completed")

        self.after(0, finalize)

    def on_mode_change(self):
        mode = self.mode_var.get()
        # Toggle GIF size inputs
        if mode in ("MP4 -> GIF", "MOV -> GIF"):
            try:
                self.size_entry.configure(state=tk.NORMAL)
            except Exception:
                pass
        else:
            try:
                self.size_entry.configure(state=tk.DISABLED)
            except Exception:
                pass
        # Update Convert button labels
        label = "Convert to GIF" if mode in ("MP4 -> GIF", "MOV -> GIF") else "Convert to PNG"
        for b in self.start_btns:
            try:
                b.configure(text=label)
            except Exception:
                pass

    def _set_buttons_state(self, start_state, cancel_state):
        # Update all mirrored buttons' states
        for b in self.start_btns:
            try:
                b.configure(state=start_state)
            except Exception:
                pass
        for b in self.cancel_btns:
            try:
                b.configure(state=cancel_state)
            except Exception:
                pass


if __name__ == "__main__":
    app = App()
    app.mainloop()
