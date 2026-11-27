"""Exporta a Francisco Ríos con rig UAL, sus clips y vistas de revisión."""
import json
import shutil
import sys
from pathlib import Path

import bpy

BASE = Path(__file__).resolve().parent
RAIZ = BASE.parents[4]
sys.path[:0] = [str(BASE), str(BASE.parent),
                str(RAIZ / 'blender/zonas/antigravity/personajes'),
                str(RAIZ / 'blender/zonas/claude/personajes')]

from exportacion_ual import exportar_glb, importar_malla, renderizar_vistas
from kit_ual import BibliotecaUAL, crear_armadura_ual, hornear_clips
from movimientos import construir_pose
from rig import ALTURA, EXTRAS, ORIGEN, asignar_pesos, segmentos

ID = BASE.name
REVISION = RAIZ / 'revisiones/codex' / ID
SALIDA = RAIZ / 'web/public/models/ciudad/codex/personajes' / ID
CLIPS = json.loads((BASE / 'clips.json').read_text())
TOMAS = [
    ('01_reposo', 'reposo', 0, (.75, -3.06, 1.6), (0, 0, .87)),
    ('02_perfil', 'reposo', 0, (-3.16, -.10, 1.6), (0, 0, .87)),
    ('03_espalda', 'reposo', 0, (.75, 3.06, 1.6), (0, 0, .87)),
    ('04_marcha', 'fanfarron_caminar', 6, (.75, -3.06, 1.6), (0, 0, .87)),
    ('05_marcha_perfil', 'fanfarron_caminar', 19, (-3.16, -.10, 1.6), (0, 0, .87)),
    ('06_llave', 'mostrar_llave', 25, (-.78, -3.08, 1.6), (-.10, 0, .87)),
    ('07_monedas', 'lanzar_monedas', 17, (-1.60, -2.91, 1.6), (-.15, -.15, .87)),
    ('08_risa', 'reir', 20, (.75, -3.06, 1.6), (0, 0, .87)),
]


def principal():
    SALIDA.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0

    malla = importar_malla(REVISION / 'malla_1024.glb', 'Francisco Ríos', ORIGEN, ALTURA)
    s = segmentos()
    rig = crear_armadura_ual('GeneralSkeleton', s, EXTRAS)
    asignar_pesos(malla, rig, s)
    rig['personaje'] = ID
    rig['frente_blender'] = '-Y'

    ual = BibliotecaUAL()
    acciones = {a.name: a for a in hornear_clips(rig, CLIPS, construir_pose(ual, s, malla), fps=24)}
    ual.limpiar_escena()

    exportar_glb(SALIDA / f'{ID}.glb', rig, malla)
    if '--sin-render' not in sys.argv:
        renderizar_vistas(rig, acciones, REVISION, TOMAS)
        shutil.copy2(REVISION / '06_llave.png', SALIDA / 'vista_previa.png')

    rig.animation_data.action = acciones['reposo']
    bpy.context.scene.frame_set(0)
    bpy.context.scene.frame_end = round(CLIPS[0]['duracion'] * 24)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(SALIDA / f'{ID}.blend'), compress=True)

    ficha = {
        'id': ID,
        'nombre': 'Francisco Ríos, el Quitacapas',
        'subtitulo': 'La Plata, 1809',
        'glb': f'{ID}.glb',
        'blend': f'{ID}.blend',
        'referencia': 'referencia.jpg',
        'altura_m': ALTURA,
        'esqueleto': {'nombre': 'GeneralSkeleton', 'ual': 53, 'extras': [n for n, _ in EXTRAS]},
        'clip_inicial': 'reposo',
        'clips': CLIPS,
        'integracion': {
            'guia': '§3, personaje 2',
            'frente': '+Z',
            'vertical': '+Y',
            'acompanante': 'zambito',
            'evento_monedas': {'clip': 'lanzar_monedas', 'fotograma': 17, 'fps': 24, 'hueso': 'DEF-hand.R'},
        },
    }
    (SALIDA / 'ficha.json').write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + '\n')
    print('Quitacapas:', len(malla.data.polygons), 'triángulos,', len(rig.data.bones), 'huesos,', len(acciones), 'clips')


if __name__ == '__main__':
    principal()
