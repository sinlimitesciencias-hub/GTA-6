"""Motor de animación: fondos synthwave, sprites de texto y escenas animadas.

Todo el arte es original y se genera por código (sin material de Rockstar).
Renderiza fotogramas RGB 1920x1080 que build.py envía a ffmpeg.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
HORIZON = 650
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "assets", "fonts")

CHANNEL = os.environ.get("CANAL_NOMBRE", "NEÓN 6")

_FONT_FILES = {
    "display": "Anton.woff",
    "alt": "BebasNeue.woff",
    "body": "InterDisplay-Bold.otf",
    "black": "InterDisplay-Black.otf",
}
_font_cache = {}


def font(kind, size):
    key = (kind, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(os.path.join(FONT_DIR, _FONT_FILES[kind]), size)
    return _font_cache[key]


# --------------------------------------------------------------------------- temas
THEMES = {
    "sunset": dict(sky=[(12, 4, 32), (70, 14, 92), (214, 54, 120), (255, 140, 90)],
                   sun=[(255, 236, 110), (255, 60, 150)], grid=(255, 70, 210),
                   ground=[(22, 4, 40), (8, 0, 18)], acc=(0, 234, 255), acc2=(255, 64, 180),
                   warm=(255, 210, 80)),
    "ocean": dict(sky=[(2, 8, 30), (8, 40, 90), (20, 120, 160), (255, 170, 110)],
                  sun=[(255, 220, 120), (255, 90, 90)], grid=(0, 220, 255),
                  ground=[(4, 16, 40), (0, 4, 14)], acc=(255, 214, 64), acc2=(0, 230, 255),
                  warm=(255, 120, 90)),
    "toxic": dict(sky=[(6, 2, 22), (40, 10, 70), (110, 30, 140), (60, 220, 160)],
                  sun=[(200, 255, 120), (40, 200, 160)], grid=(120, 255, 170),
                  ground=[(10, 4, 30), (2, 0, 10)], acc=(140, 255, 120), acc2=(220, 90, 255),
                  warm=(255, 230, 90)),
    "gold": dict(sky=[(14, 6, 10), (60, 18, 30), (190, 70, 40), (255, 190, 80)],
                 sun=[(255, 245, 160), (255, 110, 40)], grid=(255, 150, 50),
                 ground=[(24, 8, 12), (8, 2, 4)], acc=(255, 200, 60), acc2=(255, 90, 60),
                 warm=(255, 230, 140)),
    "miami": dict(sky=[(8, 4, 30), (40, 20, 100), (240, 80, 170), (90, 230, 230)],
                  sun=[(255, 250, 200), (255, 100, 200)], grid=(80, 240, 255),
                  ground=[(14, 6, 40), (4, 0, 14)], acc=(90, 245, 240), acc2=(255, 90, 200),
                  warm=(255, 220, 120)),
}


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def grad_colors(stops, n):
    """Interpola una lista de colores en n pasos -> array (n,3)."""
    stops = np.array(stops, dtype=np.float32)
    xs = np.linspace(0, 1, len(stops))
    t = np.linspace(0, 1, n)
    return np.stack([np.interp(t, xs, stops[:, c]) for c in range(3)], axis=1)


# --------------------------------------------------------------------------- fondo
def _palm(draw, base_x, base_y, height, lean, color, rnd):
    pts = []
    for i in range(24):
        t = i / 23
        x = base_x + lean * (t ** 1.6) * height
        y = base_y - t * height
        pts.append((x, y))
    for i in range(len(pts) - 1):
        w = int(lerp(26, 12, i / len(pts)))
        draw.line([pts[i], pts[i + 1]], fill=color, width=w)
    tx, ty = pts[-1]
    for k in range(9):
        ang = math.radians(-180 + k * 25 + rnd.uniform(-6, 6))
        length = height * rnd.uniform(0.42, 0.6)
        droop = rnd.uniform(0.25, 0.45)
        frond = []
        for j in range(16):
            t = j / 15
            x = tx + math.cos(ang) * length * t
            y = ty + math.sin(ang) * length * t * 0.6 + (t ** 2) * length * droop
            frond.append((x, y))
        for j in range(len(frond) - 1):
            w = int(lerp(16, 3, j / len(frond)))
            draw.line([frond[j], frond[j + 1]], fill=color, width=w)
            if 2 < j < 13:
                nx, ny = frond[j]
                for s in (-1, 1):
                    draw.line([(nx, ny), (nx + s * 6 + (frond[j + 1][0] - nx) * 0.8, ny + 22)], fill=color, width=3)
    draw.ellipse([tx - 14, ty - 10, tx + 14, ty + 14], fill=color)


def build_static_bg(theme, seed=7):
    rnd = random.Random(seed)
    th = THEMES[theme]
    img = np.zeros((H, W, 3), np.float32)
    # cielo
    sky = grad_colors(th["sky"], HORIZON)
    img[:HORIZON] = sky[:, None, :]
    # estrellas
    for _ in range(260):
        x, y = rnd.randrange(W), rnd.randrange(int(HORIZON * 0.55))
        b = rnd.uniform(0.3, 1.0) * (1 - y / (HORIZON * 0.55))
        img[y, x] = np.minimum(255, img[y, x] + 255 * b)
    # sol
    sun_r, scx, scy = 330, W // 2, HORIZON - 120
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - scx) ** 2 + (yy - scy) ** 2)
    glow = np.exp(-((d - sun_r).clip(0)) / 160.0)[..., None]
    gcol = np.array(th["sun"][1], np.float32)
    img[:HORIZON] += (glow[:HORIZON] * gcol * 0.55)
    sun_cols = grad_colors(th["sun"], 2 * sun_r)
    mask = (d <= sun_r) & (yy < HORIZON)
    rel = (yy - (scy - sun_r)).clip(0, 2 * sun_r - 1)
    stripe = np.ones((H, W), bool)
    for k in range(9):
        y0 = scy + 20 + k * 30
        thick = 3 + k * 2.2
        stripe &= ~((yy >= y0) & (yy < y0 + thick))
    m = mask & stripe
    img[m] = sun_cols[rel[m]]
    # skyline
    sk = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sk)
    x = 0
    windows = []
    while x < W:
        bw = rnd.randint(40, 120)
        center_bias = 1 - abs((x + bw / 2) - W / 2) / (W / 2)
        bh = rnd.randint(40, 120) + int(center_bias * rnd.randint(60, 260))
        if rnd.random() < 0.08:
            bh += 140
        sd.rectangle([x, HORIZON - bh, x + bw, HORIZON], fill=255)
        if rnd.random() < 0.3:
            sd.rectangle([x + bw // 2 - 2, HORIZON - bh - 40, x + bw // 2 + 2, HORIZON - bh], fill=255)
        for wy in range(HORIZON - bh + 10, HORIZON - 8, 14):
            for wx in range(x + 6, x + bw - 6, 12):
                if rnd.random() < 0.18:
                    windows.append((wx, wy))
        x += bw + rnd.randint(-6, 10)
    skm = np.asarray(sk, np.float32)[..., None] / 255.0
    sky_col = np.array([14, 6, 30], np.float32)
    img = img * (1 - skm) + sky_col * skm
    wc = np.array(th["warm"], np.float32)
    for wx, wy in windows:
        img[wy:wy + 4, wx:wx + 5] = wc * rnd.uniform(0.5, 1.0)
    # suelo
    ground = grad_colors(th["ground"], H - HORIZON)
    img[HORIZON:] = ground[:, None, :]
    # reflejo del sol
    refl = np.exp(-np.abs(xx[HORIZON:] - scx) / 260.0) * np.exp(-(yy[HORIZON:] - HORIZON) / 120.0)
    img[HORIZON:] += refl[..., None] * gcol * 0.35
    # palmeras
    pl = Image.new("L", (W, H), 0)
    pd = ImageDraw.Draw(pl)
    _palm(pd, 150, H + 20, 720, 0.28, 255, rnd)
    _palm(pd, 330, H + 40, 520, 0.12, 255, rnd)
    _palm(pd, W - 170, H + 20, 760, -0.3, 255, rnd)
    _palm(pd, W - 380, H + 50, 500, -0.1, 255, rnd)
    plm = np.asarray(pl, np.float32)[..., None] / 255.0
    img = img * (1 - plm) + np.array([8, 2, 16], np.float32) * plm
    # viñeta
    vig = 1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    img *= vig[..., None]
    return img.clip(0, 255).astype(np.uint8), plm[..., 0]


def build_grid_frames(theme, nframes=FPS):
    th = THEMES[theme]
    frames = []
    vx = W / 2
    for f in range(nframes):
        phase = f / nframes
        layer = Image.new("L", (W, H - HORIZON), 0)
        dr = ImageDraw.Draw(layer)
        for k in range(0, 22):
            z = (k + 1 - phase) * 0.5 + 0.35
            y = 260.0 / z
            if 0 <= y < H - HORIZON:
                dr.line([(0, y), (W, y)], fill=int(clamp(1.2 - z / 12) * 255), width=2)
        for i in range(-30, 31):
            x_bottom = vx + i * 230
            dr.line([(vx + i * 14, 0), (x_bottom, H - HORIZON)], fill=200, width=2)
        arr = np.asarray(layer, np.float32) / 255.0
        blur = np.asarray(layer.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255.0
        fade = np.linspace(0.15, 1.0, H - HORIZON)[:, None]
        val = ((arr * 0.9 + blur * 1.6) * fade).clip(0, 1.3)
        frames.append(val.astype(np.float32))
    return frames, np.array(th["grid"], np.float32)


class Background:
    def __init__(self, theme, seed=7):
        self.static, self.palm_mask = build_static_bg(theme, seed)
        self.grid, self.gcol = build_grid_frames(theme)
        self._full = [None] * len(self.grid)
        self._dim = [None] * len(self.grid)

    def _compose(self, i):
        img = self.static.astype(np.float32)
        g = self.grid[i][..., None] * self.gcol
        pm = self.palm_mask[HORIZON:, :, None]
        img[HORIZON:] = img[HORIZON:] + g * (1 - pm)
        return img.clip(0, 255).astype(np.uint8)

    def frame(self, fidx, dim=False):
        i = fidx % len(self.grid)
        if self._full[i] is None:
            self._full[i] = self._compose(i)
        if not dim:
            return self._full[i]
        if self._dim[i] is None:
            self._dim[i] = (self._full[i].astype(np.float32) * 0.32 + np.array([6, 2, 14])).astype(np.uint8)
        return self._dim[i]


# --------------------------------------------------------------------------- sprites
def to_sprite(img):
    a = np.asarray(img.convert("RGBA"), np.float32)
    a[..., 3] /= 255.0
    return a


def blend(dst, spr, x, y, opacity=1.0):
    if opacity <= 0.003:
        return
    h, w = spr.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4] * opacity
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (d + (s[..., :3] - d) * a).astype(np.uint8)


def wrap_text(text, fnt, max_w):
    out = []
    for para in text.split("\n"):
        words = para.split(" ")
        line = ""
        for wd in words:
            test = (line + " " + wd).strip()
            if fnt.getlength(test) <= max_w or not line:
                line = test
            else:
                out.append(line)
                line = wd
        out.append(line)
    return out


def text_image(text, kind, size, fill=(255, 255, 255), glow=None, glow_r=16, glow_strength=1.4,
               stroke=0, stroke_fill=(0, 0, 0), shadow=True, max_w=None, align="center",
               spacing=1.08, grad=None):
    fnt = font(kind, size)
    lines = wrap_text(text, fnt, max_w) if max_w else text.split("\n")
    asc, desc = fnt.getmetrics()
    lh = int((asc + desc) * spacing)
    widths = [fnt.getlength(l) for l in lines]
    tw = int(max(widths) if widths else 1) + 2 * stroke
    th_ = lh * len(lines) + 2 * stroke
    pad = int(glow_r * 2.5) + 12
    Wc, Hc = tw + 2 * pad, th_ + 2 * pad
    mask = Image.new("L", (Wc, Hc), 0)
    md = ImageDraw.Draw(mask)
    for i, l in enumerate(lines):
        if align == "center":
            lx = pad + (tw - widths[i]) / 2
        elif align == "right":
            lx = pad + tw - widths[i]
        else:
            lx = pad
        md.text((lx + stroke, pad + i * lh + stroke), l, font=fnt, fill=255, stroke_width=stroke, stroke_fill=255)
    out = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    if shadow:
        sh = mask.filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.75))
        shadow_l = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
        shadow_l.putalpha(sh)
        out.alpha_composite(shadow_l, (6, 8))
    if glow is not None:
        gm = mask.filter(ImageFilter.GaussianBlur(glow_r)).point(lambda v: min(255, int(v * glow_strength)))
        gl = Image.new("RGBA", (Wc, Hc), tuple(glow) + (0,))
        gl.putalpha(gm)
        out.alpha_composite(gl)
    # relleno + contorno
    if stroke:
        smask = Image.new("L", (Wc, Hc), 0)
        sd = ImageDraw.Draw(smask)
        for i, l in enumerate(lines):
            if align == "center":
                lx = pad + (tw - widths[i]) / 2
            elif align == "right":
                lx = pad + tw - widths[i]
            else:
                lx = pad
            sd.text((lx + stroke, pad + i * lh + stroke), l, font=fnt, fill=255, stroke_width=stroke, stroke_fill=255)
        sl = Image.new("RGBA", (Wc, Hc), tuple(stroke_fill) + (0,))
        sl.putalpha(smask)
        out.alpha_composite(sl)
        inner = Image.new("L", (Wc, Hc), 0)
        idr = ImageDraw.Draw(inner)
        for i, l in enumerate(lines):
            if align == "center":
                lx = pad + (tw - widths[i]) / 2
            elif align == "right":
                lx = pad + tw - widths[i]
            else:
                lx = pad
            idr.text((lx + stroke, pad + i * lh + stroke), l, font=fnt, fill=255)
        fill_mask = inner
    else:
        fill_mask = mask
    if grad:
        g = grad_colors(grad, Hc).astype(np.uint8)
        fl = Image.fromarray(np.repeat(g[:, None, :], Wc, axis=1), "RGB").convert("RGBA")
    else:
        fl = Image.new("RGBA", (Wc, Hc), tuple(fill) + (255,))
    fl.putalpha(fill_mask)
    out.alpha_composite(fl)
    return out


def panel_image(w, h, fill=(10, 4, 24), alpha=0.72, border=None, radius=28, border_w=3, glow=None):
    pad = 40 if glow else 4
    img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if glow:
        gm = Image.new("L", img.size, 0)
        ImageDraw.Draw(gm).rounded_rectangle([pad, pad, pad + w, pad + h], radius, outline=255, width=8)
        gm = gm.filter(ImageFilter.GaussianBlur(14))
        gl = Image.new("RGBA", img.size, tuple(glow) + (0,))
        gl.putalpha(gm)
        img.alpha_composite(gl)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([pad, pad, pad + w, pad + h], radius, fill=tuple(fill) + (int(alpha * 255),),
                        outline=(tuple(border) + (255,)) if border else None, width=border_w)
    return img


def icon_image(kind, size, color, color2=(255, 255, 255)):
    s = size
    img = Image.new("RGBA", (s + 60, s + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    o = 30
    c = tuple(color) + (255,)
    c2 = tuple(color2) + (255,)
    if kind == "warn":
        d.polygon([(o + s / 2, o), (o + s, o + s * 0.92), (o, o + s * 0.92)], fill=c)
        d.rounded_rectangle([o + s * 0.45, o + s * 0.28, o + s * 0.55, o + s * 0.62], 6, fill=(20, 10, 20, 255))
        d.ellipse([o + s * 0.44, o + s * 0.7, o + s * 0.56, o + s * 0.82], fill=(20, 10, 20, 255))
    elif kind == "check":
        d.rounded_rectangle([o, o, o + s, o + s], s // 5, fill=c)
        d.line([(o + s * 0.22, o + s * 0.52), (o + s * 0.42, o + s * 0.72), (o + s * 0.8, o + s * 0.28)],
               fill=(15, 10, 25, 255), width=max(4, s // 8), joint="curve")
    elif kind == "box":
        d.rounded_rectangle([o, o, o + s, o + s], s // 5, outline=c, width=max(3, s // 12))
    elif kind == "dot":
        d.rounded_rectangle([o + s * 0.15, o + s * 0.15, o + s * 0.85, o + s * 0.85], s // 6, fill=c)
    elif kind == "pin":
        d.ellipse([o + s * 0.2, o, o + s * 0.8, o + s * 0.6], fill=c)
        d.polygon([(o + s * 0.24, o + s * 0.4), (o + s * 0.76, o + s * 0.4), (o + s * 0.5, o + s)], fill=c)
        d.ellipse([o + s * 0.38, o + s * 0.18, o + s * 0.62, o + s * 0.42], fill=(20, 10, 30, 255))
    elif kind == "x":
        d.rounded_rectangle([o, o, o + s, o + s], s // 5, fill=c)
        w_ = max(4, s // 8)
        d.line([(o + s * 0.28, o + s * 0.28), (o + s * 0.72, o + s * 0.72)], fill=(20, 10, 25, 255), width=w_)
        d.line([(o + s * 0.72, o + s * 0.28), (o + s * 0.28, o + s * 0.72)], fill=(20, 10, 25, 255), width=w_)
    glow = img.split()[3].filter(ImageFilter.GaussianBlur(10))
    gl = Image.new("RGBA", img.size, tuple(color) + (0,))
    gl.putalpha(glow.point(lambda v: int(v * 0.8)))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(gl)
    out.alpha_composite(img)
    return out


def hstack(images, gap=20, valign="center"):
    w = sum(i.width for i in images) + gap * (len(images) - 1)
    h = max(i.height for i in images)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 0
    for im in images:
        y = (h - im.height) // 2 if valign == "center" else 0
        out.alpha_composite(im, (x, y))
        x += im.width + gap
    return out


# --------------------------------------------------------------------------- elementos
class Element:
    """Sprite animado con entrada temporizada. (cx, cy) = centro; anchor='left' usa x izquierda."""

    def __init__(self, img, cx, cy, t_in=0.0, anim="up", dur_in=0.45, anchor="center", float_amp=0.0,
                 counter=None, t_out=None):
        self.img = img
        self.spr = to_sprite(img)
        self.cx, self.cy = cx, cy
        self.t_in, self.anim, self.dur_in = t_in, anim, dur_in
        self.anchor = anchor
        self.float_amp = float_amp
        self.counter = counter  # (fn(value)->PIL, start, end, fmt, dur)
        self.t_out = t_out
        self._scaled = {}
        self._counter_cache = {}

    def _topleft(self, spr_w, spr_h, cx, cy):
        if self.anchor == "left":
            return cx, cy - spr_h / 2
        if self.anchor == "right":
            return cx - spr_w, cy - spr_h / 2
        return cx - spr_w / 2, cy - spr_h / 2

    def draw(self, frame, t, scene_dur, global_t=0.0):
        if t < self.t_in:
            return
        p = (t - self.t_in) / self.dur_in
        e = ease_out(p)
        op = e
        dx = dy = 0.0
        scale = 1.0
        if self.anim == "up":
            dy = (1 - e) * 46
        elif self.anim == "down":
            dy = -(1 - e) * 46
        elif self.anim == "left":
            dx = -(1 - e) * 140
        elif self.anim == "right":
            dx = (1 - e) * 140
        elif self.anim == "pop":
            scale = lerp(0.55, 1.0, ease_back(p)) if p < 1 else 1.0
            op = clamp(p * 2.5)
        elif self.anim == "zoom":
            scale = lerp(1.25, 1.0, e) if p < 1 else 1.0
        elif self.anim == "fade":
            pass
        # salida
        out_start = (self.t_out if self.t_out is not None else scene_dur - 0.3)
        if t > out_start:
            op *= clamp(1 - (t - out_start) / 0.3)
        if self.float_amp:
            dy += math.sin(global_t * 2.1 + self.cx * 0.01) * self.float_amp
        spr = self.spr
        if self.counter is not None:
            fn, v0, v1, fmt, cdur = self.counter
            cp = ease_out((t - self.t_in) / cdur)
            val = fmt.format(lerp(v0, v1, cp)) if cp < 1 else fmt.format(v1)
            if val not in self._counter_cache:
                self._counter_cache[val] = to_sprite(fn(val))
            spr = self._counter_cache[val]
        if abs(scale - 1.0) > 0.01:
            q = round(scale, 2)
            if q not in self._scaled:
                im = self.img
                nw, nh = max(1, int(im.width * q)), max(1, int(im.height * q))
                self._scaled[q] = to_sprite(im.resize((nw, nh), Image.BILINEAR))
            spr = self._scaled[q]
        h, w = spr.shape[:2]
        x, y = self._topleft(w, h, self.cx + dx, self.cy + dy)
        blend(frame, spr, x, y, op)


class LineGrow:
    """Línea horizontal que crece (para la línea de tiempo)."""

    def __init__(self, x0, x1, y, color, keyframes):
        self.x0, self.x1, self.y, self.color = x0, x1, y, np.array(color, np.float32)
        self.keyframes = keyframes  # [(t, frac)]

    def draw(self, frame, t, scene_dur, global_t=0.0):
        frac = 0.0
        for i, (kt, kf) in enumerate(self.keyframes):
            if t >= kt:
                prev = self.keyframes[i - 1][1] if i else 0.0
                frac = lerp(prev, kf, ease_out((t - kt) / 0.5))
        op = 1.0
        if t > scene_dur - 0.3:
            op = clamp(1 - (t - (scene_dur - 0.3)) / 0.3)
        xe = int(lerp(self.x0, self.x1, frac))
        if xe <= self.x0:
            return
        for off, a in ((-6, 0.15), (-3, 0.35), (0, 1.0), (3, 0.35), (6, 0.15)):
            yy = self.y + off
            seg = frame[yy:yy + 3, self.x0:xe].astype(np.float32)
            frame[yy:yy + 3, self.x0:xe] = (seg + (self.color - seg) * a * op).astype(np.uint8)


# --------------------------------------------------------------------------- escenas
def reveal_times(scene, seg_starts, n, dur, offset=None, stagger=0.32):
    """Tiempo de aparición de n elementos sincronizado con la narración."""
    ats = scene.get("at")
    if ats is not None:
        times = []
        last_seg, k = None, 0
        for a in ats:
            a = min(a, len(seg_starts) - 1)
            k = k + 1 if a == last_seg else 0
            last_seg = a
            times.append(seg_starts[a] + 0.15 + k * stagger)
        return times
    if offset is None:
        offset = 1 if len(seg_starts) >= n + 1 else 0
    if len(seg_starts) - offset >= n:
        return [seg_starts[i + offset] + 0.15 for i in range(n)]
    start = seg_starts[min(offset, len(seg_starts) - 1)] + 0.3
    span = max(0.5, dur * 0.7 - start)
    return [start + i * min(0.6, span / max(1, n)) for i in range(n)]


def heading(text, th, y=150, size=104, t=0.1):
    img = text_image(text, "display", size, fill=(255, 255, 255), glow=th["acc2"], glow_r=18,
                     max_w=1700, grad=[(255, 255, 255), th["warm"]])
    return Element(img, W / 2, y, t, "down")


def scene_title(sc, th, segs, dur):
    els = []
    t = text_image(sc["title"], "display", sc.get("size", 176), glow=th["acc2"], glow_r=26, glow_strength=1.6,
                   grad=[(255, 255, 255), (255, 255, 255), th["warm"]], stroke=0, spacing=0.9)
    pad = int(26 * 2.5) + 12
    inner_h = t.height - 2 * pad
    cy = 520
    top, bottom = cy - inner_h / 2, cy + inner_h / 2
    if sc.get("kicker"):
        k = text_image(sc["kicker"], "alt", 78, fill=th["acc"], glow=th["acc"], glow_r=12, shadow=True)
        els.append(Element(k, W / 2, top - 70, 0.05, "down"))
    els.append(Element(t, W / 2, cy, 0.25, "pop", dur_in=0.6))
    if sc.get("sub"):
        s = text_image(sc["sub"], "body", 50, fill=(255, 255, 255), glow=(0, 0, 0), glow_r=10, glow_strength=2.0)
        els.append(Element(s, W / 2, bottom + 85, 0.75, "up"))
    return els, False


def scene_quote(sc, th, segs, dur):
    els = []
    if sc.get("kicker"):
        k = text_image(sc["kicker"], "alt", 70, fill=th["acc"], glow=th["acc"], glow_r=10)
        els.append(Element(k, W / 2, 300, 0.05, "down"))
    q = text_image(sc["text"], "display", sc.get("size", 150), glow=th["acc2"], glow_r=24, max_w=1650,
                   grad=[(255, 255, 255), th["warm"]], spacing=0.9)
    els.append(Element(q, W / 2, 530, 0.2, "pop", dur_in=0.55))
    if sc.get("sub"):
        s = text_image(sc["sub"], "body", 46, fill=(235, 235, 245), max_w=1500)
        t_sub = segs[1] + 0.1 if len(segs) > 1 else 0.9
        els.append(Element(s, W / 2, 780, t_sub, "up"))
    return els, True


def scene_bullets(sc, th, segs, dur):
    els = [heading(sc["heading"], th)]
    items = sc["items"]
    marker = sc.get("marker", "dot")
    fsize = sc.get("size", 54 if len(items) <= 4 else 46)
    imgs = []
    for it in items:
        txt = text_image(it, "body", fsize, fill=(255, 255, 255), max_w=1260, align="left", shadow=True, glow_r=4)
        mk = icon_image(marker, int(fsize * 0.85), th["warm"] if marker == "warn" else th["acc"])
        imgs.append(hstack([mk, txt], gap=4))
    gap = 26
    total = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    top = max(300, 600 - total / 2)
    pw, ph = 1560, int(total + 70)
    pan = panel_image(pw, ph, border=th["acc"], glow=th["acc"])
    els.append(Element(pan, W / 2, top + total / 2, 0.05, "fade", dur_in=0.35))
    times = reveal_times(sc, segs, len(items), dur)
    y = top
    for img, t in zip(imgs, times):
        els.append(Element(img, 230, y + img.height / 2, t, "left", anchor="left"))
        y += img.height + gap
    return els, True


def scene_stat(sc, th, segs, dur):
    els = []
    if sc.get("kicker"):
        k = text_image(sc["kicker"], "alt", 80, fill=th["acc"], glow=th["acc"], glow_r=12)
        els.append(Element(k, W / 2, 230, 0.05, "down"))

    def val_img(v):
        return text_image(v + (" " + sc["unit"] if sc.get("unit") else ""), "display", sc.get("size", 290),
                          glow=th["acc2"], glow_r=30, glow_strength=1.7,
                          grad=[(255, 255, 255), th["warm"]], spacing=1.0)

    counter = None
    if "count" in sc:
        v0, v1, fmt = sc["count"]
        counter = (val_img, v0, v1, fmt, 1.1)
        first = val_img(fmt.format(v1))
    else:
        first = val_img(sc["value"])
    els.append(Element(first, W / 2, 520, 0.2, "pop", dur_in=0.55, counter=counter))
    if sc.get("label"):
        lb = text_image(sc["label"], "body", 52, fill=(255, 255, 255), max_w=1500, glow=(0, 0, 0), glow_r=8,
                        glow_strength=2.0)
        els.append(Element(lb, W / 2, 800, 0.7, "up"))
    return els, False


def scene_cards(sc, th, segs, dur):
    els = [heading(sc["heading"], th)] if sc.get("heading") else []
    cards = sc["cards"]
    n = len(cards)
    cw = min(720, int((1700 - (n - 1) * 60) / n))
    ch = 520
    imgs = []
    for i, c in enumerate(cards):
        col = th["acc"] if i % 2 == 0 else th["acc2"]
        base = panel_image(cw, ch, border=col, glow=col)
        v = text_image(c[0], "display", c[3] if len(c) > 3 else 170, glow=col, glow_r=20,
                       grad=[(255, 255, 255), th["warm"]])
        t = text_image(c[1], "alt", 76, fill=col, glow=col, glow_r=8)
        s = text_image(c[2], "body", 38, fill=(230, 230, 240), max_w=cw - 60) if len(c) > 2 and c[2] else None
        base.alpha_composite(t, (int((base.width - t.width) / 2), 40 + 30))
        base.alpha_composite(v, (int((base.width - v.width) / 2), int(base.height / 2 - v.height / 2 + 10)))
        if s:
            base.alpha_composite(s, (int((base.width - s.width) / 2), base.height - s.height - 60))
        imgs.append(base)
    times = reveal_times(sc, segs, n, dur)
    total_w = n * cw + (n - 1) * 60
    x = W / 2 - total_w / 2 + cw / 2
    for img, t in zip(imgs, times):
        els.append(Element(img, x, 610, t, "pop", dur_in=0.5))
        x += cw + 60
    return els, True


def scene_table(sc, th, segs, dur):
    els = [heading(sc["heading"], th, y=140, size=96)]
    rows = sc["rows"]
    n = len(rows)
    rh = min(100, int(700 / n))
    lsize = int(rh * 0.5)
    desc = sc.get("style") == "desc"
    top = 290
    total = n * rh
    top = max(260, 600 - total / 2 + 20)
    times = reveal_times(sc, segs, n, dur)
    for i, (row, t) in enumerate(zip(rows, times)):
        left, right = row[0], row[1]
        hl = len(row) > 2 and row[2]
        rowimg = Image.new("RGBA", (1600, rh - 10), (0, 0, 0, 0))
        dr = ImageDraw.Draw(rowimg)
        bg = (40, 12, 70, 200) if i % 2 == 0 else (20, 6, 40, 200)
        if hl:
            bg = tuple(int(c * 0.45) for c in th["acc2"]) + (230,)
        dr.rounded_rectangle([0, 0, 1599, rh - 11], 16, fill=bg)
        dr.rectangle([0, 0, 8, rh - 11], fill=tuple(th["acc"]) + (255,))
        lt = text_image(left, "body", lsize, fill=(255, 255, 255), shadow=False, glow_r=2, max_w=760 if desc else 1000,
                        align="left")
        rowimg.alpha_composite(lt, (40 - 17, int((rh - 10 - lt.height) / 2)))
        if desc:
            rt = text_image(right, "body", int(lsize * 0.82), fill=(220, 225, 240), shadow=False, glow_r=2, max_w=820,
                            align="right")
        else:
            rt = text_image(right, "display", int(lsize * 1.15), fill=th["warm"], shadow=False, glow_r=2)
        rowimg.alpha_composite(rt, (1600 - rt.width - 30 + 17, int((rh - 10 - rt.height) / 2)))
        els.append(Element(rowimg, W / 2, top + i * rh + rh / 2, t, "left"))
    return els, True


def scene_compare(sc, th, segs, dur):
    els = [heading(sc["heading"], th)]
    cols = sc["cols"]  # [(title, [items]), (title, [items])]
    cw = 820
    times = reveal_times(sc, segs, 2, dur)
    built = []
    for i, (title, items) in enumerate(cols):
        col = th["acc"] if i == 0 else th["acc2"]
        tt = text_image(title, "display", 72, fill=col, glow=col, glow_r=10, max_w=cw - 60)
        rows = []
        for it in items:
            mk = icon_image("check" if sc.get("marker") == "check" else "dot", 40, col)
            tx = text_image(it, "body", 50, fill=(255, 255, 255), max_w=cw - 170, align="left", shadow=False, glow_r=2)
            rows.append(hstack([mk, tx], gap=0))
        built.append((col, tt, rows))
    ch = max(tt.height - 40 + sum(r.height - 22 for r in rows) + 40 for _, tt, rows in built)
    for i, ((col, tt, rows), t) in enumerate(zip(built, times)):
        base = panel_image(cw, ch, border=col, glow=col)
        base.alpha_composite(tt, (int((base.width - tt.width) / 2), 40 - 10))
        y = 40 - 10 + tt.height - 40
        for row in rows:
            base.alpha_composite(row, (40 + 6, y))
            y += row.height - 22
        x = W / 2 - 450 if i == 0 else W / 2 + 450
        els.append(Element(base, x, 300 + base.height / 2 - 40 + max(0, (620 - ch) / 2), t, "left" if i == 0 else "right"))
    return els, True


def scene_timeline(sc, th, segs, dur):
    els = [heading(sc["heading"], th)]
    pts = sc["points"]
    n = len(pts)
    x0, x1, y = 200, W - 200, 560
    xs = [x0 + (x1 - x0) * (i + 0.5) / n for i in range(n)]
    times = reveal_times(sc, segs, n, dur)
    kf = [(t - 0.1, (xs[i] - x0) / (x1 - x0) + (0.5 / n if i == n - 1 else 0)) for i, t in enumerate(times)]
    els.append(LineGrow(x0, x1, y, th["acc"], kf))
    colw = int((x1 - x0) / n) - 30
    for i, (p, t) in enumerate(zip(pts, times)):
        dot = icon_image("dot", 44, th["acc2"])
        els.append(Element(dot, xs[i], y + 2, t, "pop", dur_in=0.4))
        lab = text_image(p[0], "display", 66 if n <= 4 else 56, glow=th["acc2"], glow_r=12, max_w=colw,
                         grad=[(255, 255, 255), th["warm"]])
        els.append(Element(lab, xs[i], y - 105, t + 0.08, "down"))
        body = text_image(p[1], "body", 44 if n <= 3 else 38, fill=(240, 240, 250), max_w=colw, glow=(0, 0, 0),
                          glow_r=6, glow_strength=2.0)
        els.append(Element(body, xs[i], y + 70 + body.height / 2 - 30, t + 0.16, "up"))
    return els, True


# Esquema ficticio y aproximado de un estado peninsular (arte original).
_LAND = [(560, 250), (980, 230), (1180, 260), (1300, 330), (1340, 430), (1390, 560), (1420, 680),
         (1400, 790), (1330, 880), (1260, 900), (1220, 860), (1150, 760), (1060, 700), (980, 640),
         (920, 560), (850, 500), (760, 460), (640, 440), (520, 420), (420, 400), (380, 330), (440, 270)]
_KEYS = [(1180, 950), (1120, 975), (1055, 992), (990, 1003), (925, 1010), (860, 1012)]


def scene_map(sc, th, segs, dur):
    els = []
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gm = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(gm)
    gd.polygon(_LAND, outline=255, width=10)
    for kx, ky in _KEYS:
        gd.ellipse([kx - 22, ky - 12, kx + 22, ky + 12], outline=255, width=8)
    gm = gm.filter(ImageFilter.GaussianBlur(12))
    gl = Image.new("RGBA", (W, H), tuple(th["acc"]) + (0,))
    gl.putalpha(gm)
    img.alpha_composite(gl)
    d = ImageDraw.Draw(img)
    d.polygon(_LAND, fill=(24, 10, 50, 235), outline=tuple(th["acc"]) + (255,), width=4)
    for kx, ky in _KEYS:
        d.ellipse([kx - 22, ky - 12, kx + 22, ky + 12], fill=(24, 10, 50, 235), outline=tuple(th["acc"]) + (255,), width=3)
    # textura de pantano / bosque
    rnd = random.Random(3)
    for _ in range(140):
        x, y = rnd.randint(1000, 1250), rnd.randint(700, 860)
        d.line([(x, y), (x + 8, y - 10)], fill=(60, 160, 120, 140), width=2)
    for _ in range(90):
        x, y = rnd.randint(700, 1100), rnd.randint(270, 400)
        d.polygon([(x, y), (x + 9, y + 18), (x - 9, y + 18)], fill=(60, 140, 90, 150))
    els.append(Element(img, W / 2, H / 2, 0.0, "fade", dur_in=0.6))
    regions = sc["regions"]  # [(name, x, y, side)]
    times = reveal_times(sc, segs, len(regions), dur)
    for (name, x, y, side), t in zip(regions, times):
        pin = icon_image("pin", 56, th["acc2"])
        els.append(Element(pin, x, y - 30, t, "pop", dur_in=0.45))
        lab = text_image(name, "display", 50, glow=th["acc2"], glow_r=10, grad=[(255, 255, 255), th["warm"]])
        lx = x + 45 if side == "r" else x - 45
        els.append(Element(lab, lx, y - 30, t + 0.1, "right" if side == "r" else "left",
                           anchor="left" if side == "r" else "right"))
    note = text_image(sc.get("note", "Esquema ilustrativo · ubicaciones aproximadas"), "body", 30, fill=(200, 200, 220))
    els.append(Element(note, W / 2, H - 40, 0.8, "fade"))
    if sc.get("heading"):
        els.append(heading(sc["heading"], th, y=110, size=90))
    return els, True


def scene_outro(sc, th, segs, dur):
    els = []
    name = text_image(CHANNEL, "display", 150, glow=th["acc2"], glow_r=26, grad=[(255, 255, 255), th["warm"]])
    els.append(Element(name, W / 2, 230, 0.05, "pop"))

    def button(label, color, txtcol=(255, 255, 255)):
        b = Image.new("RGBA", (640, 150), (0, 0, 0, 0))
        ImageDraw.Draw(b).rounded_rectangle([0, 0, 639, 149], 30, fill=tuple(color) + (255,))
        tx = text_image(label, "black", 64, fill=txtcol, shadow=False, glow_r=2)
        b.alpha_composite(tx, (int((640 - tx.width) / 2), int((150 - tx.height) / 2)))
        return b

    sub = Element(button("SUSCRÍBETE", (230, 30, 40)), W / 2, 470, 0.4, "pop", t_out=2.2)
    done = Element(button("SUSCRITO ✓" if False else "SUSCRITO", (70, 70, 85), (220, 220, 230)), W / 2, 470, 2.2,
                   "fade", dur_in=0.12)
    els += [sub, done]
    # cursor
    cur = Image.new("RGBA", (60, 80), (0, 0, 0, 0))
    ImageDraw.Draw(cur).polygon([(4, 4), (4, 64), (20, 50), (32, 76), (42, 70), (30, 46), (52, 46)],
                                fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    els.append(CursorMove(cur, (1500, 900), (W / 2 + 120, 500), 1.2, 2.1))
    bell = text_image("y activa la campanita", "body", 46, fill=(255, 255, 255))
    els.append(Element(bell, W / 2, 600, 2.4, "up"))
    if sc.get("next"):
        k = text_image("SIGUIENTE VIDEO", "alt", 60, fill=th["acc"], glow=th["acc"], glow_r=8)
        nx = text_image(sc["next"], "display", 64, max_w=1400, glow=th["acc2"], glow_r=10)
        card = panel_image(max(k.width, nx.width) + 80, k.height + nx.height + 20, border=th["acc"], glow=th["acc"])
        card.alpha_composite(k, (int((card.width - k.width) / 2), 40 + 10))
        card.alpha_composite(nx, (int((card.width - nx.width) / 2), 40 + k.height - 10))
        els.append(Element(card, W / 2, 850, 3.0, "up"))
    return els, True


class CursorMove:
    def __init__(self, img, p0, p1, t0, t1):
        self.spr = to_sprite(img)
        self.p0, self.p1, self.t0, self.t1 = p0, p1, t0, t1

    def draw(self, frame, t, scene_dur, global_t=0.0):
        if t < self.t0 or t > self.t1 + 1.2:
            return
        e = ease_out((t - self.t0) / (self.t1 - self.t0))
        x = lerp(self.p0[0], self.p1[0], e)
        y = lerp(self.p0[1], self.p1[1], e)
        if self.t1 - 0.05 < t < self.t1 + 0.15:
            y += 6
        op = clamp(1 - (t - self.t1 - 0.8) / 0.4)
        blend(frame, self.spr, x, y, op)


BUILDERS = {
    "title": scene_title, "quote": scene_quote, "bullets": scene_bullets, "stat": scene_stat,
    "cards": scene_cards, "table": scene_table, "compare": scene_compare, "timeline": scene_timeline,
    "map": scene_map, "outro": scene_outro,
}


# --------------------------------------------------------------------------- superposiciones fijas
class Overlay:
    def __init__(self, th, label_texts):
        self.th = th
        bug = text_image(CHANNEL, "display", 40, glow=th["acc2"], glow_r=8, grad=[(255, 255, 255), th["warm"]])
        self.bug = to_sprite(bug)
        self.labels = {}
        for key, txt in label_texts.items():
            if txt:
                self.labels[key] = to_sprite(text_image(txt, "alt", 40, fill=th["acc"], glow=th["acc"], glow_r=6))
        band = np.zeros((H, 260, 4), np.float32)
        xs = np.linspace(-1, 1, 260)
        prof = np.exp(-xs ** 2 * 6)
        band[..., :3] = np.array(th["acc"], np.float32)
        band[..., 3] = prof[None, :] * 0.85
        self.band = band
        self.col = np.array(th["acc2"], np.float32)

    def draw(self, frame, gt, total, scene_idx, scene_t):
        blend(frame, self.bug, 10, 6, 0.9)
        lab = self.labels.get(scene_idx)
        if lab is not None:
            blend(frame, lab, W - lab.shape[1] - 20, 14, clamp(scene_t / 0.4) * 0.95)
        # barra de progreso
        px = int(W * clamp(gt / total))
        frame[H - 8:H, :px] = (frame[H - 8:H, :px] * 0.2 + self.col * 0.8).astype(np.uint8)
        # barrido de transición al inicio de cada escena
        if scene_idx > 0 and scene_t < 0.35:
            p = scene_t / 0.35
            x = int(lerp(-300, W + 40, ease_out(p)))
            blend(frame, self.band, x, 0, 1 - p * 0.6)


def build_scene_elements(sc, theme, seg_starts, dur):
    th = THEMES[theme]
    els, dim = BUILDERS[sc["type"]](sc, th, seg_starts, dur)
    return els, sc.get("dim", dim)
