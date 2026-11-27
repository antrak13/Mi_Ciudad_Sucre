"""Informe visual: únicamente recorte y escala uniforme, sin retocar el render ni el diseño."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BASE=Path(__file__).resolve().parent
RAIZ=BASE.parents[4]
SALIDA=RAIZ/'web/public/models/ciudad/codex/personajes/sirviente'

def main():
    datos=json.loads((BASE/'diseno.json').read_text())
    original=RAIZ/datos['referencia']
    if not original.exists():original=SALIDA/'referencia.png'
    referencia=Image.open(original).convert('RGB').crop((250,0,690,1024))
    render=Image.open(SALIDA/'vista_previa.png').convert('RGB')
    w,h=render.size
    render=render.crop((int(w*.22),0,int(w*.80),h))
    lienzo=Image.new('RGB',(1160,1130),'#f2ede6')
    dib=ImageDraw.Draw(lienzo)
    fuente=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
    for i,(im,titulo) in enumerate([(referencia,'REFERENCIA NUEVA'),(render,'MODELO · RENDER DE BLENDER')]):
        escala=min(1000/im.height,550/im.width)
        im=im.resize((round(im.width*escala),round(im.height*escala)),Image.Resampling.LANCZOS)
        lienzo.paste(im,(i*580+(580-im.width)//2,65+(1000-im.height)//2))
        dib.text((i*580+30,24),titulo,font=fuente,fill='#493b30')
    dib.text((30,1090),'Referencia y render real del modelo. Recorte y escala uniforme.',font=fuente,fill='#65564a')
    lienzo.save(SALIDA/'comparacion.png')
    print('Comparación:',SALIDA/'comparacion.png')

if __name__=='__main__':main()
