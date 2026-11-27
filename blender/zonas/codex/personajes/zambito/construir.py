"""Rig y exportación de los movimientos del acompañante del Quitacapas."""
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
from accesorios import separar_vaina
from movimientos import construir_pose
from rig import ALTURA, EXTRAS, ORIGEN, asignar_pesos, segmentos

ID = BASE.name
REVISION = RAIZ / 'revisiones/codex' / ID
SALIDA = RAIZ / 'web/public/models/ciudad/codex/personajes' / ID
CLIPS = json.loads((BASE / 'clips.json').read_text())
TOMAS = [
    ('01_reposo', 'reposo', 0, (-1.28, -2.75, 1.6), (0, 0, .81)),
    ('02_perfil', 'reposo', 0, (-3.00, -.22, 1.6), (0, 0, .81)),
    ('03_espalda', 'reposo', 0, (1.05, 2.85, 1.6), (0, 0, .81)),
    ('04_paso', 'caminar', 5, (-1.28, -2.75, 1.6), (0, 0, .81)),
    ('05_paso_perfil', 'caminar', 15, (-2.95, -.65, 1.6), (0, 0, .80)),
    ('06_paso_rapido', 'caminar_rapido', 5, (1.28, -2.75, 1.6), (0, 0, .80)),
    ('07_cargar_bulto', 'cargar_bulto', 23, (1.10, -2.85, 1.6), (0, 0, .81)),
    ('08_mirar_atras', 'mirar_atras', 22, (-1.10, -2.85, 1.6), (0, 0, .81)),
    ('09_desde_10m', 'caminar', 15, (-2.3, -9.7, 1.6), (0, 0, .81)),
]


def principal():
    SALIDA.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0

    malla = importar_malla(REVISION / 'malla_1024.glb', 'Zambito', ORIGEN, ALTURA)
    s = segmentos()
    rig = crear_armadura_ual('GeneralSkeleton', s, EXTRAS)
    asignar_pesos(malla, rig, s, separar_vaina(malla))
    rig['personaje'] = ID
    rig['frente_blender'] = '-Y'
    ual = BibliotecaUAL()
    acciones = {a.name: a for a in hornear_clips(rig, CLIPS, construir_pose(ual, s, malla), fps=24)}
    ual.limpiar_escena()

    exportar_glb(SALIDA / f'{ID}.glb', rig, malla)
    if '--sin-render' not in sys.argv:
        renderizar_vistas(rig, acciones, REVISION, TOMAS)
        shutil.copy2(REVISION / '04_paso.png', SALIDA / 'vista_previa.png')

    rig.animation_data.action = acciones['reposo']
    bpy.context.scene.frame_set(0)
    bpy.context.scene.frame_end = round(CLIPS[0]['duracion'] * 24)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(SALIDA / f'{ID}.blend'), compress=True)

    ficha = {
        'id': ID,
        'nombre': 'El zambito',
        'subtitulo': 'Acompañante del Quitacapas · La Plata, 1809',
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
            'acompanante_de': 'quitacapas',
            'retraso_s': 1.5,
            'distancia_pasos': 2,
            'ficha_propia': False,
            'fuentes': ['Q-0455-1'],
        },
    }
    (SALIDA / 'ficha.json').write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + '\n')
    print('Zambito:', len(malla.data.polygons), 'triángulos,', len(rig.data.bones), 'huesos,', len(acciones), 'clips')


if __name__ == '__main__':
    principal()
