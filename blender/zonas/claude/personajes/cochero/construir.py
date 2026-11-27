"""Cochero de las carrozas (personas/cochero): figura sentada en el pescante, fundida al kit de tráfico de cada carroza.

El GLB del usuario (`personas/cochero/chofer.glb`, 4,9 M triángulos, sin esqueleto) ya viene sentado con las manos
al frente, como en la lámina (`personas/cochero/diseno.png`): no se riggea. Se reduce a ~6 k triángulos, el color de
la textura pasa a cada cara (facetado, como el caballo ROME) y se exporta con el origen en el apoyo de las nalgas
(atrás y abajo del asiento), mirando a +X (frente de los vehículos). En `extras.pescante` va dónde se sienta en cada
carroza (marco del vehículo, metros): lo usa web/scripts/preparar_vehiculos.mjs.

Uso (un solo Blender pesado a la vez; ~1,5 GB de memoria la primera vez, al simplificar):
    ~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/cochero/construir.py
    ... -- --sin-render   exporta sin los renders de control
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE), str(BASE.parent)]

import kit_personaje as kp  # noqa: E402
from kit_personaje import RAIZ  # noqa: E402

ARGS = kp.argumentos()
ID = 'cochero'
ALTO_SENTADO = 1.30   # de la suela al ala del sombrero, sentado (de pie ~1,68 m)
ENTRADA = RAIZ / 'personas/cochero/chofer.glb'
MALLA_6K = kp.SCRATCH / 'cochero_6k.glb'
SALIDA = RAIZ / f'web/public/models/ciudad/claude/personajes/{ID}/cochero_sentado.glb'
REV = RAIZ / f'revisiones/claude/{ID}'
CARROZAS = RAIZ / 'web/public/models/ciudad/codex/vehiculos/carrozas'

# Apoyo de las nalgas en el pescante de cada carroza (marco del vehículo: x adelante, y arriba, z derecha; m).
# Medido en los renders de control (revisiones/claude/cochero/): asiento de cuero del pescante y reposapiés.
PESCANTE = {
    'carroza_azul': [0.80, 1.79, 0.0],
    'carruaje_madera': [0.68, 2.47, 0.0],
}


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def preparar_malla():
    kp.simplificar(ENTRADA, MALLA_6K, ratio=0.0013, textura_px=1024)
    malla, _ = kp.importar_malla(MALLA_6K, ALTO_SENTADO, ID)
    me = malla.data
    # color de la textura en el centro de cada cara (en UV): facetado, sin degradados entre caras
    uv = np.empty(len(me.loops) * 2, dtype=np.float32)
    me.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    inicio = np.empty(len(me.polygons), dtype=np.int64)
    cuenta = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get('loop_start', inicio)
    me.polygons.foreach_get('loop_total', cuenta)
    centro = np.array([uv[s:s + c].mean(axis=0) for s, c in zip(inicio, cuenta)])
    nodo = next(n for n in malla.active_material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    img = nodo.inputs['Base Color'].links[0].from_node.image
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    ix = np.clip((centro[:, 0] % 1.0 * w).astype(int), 0, w - 1)
    iy = np.clip((centro[:, 1] % 1.0 * h).astype(int), 0, h - 1)
    col_cara = px[iy, ix, :3]  # lineal (Blender guarda las imágenes sRGB ya convertidas en pixels? no: crudo)
    if img.colorspace_settings.name == 'sRGB':
        col_cara = np.where(col_cara <= 0.04045, col_cara / 12.92, ((col_cara + 0.055) / 1.055) ** 2.4)
    attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    col_esq = np.repeat(col_cara, cuenta, axis=0)
    rgba = np.concatenate([col_esq, np.ones((len(col_esq), 1))], axis=1).astype(np.float32)
    attr.data.foreach_set('color', rgba.ravel())
    # material sin textura, que lee el color de los vértices (el visor y Godot lo ignoran: usan COLOR_0)
    mat = bpy.data.materials.new('cochero')
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    ca = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    ca.layer_name = 'Col'
    mat.node_tree.links.new(ca.outputs['Color'], bsdf.inputs['Base Color'])
    me.materials.clear()
    me.materials.append(mat)
    for u in list(me.uv_layers):
        me.uv_layers.remove(u)
    orientar_y_apoyar(malla)
    return malla


def orientar_y_apoyar(malla):
    """Frente a +X (los vehículos): las rodillas y las botas son lo que más sobresale hacia adelante. Origen en el
    apoyo de las nalgas: atrás del todo y a la altura más baja de la mitad trasera (el asiento)."""
    me = malla.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    # el frente: el lado hacia donde está el centro de masa de la mitad baja (piernas) respecto de la de arriba
    bajo = co[co[:, 2] < ALTO_SENTADO * 0.45].mean(axis=0)
    alto = co[co[:, 2] > ALTO_SENTADO * 0.6].mean(axis=0)
    frente = bajo[:2] - alto[:2]
    ang = math.atan2(frente[1], frente[0])
    c, s = math.cos(-ang), math.sin(-ang)
    xy = co[:, :2] @ np.array([[c, s], [-s, c]])
    co[:, 0], co[:, 1] = xy[:, 0], xy[:, 1]
    co[:, 1] -= (co[:, 1].min() + co[:, 1].max()) / 2.0
    atras = co[:, 0].min()
    largo = co[:, 0].max() - atras
    mitad_trasera = co[co[:, 0] < atras + largo * 0.35]
    asiento = mitad_trasera[mitad_trasera[:, 2] < ALTO_SENTADO * 0.6][:, 2].min()
    co[:, 0] -= atras
    co[:, 2] -= asiento
    me.vertices.foreach_set('co', co.ravel())
    me.update()
    malla['manos'] = manos(co)
    print(f'cochero: manos {malla["manos"]}')
    print(f'cochero: frente girado {math.degrees(ang):.1f}°, asiento a {asiento:.3f} m, largo {largo:.2f} m')


def manos(co):
    """Puños (donde van las riendas): lo más adelantado de cada lado entre 0,2 y 0,5 m sobre el asiento (por debajo
    quedan las rodillas, que sobresalen más). Marco glTF del modelo: x adelante, y arriba, z derecha."""
    res = {}
    banda = co[(co[:, 2] > 0.2) & (co[:, 2] < 0.5)]
    for lado, signo in (('izquierda', 1.0), ('derecha', -1.0)):
        b = banda[banda[:, 1] * signo > 0.03]
        punta = b[b[:, 0] > b[:, 0].max() - 0.05]
        c = punta.mean(axis=0)
        res[lado] = [round(float(c[0]) - 0.03, 4), round(float(c[2]), 4), round(float(-c[1]), 4)]
    return res


def renders(malla):
    REV.mkdir(parents=True, exist_ok=True)
    escena = bpy.context.scene
    escena.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else escena.render.engine
    escena.render.resolution_x, escena.render.resolution_y = 900, 600
    mundo = bpy.data.worlds.new('m')
    mundo.use_nodes = True
    next(n for n in mundo.node_tree.nodes if n.type == 'BACKGROUND').inputs['Color'].default_value = (0.75, 0.72, 0.7, 1)
    escena.world = mundo
    sol = bpy.data.objects.new('sol', bpy.data.lights.new('sol', 'SUN'))
    sol.rotation_euler = (math.radians(50), 0, math.radians(30))
    escena.collection.objects.link(sol)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    escena.collection.objects.link(cam)
    escena.camera = cam
    malla.hide_render = True
    for id_, p in PESCANTE.items():
        bpy.ops.import_scene.gltf(filepath=str(CARROZAS / f'{id_}.glb'))
        carro = [o for o in bpy.context.selected_objects]
        figura = malla.copy()
        figura.hide_render = False
        escena.collection.objects.link(figura)
        # marco glTF (x adelante, y arriba, z derecha) → Blender (x adelante, y izquierda, z arriba)
        figura.location = (p[0], -p[2], p[1])
        for nombre, pos, mira in [('perfil', (1.0, -7.0, 1.7), (1.0, 0, 1.6)), ('tres_cuartos', (6.0, -5.0, 3.0), (0.8, 0, 1.6))]:
            cam.location = pos
            d = np.array(mira) - np.array(pos)
            cam.rotation_euler = (math.atan2(math.hypot(d[0], d[1]), -d[2]), 0, math.atan2(d[1], d[0]) - math.pi / 2)
            escena.render.filepath = str(REV / f'{id_}_{nombre}.png')
            bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(figura, do_unlink=True)
        for o in carro:
            bpy.data.objects.remove(o, do_unlink=True)
    malla.hide_render = False


def exportar(malla):
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    malla['pescante'] = {k: list(v) for k, v in PESCANTE.items()}
    bpy.ops.object.select_all(action='DESELECT')
    malla.select_set(True)
    bpy.context.view_layer.objects.active = malla
    bpy.ops.export_scene.gltf(filepath=str(SALIDA), use_selection=True, export_format='GLB', export_extras=True,
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_yup=True)
    tris = sum(len(p.vertices) - 2 for p in malla.data.polygons)
    (SALIDA.parent / 'ficha.json').write_text(json.dumps({
        'id': ID, 'nombre': 'Cochero de las carrozas', 'origen': 'personas/cochero/chofer.glb',
        'alto_sentado_m': ALTO_SENTADO, 'triangulos': tris, 'pescante': PESCANTE,
        'uso': 'Figura estática sentada; preparar_vehiculos.mjs la funde al cuerpo de las carrozas (cochero: true).',
    }, ensure_ascii=False, indent=1) + '\n')
    print(f'cochero → {SALIDA} ({tris} triángulos)')


limpiar()
m = preparar_malla()
if '--sin-render' not in ARGS:
    renders(m)
exportar(m)
