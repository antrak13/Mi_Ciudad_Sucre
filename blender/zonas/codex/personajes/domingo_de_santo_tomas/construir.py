"""Exporta el GLB animado y el maestro Blender de fray Domingo de Santo Tomás."""
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
    ('01_reposo', 'reposo', 0, (.82, -3.11, 1.60), (0, 0, .84)),
    ('02_perfil', 'reposo', 0, (-3.20, -.08, 1.60), (0, 0, .84)),
    ('03_espalda', 'reposo', 0, (.87, 3.10, 1.60), (0, 0, .84)),
    ('04_lectura', 'leer_libro', 42, (.82, -3.11, 1.60), (0, 0, .84)),
    ('05_detalle_libro', 'leer_libro', 60, (-.90, -1.52, 1.65), (0, -.16, 1.23)),
    ('06_saludo', 'saludar', 20, (.82, -3.11, 1.60), (0, 0, .84)),
    ('07_marcha', 'caminar', 6, (.82, -3.11, 1.60), (0, 0, .84)),
    ('08_marcha_perfil', 'caminar', 24, (-3.20, -.08, 1.60), (0, 0, .84)),
    ('09_hablar', 'hablar', 26, (.82, -3.11, 1.60), (0, 0, .84)),
]


def principal():
    SALIDA.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0

    malla = importar_malla(REVISION / 'malla_1024.glb', 'fray Domingo de Santo Tomás', ORIGEN, ALTURA)
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
        shutil.copy2(REVISION / '04_lectura.png', SALIDA / 'vista_previa.png')

    rig.animation_data.action = acciones['reposo']
    bpy.context.scene.frame_set(0)
    bpy.context.scene.frame_end = round(CLIPS[0]['duracion'] * 24)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(SALIDA / f'{ID}.blend'), compress=True)

    ficha = {
        'id': ID,
        'nombre': 'Fray Domingo de Santo Tomás',
        'subtitulo': 'La Gramática quechua · La Plata, 1563–1570',
        'glb': f'{ID}.glb',
        'blend': f'{ID}.blend',
        'referencia': 'referencia.jpg',
        'altura_m': ALTURA,
        'esqueleto': {'nombre': 'GeneralSkeleton', 'ual': 53, 'extras': [n for n, _ in EXTRAS]},
        'clip_inicial': 'reposo',
        'clips': CLIPS,
        'integracion': {'guia': '§5, personaje 25', 'frente': '+Z', 'vertical': '+Y',
                        'gesto_espera': 'leer_libro', 'gesto_llegada': 'saludar'},
    }
    (SALIDA / 'ficha.json').write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + '\n')
    print(f'{ID}: {len(malla.data.polygons)} triángulos, {len(rig.data.bones)} huesos, {len(acciones)} clips')


if __name__ == '__main__':
    principal()
