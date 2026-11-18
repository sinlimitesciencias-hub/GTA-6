"""Construye cada video: voz -> mezcla de audio -> animación -> MP4, más miniatura, SRT, guion y metadatos.

Uso:
    python build.py            # todos
    python build.py 01 03      # sólo esos
    python build.py --preview 01   # renderiza fotogramas de muestra (PNG) sin video
"""
import math
import os
import subprocess
import sys
import time

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter

import audio
import engine as E
from contenido import VIDEOS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "videos")
CACHE = os.environ.get("CACHE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache"))


def vdir(v):
    d = os.path.join(OUT, f"{v['id']}-{v['slug']}")
    os.makedirs(d, exist_ok=True)
    return d


def fmt_ts(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


# --------------------------------------------------------------------------- miniatura
def thumb_icon(kind, size, th):
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    a, b, w = tuple(th["acc"]) + (255,), tuple(th["warm"]) + (255,), (255, 255, 255, 255)
    k = s / 400
    if kind == "clock":
        d.ellipse([20 * k, 20 * k, 380 * k, 380 * k], fill=(20, 8, 40, 255), outline=a, width=int(22 * k))
        for i in range(12):
            ang = i * math.pi / 6
            r0, r1 = 135 * k, 160 * k
            d.line([(200 * k + r0 * math.sin(ang), 200 * k - r0 * math.cos(ang)),
                    (200 * k + r1 * math.sin(ang), 200 * k - r1 * math.cos(ang))], fill=w, width=int(10 * k))
        d.line([(200 * k, 200 * k), (200 * k, 80 * k)], fill=w, width=int(20 * k))
        d.line([(200 * k, 200 * k), (290 * k, 200 * k)], fill=b, width=int(20 * k))
        d.ellipse([180 * k, 180 * k, 220 * k, 220 * k], fill=b)
    elif kind == "disk":
        for i in range(3):
            y = 60 * k + i * 100 * k
            d.rounded_rectangle([40 * k, y, 360 * k, y + 80 * k], int(20 * k), fill=(20, 8, 40, 255), outline=a, width=int(12 * k))
            d.ellipse([290 * k, y + 28 * k, 314 * k, y + 52 * k], fill=b if i < 2 else (255, 60, 60, 255))
    elif kind == "price":
        d.polygon([(60 * k, 140 * k), (200 * k, 30 * k), (370 * k, 200 * k), (230 * k, 370 * k), (60 * k, 300 * k)],
                  fill=(20, 8, 40, 255), outline=a)
        d.line([(60 * k, 140 * k), (200 * k, 30 * k), (370 * k, 200 * k), (230 * k, 370 * k), (60 * k, 300 * k), (60 * k, 140 * k)],
               fill=a, width=int(16 * k))
        d.ellipse([110 * k, 150 * k, 160 * k, 200 * k], fill=b)
        f = E.font("display", int(170 * k))
        d.text((235 * k, 215 * k), "$", font=f, fill=b, anchor="mm")
    elif kind == "pc":
        d.rounded_rectangle([30 * k, 50 * k, 370 * k, 280 * k], int(20 * k), fill=(20, 8, 40, 255), outline=a, width=int(16 * k))
        d.rectangle([170 * k, 280 * k, 230 * k, 330 * k], fill=a)
        d.rounded_rectangle([110 * k, 330 * k, 290 * k, 360 * k], int(10 * k), fill=a)
        f = E.font("display", int(150 * k))
        d.text((200 * k, 165 * k), "?", font=f, fill=b, anchor="mm")
    elif kind == "console":
        d.rounded_rectangle([20 * k, 120 * k, 380 * k, 300 * k], int(80 * k), fill=(20, 8, 40, 255), outline=a, width=int(16 * k))
        d.rectangle([85 * k, 195 * k, 145 * k, 220 * k], fill=w)
        d.rectangle([102 * k, 178 * k, 128 * k, 238 * k], fill=w)
        for (x, y) in ((280, 180), (320, 210), (240, 210), (280, 240)):
            d.ellipse([(x - 14) * k, (y - 14) * k, (x + 14) * k, (y + 14) * k], fill=b)
    elif kind == "duo":
        for cx, col in ((140, a), (260, tuple(th["acc2"]) + (255,))):
            d.ellipse([(cx - 60) * k, 60 * k, (cx + 60) * k, 180 * k], fill=(20, 8, 40, 255), outline=col, width=int(14 * k))
            d.pieslice([(cx - 110) * k, 200 * k, (cx + 110) * k, 420 * k], 180, 360, fill=(20, 8, 40, 255), outline=col, width=int(14 * k))
    elif kind == "pin":
        d.ellipse([90 * k, 20 * k, 310 * k, 240 * k], fill=a)
        d.polygon([(105 * k, 170 * k), (295 * k, 170 * k), (200 * k, 380 * k)], fill=a)
        d.ellipse([150 * k, 80 * k, 250 * k, 180 * k], fill=(20, 8, 40, 255))
    elif kind == "check":
        d.rounded_rectangle([30 * k, 30 * k, 370 * k, 370 * k], int(60 * k), fill=a)
        d.line([(100 * k, 210 * k), (175 * k, 285 * k), (310 * k, 120 * k)], fill=(20, 8, 40, 255), width=int(44 * k), joint="curve")
    elif kind == "online":
        for i, r in enumerate((170, 120, 70)):
            d.arc([(200 - r) * k, (250 - r) * k, (200 + r) * k, (250 + r) * k], 220, 320, fill=a, width=int(30 * k))
        d.ellipse([175 * k, 225 * k, 225 * k, 275 * k], fill=a)
        f = E.font("display", int(130 * k))
        d.text((310 * k, 320 * k), "?", font=f, fill=b, anchor="mm")
    elif kind == "calendar":
        d.rounded_rectangle([40 * k, 60 * k, 360 * k, 360 * k], int(30 * k), fill=(20, 8, 40, 255), outline=a, width=int(16 * k))
        d.rectangle([40 * k, 60 * k, 360 * k, 130 * k], fill=a)
        f = E.font("display", int(170 * k))
        d.text((200 * k, 250 * k), "13", font=f, fill=b, anchor="mm")
    glow = img.split()[3].filter(ImageFilter.GaussianBlur(14))
    gl = Image.new("RGBA", img.size, tuple(th["acc"]) + (0,))
    gl.putalpha(glow)
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out.alpha_composite(gl)
    out.alpha_composite(img)
    return out


def make_thumbnail(v, bg, path):
    th = E.THEMES[v["theme"]]
    base = Image.fromarray(bg.frame(5)).convert("RGBA")
    arr = np.asarray(base, np.float32)
    arr[..., :3] = np.clip(arr[..., :3] * 1.15, 0, 255)
    base = Image.fromarray(arr.astype(np.uint8))
    # oscurece la izquierda para el texto
    shade = Image.new("L", (E.W, E.H), 0)
    sd = ImageDraw.Draw(shade)
    for x in range(E.W):
        sd.line([(x, 0), (x, E.H)], fill=int(190 * max(0, 1 - x / 1300)))
    dark = Image.new("RGBA", (E.W, E.H), (6, 2, 14, 255))
    dark.putalpha(shade)
    base.alpha_composite(dark)
    icon = thumb_icon(v["thumb"]["icon"], 560, th)
    base.alpha_composite(icon, (E.W - 560 - 110, 300))
    tag = E.text_image("GTA 6", "display", 140, fill=th["warm"], stroke=8, stroke_fill=(10, 0, 20), glow=th["acc2"], glow_r=18)
    base.alpha_composite(tag, (40, 30))
    y = 230
    for i, line in enumerate(v["thumb"]["lines"]):
        size = 250 if len(line) <= 9 else 200
        t = E.text_image(line, "display", size, fill=(255, 255, 255) if i == 0 else th["warm"], stroke=12,
                         stroke_fill=(10, 0, 20), glow=th["acc2"], glow_r=22, spacing=1.0)
        base.alpha_composite(t, (30, y))
        y += t.height - 150
    badge_txt = E.text_image(v["thumb"]["badge"], "black", 74, fill=(15, 5, 25), shadow=False, glow_r=2)
    bw, bh = badge_txt.width + 10, badge_txt.height - 30
    badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(badge).rounded_rectangle([0, 0, bw - 1, bh - 1], 22, fill=tuple(th["acc"]) + (255,))
    badge.alpha_composite(badge_txt, (5, int((bh - badge_txt.height) / 2)))
    badge = badge.rotate(4, expand=True, resample=Image.BICUBIC)
    base.alpha_composite(badge, (E.W - badge.width - 60, 120))
    base.convert("RGB").resize((1280, 720), Image.LANCZOS).save(path, quality=92)


# --------------------------------------------------------------------------- textos
DISCLAIMER = ("Canal de fans no oficial. No está afiliado a Rockstar Games ni a Take-Two Interactive. "
              "GTA y Grand Theft Auto son marcas de sus respectivos dueños. Información verificada al 18 de noviembre "
              "de 2026; lo no confirmado se indica como tal.")


def write_texts(v, timeline, total, d):
    chapters = []
    for sc, tl in zip(v["scenes"], timeline):
        if sc.get("chapter"):
            chapters.append((0 if not chapters else tl["start"], sc["chapter"]))
    idx = {x["id"]: x for x in VIDEOS}
    others = [x for x in VIDEOS if x["id"] != v["id"]][:3]
    md = [f"# {v['title']}", "", f"**Publicar:** {v['publish']}  ", f"**Duración:** {fmt_ts(total)}  ",
          f"**Archivo:** `video.mp4` · **Miniatura:** `miniatura.jpg` · **Subtítulos:** `subtitulos.srt` (español)", "",
          "## Título", "", "```", v["title"], "```", "", "## Descripción (copiar y pegar)", "", "```",
          v["desc"], "", "⏱️ CAPÍTULOS"]
    md += [f"{fmt_ts(t)} {name}" for t, name in chapters]
    md += ["", "📺 MÁS VIDEOS DE GTA 6 EN EL CANAL:"] + [f"▶ {o['title']}" for o in others]
    md += ["", "🔔 Suscríbete para todas las guías de GTA 6 desde el día 1.", "",
           "#GTA6 #GTAVI #GTA6Español", "", DISCLAIMER, "```", "", "## Etiquetas", "", "```", ", ".join(v["tags"]), "```", "",
           "## Ajustes recomendados al subir", "",
           "- Idioma del video: Español · Subir `subtitulos.srt` como subtítulos en español",
           "- Categoría: Videojuegos · Juego: Grand Theft Auto VI",
           "- \"Contenido alterado o sintético\": **Sí** (voz generada por IA). Es obligatorio declararlo en YouTube.",
           "- Pantalla final: suscribirse + el video siguiente de la serie (últimos 10 s)",
           "- Tarjeta en el minuto 1: video 01 (horarios) o el que se mencione en la narración",
           ""]
    open(os.path.join(d, "metadata.md"), "w", encoding="utf-8").write("\n".join(md))
    g = [f"# Guion — {v['title']}", "", f"Duración final: {fmt_ts(total)} · Voz: Kokoro `{audio.VOICE}` ({audio.LANG})", ""]
    for i, (sc, tl) in enumerate(zip(v["scenes"], timeline), 1):
        g.append(f"## Escena {i} · {fmt_ts(tl['start'])} · visual: `{sc['type']}`")
        vis = {k: sc[k] for k in ("kicker", "title", "text", "heading", "items", "rows", "cards", "cols", "points", "value", "label", "sub", "next")
               if k in sc}
        for k, val in vis.items():
            if isinstance(val, list):
                g.append(f"- **{k}:** " + " | ".join(" / ".join(map(str, x)) if isinstance(x, (list, tuple)) else str(x) for x in val))
            else:
                g.append(f"- **{k}:** {str(val).replace(chr(10), ' ')}")
        g.append("")
        for (t0, txt, _) in tl["segs"]:
            g.append(f"> `{fmt_ts(t0)}` {txt}")
        g.append("")
    open(os.path.join(d, "guion.md"), "w", encoding="utf-8").write("\n".join(g))


# --------------------------------------------------------------------------- render
def prepare(v):
    d = vdir(v)
    voice, timeline = audio.build_voice(v, os.path.join(CACHE, v["id"]))
    total = timeline[-1]["end"] + 0.6
    return d, voice, timeline, total


def scene_plan(v, timeline):
    plan = []
    for sc, tl in zip(v["scenes"], timeline):
        dur = tl["end"] - tl["start"]
        seg_rel = [s[0] - tl["start"] for s in tl["segs"]]
        els, dim = E.build_scene_elements(sc, v["theme"], seg_rel, dur)
        plan.append((tl["start"], dur, els, dim))
    return plan


def render(v, preview=False):
    t0 = time.time()
    d, voice, timeline, total = prepare(v)
    bg = E.Background(v["theme"], seed=int(v["id"]))
    make_thumbnail(v, bg, os.path.join(d, "miniatura.jpg"))
    plan = scene_plan(v, timeline)
    overlay = E.Overlay(E.THEMES[v["theme"]], {i: (sc.get("label", "") if sc["type"] != "stat" else sc.get("tag", "")) for i, sc in enumerate(v["scenes"])})
    nframes = int(math.ceil(total * E.FPS))

    def frame_at(fi):
        gt = fi / E.FPS
        si = 0
        while si + 1 < len(plan) and gt >= plan[si + 1][0]:
            si += 1
        start, dur, els, dim = plan[si]
        st = gt - start
        frame = bg.frame(fi, dim=dim).copy()
        for el in els:
            el.draw(frame, st, dur, gt)
        overlay.draw(frame, gt, total, si, st)
        return frame

    if preview:
        pdir = os.path.join(CACHE, "preview")
        os.makedirs(pdir, exist_ok=True)
        for si, (start, dur, _, _) in enumerate(plan):
            fi = int((start + dur * 0.85) * E.FPS)
            Image.fromarray(frame_at(fi)).save(os.path.join(pdir, f"{v['id']}_{si:02d}.jpg"), quality=85)
        print("preview", v["id"], fmt_ts(total))
        return
    mixwav = os.path.join(CACHE, f"{v['id']}_mix.wav")
    sf.write(mixwav, audio.mix(voice, timeline, total, v["music"], int(v["id"])), audio.SR, subtype="PCM_16")
    open(os.path.join(d, "subtitulos.srt"), "w", encoding="utf-8").write(audio.make_srt(timeline))
    write_texts(v, timeline, total, d)
    out = os.path.join(d, "video.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{E.W}x{E.H}",
           "-r", str(E.FPS), "-i", "-", "-i", mixwav, "-c:v", "libx264", "-preset", os.environ.get("X264_PRESET", "medium"),
           "-crf", os.environ.get("CRF", "22"), "-tune", "animation", "-pix_fmt", "yuv420p", "-threads", "2",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(nframes):
        p.stdin.write(frame_at(fi).tobytes())
        if fi % 900 == 0:
            print(f"[{v['id']}] {fi}/{nframes} ({time.time() - t0:.0f}s)", flush=True)
    p.stdin.close()
    p.wait()
    print(f"[{v['id']}] listo {fmt_ts(total)} en {time.time() - t0:.0f}s -> {out}", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--preview" in args
    ids = [a for a in args if not a.startswith("--")]
    for v in VIDEOS:
        if not ids or v["id"] in ids:
            render(v, preview=preview)
