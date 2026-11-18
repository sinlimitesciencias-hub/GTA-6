"""Genera el banner (2560x1440) y la foto de perfil (800x800) del canal."""
import os

import numpy as np
from PIL import Image, ImageDraw

import engine as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "canal")
os.makedirs(OUT, exist_ok=True)
th = E.THEMES["sunset"]
bg = E.Background("sunset", seed=11)
frame = Image.fromarray(bg.frame(0)).convert("RGBA")

# Banner: el área segura (visible en todos los dispositivos) es 1546x423 en el centro.
banner = frame.resize((2560, 1440), Image.LANCZOS)
name = E.text_image(E.CHANNEL, "display", 230, glow=th["acc2"], glow_r=30, grad=[(255, 255, 255), th["warm"]])
banner.alpha_composite(name, (int(1280 - name.width / 2), int(650 - name.height / 2)))
tag = E.text_image("GUÍAS · NOTICIAS · SECRETOS DE GTA 6 EN ESPAÑOL", "alt", 70, fill=th["acc"], glow=th["acc"], glow_r=10)
banner.alpha_composite(tag, (int(1280 - tag.width / 2), int(820 - tag.height / 2)))
banner.convert("RGB").save(os.path.join(OUT, "banner_2560x1440.jpg"), quality=92)

# Avatar
av = frame.crop((E.W // 2 - 540, 0, E.W // 2 + 540, 1080)).resize((800, 800), Image.LANCZOS)
dark = Image.new("RGBA", av.size, (8, 2, 20, 120))
av.alpha_composite(dark)
n = E.text_image("N6", "display", 420, glow=th["acc2"], glow_r=30, grad=[(255, 255, 255), th["warm"]], spacing=0.9)
av.alpha_composite(n, (int(400 - n.width / 2), int(400 - n.height / 2)))
mask = Image.new("L", av.size, 0)
ImageDraw.Draw(mask).ellipse([0, 0, 799, 799], fill=255)
av.convert("RGB").save(os.path.join(OUT, "avatar_800.png"))
print("ok")
