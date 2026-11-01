# Ersetzt die Capacitor-Standard-Icons und den Splash durch Bullseye-Boss-Grafiken.
import os, sys
from PIL import Image
res = 'android/app/src/main/res'
src = Image.open('icon-512.png').convert('RGBA')
mask = Image.open('icon-maskable.png').convert('RGBA')
bg = mask.getpixel((4, 4))[:3]
sizes = {'mdpi': (48, 108), 'hdpi': (72, 162), 'xhdpi': (96, 216), 'xxhdpi': (144, 324), 'xxxhdpi': (192, 432)}
for d, (ic, fg) in sizes.items():
    p = f'{res}/mipmap-{d}'
    os.makedirs(p, exist_ok=True)
    full = src.resize((ic, ic), Image.LANCZOS)
    for n in ('ic_launcher.png', 'ic_launcher_round.png'):
        full.save(f'{p}/{n}')
    canvas = Image.new('RGBA', (fg, fg), (0, 0, 0, 0))
    inner = int(fg * 0.62)
    canvas.paste(src.resize((inner, inner), Image.LANCZOS), ((fg - inner) // 2, (fg - inner) // 2))
    canvas.save(f'{p}/ic_launcher_foreground.png')
os.makedirs(f'{res}/values', exist_ok=True)
open(f'{res}/values/ic_launcher_background.xml', 'w').write(
    '<?xml version="1.0" encoding="utf-8"?><resources><color name="ic_launcher_background">#%02x%02x%02x</color></resources>' % bg)
# Splash: einfarbig dunkel
solid = Image.new('RGB', (16, 16), (14, 20, 16))
for root, _, files in os.walk(res):
    for f in files:
        if f == 'splash.png':
            solid.save(os.path.join(root, f))
print('assets ok', bg)
