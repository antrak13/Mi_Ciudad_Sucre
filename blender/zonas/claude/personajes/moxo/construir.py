"""Rig y animaciones de Benito María de Moxó (Guía #24): dos modelos, de día y de noche.

Parte de los modelos estáticos de Tripo (`personas/moxo/moxo_dia.glb` y `moxo_noche.glb`): no se modela nada de cero.
Esqueleto: los 53 huesos de la Universal Animation Library. Cada variante (`variante_dia.py`, `variante_noche.py`)
trae su anatomía, sus clips y sus poses; este archivo es el proceso común.

Uso (un solo Blender pesado a la vez; ~1,2 GB de memoria):
    ~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/moxo/construir.py -- dia|noche
    ... -- dia --prueba [clip…]   solo renders de control (sin hornear ni exportar)
    ... -- dia --pesos            renders del hueso dominante de cada vértice (en reposo)
"""
import importlib
import sys
from pathlib import Path

import bpy
from mathutils import Vector

BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE), str(BASE.parent)]

import kit_personaje as kp  # noqa: E402
from kit_personaje import RAIZ  # noqa: E402
from kit_ual import BibliotecaUAL, crear_armadura_ual, hornear_clips  # noqa: E402

COLORES_HUESO = {
    'DEF-hips': (0.9, 0.9, 0.9), 'DEF-spine.001': (0.7, 0.7, 0.4), 'DEF-spine.002': (0.5, 0.5, 0.9),
    'DEF-spine.003': (0.3, 0.9, 0.9), 'DEF-neck': (0.9, 0.5, 0.0), 'DEF-head': (1.0, 1.0, 0.0),
    'DEF-upper_arm.L': (0.0, 0.5, 0.0), 'DEF-forearm.L': (0.0, 0.8, 0.0), 'DEF-hand.L': (0.5, 1.0, 0.5),
    'DEF-upper_arm.R': (0.5, 0.0, 0.0), 'DEF-forearm.R': (0.8, 0.0, 0.0), 'DEF-hand.R': (1.0, 0.5, 0.5),
    'DEF-shoulder.L': (0.0, 0.3, 0.3), 'DEF-shoulder.R': (0.3, 0.0, 0.3),
    'DEF-thigh.L': (0.0, 0.3, 1.0), 'DEF-thigh.R': (0.6, 0.0, 1.0),
    'DEF-shin.L': (0.0, 0.0, 0.6), 'DEF-shin.R': (0.4, 0.0, 0.6),
    'DEF-foot.L': (1.0, 0.0, 0.5), 'DEF-foot.R': (1.0, 0.0, 0.5),
}


def renders_pesos(malla, nombres, W, carpeta, altura):
    """Pinta cada vértice con el color de su hueso dominante y lo fotografía de frente, de lado y de espaldas."""
    dominante = W.argmax(axis=1)
    attr = malla.data.color_attributes.new('dominante', 'FLOAT_COLOR', 'POINT')
    for i, j in enumerate(dominante):
        attr.data[i].color = (*COLORES_HUESO.get(nombres[j], (0.3, 0.3, 0.3)), 1.0)
    cam = kp.preparar_render(500, 700)
    bpy.context.scene.display.shading.color_type = 'VERTEX'
    mira = Vector((0.0, 0.0, 0.5 * altura))
    for nombre, pos in [('pesos_frente', (0.4, -3.2, 0.9)), ('pesos_lado', (3.2, -0.6, 0.9)),
                        ('pesos_espalda', (-0.5, 3.2, 0.9))]:
        kp.tomar(cam, Path(carpeta) / f'{nombre}.png', Vector(pos) * (altura / 1.6), mira)
    kp.lamina_control(carpeta, ['pesos_frente', 'pesos_lado', 'pesos_espalda'], por_fila=3)


def main():
    args = kp.argumentos()
    v = importlib.import_module(f'variante_{args[0]}')
    H = v.ALTURA_M
    rev = RAIZ / f'revisiones/claude/{v.ID}'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    malla, co_norm = kp.importar_malla(kp.simplificar(v.ENTRADA, kp.SCRATCH / f'{v.ID}_30k.glb'), H, f'{v.ID}_malla')
    seg = {n: (Vector(a) * H, Vector(b) * H) for n, (a, b) in v.anatomia.segmentos().items()}
    rig = crear_armadura_ual('GeneralSkeleton', seg, huesos_extra=v.anatomia.HUESOS_EXTRA)
    tris = kp.triangulos(malla)
    nombres, W = v.anatomia.calcular_pesos(co_norm, tris, kp.color_base_por_vertice(malla))
    if '--pesos' in args:
        renders_pesos(malla, nombres, W, rev, H)
        return
    extra = [v.anatomia.caras_extra(co_norm, tris, nombres, W)] if hasattr(v.anatomia, 'caras_extra') else []
    kp.cortar_falda_y_pies(malla, co_norm, tris, nombres, W, H, otras=extra)
    for pieza, perm in getattr(v.anatomia, 'PIEZAS_SUELTAS', []):
        W = kp.desdoblar_costuras(malla, nombres, W, pieza, permitidos=perm)
    kp.asignar_grupos(malla, nombres, W)
    malla.parent = rig
    malla.modifiers.new(name='Armature', type='ARMATURE').object = rig

    ual = BibliotecaUAL()
    pose = v.construir_pose(ual)
    if '--prueba' in args:
        solo = [a for a in args[1:] if not a.startswith('--')]
        kp.renderizar_control(rig, pose, v.CLIPS, [t for t in v.TOMAS if not solo or t[1] in solo], v.CAMARAS, rev)
        return
    hornear_clips(rig, v.CLIPS, pose, fps=24)
    if '--sin-render' not in args:
        kp.renderizar_control(rig, pose, v.CLIPS, v.TOMAS, v.CAMARAS, rev)
    ual.limpiar_escena()
    kp.exportar(rig, RAIZ / f'web/public/models/ciudad/claude/personajes/{v.ID}', v.ID, v.FICHA,
                accion_blend=v.FICHA['clip_inicial'], lamina=v.LAMINA, vista_previa=rev / v.VISTA_PREVIA,
                doble_cara=True)


if __name__ == '__main__':
    main()
