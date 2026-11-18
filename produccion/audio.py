"""Voz (Kokoro TTS offline), música synthwave original, efectos, mezcla y subtítulos."""
import math
import os
import re

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, lfilter

SR = 48000
VOICE = os.environ.get("VOZ", "em_alex")
LANG = os.environ.get("VOZ_IDIOMA", "es-419")
SPEED = float(os.environ.get("VOZ_VELOCIDAD", "1.07"))
MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.join(os.path.dirname(__file__), "modelos"))

# Pronunciación: el texto en pantalla/subtítulos queda igual; sólo cambia lo que "lee" la voz.
PHON = [
    (r"Red Dead Redemption 2", "Red Ded Redémshon dos"), (r"Red Dead Online", "Red Ded Onlain"),
    (r"RDR 2", "Red Ded dos"), (r"GTA 6 Online", "ge te a seis Onlain"), (r"GTA Online", "ge te a Onlain"),
    (r"GTA Plus", "ge te a plas"), (r"GTA\+", "ge te a plas"),
    (r"GTA 6", "ge te a seis"), (r"GTA VI", "ge te a seis"), (r"GTA V\b", "ge te a cinco"),
    (r"GTA IV", "ge te a cuatro"), (r"\bGTA\b", "ge te a"),
    (r"Vice City", "Vais Siti"), (r"Leonida Keys", "Leonida Kis"), (r"Port Gellhorn", "Port Guélhorn"),
    (r"Grassrivers", "Grass Rívers"), (r"Mount Kalaga", "Maunt Kalaga"), (r"Jason", "Yéison"),
    (r"Duval", "Duval"), (r"Ultimate", "Áltimet"), (r"PS5 Pro", "pe ese cinco Pro"), (r"PS5", "pe ese cinco"),
    (r"PlayStation Plus", "Pleistéishon Plas"), (r"PlayStation Store", "Pleistéishon Stor"),
    (r"PlayStation", "Pleistéishon"), (r"Microsoft Store", "Maicrosoft Stor"), (r"Xbox", "Equisbox"),
    (r"Series X", "Series Equis"), (r"Series S", "Series Ese"), (r"Cloud Gaming", "Claud Gueiming"),
    (r"\bonline\b", "onlain"), (r"\bOnline\b", "Onlain"), (r"Rockstar", "Rocstar"), (r"\bPC\b", "pe ce"),
    (r"PSSR", "pe ese ese erre"), (r"\bHDR\b", "hache de erre"), (r"\bSSD\b", "ese ese de"),
    (r"NVMe", "ene ve eme e"), (r"\bFPS\b", "efe pe ese"), (r"\bUSB\b", "u ese be"),
    (r"Shark Cards", "Shark Cards"), (r"Bonnie y Clyde", "Boni y Claid"), (r"Cal Hampton", "Cal Hámpton"),
    (r"Boobie Ike", "Bubi Aik"), (r"Dre'Quan Priest", "Dricuan Prist"), (r"Real Dimez", "Rial Daims"),
    (r"Brian Heder", "Bráian Jéder"), (r"Everglades", "Évergleids"), (r"Vintage", "Víntach"),
    (r"\bgigas\b", "guigas"), (r"Twitter", "Tuíter"), (r"YouTube", "Yutub"), (r"Take-Two", "Teik Tu"),
    (r"\bstart\b", "estart"), (r"tráiler", "tréiler"), (r"tráilers", "tréilers"),
]


def phonetize(text):
    for pat, rep in PHON:
        text = re.sub(pat, rep, text)
    return text


_kokoro = None


def tts(text):
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
    a, sr = _kokoro.create(phonetize(text), voice=VOICE, speed=SPEED, lang=LANG)
    a = np.asarray(a, np.float32)
    # recorta silencios de los bordes
    thr = 0.01
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx):
        a = a[max(0, idx[0] - int(0.03 * sr)):idx[-1] + int(0.08 * sr)]
    a = resample_poly(a, SR, sr).astype(np.float32)
    return a


def build_voice(video, cache_dir):
    """Devuelve (voz 48k mono, timeline). timeline = [{start, dur, segs:[(t,text,len)]}] por escena."""
    os.makedirs(cache_dir, exist_ok=True)
    gap, tail, lead = 0.28, 0.6, 0.45
    pieces, timeline = [np.zeros(int(lead * SR), np.float32)], []
    t = lead
    for si, sc in enumerate(video["scenes"]):
        seg_list = sc["narr"] if isinstance(sc["narr"], list) else [sc["narr"]]
        scene_start = t - (lead if si == 0 else 0)
        segs = []
        for gi, txt in enumerate(seg_list):
            fn = os.path.join(cache_dir, f"s{si:02d}_{gi:02d}.wav")
            key = fn + ".txt"
            if os.path.exists(fn) and os.path.exists(key) and open(key, encoding="utf-8").read() == txt + VOICE + str(SPEED):
                a, _ = sf.read(fn, dtype="float32")
            else:
                a = tts(txt)
                sf.write(fn, a, SR)
                open(key, "w", encoding="utf-8").write(txt + VOICE + str(SPEED))
            segs.append((t, txt, len(a) / SR))
            pieces.append(a)
            t += len(a) / SR
            pieces.append(np.zeros(int(gap * SR), np.float32))
            t += gap
        extra = sc.get("pad", tail)
        pieces.append(np.zeros(int(extra * SR), np.float32))
        t += extra
        timeline.append(dict(start=scene_start, end=t, segs=segs))
    voice = np.concatenate(pieces)
    # normaliza voz a RMS ~ -17 dBFS en zonas habladas
    active = np.abs(voice) > 0.02
    rms = np.sqrt(np.mean(voice[active] ** 2)) if active.any() else 0.1
    voice *= (10 ** (-17 / 20)) / max(rms, 1e-4)
    return voice, timeline


# --------------------------------------------------------------------------- música original
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def midi(n, octave):
    return 12 * (octave + 1) + NOTE[n]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


PROGRESSIONS = {
    "a": (["A", "F", "C", "G"], [True, False, False, False], 100),   # Am F C G
    "b": (["D", "A#", "F", "C"], [True, False, False, False], 96),   # Dm Bb F C
    "c": (["E", "C", "G", "D"], [True, False, False, False], 104),   # Em C G D
    "d": (["F#", "D", "A", "E"], [True, False, False, False], 92),   # F#m D A E
}


def _saw(f, t):
    return 2 * ((t * f) % 1.0) - 1


def _onepole(x, cutoff):
    a = math.exp(-2 * math.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)


def make_music(seconds, style="a", seed=1):
    roots, minor, bpm = PROGRESSIONS[style]
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = 4 * beat
    loop_bars = 8
    n = int(bar * loop_bars * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for b in range(loop_bars):
        root = roots[b % 4]
        is_minor = minor[b % 4]
        rm = midi(root, 3)
        chord = [rm, rm + (3 if is_minor else 4), rm + 7, rm + 12]
        s0, s1 = int(b * bar * SR), int((b + 1) * bar * SR)
        tt = t[s0:s1] - t[s0]
        env = np.minimum(1, tt / 0.4) * np.minimum(1, (bar - tt) / 0.3)
        pad = sum(_saw(hz(m) * d, tt) for m in chord for d in (0.997, 1.003)) / 8
        out[s0:s1] += (pad * env * 0.22).astype(np.float32)
        # bajo en corcheas
        for k in range(8):
            a0 = s0 + int(k * beat / 2 * SR)
            ln = int(beat / 2 * SR * 0.9)
            tb = np.arange(ln) / SR
            f = hz(midi(root, 1) + (12 if k % 4 == 3 else 0))
            v = np.sign(np.sin(2 * np.pi * f * tb)) * 0.5 + _saw(f, tb) * 0.5
            out[a0:a0 + ln] += (v * np.exp(-tb * 5) * 0.32).astype(np.float32)
        # arpegio en semicorcheas
        arp = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[3] + 12, chord[2] + 12, chord[1] + 12]
        for k in range(16):
            a0 = s0 + int(k * beat / 4 * SR)
            ln = int(beat / 4 * SR)
            ta = np.arange(ln) / SR
            f = hz(arp[k % len(arp)])
            tri = 2 * np.abs(2 * ((ta * f) % 1) - 1) - 1
            out[a0:a0 + ln] += (tri * np.exp(-ta * 14) * 0.13).astype(np.float32)
    out = _onepole(out, 2600).astype(np.float32)
    # batería
    drums = np.zeros(n, np.float32)
    kl = int(0.35 * SR)
    tk = np.arange(kl) / SR
    kick = np.sin(2 * np.pi * (45 * tk + 90 * (1 - np.exp(-tk * 30)) / 30)) * np.exp(-tk * 9)
    sl = int(0.25 * SR)
    ts = np.arange(sl) / SR
    snare = (rng.standard_normal(sl) * 0.6 + np.sin(2 * np.pi * 190 * ts) * 0.4) * np.exp(-ts * 18)
    snare = snare - _onepole(snare, 900)
    hl = int(0.06 * SR)
    hat = rng.standard_normal(hl) * np.exp(-np.arange(hl) / SR * 70)
    hat = hat - _onepole(hat, 7000)
    total_beats = loop_bars * 4
    for bt in range(total_beats):
        p = int(bt * beat * SR)
        drums[p:p + kl] += kick[: max(0, min(kl, n - p))] * 0.75
        if bt % 2 == 1:
            drums[p:p + sl] += snare[: max(0, min(sl, n - p))] * 0.42
        for h_ in (0, 0.5):
            q = int((bt + h_) * beat * SR)
            drums[q:q + hl] += hat[: max(0, min(hl, n - q))] * 0.16
    loop = out + drums
    loop /= np.max(np.abs(loop)) + 1e-6
    reps = int(math.ceil(seconds * SR / n)) + 1
    music = np.tile(loop, reps)[: int(seconds * SR)]
    fade = int(2.5 * SR)
    music[-fade:] *= np.linspace(1, 0, fade)
    music[: int(0.8 * SR)] *= np.linspace(0, 1, int(0.8 * SR))
    return music.astype(np.float32)


def whoosh(seed=0):
    rng = np.random.default_rng(seed)
    ln = int(0.55 * SR)
    t = np.arange(ln) / SR
    noise = rng.standard_normal(ln).astype(np.float32)
    env = np.sin(np.pi * np.clip(t / 0.55, 0, 1)) ** 2
    # filtro paso bajo con barrido
    y = np.zeros(ln, np.float32)
    s = 0.0
    for i in range(ln):
        fc = 300 + 5000 * (t[i] / 0.55)
        a = math.exp(-2 * math.pi * fc / SR)
        s = (1 - a) * noise[i] + a * s
        y[i] = s
    return (y * env / (np.max(np.abs(y)) + 1e-6)).astype(np.float32)


def impact():
    ln = int(1.2 * SR)
    t = np.arange(ln) / SR
    return (np.sin(2 * np.pi * (38 * t + 60 * (1 - np.exp(-t * 8)) / 8)) * np.exp(-t * 3.2)).astype(np.float32)


def mix(voice, timeline, total, music_style, seed):
    n = int(total * SR)
    v = np.zeros(n, np.float32)
    v[: min(n, len(voice))] = voice[:n]
    music = make_music(total, music_style, seed)
    # ducking según la voz
    env = np.abs(v)
    win = int(0.12 * SR)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    env = _onepole(env, 4.0)
    duck = 1 - 0.62 * np.clip(env / 0.03, 0, 1)
    music_gain = 0.20 * duck
    fx = np.zeros(n, np.float32)
    wh = whoosh(seed)
    for i, sc in enumerate(timeline):
        p = int(max(0, sc["start"] - 0.12) * SR)
        if i > 0:
            fx[p:p + len(wh)] += wh[: max(0, min(len(wh), n - p))] * 0.16
    imp = impact()
    fx[: len(imp)] += imp[:n] * 0.5
    out = v + music * music_gain + fx
    out = np.tanh(out * 1.1) / math.tanh(1.1)
    out *= 0.92 / (np.max(np.abs(out)) + 1e-6)
    return np.stack([out, out], axis=1)


# --------------------------------------------------------------------------- subtítulos
def _fmt(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_srt(timeline, max_chars=84):
    cues = []
    for sc in timeline:
        for (t0, text, d) in sc["segs"]:
            words = text.split()
            chunks, cur = [], ""
            for w in words:
                if len(cur) + len(w) + 1 > max_chars and cur:
                    chunks.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
                if cur.endswith((".", "?", "!", ":")) and len(cur) > 30:
                    chunks.append(cur)
                    cur = ""
            if cur:
                chunks.append(cur)
            total_chars = sum(len(c) for c in chunks)
            t = t0
            for c in chunks:
                cd = d * len(c) / total_chars
                cues.append((t, t + cd, c))
                t += cd
    lines = []
    for i, (a, b, c) in enumerate(cues, 1):
        if len(c) > 42:
            words = c.split()
            best, half = None, len(c) / 2
            acc = 0
            for j, w in enumerate(words[:-1]):
                acc += len(w) + 1
                if best is None or abs(acc - half) < abs(best[1] - half):
                    best = (j + 1, acc)
            c = " ".join(words[: best[0]]) + "\n" + " ".join(words[best[0]:])
        lines.append(f"{i}\n{_fmt(a)} --> {_fmt(b)}\n{c}\n")
    return "\n".join(lines)
