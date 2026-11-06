import json
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox

import requests
from PIL import Image, ImageDraw, ImageTk

import core
from core import AUTO, FREE_LANGUAGES, LANG_NAMES, PRO_LANGUAGES
from glass_ui import (P, THEMES, set_theme, palette_snapshot, GlassCanvas, GlassButton, GlassSheet, GlassDialog, WindowControls,
                      borderless, show_main_window, minimize_window, pill_image, render_logo, enable_dpi_awareness,
                      ui_scale, ease_in_out)

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except Exception:
    TkinterDnD, DND_FILES = None, None

CURRENT_VERSION = "v3.0.0-Free"
RELEASES_REPO = "manyaksisko35/LocaGenFree"
RELEASES_API = f"https://api.github.com/repos/{RELEASES_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{RELEASES_REPO}/releases/latest"
PRO_URL = "https://hasan-alp-gungor.itch.io/locagen-pro-universal-game-localization-tool"
REPO_URL = "https://github.com/manyaksisko35/LocaGenFree"

FREE_CODES = {code for _name, code in FREE_LANGUAGES}
FREE_THEMES = {"Neon Void", "Frost"}
PRO_BULLETS = [
    "13 formats: CSV, Excel, PO, Ren'Py, RPG Maker, YAML, XLIFF…",
    "28 languages, translate to many at once",
    "DeepL and private offline translation",
    "Glossary, review window and quality report",
    "Only new & changed strings, translation memory",
    "All 8 glass themes",
]


def is_compiled():
    return "__compiled__" in globals() or getattr(sys, "frozen", False)


def _detect_current_exe():
    if not is_compiled():
        return None
    compiled = globals().get("__compiled__")
    for cand in (getattr(compiled, "original_argv0", None), sys.argv[0] if sys.argv else None, sys.executable):
        if cand:
            path = os.path.abspath(cand)
            if path.lower().endswith(".exe") and os.path.isfile(path):
                return path
    return None


CURRENT_EXE = _detect_current_exe()


def resource_path(name):
    for base in (os.path.dirname(os.path.abspath(__file__)), os.path.dirname(CURRENT_EXE or __file__)):
        path = os.path.join(base, name)
        if os.path.exists(path):
            return path
    return name


def parse_version(tag):
    nums = re.findall(r"\d+", tag or "")
    return tuple(int(n) for n in nums[:4]) if nums else (0,)


def human_size(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0


def open_folder(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def blobs_main(pal=None):
    b = (pal or P).blobs
    return [(70, 110, 270, b[0], 0.60), (480, 360, 250, b[1], 0.45), (110, 640, 260, b[2], 0.45), (470, 700, 190, b[3], 0.22)]


def theme_swatch(theme, scale):
    w, h = int(round(40 * scale)), int(round(22 * scale))
    img = pill_image(w, h, h // 2, fill=tuple(int(theme.bg[i:i + 2], 16) for i in (1, 3, 5)) + (255,),
                     outline=(255, 255, 255, 120) if not theme.light else (40, 30, 70, 90))
    img.alpha_composite(pill_image(w - 8, h - 8, (h - 8) // 2, gradient=(theme.accent1, theme.accent2, 1.0)), (4, 4))
    return img


def file_icon(ui, size):
    s = ui.px(size)
    img = pill_image(s, s, ui.px(size * 0.3), gradient=(P.accent1, P.accent2, 0.9), outline=(255, 255, 255, 90))
    k = 4
    glyph = Image.new("RGBA", (s * k, s * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(glyph)
    w = h = s * k
    x0, y0, x1, y1 = w * 0.32, h * 0.24, w * 0.68, h * 0.76
    fold, lw = w * 0.11, max(2, int(w * 0.045))
    d.line([(x0, y0), (x1 - fold, y0), (x1, y0 + fold), (x1, y1), (x0, y1), (x0, y0)], fill=(255, 255, 255, 255), width=lw, joint="curve")
    d.line([(x1 - fold, y0), (x1 - fold, y0 + fold), (x1, y0 + fold)], fill=(255, 255, 255, 255), width=lw, joint="curve")
    for i, frac in enumerate((0.47, 0.57, 0.67)):
        d.line([(x0 + w * 0.08, h * frac), (x1 - w * (0.08 if i < 2 else 0.16), h * frac)], fill=(255, 255, 255, 230), width=lw)
    img.alpha_composite(glyph.resize((s, s), Image.LANCZOS))
    return img


class LocaGenFreeApp(tk.Tk):
    W, H = 520, 700

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title(f"LocaGen Free {CURRENT_VERSION}")
        self.resizable(False, False)
        self.settings_path = os.path.join(core.data_dir(), "settings.json")
        self.settings = self._load_settings()
        theme = self.settings.get("theme", "Neon Void")
        set_theme(theme if theme in FREE_THEMES else "Neon Void")
        self.configure(bg=P.bg)
        self.scale = ui_scale(self, self.H)
        self.g = GlassCanvas(self, self.W, self.H, self.scale, blobs_main())
        self.data = None
        self.path = None
        self.source_code = self.settings.get("source", AUTO)
        if self.source_code != AUTO and self.source_code not in LANG_NAMES:
            self.source_code = AUTO
        self.target_code = self.settings.get("target", "en") if self.settings.get("target") in FREE_CODES else "en"
        self.busy = False
        self.stop_event = threading.Event()
        self.last_output = None
        self._status = ("Ready.", P.text_sub)
        self._progress_item = None
        self._progress_photo = None
        self._progress_value = 0.0
        self._ui_queue = queue.Queue()
        self.after(50, self._drain_ui_queue)
        self._set_icon()
        self._build()
        self._enable_drop()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.g.r.W) // 2
        y = max(0, (self.winfo_screenheight() - self.g.r.H) // 2 - 30)
        self.geometry(f"+{x}+{y}")
        borderless(self)
        show_main_window(self)
        self.after(500, self.g.prewarm_sheet)
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def _load_settings(self):
        try:
            with open(self.settings_path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save_settings(self):
        self.settings.update(theme=P.name, source=self.source_code, target=self.target_code)
        try:
            core.write_json_atomic(self.settings_path, self.settings)
        except OSError:
            pass

    def _set_icon(self):
        try:
            self._icon_photos = [ImageTk.PhotoImage(render_logo(P, s), master=self) for s in (64, 32, 16)]
            self.iconphoto(True, *self._icon_photos)
        except Exception:
            pass

    def _build(self):
        g, c = self.g, self.g.canvas
        title_w = g.measure("LocaGen", 27, "semibold")
        badge = (90 + title_w + 10, 38, 90 + title_w + 10 + 52, 60)
        g.panel(badge, 11, shadow=False, blur=4, refraction=3, frost=0.08, rim=1.1)
        g.panel((20, 268, 500, 470), 28, blur=8, refraction=10)
        g.divider(38, 482, 374)
        g.divider(38, 482, 422)
        g.panel((20, 586, 500, 596), 5, shadow=False, blur=3, refraction=2, frost=0.03, rim=0.7)
        g.r.shadow((20, 132, 500, 232), 26, offset=10, blur=20, alpha=0.5)
        g.r.shadow((20, 498, 500, 560), 31, offset=10, blur=22, color=P.accent1, alpha=0.45)
        g.finalize_background()

        g.image(22, 26, render_logo(P, g.px(56)))
        g.text(90, 49, "LocaGen", 27, "semibold", P.text)
        g.text((badge[0] + badge[2]) / 2, 49, "FREE", 11, "semibold", P.info, anchor="center")
        g.text(91, 78, f"Free game translator  ·  {CURRENT_VERSION.replace('-Free', '')}", 12.5, "normal", P.text_sub)
        WindowControls(self, g, self.on_close, self.minimize, drag_height=100)
        self.btn_theme = GlassButton(g, (322, 14, 414, 44), 15, "Theme", self.open_theme_picker, size=12.5,
                                     align="left", text_pad=34)
        self.btn_theme.add(g.image(336, 22, pill_image(g.px(14), g.px(14), g.px(7), gradient=(P.accent1, P.accent2, 1.0),
                                                        outline=(255, 255, 255, 140))))
        self.btn_pro = GlassButton(g, (386, 60, 496, 92), 16, "★ Get Pro", lambda: self.show_upgrade(),
                                   style="primary", size=12.5)

        g.text(28, 116, "SOURCE FILE", 11, "semibold", P.text_dim)
        g.text(496, 116, "drop a .json file here" if TkinterDnD else "", 11, "normal", P.text_dim, anchor="e")
        self.btn_file = GlassButton(g, (20, 132, 500, 232), 26, command=self.choose_file)
        self.btn_file.add(g.image(40, 154, file_icon(g, 56)))
        self.lbl_file = self.btn_file.add(g.text(114, 170, "Choose a JSON file", 16, "semibold", P.text))
        self.lbl_meta = self.btn_file.add(g.text(114, 196, "JSON  ·  13 more formats in Pro", 12.5, "normal", P.text_sub))

        g.text(28, 252, "TRANSLATION", 11, "semibold", P.text_dim)
        g.text(496, 252, "Google Translate", 11, "normal", P.text_dim, anchor="e")
        g.text(40, 292, "From", 12, "normal", P.text_sub)
        g.text(272, 292, "To", 12, "normal", P.text_sub)
        self.btn_source = GlassButton(g, (34, 306, 256, 356), 25, "", lambda: self.open_picker("source"),
                                      size=14, align="left", chevron=True)
        self.btn_target = GlassButton(g, (264, 306, 486, 356), 25, "", lambda: self.open_picker("target"),
                                      size=14, align="left", chevron=True)
        self._refresh_language_buttons()

        g.text(40, 398, "Engines", 13.5, "normal", P.text)
        g.text(112, 398, "DeepL · Offline", 12.5, "normal", P.text_sub)
        self.btn_engines = GlassButton(g, (408, 384, 484, 412), 14, "PRO", lambda: self.show_upgrade(
            "DeepL and offline translation are part of LocaGen Pro."), size=11.5, fg=P.info)
        g.text(40, 446, "Glossary", 13.5, "normal", P.text)
        g.text(112, 446, "fixed terms & names", 12.5, "normal", P.text_sub)
        self.btn_glossary = GlassButton(g, (408, 432, 484, 460), 14, "PRO", lambda: self.show_upgrade(
            "The glossary keeps names and game terms consistent in LocaGen Pro."), size=11.5, fg=P.info)

        self.btn_start = GlassButton(g, (20, 498, 500, 560), 31, "Translate", self.on_translate, style="primary", size=17)
        self.lbl_status = g.text(24, 620, "", 12.5, "normal", P.text_sub)
        self.lbl_right = g.text(496, 620, "", 12.5, "semibold", P.info, anchor="e", interactive=True)
        c.tag_bind(self.lbl_right, "<Button-1>", lambda e: self.last_output and open_folder(os.path.dirname(self.last_output)))
        footer = g.text(self.W / 2, 674, "Open source (GPL-3.0)  ·  Hasan Alp Güngör", 12, "normal", P.text_dim,
                        anchor="center", interactive=True)
        c.tag_bind(footer, "<Button-1>", lambda e: webbrowser.open(REPO_URL))
        c.tag_bind(footer, "<Enter>", lambda e: g.set_cursor("hand2"))
        c.tag_bind(footer, "<Leave>", lambda e: g.set_cursor(""))
        self.update_status(*self._status)
        if self.path:
            self._show_file()

    def _enable_drop(self):
        if TkinterDnD is None:
            return
        try:
            TkinterDnD.require(self)
            self.g.canvas.drop_target_register(DND_FILES)
            self.g.canvas.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        if paths and not self.busy:
            self.load_file(paths[0])
        return event.action

    def ui(self, fn, *args):
        if threading.current_thread() is threading.main_thread():
            fn(*args)
        else:
            self._ui_queue.put((fn, args))

    def _drain_ui_queue(self):
        try:
            while True:
                fn, args = self._ui_queue.get_nowait()
                try: fn(*args)
                except Exception: pass
        except queue.Empty:
            pass
        self.after(50, self._drain_ui_queue)

    def update_status(self, text, color=None):
        color = color or P.text_sub
        if threading.current_thread() is not threading.main_thread():
            self.ui(self.update_status, text, color)
            return
        self._status = (text, color)
        self.g.set_text(self.lbl_status, self.g.fit_text(text, 12.5, 380), color)
        self.g.fade_text(self.lbl_status, color, 0.35)

    def set_progress(self, value):
        self.ui(self._draw_progress, value)

    def _draw_progress(self, value):
        g, c = self.g, self.g.canvas
        value = max(0.0, min(1.0, value))
        self._progress_value = value
        w = int(g.px(476) * value)
        if w < g.px(6):
            if self._progress_item is not None:
                c.itemconfigure(self._progress_item, state="hidden")
        else:
            self._progress_photo = ImageTk.PhotoImage(pill_image(w, g.px(6), g.px(3), gradient=(P.accent1, P.accent2, 1.0)),
                                                      master=c)
            if self._progress_item is None:
                self._progress_item = c.create_image(g.px(22), g.px(588), anchor="nw", image=self._progress_photo,
                                                     state="disabled")
            else:
                c.itemconfigure(self._progress_item, image=self._progress_photo, state="disabled")
        if self.busy:
            g.set_text(self.lbl_right, f"{int(value * 100)}%", P.info)
            self.btn_start.set_text(f"Stop  ·  {int(value * 100)}%")

    def set_busy(self, busy):
        self.busy = busy
        for btn in (self.btn_file, self.btn_source, self.btn_target, self.btn_theme):
            btn.set_enabled(not busy)
        self.btn_start.set_text("Stop" if busy else "Translate")
        if busy:
            self.g.set_text(self.lbl_right, "")

    def minimize(self):
        minimize_window(self)

    def on_close(self):
        if self.busy and not messagebox.askyesno("LocaGen Free", "A translation is running. Quit anyway?", parent=self):
            return
        self.stop_event.set()
        self.save_settings()
        self.withdraw()
        os._exit(0)

    def show_upgrade(self, reason=None):
        return GlassDialog(self.g, "Get LocaGen Pro", reason or "Everything in Free, plus the tools for shipping a real game.",
                    PRO_BULLETS, "Get LocaGen Pro  →", lambda: webbrowser.open(PRO_URL))

    def choose_file(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self, initialdir=self.settings.get("open_dir"),
                                          filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if path:
            self.load_file(path)

    def load_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext != ".json":
            self.update_status(f"{ext or 'This file'} needs LocaGen Pro.", P.warn)
            self.show_upgrade(f"LocaGen Free reads JSON files. {ext.upper()[1:] or 'This format'} and 12 other formats "
                              "are part of LocaGen Pro.")
            return
        try:
            data = core.load_json(path)
        except Exception as e:
            self.update_status(f"Could not read {os.path.basename(path)}: {e}", P.error)
            return
        if not core.count_strings(data):
            self.update_status("This JSON file has no text to translate.", P.warn)
            return
        self.data, self.path = data, path
        self.settings["open_dir"] = os.path.dirname(os.path.abspath(path))
        self._show_file()
        self._draw_progress(0)
        self.last_output = None
        self.g.set_text(self.lbl_right, "")
        self.update_status("Ready to translate.")

    def _show_file(self):
        g = self.g
        size = human_size(os.path.getsize(self.path)) if os.path.exists(self.path) else ""
        g.set_text(self.lbl_file, g.fit_text(os.path.basename(self.path), 16, 330, "semibold"))
        g.set_text(self.lbl_meta, f"JSON  ·  {core.count_strings(self.data):,} strings  ·  {size}", P.info)
        g.fade_text(self.lbl_file, P.text)

    def open_picker(self, which):
        if self.busy:
            return
        if which == "source":
            options = [("Auto-Detect", AUTO, "")] + [(n, c, c) for n, c in FREE_LANGUAGES + PRO_LANGUAGES]
            GlassSheet(self.g, "Translate from", options, self.source_code, self._set_source)
        else:
            options = [(n, c, c) for n, c in FREE_LANGUAGES] + [(n, c, "PRO") for n, c in PRO_LANGUAGES]
            GlassSheet(self.g, "Translate to", options, self.target_code, self._set_target)

    def _set_source(self, code):
        self.source_code = code
        self._refresh_language_buttons()
        self.save_settings()

    def _set_target(self, code):
        if code not in FREE_CODES:
            self.show_upgrade(f"{LANG_NAMES[code]} and 21 more languages are part of LocaGen Pro.")
            return
        self.target_code = code
        self._refresh_language_buttons()
        self.save_settings()

    def _refresh_language_buttons(self):
        self.btn_source.set_text("Auto-Detect" if self.source_code == AUTO else LANG_NAMES[self.source_code])
        self.btn_target.set_text(LANG_NAMES[self.target_code])

    def open_theme_picker(self):
        if self.busy:
            return
        options = [(t.name, t.name, "" if t.name in FREE_THEMES else "PRO", theme_swatch(t, self.g.scale)) for t in THEMES]
        GlassSheet(self.g, "Theme", options, P.name, self.apply_theme, cols=1)

    def apply_theme(self, name):
        if name not in FREE_THEMES:
            self.show_upgrade(f"The {name} theme and 5 more are part of LocaGen Pro.")
            return
        if name == P.name or self.busy:
            return
        old = palette_snapshot()
        text, color = self._status
        kind = next((k for k in ("success", "error", "warn", "info") if getattr(old, k) == color), "text_sub")
        set_theme(name)
        self._status = (text, getattr(P, kind))
        self.save_settings()
        old_base = self.g.r.base
        self.configure(bg=P.bg)
        self.g.canvas.destroy()
        self.g = GlassCanvas(self, self.W, self.H, self.scale, blobs_main())
        self._progress_item = None
        self._build()
        self._draw_progress(self._progress_value)
        if self.last_output:
            self.g.set_text(self.lbl_right, "Open folder ›", P.info)
        self._enable_drop()
        self._set_icon()
        self._crossfade(old_base)
        self.after(600, self.g.prewarm_sheet)

    def _crossfade(self, old_base):
        g = self.g
        if old_base.size != g.r.base.size:
            return
        frames = [ImageTk.PhotoImage(Image.blend(old_base, g.r.base, t), master=g.canvas) for t in (0.0, 0.34, 0.67)]
        overlay = g.canvas.create_image(0, 0, anchor="nw", image=frames[0], state="disabled")
        g.canvas.tag_raise(overlay, g.bg_item)
        g.anim.run("themefade", 0.38, lambda t: g.canvas.itemconfigure(overlay, image=frames[min(2, int(t * 3))]),
                   done=lambda: (g.canvas.delete(overlay), frames.clear()), ease=ease_in_out)

    def on_translate(self):
        if self.busy:
            self.stop_event.set()
            self.update_status("Stopping…", P.warn)
            return
        if self.data is None:
            self.update_status("Choose a JSON file first.", P.error)
            return
        if core.GoogleTranslator is None:
            messagebox.showerror("LocaGen Free", "deep-translator is not installed.", parent=self)
            return
        name = LANG_NAMES[self.target_code].split(" (")[0].replace(" ", "_")
        save_path = filedialog.asksaveasfilename(parent=self, initialdir=os.path.dirname(self.path),
                                                 initialfile=f"translated_{name}.json", defaultextension=".json",
                                                 filetypes=[("JSON", "*.json")])
        if not save_path:
            self.update_status("Cancelled.")
            return
        self.stop_event = threading.Event()
        self.set_busy(True)
        self._draw_progress(0)
        self.update_status(f"Translating to {LANG_NAMES[self.target_code]}…", P.info)
        args = (self.data, self.source_code, self.target_code, save_path, self.stop_event)
        threading.Thread(target=self._run, args=args, daemon=True).start()

    def _run(self, data, source, target, save_path, stop_event):
        try:
            translator = core.Translator(target, source)
            result, failed = core.translate_json(data, translator, self.set_progress, stop_event)
            if stop_event.is_set():
                self.update_status("Stopped. Nothing was saved.", P.warn)
                self.set_progress(0)
                return
            core.save_json(save_path, result)
            self.last_output = save_path
            if failed:
                self.update_status(f"Saved. {failed} string(s) kept original.", P.warn)
            else:
                self.update_status(f"Done. Saved {os.path.basename(save_path)}.", P.success)
        except Exception as e:
            self.update_status(f"Error: {e}", P.error)
        finally:
            self.ui(self.set_busy, False)
            if self.last_output:
                self.ui(lambda: self.g.set_text(self.lbl_right, "Open folder ›", P.info))

    def check_for_updates(self):
        try:
            response = requests.get(RELEASES_API, headers={"Accept": "application/vnd.github+json"}, timeout=8)
            if response.status_code != 200:
                return
            data = response.json()
            latest = data.get("tag_name", "")
            if parse_version(latest) <= parse_version(CURRENT_VERSION):
                return
            asset = next((a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".exe")), None)
            self.ui(lambda: self.after(2000, self.prompt_update, latest, asset, data.get("html_url") or RELEASES_PAGE))
        except Exception:
            pass

    def prompt_update(self, latest, asset, page_url):
        if self.busy:
            self.after(5000, self.prompt_update, latest, asset, page_url)
            return
        if not CURRENT_EXE or not asset:
            if messagebox.askyesno("Update LocaGen Free", f"New version {latest} available.\nOpen download page?", parent=self):
                webbrowser.open(page_url)
            return
        if messagebox.askyesno("Update LocaGen Free", f"New version {latest} available. Update now?", parent=self):
            self.set_busy(True)
            self.btn_start.set_enabled(False)
            self.update_status(f"Downloading {latest}…", P.info)
            threading.Thread(target=self.perform_update,
                             args=(asset["browser_download_url"], asset.get("size", 0), page_url), daemon=True).start()

    def perform_update(self, url, expected_size, page_url):
        exe_path = CURRENT_EXE
        base, ext = os.path.splitext(exe_path)
        old_path, new_path = base + "_old" + ext, exe_path + ".download"
        renamed = False
        try:
            with requests.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                total = expected_size or int(response.headers.get("Content-Length", 0) or 0)
                done = 0
                with open(new_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=256 * 1024):
                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            if total:
                                self.set_progress(min(done / total, 1.0))
            if done == 0 or (expected_size and done != expected_size):
                raise IOError(f"Download incomplete ({done}/{expected_size} bytes)")
            if os.path.exists(old_path):
                os.remove(old_path)
            os.rename(exe_path, old_path)
            renamed = True
            os.rename(new_path, exe_path)
            subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
            self.ui(lambda: (self.save_settings(), os._exit(0)))
        except Exception as e:
            if renamed and not os.path.exists(exe_path) and os.path.exists(old_path):
                try: os.rename(old_path, exe_path)
                except OSError: pass
            if os.path.exists(new_path):
                try: os.remove(new_path)
                except OSError: pass
            self.ui(self.update_failed, e, page_url)

    def update_failed(self, error, page_url):
        self.set_busy(False)
        self.btn_start.set_enabled(True)
        self.update_status("Update failed.", P.error)
        if messagebox.askyesno("Update Error", f"Failed: {error}\n\nOpen download page?", parent=self):
            webbrowser.open(page_url)


def cleanup_old_versions():
    if CURRENT_EXE:
        old = os.path.splitext(CURRENT_EXE)[0] + "_old.exe"
        for path in (old, CURRENT_EXE + ".download"):
            if os.path.exists(path):
                try: os.remove(path)
                except OSError: pass


def run_selftest(path):
    lines = []
    for name in ("deep_translator", "requests", "PIL", "numpy", "tkinterdnd2"):
        try:
            __import__(name)
            lines.append(f"ok {name}")
        except Exception as e:
            lines.append(f"FAIL {name}: {e}")
    try:
        app = LocaGenFreeApp()
        app.update()
        lines.append(f"ok window {app.g.r.W}x{app.g.r.H} theme={P.name}")
        lines.append("ok drag-and-drop" if TkinterDnD else "FAIL drag-and-drop: tkinterdnd2 missing")
    except Exception as e:
        lines.append(f"FAIL window: {type(e).__name__}: {e}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os._exit(0)


def main():
    enable_dpi_awareness()
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        run_selftest(sys.argv[2])
    cleanup_old_versions()
    app = LocaGenFreeApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
