import math
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageTk


class Palette:
    def __init__(self, name, light, bg, text, text_sub, text_dim, accent1, accent2, info, field, blobs,
                 success="#3dffc8", error="#ff4d7d", warn="#ffc24d"):
        self.name, self.light = name, light
        self.bg, self.text, self.text_sub, self.text_dim = bg, text, text_sub, text_dim
        self.accent1, self.accent2, self.info, self.field, self.blobs = accent1, accent2, info, field, blobs
        self.success, self.error, self.warn = success, error, warn

    def overlay(self, alpha):
        return (20, 14, 40, int(alpha * 0.75)) if self.light else (255, 255, 255, alpha)


THEMES = [
    Palette("Neon Void", False, "#07020f", "#f6f0ff", "#b6a4d6", "#7d6a9e", "#b026ff", "#00f0ff", "#7ff6ff", "#150a26",
            ["#b026ff", "#00c8ff", "#5a1cff", "#ff2bd6"]),
    Palette("Ocean", False, "#020a14", "#eef7ff", "#9db8d6", "#5f7a99", "#2f6bff", "#00e5c7", "#7ff0e6", "#0a1828",
            ["#2f6bff", "#00e5c7", "#1a3cff", "#00a2ff"]),
    Palette("Sunset", False, "#12040a", "#fff3ef", "#dbaaa6", "#9c6b72", "#ff2f7a", "#ffb23d", "#ffd27f", "#230b14",
            ["#ff2f7a", "#ff8a3d", "#8a1cff", "#ffb23d"]),
    Palette("Rose", False, "#16040f", "#fff0f7", "#e6a9c9", "#a76d8c", "#ff2d8f", "#c026d3", "#ff9fd2", "#2a0a1d",
            ["#ff2d8f", "#ff6fb8", "#9d1a6c", "#e05cff"]),
    Palette("Emerald", False, "#020e09", "#effff6", "#a3d3b8", "#62937b", "#00b86b", "#c6ff3d", "#b9ff8a", "#08190f",
            ["#00b86b", "#3dffb0", "#0a7a5a", "#c6ff3d"]),
    Palette("Graphite", False, "#09090b", "#f4f5f7", "#b0b4bc", "#757a84", "#5c6270", "#aab0ba", "#e9ebef", "#17181b",
            ["#5a5f6b", "#8a909c", "#3a3d45", "#b4b8c0"]),
    Palette("Sakura", True, "#f7e4ee", "#3b1630", "#7c4766", "#a8829a", "#e8357f", "#b44cf0", "#c0246e", "#fffafc",
            ["#ff9cc9", "#ffc6df", "#f2a6ff", "#ffd9e8"], success="#0f9a6c", error="#d4244e", warn="#b06d0d"),
    Palette("Frost", True, "#e8ebf4", "#1a1530", "#565070", "#8c87a3", "#7b5cff", "#00b3d6", "#0a7fa8", "#ffffff",
            ["#b9a8ff", "#8fe6ff", "#c7b8ff", "#ffc2e6"], success="#0a9d6c", error="#d7264f", warn="#b57412"),
]
THEME_NAMES = [t.name for t in THEMES]
P = Palette(**{k: v for k, v in vars(THEMES[0]).items()})


def palette_snapshot(theme=None):
    return Palette(**{k: v for k, v in vars(theme or P).items()})


def set_theme(name):
    theme = next((t for t in THEMES if t.name == name), THEMES[0])
    P.__dict__.update(vars(theme))
    return theme.name


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb01(h):
    return np.array(hex_rgb(h), dtype=np.float32) / 255.0


_INPUT = [0.0]


def note_input(_event=None):
    _INPUT[0] = time.monotonic()


def input_recent(window=0.25):
    return time.monotonic() - _INPUT[0] < window


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def mix(c1, c2, t):
    a, b = hex_rgb(c1), hex_rgb(c2)
    return "#%02x%02x%02x" % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


class Tween:
    FRAME_MS = 15

    def __init__(self, widget):
        self.widget = widget
        self.jobs = {}

    def run(self, key, duration, step, done=None, ease=ease_out):
        self.cancel(key)
        start = time.perf_counter()

        def tick():
            try:
                t = 1.0 if duration <= 0 else min(1.0, (time.perf_counter() - start) / duration)
                step(ease(t))
                if t < 1.0:
                    self.jobs[key] = self.widget.after(self.FRAME_MS, tick)
                    return
                self.jobs.pop(key, None)
                if done:
                    done()
            except tk.TclError:
                self.jobs.pop(key, None)

        tick()

    def cancel(self, key):
        job = self.jobs.pop(key, None)
        if job:
            try: self.widget.after_cancel(job)
            except Exception: pass

    def running(self, key):
        return key in self.jobs


def enable_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception: ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def ui_scale(root, logical_height):
    try: dpi = root.winfo_fpixels("1i") / 96.0
    except Exception: dpi = 1.0
    dpi = max(1.0, dpi)
    fit = (root.winfo_screenheight() - 90) / float(logical_height)
    return max(0.75, min(dpi, fit))


_SDF_CACHE = {}


def _rounded_sdf(w, h, r):
    key = (w, h, r)
    cached = _SDF_CACHE.get(key)
    if cached is not None:
        return cached
    if len(_SDF_CACHE) > 160:
        _SDF_CACHE.clear()
    result = _SDF_CACHE[key] = _compute_sdf(w, h, r)
    return result


_EDGE_CACHE = {}


def _edge_maps(w, h, r, s):
    key = (w, h, r, round(s, 3))
    cached = _EDGE_CACHE.get(key)
    if cached is not None:
        return cached
    d, nx, ny, ys = _rounded_sdf(w, h, r)
    lx, ly = -0.5, -0.85
    norm = math.hypot(lx, ly)
    dot = (nx * lx + ny * ly) / norm
    light = 0.16 + 0.8 * np.clip(dot, 0, 1) ** 1.5 + 0.45 * np.clip(-dot, 0, 1) ** 2
    rim_band = np.clip(1 + d / (1.4 * s), 0, 1)
    inner = np.clip(1 + d / (7 * s), 0, 1) ** 2
    edge_light = (light * (rim_band + inner * 0.10))[..., None].astype(np.float32)
    sheen_map = (np.clip(1 - ys / (h * 0.6), 0, 1) ** 2)[..., None].astype(np.float32)
    alpha = (np.clip(0.5 - d, 0, 1) * 255 + 0.5).astype(np.uint8)
    if len(_EDGE_CACHE) > 160:
        _EDGE_CACHE.clear()
    result = _EDGE_CACHE[key] = (sheen_map, edge_light, alpha)
    return result


def _compute_sdf(w, h, r):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    px = xs + 0.5 - w / 2.0
    py = ys + 0.5 - h / 2.0
    qx = np.abs(px) - (w / 2.0 - r)
    qy = np.abs(py) - (h / 2.0 - r)
    mx, my = np.maximum(qx, 0), np.maximum(qy, 0)
    outside = np.sqrt(mx * mx + my * my)
    d = outside + np.minimum(np.maximum(qx, qy), 0) - r
    corner = (qx > 0) & (qy > 0)
    safe = outside + 1e-6
    nx = np.where(corner, mx / safe, np.where(qx > qy, 1.0, 0.0)) * np.sign(px)
    ny = np.where(corner, my / safe, np.where(qx > qy, 0.0, 1.0)) * np.sign(py)
    return d, nx.astype(np.float32), ny.astype(np.float32), ys


def _bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    wx = x - x0
    wy = y - y0
    a = img[y0, x0] * (1 - wx) + img[y0, x0 + 1] * wx
    b = img[y0 + 1, x0] * (1 - wx) + img[y0 + 1, x0 + 1] * wx
    return a * (1 - wy) + b * wy


def h_gradient(w, h, c1, c2):
    t = np.linspace(0, 1, max(w, 1), dtype=np.float32)[None, :, None]
    grad = rgb01(c1)[None, None, :] * (1 - t) + rgb01(c2)[None, None, :] * t
    return np.repeat(grad, h, axis=0)


def pill_image(w, h, r, fill=None, outline=None, width=1, gradient=None):
    k = 4
    W, H = max(int(w), 1), max(int(h), 1)
    mask = Image.new("L", (W * k, H * k), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W * k - 1, H * k - 1), radius=r * k, fill=255)
    mask = mask.resize((W, H), Image.LANCZOS)
    if gradient:
        c1, c2, alpha = gradient
        arr = (h_gradient(W, H, c1, c2) * 255).astype(np.uint8)
        img = Image.fromarray(arr, "RGB").convert("RGBA")
        img.putalpha(mask.point(lambda v: int(v * alpha)))
    else:
        img = Image.new("RGBA", (W, H), fill or (0, 0, 0, 0))
        img.putalpha(mask.point(lambda v: int(v * (fill[3] / 255.0))) if fill else mask.point(lambda v: 0))
    if outline:
        ol = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0))
        ImageDraw.Draw(ol).rounded_rectangle((0, 0, W * k - 1, H * k - 1), radius=r * k, outline=outline, width=width * k)
        img = Image.alpha_composite(img, ol.resize((W, H), Image.LANCZOS))
    return img


_LOGO_CACHE = {}


def _diag_gradient(size, c1, c2):
    t = (np.linspace(0, 1, size, dtype=np.float32)[None, :] + np.linspace(0, 1, size, dtype=np.float32)[:, None]) / 2
    arr = rgb01(c1)[None, None, :] * (1 - t[..., None]) + rgb01(c2)[None, None, :] * t[..., None]
    return Image.fromarray((arr * 255).astype(np.uint8), "RGB")


def _stroke_mask(size, k, draw_fn):
    mask = Image.new("L", (size, size), 0)
    draw_fn(ImageDraw.Draw(mask), lambda v: v * k)
    return mask


def render_logo(theme, size):
    key = (theme.name, size)
    cached = _LOGO_CACHE.get(key)
    if cached is not None:
        return cached
    small = size <= 32
    S = 1024 if size > 128 else (512 if size > 64 else 256)
    k = S / 512.0
    br, ring, mer = (52, 30, 24) if small else (40, 22, 14)
    a1, a2 = theme.accent1, theme.accent2
    if theme.light:
        top, bottom = "#ffffff", mix(theme.bg, a1, 0.12)
    else:
        top, bottom = mix(theme.bg, a1, 0.16), mix(theme.bg, "#000000", 0.3)

    tile_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tile_mask).rounded_rectangle((8 * k, 8 * k, 504 * k, 504 * k), radius=112 * k, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(_diag_gradient(S, top, bottom), (0, 0), tile_mask)

    ys, xs = np.mgrid[0:S, 0:S].astype(np.float32) / k
    dist = np.sqrt((xs - 256) ** 2 + (ys - 216) ** 2) / 298
    glow = np.clip(1 - dist, 0, 1) * (0.22 if theme.light else 0.35)
    glow_layer = Image.new("RGBA", (S, S), hex_rgb(a1) + (0,))
    glow_layer.putalpha(Image.fromarray((glow * np.asarray(tile_mask, np.float32)).astype(np.uint8)))
    img.alpha_composite(glow_layer)

    sheen = np.clip(1 - np.linspace(0, 2, S, dtype=np.float32), 0, 1)[:, None] * np.ones((1, S), np.float32)
    sheen_layer = Image.new("RGBA", (S, S), (255, 255, 255, 0))
    sheen_layer.putalpha(Image.fromarray((sheen * (0.10 if theme.light else 0.16) * np.asarray(tile_mask, np.float32)).astype(np.uint8)))
    img.alpha_composite(sheen_layer)

    edge_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(edge_mask).rounded_rectangle((10 * k, 10 * k, 502 * k, 502 * k), radius=110 * k, outline=255,
                                                width=int((6 if small else 4) * k))
    edge = _diag_gradient(S, "#ffffff", a2).convert("RGBA")
    edge.putalpha(edge_mask.point(lambda v: int(v * (0.45 if theme.light else 0.7))))
    img.alpha_composite(edge)

    def round_line(d, f, pts, width):
        d.line([(f(x), f(y)) for x, y in pts], fill=255, width=int(f(width)), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = f(width) / 2
            d.ellipse((f(x) - r, f(y) - r, f(x) + r, f(y) + r), fill=255)

    left = _stroke_mask(S, k, lambda d, f: round_line(d, f, [(160, 116), (108, 116), (108, 396), (160, 396)], br))
    right = _stroke_mask(S, k, lambda d, f: round_line(d, f, [(352, 116), (404, 116), (404, 396), (352, 396)], br))

    def globe(d, f):
        d.ellipse((f(256 - 92 - ring / 2), f(256 - 92 - ring / 2), f(256 + 92 + ring / 2), f(256 + 92 + ring / 2)), fill=255)
        d.ellipse((f(256 - 92 + ring / 2), f(256 - 92 + ring / 2), f(256 + 92 - ring / 2), f(256 + 92 - ring / 2)), fill=0)
        d.ellipse((f(256 - 40 - mer / 2), f(256 - 92 - mer / 2), f(256 + 40 + mer / 2), f(256 + 92 + mer / 2)), outline=255,
                  width=int(f(mer)))
        rows = [(166, 346, 256)] + ([] if small else [(184, 328, 206), (184, 328, 306)])
        for x0, x1, y in rows:
            round_line(d, f, [(x0, y), (x1, y)], mer)

    globe_mask = _stroke_mask(S, k, globe)
    mark = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mark.paste(Image.new("RGB", (S, S), hex_rgb(a1)), (0, 0), left)
    mark.paste(Image.new("RGB", (S, S), hex_rgb(a2)), (0, 0), right)
    mark.paste(_diag_gradient(S, mix(a1, "#ffffff", 0.15), a2), (0, 0), globe_mask)
    if not small and not theme.light:
        halo = mark.filter(ImageFilter.GaussianBlur(10 * k))
        img.alpha_composite(halo)
        img.alpha_composite(halo)
    img.alpha_composite(mark)
    result = img.resize((size, size), Image.LANCZOS)
    _LOGO_CACHE[key] = result
    return result


_BG_CACHE = {}
_BG_LOCK = threading.Lock()


def prewarm_backgrounds(specs):
    def work():
        for width, height, scale, blobs, pal in specs:
            while input_recent(0.4):
                time.sleep(0.15)
            try:
                GlassRenderer(width, height, scale, blobs, pal=pal)
                render_logo(pal, int(round(56 * scale)))
                for size in (64, 32, 16):
                    render_logo(pal, size)
            except Exception:
                pass
    threading.Thread(target=work, daemon=True).start()


class GlassRenderer:
    PAD = 120

    def __init__(self, width, height, scale, blobs, grid=28, pal=None):
        self.scale = scale
        self.pal = pal or palette_snapshot()
        self.W, self.H = self.px(width), self.px(height)
        self.base = self._background(blobs, grid)

    def px(self, v):
        return int(round(v * self.scale))

    def box(self, b):
        return tuple(self.px(v) for v in b)

    def _background(self, blobs, grid):
        W, H, s, pal = self.W, self.H, self.scale, self.pal
        key = (pal.name, W, H, round(s, 3), tuple(blobs), grid)
        with _BG_LOCK:
            if key in _BG_CACHE:
                return _BG_CACHE[key].copy()
        q = 4
        w, h = max(1, W // q), max(1, H // q)
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        xs, ys = (xs + 0.5) * W / w, (ys + 0.5) * H / h
        img = np.zeros((h, w, 3), np.float32) + rgb01(pal.bg)
        for cx, cy, r, color, a in blobs:
            g = np.exp(-(((xs - cx * s) ** 2 + (ys - cy * s) ** 2) / (r * s) ** 2) * 2.0) * a
            if pal.light:
                k = (g * 0.85)[..., None]
                img = img * (1 - k) + rgb01(color) * k
            else:
                img = 1 - (1 - img) * (1 - rgb01(color) * g[..., None])
        small = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")
        img = np.asarray(small.resize((W, H), Image.BICUBIC), dtype=np.float32) / 255.0
        step, lw = grid * s, max(1.0, s)
        col = (np.mod(np.arange(W, dtype=np.float32), step) < lw)[None, :]
        row = (np.mod(np.arange(H, dtype=np.float32), step) < lw)[:, None]
        lines = (col | row).astype(np.float32)[..., None]
        img = img * (1 - lines * 0.04) if pal.light else img + (1 - img) * lines * 0.028
        rng = np.random.default_rng(7)
        img = img + rng.standard_normal(img.shape, dtype=np.float32) * 0.006
        result = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")
        with _BG_LOCK:
            if len(_BG_CACHE) > 24:
                _BG_CACHE.clear()
            _BG_CACHE[key] = result.copy()
        return result

    def _crop(self, src, x0, y0, x1, y1):
        img = src or self.base
        W, H = img.size
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        region = img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
        if (cx0, cy0, cx1, cy1) != (x0, y0, x1, y1):
            arr = np.pad(np.asarray(region), ((cy0 - y0, y1 - cy1), (cx0 - x0, x1 - cx1), (0, 0)), mode="edge")
            region = Image.fromarray(arr, "RGB")
        return region

    def glass(self, box, radius, *, src=None, blur=7, refraction=9, frost=0.06, darken=0.0,
              tint=None, tint_alpha=0.0, rim=1.0, sheen=0.07):
        x0, y0, x1, y1 = self.box(box)
        w, h = x1 - x0, y1 - y0
        r = max(1, min(self.px(radius), w // 2, h // 2))
        s = self.scale
        refr, bl = refraction * s, blur * s
        pad = min(int(refr * 2 + bl * 3) + 2, self.PAD)

        key = (x0, y0, x1, y1, r, round(refr, 3), round(bl, 3))
        cache = getattr(self, "_refract_cache", None)
        if src is None and cache is not None and key in cache:
            base_out, d, nx, ny, ys = cache[key]
        else:
            region = self._crop(src, x0 - pad, y0 - pad, x1 + pad, y1 + pad)
            if bl >= 4 and min(region.size) > 16:
                small = region.reduce(2).filter(ImageFilter.GaussianBlur(bl / 2))
                region = small.resize(region.size, Image.BILINEAR)
            elif bl > 0:
                region = region.filter(ImageFilter.GaussianBlur(bl))
            crop = np.asarray(region, dtype=np.float32) / 255.0
            d, nx, ny, ys = _rounded_sdf(w, h, r)
            t = np.clip(1 + d / max(refr * 2.2, 1.0), 0, 1) ** 2
            disp = refr * t
            base_out = crop[pad:pad + h, pad:pad + w].copy()
            by, bx = np.nonzero(t > 0)
            if len(by):
                bdx, bdy = nx[by, bx] * disp[by, bx], ny[by, bx] * disp[by, bx]
                fx, fy = bx.astype(np.float32) + pad, by.astype(np.float32) + pad
                for ch, k in ((0, 1.18), (1, 1.0), (2, 0.82)):
                    base_out[by, bx, ch] = _bilinear(crop[..., ch], fx + bdx * k, fy + bdy * k)
            if src is None:
                if cache is None or len(cache) > 64:
                    cache = self._refract_cache = {}
                cache[key] = (base_out, d, nx, ny, ys)
        out = base_out.copy()

        if darken:
            out *= (1 - darken)
        if tint is not None and tint_alpha > 0:
            tint_arr = h_gradient(w, h, *tint) if isinstance(tint, tuple) else rgb01(tint)
            out = out * (1 - tint_alpha) + tint_arr * tint_alpha
        out = out + (1 - out) * frost
        sheen_map, edge_light, alpha = _edge_maps(w, h, r, s)
        if sheen:
            out = out + (1 - out) * (sheen_map * sheen)
        out = out + (1 - out) * np.minimum(edge_light * rim, 1.0)
        rgba = np.empty((h, w, 4), np.uint8)
        rgba[..., :3] = np.clip(out * 255 + 0.5, 0, 255)
        rgba[..., 3] = alpha
        return Image.fromarray(rgba, "RGBA"), (x0, y0)

    def shadow(self, box, radius, *, offset=8, blur=16, color="#000000", alpha=0.45):
        if self.pal.light:
            color, alpha = ("#2a2050", alpha * 0.45) if color == "#000000" else (color, alpha * 0.6)
        x0, y0, x1, y1 = self.box(box)
        off, bl, r = self.px(offset), max(1, self.px(blur)), self.px(radius)
        m = bl * 3
        layer = Image.new("RGBA", (x1 - x0 + 2 * m, y1 - y0 + 2 * m), hex_rgb(color) + (0,))
        ImageDraw.Draw(layer).rounded_rectangle((m, m + off, m + x1 - x0, m + off + y1 - y0), radius=r,
                                                fill=hex_rgb(color) + (int(255 * alpha),))
        layer = layer.filter(ImageFilter.GaussianBlur(bl))
        self.base.paste(layer.convert("RGB"), (x0 - m, y0 - m), layer)
        self._refract_cache = None

    def bake(self, img, pos):
        self.base.paste(img.convert("RGB"), pos, img)
        self._refract_cache = None


class GlassCanvas:
    def __init__(self, master, width, height, scale, blobs):
        self.master = master
        self.w, self.h, self.scale = width, height, scale
        self.r = GlassRenderer(width, height, scale, blobs)
        self.canvas = tk.Canvas(master, width=self.r.W, height=self.r.H, highlightthickness=0, bd=0, bg=P.bg)
        self.canvas.pack()
        self.canvas.bind("<Motion>", note_input, add="+")
        self.cache = {}
        self._photos = []
        self._tag_n = 0
        self.bg_item = None
        self.anim = Tween(self.canvas)
        self._pending_sheets = {}
        self._deferred = []
        self._defer_job = None
        families = set(tkfont.families(master))
        self.family = next((f for f in ("Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", "DejaVu Sans") if f in families), "TkDefaultFont")
        self.family_semibold = next((f for f in ("Segoe UI Semibold", "Inter SemiBold") if f in families), None)

    def px(self, v):
        return int(round(v * self.scale))

    def photo(self, img):
        p = ImageTk.PhotoImage(img, master=self.canvas)
        self._photos.append(p)
        return p

    def new_tag(self):
        self._tag_n += 1
        return f"w{self._tag_n}"

    def font(self, size, weight="normal"):
        if weight == "semibold":
            if self.family_semibold:
                return (self.family_semibold, -self.px(size))
            weight = "bold"
        return (self.family, -self.px(size), weight)

    def measure(self, text, size, weight="normal"):
        return tkfont.Font(root=self.master, font=self.font(size, weight)).measure(text) / self.scale

    def panel(self, box, radius, *, shadow=True, **glass_kw):
        if shadow:
            self.r.shadow(box, radius, offset=10, blur=20, alpha=0.5)
        img, pos = self.r.glass(box, radius, **glass_kw)
        self.r.bake(img, pos)

    def divider(self, x0, x1, y, alpha=0.10):
        img = Image.new("RGBA", (self.px(x1 - x0), max(1, self.px(1))), P.overlay(int(255 * alpha)))
        self.r.bake(img, (self.px(x0), self.px(y)))

    def finalize_background(self):
        photo = self.photo(self.r.base)
        if self.bg_item is None:
            self.bg_item = self.canvas.create_image(0, 0, anchor="nw", image=photo)
        else:
            self.canvas.itemconfigure(self.bg_item, image=photo)
        self.canvas.tag_lower(self.bg_item)

    def text(self, x, y, text, size=13, weight="normal", fill=None, anchor="w", interactive=False, **kw):
        fill = fill or P.text
        return self.canvas.create_text(self.px(x), self.px(y), text=text, font=self.font(size, weight), fill=fill,
                                       disabledfill=fill, anchor=anchor,
                                       state="normal" if interactive else "disabled", **kw)

    def image(self, x, y, img, anchor="nw", **kw):
        return self.canvas.create_image(self.px(x), self.px(y), image=self.photo(img), anchor=anchor, state="disabled", **kw)

    def set_text(self, item, text=None, fill=None):
        kw = {}
        if text is not None: kw["text"] = text
        if fill is not None: kw.update(fill=fill, disabledfill=fill)
        self.canvas.itemconfigure(item, **kw)

    def defer(self, fn):
        self._deferred.append(fn)
        if self._defer_job is None:
            self._defer_job = self.canvas.after(120, self._run_deferred)

    def set_cursor(self, name):
        if self.canvas.cget("cursor") != name:
            self.canvas.configure(cursor=name)

    def _run_deferred(self):
        self._defer_job = None
        if not self._deferred:
            return
        if input_recent(0.2):
            try:
                self._defer_job = self.canvas.after(120, self._run_deferred)
            except tk.TclError:
                self._deferred.clear()
            return
        fn = self._deferred.pop(0)
        try:
            fn()
        except tk.TclError:
            self._deferred.clear()
            return
        except Exception:
            pass
        if self._deferred:
            try:
                self._defer_job = self.canvas.after(16, self._run_deferred)
            except tk.TclError:
                self._deferred.clear()

    def fade_text(self, item, color, duration=0.3, start=None):
        start = start or mix(P.bg, color, 0.15)
        self.anim.run(("fade", item), duration,
                      lambda t: self.canvas.itemconfigure(item, fill=mix(start, color, t), disabledfill=mix(start, color, t)))

    def slide(self, item, x, y, key, duration=0.14):
        c = self.canvas
        tx, ty = self.px(x), self.px(y)
        cur = c.coords(item)
        if c.itemcget(item, "state") == "hidden" or not cur:
            self.anim.cancel(key)
            c.coords(item, tx, ty)
            c.itemconfigure(item, state="disabled")
            return
        sx, sy = cur[0], cur[1]
        if abs(sx - tx) < 0.5 and abs(sy - ty) < 0.5 and not self.anim.running(key):
            return
        self.anim.run(key, duration, lambda t: c.coords(item, sx + (tx - sx) * t, sy + (ty - sy) * t))

    def sheet_box(self):
        return (16, 64, self.w - 16, self.h - 16)

    def _sheet_images(self, box, base):
        dim = base.filter(ImageFilter.GaussianBlur(self.px(12)))
        dim = ImageEnhance.Brightness(dim).enhance(0.88 if P.light else 0.5)
        img, pos = self.r.glass(box, 30, src=dim, blur=10, refraction=12, frost=0.05)
        final = dim.convert("RGBA")
        final.paste(img, pos, img)
        final = final.convert("RGB")
        return [Image.blend(base, final, t) for t in (0.3, 0.55, 0.8)] + [final]

    def sheet_frames(self, box):
        key = ("sheetf", box, P.name)
        if key not in self.cache:
            pil = self._pending_sheets.pop(key, None)
            if not isinstance(pil, list):
                pil = self._sheet_images(box, self.r.base.copy())
            self.cache[key] = [self.photo(im) for im in pil]
        return self.cache[key]

    def prewarm_sheet(self, box=None):
        box = box or self.sheet_box()
        key = ("sheetf", box, P.name)
        if key in self.cache or key in self._pending_sheets:
            return
        self._pending_sheets[key] = "working"
        base = self.r.base.copy()

        def work():
            try:
                self._pending_sheets[key] = self._sheet_images(box, base)
            except Exception:
                self._pending_sheets.pop(key, None)

        def poll():
            try:
                if not self.canvas.winfo_exists():
                    return
                if self._pending_sheets.get(key) == "working":
                    self.canvas.after(80, poll)
                elif key in self._pending_sheets:
                    self.sheet_frames(box)
            except tk.TclError:
                pass

        threading.Thread(target=work, daemon=True).start()
        self.canvas.after(80, poll)

    def fit_text(self, text, size, max_width, weight="normal"):
        if self.measure(text, size, weight) <= max_width:
            return text
        while len(text) > 4 and self.measure(text + "…", size, weight) > max_width:
            text = text[:-1]
        return text + "…"


class GlassButton:
    STYLES = {
        "glass": {
            "normal": dict(frost=0.05, rim=0.9),
            "hover": dict(frost=0.11, rim=1.25),
            "pressed": dict(frost=0.02, darken=0.08, rim=0.8),
            "disabled": dict(frost=0.02, darken=0.12, rim=0.45, sheen=0.03),
        },
        "primary": {
            "normal": dict(tint_alpha=0.55, frost=0.03, rim=1.1),
            "hover": dict(tint_alpha=0.70, frost=0.07, rim=1.35),
            "pressed": dict(tint_alpha=0.50, darken=0.12, rim=1.0),
            "disabled": dict(tint_alpha=0.22, frost=0.02, darken=0.05, rim=0.6),
        },
        "window": {
            "normal": dict(frost=0.04, rim=0.8, sheen=0.04),
            "hover": dict(frost=0.13, rim=1.2),
            "pressed": dict(frost=0.02, darken=0.10, rim=0.8),
            "disabled": dict(frost=0.04, rim=0.8, sheen=0.04),
        },
        "close": {
            "normal": dict(frost=0.04, rim=0.8, sheen=0.04),
            "hover": dict(tint="error", tint_alpha=0.85, rim=1.2),
            "pressed": dict(tint="error", tint_alpha=0.70, darken=0.10, rim=1.0),
            "disabled": dict(frost=0.04, rim=0.8, sheen=0.04),
        },
    }

    def __init__(self, ui, box, radius, text="", command=None, style="glass", size=14, weight="semibold",
                 align="center", chevron=False, text_pad=18, fg=None):
        self.ui, self.box, self.command = ui, box, command
        self.fg = fg or ("#ffffff" if style == "primary" else P.text)
        self.enabled = True
        self.hover = False
        self.tag = ui.new_tag()
        c = ui.canvas
        x0, y0, x1, y1 = box
        self.radius, self.style = radius, style
        self.images, self.pil = {}, {}
        self._level, self._frames = 0.0, None
        self._render("normal")
        pos = ui.r.box(box)[:2]
        self.img_item = c.create_image(pos[0], pos[1], anchor="nw", image=self.images["normal"], tags=(self.tag,))
        cy = (y0 + y1) / 2
        if align == "center":
            self.text_item = ui.text((x0 + x1) / 2, cy, text, size, weight, self.fg, anchor="center", tags=(self.tag,))
        else:
            self.text_item = ui.text(x0 + text_pad, cy, text, size, weight, self.fg, anchor="w", tags=(self.tag,))
        self.extra = []
        self._extra_colors = {}
        if chevron:
            cx = x1 - 22
            self.extra.append(c.create_line(ui.px(cx - 5), ui.px(cy - 2.5), ui.px(cx), ui.px(cy + 2.5), ui.px(cx + 5), ui.px(cy - 2.5),
                                            fill=P.text_sub, disabledfill=P.text_sub, width=max(1, ui.px(1.8)), capstyle="round",
                                            joinstyle="round", state="disabled", tags=(self.tag,)))
        c.tag_bind(self.img_item, "<Enter>", self._enter)
        c.tag_bind(self.img_item, "<Leave>", self._leave)
        self._prepare()
        c.tag_bind(self.img_item, "<ButtonPress-1>", self._press)
        c.tag_bind(self.img_item, "<ButtonRelease-1>", self._release)

    def _render(self, state):
        if state in self.images:
            return self.images[state]
        kw = self.STYLES[self.style][state]
        if kw.get("tint") == "error":
            kw = dict(kw, tint=P.error)
        if self.style == "primary":
            kw = dict(kw, tint=(P.accent1, P.accent2))
            if P.light:
                kw["tint_alpha"] = min(1.0, kw["tint_alpha"] + 0.32)
        img, _pos = self.ui.r.glass(self.box, self.radius, blur=6, refraction=7, **kw)
        self.pil[state] = img
        self.images[state] = self.ui.photo(img)
        return self.images[state]

    def _prepare(self):
        for state in ("hover", "pressed", "disabled"):
            self.ui.defer(lambda s=state: self._render(s))
        self.ui.defer(self._hover_frames)

    def add(self, item):
        c = self.ui.canvas
        c.itemconfigure(item, state="disabled")
        c.addtag_withtag(self.tag, item)
        if c.type(item) == "line":
            self.extra.append(item)
        return item

    def _show(self, state):
        self.ui.anim.cancel(self.tag)
        self.ui.canvas.itemconfigure(self.img_item, image=self._render(state))

    def _hover_frames(self):
        if self._frames is None:
            self._render("hover")
            a, b = self.pil["normal"], self.pil["hover"]
            mid = [self.ui.photo(Image.blend(a, b, i / 6)) for i in range(1, 6)]
            self._frames = [self.images["normal"]] + mid + [self.images["hover"]]
        return self._frames

    def _fade_to(self, target):
        frames = self._hover_frames()
        start = self._level
        last = len(frames) - 1

        def step(t):
            self._level = start + (target - start) * t
            self.ui.canvas.itemconfigure(self.img_item, image=frames[int(round(self._level * last))])

        self.ui.anim.run(self.tag, 0.05 + 0.17 * abs(target - start), step)

    def _enter(self, _e):
        self.hover = True
        if self.enabled:
            self.ui.set_cursor("hand2")
            if self._frames is None:
                self._level = 1.0
                self._show("hover")
                self.ui.defer(self._hover_frames)
            else:
                self._fade_to(1.0)

    def _leave(self, _e):
        self.hover = False
        self.ui.set_cursor("")
        if not self.enabled:
            self._show("disabled")
        elif self._frames is None:
            self._level = 0.0
            self._show("normal")
        else:
            self._fade_to(0.0)

    def _press(self, _e):
        if self.enabled:
            self._show("pressed")

    def _release(self, _e):
        if not self.enabled:
            return
        self._level = 1.0
        if self.hover:
            self._show("hover")
            if self.command:
                self.command()
        else:
            self._fade_to(0.0)

    def set_text(self, text):
        self.ui.set_text(self.text_item, text)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self._level = 1.0 if (enabled and self.hover) else 0.0
        self._show(("hover" if self.hover else "normal") if enabled else "disabled")
        self.ui.set_text(self.text_item, fill=self.fg if enabled else P.text_dim)
        for item in self.extra:
            color = getattr(self, "_extra_colors", {}).setdefault(item, self.ui.canvas.itemcget(item, "fill"))
            self.ui.canvas.itemconfigure(item, fill=color if enabled else P.text_dim, disabledfill=color if enabled else P.text_dim)
        if not enabled and self.hover:
            self.ui.canvas.configure(cursor="")


class GlassSheet:
    def __init__(self, ui, title, options, selected, on_pick, cols=2, multi=False):
        self.ui, self.options, self.on_pick, self.multi = ui, options, on_pick, multi
        self.selected = set(selected) if multi else {selected}
        self.ready = self.closing = False
        self._hover_index = -1
        c = ui.canvas
        self.hidden_windows = [i for i in c.find_all() if c.type(i) == "window" and c.itemcget(i, "state") != "hidden"]
        for item in self.hidden_windows:
            c.itemconfigure(item, state="hidden")
        self.box = box = ui.sheet_box()
        self.frames = ui.sheet_frames(box)
        self.bg = c.create_image(0, 0, anchor="nw", image=self.frames[0], tags=("sheet",))
        ui.text(box[0] + 24, box[1] + 32, title, 18, "semibold", P.text, tags=("sheet", "sheetc"))
        if multi:
            self.close_xy = (box[2] - 44, box[1] + 32)
            ui.text(*self.close_xy, "Done", 14, "semibold", P.info, anchor="center", tags=("sheet", "sheetc"))
            self.count_item = ui.text(box[2] - 80, box[1] + 32, "", 12, "normal", P.text_sub, anchor="e", tags=("sheet", "sheetc"))
        else:
            self.close_xy = (box[2] - 30, box[1] + 32)
            ui.text(*self.close_xy, "✕", 15, "normal", P.text_sub, anchor="center", tags=("sheet", "sheetc"))

        gx0, gy0, gx1, gy1 = box[0] + 14, box[1] + 64, box[2] - 14, box[3] - 14
        rows = math.ceil(len(options) / cols)
        self.row_h = min(40.0, (gy1 - gy0) / rows)
        self.col_w = (gx1 - gx0) / cols
        self.origin = (gx0, gy0)
        self.cols = cols
        cw, rh = self.col_w - 6, self.row_h - 4
        k = ("pills", cw, rh, P.name)
        if k not in ui.cache:
            ui.cache[k] = (
                ui.photo(pill_image(ui.px(cw), ui.px(rh), ui.px(rh / 2), fill=P.overlay(24), outline=P.overlay(60))),
                ui.photo(pill_image(ui.px(cw), ui.px(rh), ui.px(rh / 2), gradient=(P.accent1, P.accent2, 0.42), outline=(255, 255, 255, 110))),
            )
        self.hover_pill, self.sel_pill = ui.cache[k]
        self.hover_item = c.create_image(0, 0, anchor="nw", image=self.hover_pill, state="hidden", tags=("sheet",))
        self.sel_items = {}
        for i, option in enumerate(options):
            label, value, sub = option[:3]
            x, y = self._cell_xy(i)
            label_x = x + 16
            if len(option) > 3 and option[3] is not None:
                swatch = option[3]
                c.create_image(ui.px(x + 12), ui.px(y + rh / 2), anchor="w", image=ui.photo(swatch), state="disabled",
                               tags=("sheet", "sheetc"))
                label_x = x + 22 + swatch.width / ui.scale
            ui.text(label_x, y + rh / 2, label, 13.5, "normal", P.text, tags=("sheet", "sheetc"))
            if sub:
                ui.text(x + cw - 14, y + rh / 2, sub, 11, "normal", P.text_sub, anchor="e", tags=("sheet", "sheetc"))
            if value in self.selected:
                self._mark(i, True)
        self._update_count()

        self.content = [(item, c.itemcget(item, "state")) for item in c.find_withtag("sheetc")]
        for item, _state in self.content:
            c.itemconfigure(item, state="hidden")
        c.tag_bind(self.bg, "<Motion>", self._motion)
        c.tag_bind(self.bg, "<Leave>", self._leave)
        c.tag_bind(self.bg, "<ButtonRelease-1>", self._click)
        self._esc = ui.master.bind("<Escape>", lambda e: self.close(), add="+")
        last = len(self.frames) - 1
        ui.anim.run("sheet", 0.2, lambda t: c.itemconfigure(self.bg, image=self.frames[int(round(t * last))]),
                    done=self._reveal)

    def _reveal(self):
        c, ui = self.ui.canvas, self.ui
        colors = {}
        for item, state in self.content:
            c.itemconfigure(item, state=state)
            if c.type(item) == "text":
                colors[item] = c.itemcget(item, "fill")
        start_bg = mix(P.bg, P.text, 0.08)
        shift = ui.px(12)
        c.move("sheetc", 0, shift)
        moved = [shift]

        def step(t):
            target = shift * (1 - t)
            c.move("sheetc", 0, target - moved[0])
            moved[0] = target
            for item, color in colors.items():
                col = mix(start_bg, color, min(1.0, t * 1.3))
                c.itemconfigure(item, fill=col, disabledfill=col)

        self.ready = True
        ui.anim.run("sheetc", 0.24, step)

    def _leave(self, _e):
        self._hover_index = -1
        self.ui.anim.cancel("sheethover")
        self.ui.canvas.itemconfigure(self.hover_item, state="hidden")

    def _mark(self, i, on):
        c = self.ui.canvas
        if on and i not in self.sel_items:
            x, y = self._cell_xy(i)
            item = c.create_image(self.ui.px(x), self.ui.px(y), anchor="nw", image=self.sel_pill, state="disabled",
                                  tags=("sheet", "sheetc"))
            c.tag_raise(item, self.bg)
            self.sel_items[i] = item
        elif not on and i in self.sel_items:
            c.delete(self.sel_items.pop(i))

    def _update_count(self):
        if self.multi:
            n = len(self.selected)
            self.ui.set_text(self.count_item, f"{n} selected" if n else "none selected")

    def _cell_xy(self, i):
        gx0, gy0 = self.origin
        return gx0 + (i % self.cols) * self.col_w + 3, gy0 + (i // self.cols) * self.row_h + 2

    def _index_at(self, ex, ey):
        x, y = ex / self.ui.scale, ey / self.ui.scale
        gx0, gy0 = self.origin
        col, row = int((x - gx0) // self.col_w), int((y - gy0) // self.row_h)
        if 0 <= col < self.cols and row >= 0 and x >= gx0 and y >= gy0:
            i = row * self.cols + col
            if i < len(self.options):
                return i
        return None

    def _motion(self, e):
        if not self.ready or self.closing:
            return
        i = self._index_at(e.x, e.y)
        if i is None:
            near = math.hypot(e.x / self.ui.scale - self.close_xy[0], e.y / self.ui.scale - self.close_xy[1]) < 24
            self.ui.set_cursor("hand2" if near else "")
        if i == self._hover_index:
            return
        self._hover_index = i
        if i is None:
            self.ui.anim.cancel("sheethover")
            self.ui.canvas.itemconfigure(self.hover_item, state="hidden")
        else:
            x, y = self._cell_xy(i)
            self.ui.slide(self.hover_item, x, y, "sheethover", 0.12)
            self.ui.set_cursor("hand2")

    def _click(self, e):
        if not self.ready or self.closing:
            return
        x, y = e.x / self.ui.scale, e.y / self.ui.scale
        bx0, by0, bx1, by1 = self.box
        if not (bx0 <= x <= bx1 and by0 <= y <= by1) or math.hypot(x - self.close_xy[0], y - self.close_xy[1]) < 24:
            self.close()
            return
        i = self._index_at(e.x, e.y)
        if i is None:
            return
        value = self.options[i][1]
        if self.multi:
            on = value not in self.selected
            (self.selected.add if on else self.selected.discard)(value)
            self._mark(i, on)
            self._update_count()
        else:
            self.close(pick=value)

    def close(self, pick=None):
        if self.closing:
            return
        self.closing = True
        ui, c = self.ui, self.ui.canvas
        ui.anim.cancel("sheetc")
        ui.anim.cancel("sheethover")
        c.delete("sheetc")
        c.delete(self.hover_item)
        c.configure(cursor="")
        try: ui.master.unbind("<Escape>", self._esc)
        except Exception: pass
        last = len(self.frames) - 1

        def finish():
            c.delete("sheet")
            for item in self.hidden_windows:
                try: c.itemconfigure(item, state="normal")
                except tk.TclError: pass
            if self.multi:
                self.on_pick(set(self.selected))
            elif pick is not None:
                self.on_pick(pick)

        ui.anim.run("sheet", 0.16, lambda t: c.itemconfigure(self.bg, image=self.frames[int(round((1 - t) * last))]),
                    done=finish, ease=ease_in_out)


class GlassEntry:
    def __init__(self, ui, box, placeholder="", size=14, on_submit=None, show=""):
        self.ui, self.placeholder, self.show = ui, placeholder, show
        img, pos = ui.r.glass(box, (box[3] - box[1]) / 2, blur=4, refraction=4, frost=0.0,
                              tint=P.field, tint_alpha=1.0, sheen=0.0, rim=0.7)
        ui.r.bake(img, pos)
        x0, y0, x1, y1 = box
        self.var = tk.StringVar(master=ui.master)
        self.entry = tk.Entry(ui.master, textvariable=self.var, bd=0, relief="flat", highlightthickness=0,
                              bg=P.field, fg=P.text_dim, insertbackground=P.accent2, font=ui.font(size),
                              selectbackground=P.accent1, selectforeground="#ffffff")
        ui.canvas.create_window(ui.px(x0 + 18), ui.px((y0 + y1) / 2), anchor="w", window=self.entry,
                                width=ui.px(x1 - x0 - 36), height=ui.px(min(26, y1 - y0 - 8)))
        self._placeholder_on = False
        self._show_placeholder()
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", lambda e: self._show_placeholder())
        if on_submit:
            self.entry.bind("<Return>", lambda e: on_submit())

    def _show_placeholder(self):
        if not self.var.get():
            self._placeholder_on = True
            self.entry.configure(fg=P.text_dim, show="")
            self.var.set(self.placeholder)

    def _focus_in(self, _e):
        if self._placeholder_on:
            self._placeholder_on = False
            self.var.set("")
            self.entry.configure(fg=P.text, show=self.show)

    def get(self):
        return "" if self._placeholder_on else self.var.get()

    def clear(self):
        self._placeholder_on = False
        self.var.set("")
        self.entry.configure(fg=P.text, show=self.show)
        if self.ui.master.focus_get() is not self.entry:
            self._show_placeholder()

    def set(self, text):
        self._placeholder_on = False
        self.var.set(text)
        self.entry.configure(fg=P.text, show=self.show)
        if not text and self.ui.master.focus_get() is not self.entry:
            self._show_placeholder()

    def set_enabled(self, enabled):
        self.entry.configure(state="normal" if enabled else "disabled", disabledbackground=P.field,
                             disabledforeground=P.text_dim)


class GlassToggle:
    def __init__(self, ui, x, y, value=False, command=None):
        self.ui, self.value, self.command, self.enabled = ui, value, command, True
        self.x, self.y = x, y
        box = (x, y, x + 46, y + 26)
        off, _ = ui.r.glass(box, 13, blur=4, refraction=3, frost=0.03, darken=0.12, rim=0.8, sheen=0.04)
        on, _ = ui.r.glass(box, 13, blur=4, refraction=3, tint=(P.accent1, P.accent2), tint_alpha=0.78, rim=1.2)
        self.track_frames = [ui.photo(off)] + [None] * 5 + [ui.photo(on)]
        self.tracks = {False: self.track_frames[0], True: self.track_frames[-1]}
        self._track_pil = (off, on)
        ui.defer(self._blend_frames)
        self.key = ("toggle", x, y)
        k = ui.px(20)
        knob = Image.new("RGBA", (k + 4, k + 4), (0, 0, 0, 0))
        shadow = pill_image(k, k, k // 2, fill=(0, 0, 0, 90)).filter(ImageFilter.GaussianBlur(1.2))
        knob.alpha_composite(shadow, (2, 3))
        knob.alpha_composite(pill_image(k, k, k // 2, fill=(255, 255, 255, 250)), (2, 1))
        self.knob_photo = ui.photo(knob)
        c = ui.canvas
        self.track_item = c.create_image(ui.px(x), ui.px(y), anchor="nw", image=self.tracks[value])
        self.knob_item = c.create_image(ui.px(self._knob_x(value)) - 2, ui.px(y + 3) - 1, anchor="nw",
                                        image=self.knob_photo, state="disabled")
        c.tag_bind(self.track_item, "<ButtonRelease-1>", lambda e: self.toggle())
        c.tag_bind(self.track_item, "<Enter>", lambda e: c.configure(cursor="hand2" if self.enabled else ""))
        c.tag_bind(self.track_item, "<Leave>", lambda e: c.configure(cursor=""))

    def _blend_frames(self):
        off, on = self._track_pil
        for i in range(1, 6):
            if self.track_frames[i] is None:
                self.track_frames[i] = self.ui.photo(Image.blend(off, on, i / 6))

    def _knob_x(self, value):
        return self.x + (23 if value else 3)

    def bind_label(self, item):
        c = self.ui.canvas
        c.itemconfigure(item, state="normal")
        c.tag_bind(item, "<ButtonRelease-1>", lambda e: self.toggle())
        c.tag_bind(item, "<Enter>", lambda e: c.configure(cursor="hand2" if self.enabled else ""))
        c.tag_bind(item, "<Leave>", lambda e: c.configure(cursor=""))

    def toggle(self):
        if self.enabled:
            self.set(not self.value, animate=True)
            if self.command:
                self.command(self.value)

    def set(self, value, animate=False):
        self.value = value
        c, ui = self.ui.canvas, self.ui
        x_off, x_on = self._knob_x(False), self._knob_x(True)
        target = x_on if value else x_off
        if not animate:
            ui.anim.cancel(self.key)
            c.itemconfigure(self.track_item, image=self.tracks[value])
            c.coords(self.knob_item, ui.px(target) - 2, ui.px(self.y + 3) - 1)
            return
        self._blend_frames()
        cur = c.coords(self.knob_item)
        start = (cur[0] + 2) / ui.scale if cur else (x_on if not value else x_off)
        last = len(self.track_frames) - 1

        def step(t):
            pos = start + (target - start) * t
            frac = (pos - x_off) / (x_on - x_off)
            c.coords(self.knob_item, ui.px(pos) - 2, ui.px(self.y + 3) - 1)
            c.itemconfigure(self.track_item, image=self.track_frames[max(0, min(last, int(round(frac * last))))])

        ui.anim.run(self.key, 0.24, step, ease=ease_in_out)

    def set_enabled(self, enabled):
        self.enabled = enabled


class GlassTextArea:
    def __init__(self, ui, box, size=13.5, radius=18):
        self.ui = ui
        img, pos = ui.r.glass(box, radius, blur=4, refraction=4, frost=0.0, tint=P.field, tint_alpha=1.0,
                              sheen=0.0, rim=0.7)
        ui.r.bake(img, pos)
        x0, y0, x1, y1 = box
        self.text = tk.Text(ui.master, bd=0, relief="flat", highlightthickness=0, bg=P.field, fg=P.text,
                            insertbackground=P.accent2, font=ui.font(size), wrap="word", undo=True, padx=0, pady=0,
                            selectbackground=P.accent1, selectforeground="#ffffff")
        ui.canvas.create_window(ui.px(x0 + 16), ui.px(y0 + 11), anchor="nw", window=self.text,
                                width=ui.px(x1 - x0 - 32), height=ui.px(y1 - y0 - 22))

    def get(self):
        return self.text.get("1.0", "end-1c")

    def set(self, value):
        state = self.text.cget("state")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value)
        self.text.edit_reset()
        self.text.configure(state=state)

    def set_enabled(self, enabled):
        self.text.configure(state="normal" if enabled else "disabled", fg=P.text if enabled else P.text_dim)


WS_EX_TOOLWINDOW, WS_EX_APPWINDOW, WS_MINIMIZEBOX, WS_SYSMENU = 0x00000080, 0x00040000, 0x00020000, 0x00080000


def _hwnd(window):
    import ctypes
    return ctypes.windll.user32.GetParent(window.winfo_id())


def _round_corners(hwnd):
    try:
        import ctypes
        corner = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner))
    except Exception:
        pass


def borderless(window):
    window.overrideredirect(True)


def show_main_window(window):
    window.deiconify()
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        window.update_idletasks()
        hwnd = _hwnd(window)
        ex = user32.GetWindowLongW(hwnd, -20)
        user32.SetWindowLongW(hwnd, -20, (ex & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW)
        style = user32.GetWindowLongW(hwnd, -16)
        user32.SetWindowLongW(hwnd, -16, style | WS_MINIMIZEBOX | WS_SYSMENU)
        _round_corners(hwnd)
        window.withdraw()
        window.deiconify()
    except Exception:
        pass


def show_child_window(window):
    window.deiconify()
    if sys.platform == "win32":
        try:
            window.update_idletasks()
            hwnd = _hwnd(window)
            threading.Thread(target=_round_corners, args=(hwnd,), daemon=True).start()
        except Exception:
            pass


def minimize_window(window):
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindowAsync(_hwnd(window), 6)
            return
        except Exception:
            pass

    def restore(e):
        if e.widget is window and window.state() == "normal":
            window.overrideredirect(True)
            window.unbind("<Map>", bind_id)

    window.overrideredirect(False)
    bind_id = window.bind("<Map>", restore, add="+")
    window.iconify()


class WindowControls:
    def __init__(self, window, ui, on_close, on_minimize=None, drag_height=96, top=14):
        self.window, self.ui = window, ui
        c = ui.canvas
        x1 = ui.w - 20
        self.buttons = []
        self.btn_close = GlassButton(ui, (x1 - 30, top, x1, top + 30), 15, "", on_close, style="close")
        cx, cy = x1 - 15, top + 15
        for a, b in (((-4.5, -4.5), (4.5, 4.5)), ((-4.5, 4.5), (4.5, -4.5))):
            self.btn_close.add(c.create_line(ui.px(cx + a[0]), ui.px(cy + a[1]), ui.px(cx + b[0]), ui.px(cy + b[1]),
                                             fill=P.text, width=max(1, ui.px(1.6)), capstyle="round"))
        self.buttons.append(self.btn_close)
        if on_minimize:
            self.btn_min = GlassButton(ui, (x1 - 68, top, x1 - 38, top + 30), 15, "", on_minimize, style="window")
            mx = x1 - 53
            self.btn_min.add(c.create_line(ui.px(mx - 5), ui.px(cy), ui.px(mx + 5), ui.px(cy), fill=P.text,
                                           width=max(1, ui.px(1.6)), capstyle="round"))
            self.buttons.append(self.btn_min)
        self.left_edge = x1 - (68 if on_minimize else 30)
        self.drag_height = drag_height
        self._offset = None
        c.bind("<ButtonPress-1>", self._press, add="+")
        c.bind("<B1-Motion>", self._drag, add="+")
        c.bind("<ButtonRelease-1>", lambda e: setattr(self, "_offset", None), add="+")

    def _press(self, e):
        if e.y / self.ui.scale > self.drag_height:
            return
        current = self.ui.canvas.find_withtag("current")
        if current and current[0] != self.ui.bg_item:
            return
        self._offset = (e.x_root - self.window.winfo_x(), e.y_root - self.window.winfo_y())

    def _drag(self, e):
        if self._offset:
            self.window.geometry(f"+{e.x_root - self._offset[0]}+{e.y_root - self._offset[1]}")



class GlassDialog:
    def __init__(self, ui, title, message, bullets, primary, on_primary, secondary="Maybe later"):
        self.ui, self.on_primary = ui, on_primary
        self.closing = False
        c = ui.canvas
        self.hidden_windows = [i for i in c.find_all() if c.type(i) == "window" and c.itemcget(i, "state") != "hidden"]
        for item in self.hidden_windows:
            c.itemconfigure(item, state="hidden")
        self.box = box = ui.sheet_box()
        self.frames = ui.sheet_frames(box)
        self.bg = c.create_image(0, 0, anchor="nw", image=self.frames[0], tags=("sheet",))
        x0, y0, x1, y1 = box
        cx = (x0 + x1) / 2
        logo = render_logo(P, ui.px(64))
        c.create_image(ui.px(cx), ui.px(y0 + 70), image=ui.photo(logo), state="disabled", tags=("sheet", "sheetc"))
        ui.text(cx, y0 + 132, title, 21, "semibold", P.text, anchor="center", tags=("sheet", "sheetc"))
        c.create_text(ui.px(cx), ui.px(y0 + 162), text=message, font=ui.font(13), fill=P.text_sub, disabledfill=P.text_sub,
                      width=ui.px(x1 - x0 - 80), justify="center", anchor="n", state="disabled", tags=("sheet", "sheetc"))
        top = y0 + 224
        for i, line in enumerate(bullets):
            y = top + i * 30
            ui.text(x0 + 52, y, "✓", 13, "semibold", P.info, anchor="center", tags=("sheet", "sheetc"))
            ui.text(x0 + 70, y, line, 13, "normal", P.text, tags=("sheet", "sheetc"))
        by = min(y1 - 120, top + len(bullets) * 30 + 30)
        w = x1 - x0 - 80
        self.primary_box = (x0 + 40, by, x0 + 40 + w, by + 48)
        self.secondary_box = (x0 + 40, by + 58, x0 + 40 + w, by + 96)
        primary_img = pill_image(ui.px(w), ui.px(48), ui.px(24), gradient=(P.accent1, P.accent2, 0.95), outline=(255, 255, 255, 120))
        self.secondary_photo = ui.photo(pill_image(ui.px(w), ui.px(38), ui.px(19), fill=P.overlay(26), outline=P.overlay(70)))
        c.create_image(ui.px(x0 + 40), ui.px(by), anchor="nw", image=ui.photo(primary_img), state="disabled", tags=("sheet", "sheetc"))
        ui.text(cx, by + 24, primary, 15, "semibold", "#ffffff", anchor="center", tags=("sheet", "sheetc"))
        self.secondary_item = c.create_image(ui.px(x0 + 40), ui.px(by + 58), anchor="nw", image=self.secondary_photo,
                                             state="hidden", tags=("sheet", "sheetc"))
        ui.text(cx, by + 77, secondary, 13, "normal", P.text_sub, anchor="center", tags=("sheet", "sheetc"))
        self.content = [(item, c.itemcget(item, "state")) for item in c.find_withtag("sheetc")]
        for item, _state in self.content:
            c.itemconfigure(item, state="hidden")
        c.tag_bind(self.bg, "<Motion>", self._motion)
        c.tag_bind(self.bg, "<ButtonRelease-1>", self._click)
        self._esc = ui.master.bind("<Escape>", lambda e: self.close(), add="+")
        last = len(self.frames) - 1
        ui.anim.run("sheet", 0.2, lambda t: c.itemconfigure(self.bg, image=self.frames[int(round(t * last))]),
                    done=self._reveal)

    def _reveal(self):
        c, ui = self.ui.canvas, self.ui
        for item, state in self.content:
            c.itemconfigure(item, state=state)
        shift = ui.px(14)
        c.move("sheetc", 0, shift)
        moved = [shift]

        def step(t):
            target = shift * (1 - t)
            c.move("sheetc", 0, target - moved[0])
            moved[0] = target

        ui.anim.run("sheetc", 0.24, step)

    def _inside(self, e, box):
        x, y = e.x / self.ui.scale, e.y / self.ui.scale
        return box[0] <= x <= box[2] and box[1] <= y <= box[3]

    def _motion(self, e):
        if self.closing:
            return
        on_primary, on_secondary = self._inside(e, self.primary_box), self._inside(e, self.secondary_box)
        self.ui.set_cursor("hand2" if on_primary or on_secondary else "")
        state = "disabled" if on_secondary else "hidden"
        if self.ui.canvas.itemcget(self.secondary_item, "state") != state:
            self.ui.canvas.itemconfigure(self.secondary_item, state=state)

    def _click(self, e):
        if self.closing:
            return
        if self._inside(e, self.primary_box):
            self.close()
            self.on_primary()
        elif self._inside(e, self.secondary_box) or not self._inside(e, self.box):
            self.close()

    def close(self):
        if self.closing:
            return
        self.closing = True
        ui, c = self.ui, self.ui.canvas
        ui.anim.cancel("sheetc")
        c.delete("sheetc")
        ui.set_cursor("")
        try: ui.master.unbind("<Escape>", self._esc)
        except Exception: pass
        last = len(self.frames) - 1

        def finish():
            c.delete("sheet")
            for item in self.hidden_windows:
                try: c.itemconfigure(item, state="normal")
                except tk.TclError: pass

        ui.anim.run("sheet", 0.16, lambda t: c.itemconfigure(self.bg, image=self.frames[int(round((1 - t) * last))]),
                    done=finish, ease=ease_in_out)
