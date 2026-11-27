"""Control de un personaje exportado: reimporta el GLB y, por clip, mide el cierre (bucles: primer y último cuadro
iguales; gestos: vuelven a la pose inicial) y el punto más bajo de la malla (nada bajo el suelo).

    ~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/verificar_glb.py -- <ruta.glb>
"""
import sys

import bpy
import numpy as np

ruta = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 24
bpy.ops.import_scene.gltf(filepath=ruta)
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
malla = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.polygons))
print('HUESOS', len(rig.data.bones), 'TRIANGULOS', sum(len(p.vertices) - 2 for p in malla.data.polygons))


def puntos(f):
    bpy.context.scene.frame_set(int(round(f)))
    ev = malla.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    ev.to_mesh_clear()
    return co.reshape(-1, 3)


for a in sorted(bpy.data.actions, key=lambda a: a.name):
    f0, f1 = a.frame_range
    rig.animation_data.action = a
    cuadros = np.linspace(f0, f1, 9)
    z_min = min(puntos(f)[:, 2].min() for f in cuadros)
    cierre = np.abs(puntos(f0) - puntos(f1)).max()
    print(f'CLIP {a.name:20s} {(f1 - f0) / 24:5.2f} s  cierre={cierre:.4f} m  z_min={z_min:+.3f} m')
