# Canal de GTA 6 — 10 videos listos para el lanzamiento

GTA 6 sale el **jueves 19 de noviembre de 2026** (PS5 y Xbox Series X|S). Aquí tienes 10 videos en español
terminados (guion, voz, gráficos, animación, música, montaje), más miniaturas, subtítulos, títulos,
descripciones con capítulos, etiquetas y el arte del canal.

## Qué hay en cada carpeta

```
videos/NN-tema/
  video.mp4          ← 1920x1080, 30 fps, H.264 + AAC. Listo para subir.
  miniatura.jpg      ← 1280x720
  subtitulos.srt     ← subtítulos en español (sincronizados con la voz)
  metadata.md        ← título, descripción con capítulos, etiquetas y ajustes de subida
  guion.md           ← guion completo con tiempos y lo que sale en pantalla
canal/               ← banner, foto de perfil y descripción del canal
investigacion/       ← qué busca la gente, por qué estos 10 temas, fuentes y qué tan seguro es cada dato
produccion/          ← código que genera todo (para editar un guion y volver a renderizar)
```

## Plan de subida (horario centro de México; en España suma 7 h)

| Hora | Video | Por qué a esa hora |
|---|---|---|
| **Miércoles 18, antes de las 20:00** | 01 · ¿A qué hora sale? | Esta búsqueda muere a medianoche. Si puedes, súbelo HOY. Si no, el jueves a las 00:00. |
| Jueves 00:00 | 02 · Cuánto pesa / hacer espacio | La gente descubre que no le cabe justo al desbloquearse |
| 08:00 | 03 · Estándar vs Ultimate | Quien compra el jueves por la mañana |
| 10:00 | 05 · PS5 vs PS5 Pro vs Xbox | |
| 12:00 | 08 · 10 cosas para tu primera hora | Quien empieza a jugar al mediodía |
| 14:00 | 09 · ¿Tiene online? | |
| 16:00 | 04 · ¿GTA 6 en PC? | |
| 18:00 | 06 · Jason y Lucía (sin spoilers) | |
| 20:00 | 07 · El mapa de Leonida | |
| 22:00 | 10 · La historia de GTA 6 en 2 min | |

Usa "Programar" en YouTube Studio: subes los 10 hoy y se publican solos.

### Al subir cada video
1. Título, descripción y etiquetas: copia de `metadata.md`.
2. Miniatura: `miniatura.jpg`.
3. Subtítulos: sube `subtitulos.srt` (idioma Español).
4. **Contenido alterado o sintético → Sí.** La voz es sintética (IA) y YouTube obliga a declararlo.
5. Pantalla final (últimos ~10 s): botón de suscribirse + el video siguiente (cada video ya lo anuncia en pantalla).

## Antes de publicar: revisa esto (2 minutos)
- **Escucha al menos un video entero.** La voz es sintética y no pude escucharla yo; revisa sobre todo cómo
  pronuncia nombres en inglés (Vice City, Jason, Ultimate…). Si alguno suena mal, ajústalo en
  `produccion/audio.py` (lista `PHON`) y vuelve a renderizar ese video.
- Precios en tu país (video 03): cambian por tienda.
- Si Rockstar publica algo nuevo hoy (parche, online, PC), los videos 04, 05 y 09 son los que podrían quedar viejos.

## Derechos y riesgos
- Todo el material visual y la música son **originales, generados por código**. No hay imágenes, logos,
  música ni clips de Rockstar, así que no deberían saltar reclamos de Content ID.
- Las fuentes tipográficas (Anton, Bebas Neue, Inter) son de licencia libre (SIL OFL).
- Cada descripción incluye el aviso de canal de fans no oficial.

## Próximos videos (semana 1, cuando ya puedas grabar gameplay)
Las búsquedas más grandes después del lanzamiento son las que hoy nadie puede responder:
trucos/claves, cómo ganar dinero rápido, todos los coches y dónde encontrarlos, coleccionables,
mejores armas, misiones totales/duración, final explicado (con aviso de spoilers). Graba tu
partida y usa este mismo formato: guion corto + gráficos del canal + tu gameplay de fondo.

## Volver a generar (si cambias un guion o el nombre del canal)
```bash
pip install kokoro-onnx soundfile scipy pillow numpy   # y ffmpeg instalado
# modelo de voz (≈350 MB) en produccion/modelos/:
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd produccion
python build.py --preview 03     # fotogramas de muestra, rápido
python build.py 03               # renderiza el video 03
CANAL_NOMBRE="OTRO NOMBRE" python build.py   # cambia el nombre en todos
python canal.py                  # banner y avatar
```
Los guiones están en `produccion/contenido.py`.
