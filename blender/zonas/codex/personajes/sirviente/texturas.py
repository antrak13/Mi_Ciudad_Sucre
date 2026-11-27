"""Atlas original dibujado por código: pigmento retro, tejido y desgaste; sin recursos ajenos."""
import json
import random
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
RAIZ = BASE.parents[4]
SALIDA = RAIZ / 'web/public/models/ciudad/codex/personajes/sirviente'
if '--salida' in sys.argv:
    SALIDA=Path(sys.argv[sys.argv.index('--salida')+1]).resolve()
ROLES = ['chaqueta', 'calzon', 'sombrero', 'piel', 'camisa', 'forro', 'pelo', 'zapato',
         'suela', 'boton', 'papel', 'costura', 'ojo', 'iris', 'boca', 'cinto']


def generar():
    datos = json.loads((BASE / 'diseno.json').read_text())
    rng = random.Random(1809)
    atlas = Image.new('RGB', (1024, 1024))
    for indice, rol in enumerate(ROLES):
        color = datos['paleta'][rol].lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        imagen = Image.new('RGB', (256, 256), rgb)
        dib = ImageDraw.Draw(imagen)
        campo=Image.new('L',(12,12))
        campo.putdata([rng.randint(102,152) for _ in range(144)])
        campo=campo.resize((256,256),Image.Resampling.BILINEAR)
        paso = 6 if rol in ('chaqueta', 'calzon', 'sombrero', 'zapato') else 4
        amplitud = 12 if rol in ('chaqueta', 'sombrero') else 5
        if rol in ('piel','ojo','boca','costura','iris','pelo'): amplitud=0
        for y in range(0, 256, paso):
            for x in range(0, 256, paso):
                tono = rng.uniform(-amplitud, amplitud)
                if rol in ('chaqueta','sombrero','calzon','zapato'):
                    tono=(campo.getpixel((x,y))-128)*.75+rng.uniform(-4,4)
                if rol not in ('piel','ojo','boca','costura','iris','pelo'):
                    tono += (2 if (x // paso + y // paso) % 3 else -3)
                c = tuple(max(0, min(255, round(v + tono))) for v in rgb)
                if rol in ('chaqueta','sombrero','calzon','zapato'):
                    variacion=campo.getpixel((x,y))
                    tinte=(-6,0,6) if variacion<120 else (5,2,-4) if variacion>137 else (0,0,0)
                    c=tuple(max(0,min(255,v+t)) for v,t in zip(c,tinte))
                dib.rectangle((x, y, x+paso-1, y+paso-1), fill=c)
                if rol in ('chaqueta', 'calzon', 'camisa', 'forro'):
                    c2 = tuple(max(0, min(255, v+3)) for v in c)
                    dib.line((x, y+paso-2, x+paso-1, y+paso-2), fill=c2)
        atlas.paste(imagen, ((indice % 4)*256, (indice // 4)*256))
    SALIDA.mkdir(parents=True, exist_ok=True)
    atlas.save(SALIDA / 'sirviente_color.png')
    # La carta se imprime aparte: la geometría permite retirarla del forro.
    carta = Image.new('RGB', (256, 384), '#e0cfaa')
    dib = ImageDraw.Draw(carta)
    for y in range(384):
        for x in range(256):
            d = rng.randint(-4, 4)
            carta.putpixel((x, y), (224+d, 207+d, 170+d))
    try:
        fuente = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf', 35)
    except OSError:
        fuente = ImageFont.load_default()
    # Texto histórico conocido: solo la firma. Los renglones no inventan una carta documental.
    for y in (65, 91, 117, 143, 169, 208):
        for x in range(24, rng.randrange(155, 220), 5):
            dib.line((x, y+rng.randrange(3), x+4, y+rng.randrange(3)), fill='#948060', width=1)
    dib.text((112, 278), 'Parra', font=fuente, fill='#63482d')
    dib.line((32, 191, 224, 191), fill='#baa682')
    carta=carta.resize((256,512),Image.Resampling.NEAREST)
    carta.save(SALIDA / 'carta_parra.png')
    print('Atlas y carta originales:', SALIDA)


if __name__ == '__main__':
    generar()
