"""Rig y movimientos sobre el GLB estático de Alonso Ramírez de Vergara."""
import json
import shutil
import sys
from pathlib import Path

import bpy

BASE = Path(__file__).resolve().parent
RAIZ = BASE.parents[4]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE.parent))
sys.path.insert(0, str(RAIZ / 'blender/zonas/antigravity/personajes'))

from kit_ual import BibliotecaUAL, crear_armadura_ual, hornear_clips
from exportacion_ual import exportar_glb, importar_malla, renderizar_vistas
from movimientos import construir_pose
from rig import ALTURA, ORIGEN, asignar_pesos, segmentos

ID = 'alonso_ramirez_de_vergara'
REVISION = RAIZ / 'revisiones/codex' / ID
SALIDA = RAIZ / 'web/public/models/ciudad/codex/personajes' / ID
CLIPS = json.loads((BASE / 'clips.json').read_text())


TOMAS = [
    ('01_reposo', 'reposo', 0, (-1.50, -3.30, 1.6), (.0, 0, .97)),
    ('02_perfil', 'reposo', 0, (-3.65, -.20, 1.6), (.0, 0, .97)),
    ('03_espalda', 'reposo', 0, (1.32, 3.45, 1.6), (.0, 0, .97)),
    ('04_paso', 'caminar', 8, (-1.50, -3.30, 1.6), (.0, 0, .97)),
    ('05_paso_perfil', 'caminar', 23, (-3.65, -.20, 1.6), (.0, 0, .97)),
    ('06_incensar', 'incensar', 32, (-2.70, -2.45, 1.6), (-.05, -.05, .97)),
    ('07_detalle_incensario', 'incensar', 54, (-1.32, -1.54, 1.40), (-.30, -.24, 1.18)),
    ('08_hablar', 'hablar', 28, (1.02, -3.48, 1.6), (.0, 0, .97)),
    ('09_desde_10m', 'incensar', 32, (-3.0, -9.54, 1.6), (0, 0, .97)),
]


def principal():
    SALIDA.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0

    malla = importar_malla(REVISION / 'malla_1024.glb', 'Vergara', ORIGEN, ALTURA)
    s = segmentos()
    rig = crear_armadura_ual('GeneralSkeleton', s, [('incensario', 'DEF-hand.R')])
    asignar_pesos(malla, rig, s)
    rig['personaje'] = ID
    rig['frente_blender'] = '-Y'
    ual = BibliotecaUAL()
    acciones = {a.name: a for a in hornear_clips(rig, CLIPS, construir_pose(ual, s), fps=24)}
    ual.limpiar_escena()

    exportar_glb(SALIDA / f'{ID}.glb', rig, malla)

    if '--sin-render' not in sys.argv:
        renderizar_vistas(rig, acciones, REVISION, TOMAS)
        shutil.copy2(REVISION / '06_incensar.png', SALIDA / 'vista_previa.png')

    rig.animation_data.action = acciones['reposo']
    bpy.context.scene.frame_set(0)
    bpy.context.scene.frame_end = round(CLIPS[0]['duracion'] * 24)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(SALIDA / f'{ID}.blend'), compress=True)
    ficha = {
        'id': ID,
        'nombre': 'Alonso Ramírez de Vergara',
        'subtitulo': 'Obispo de Charcas · Procesión de Guadalupe, 1602',
        'glb': f'{ID}.glb',
        'blend': f'{ID}.blend',
        'referencia': 'referencia.jpg',
        'altura_m': ALTURA,
        'esqueleto': {'nombre': 'GeneralSkeleton', 'ual': 53, 'extras': ['incensario']},
        'clip_inicial': 'reposo',
        'clips': CLIPS,
        'integracion': {
            'guia': '§7.4 Procesión de Guadalupe',
            'frente': '+Z',
            'vertical': '+Y',
            'clips_propios': [c['id'] for c in CLIPS if c.get('propio')],
            'destinos': ['Catedral de La Plata', 'Plaza 25 de Mayo'],
            'fuentes': ['Q-0127-1', 'Q-0128-1', 'G p. 108-109', 'Ocaña, fols. 232v–234v'],
        },
    }
    (SALIDA / 'ficha.json').write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + '\n')
    print('Vergara:', len(malla.data.polygons), 'triángulos,', len(rig.data.bones), 'huesos,', len(acciones), 'clips')


if __name__ == '__main__':
    principal()
