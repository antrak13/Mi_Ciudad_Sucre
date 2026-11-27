"""Piezas comunes para riggear y animar en Blender un personaje estático (GLB de Tripo) con el esqueleto UAL.

Lo usan los `construir.py` de cada personaje de esta carpeta. Se apoya en el kit de antigravity
(`blender/zonas/antigravity/personajes/kit_ual.py`: armadura UAL, biblioteca de clips, IK y horneado).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, Quaternion

RAIZ = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(Path(__file__).resolve().parent), str(RAIZ / 'blender/zonas/antigravity/personajes')]

from kit_ual import (  # noqa: E402
    fijar_rotacion_mundo_desde_reposo, limpiar_pose, rotar_euler_mundo, ik_dos_huesos, apuntar_hueso,
)
from pesos_envolvente import caras_entre_piezas, caras_tapa_inferior  # noqa: E402,F401  (se reexportan)

MUSLOS = ['DEF-thigh.L', 'DEF-shin.L', 'DEF-thigh.R', 'DEF-shin.R']
PIES = ['DEF-foot.L', 'DEF-toe.L', 'DEF-foot.R', 'DEF-toe.R']

SCRATCH = RAIZ / 'revisiones/claude/scratch'
IDENT = Quaternion((1.0, 0.0, 0.0, 0.0))


def argumentos():
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


# ---------------------------------------------------------------------------------------------------------------
# Malla
# ---------------------------------------------------------------------------------------------------------------

def simplificar(entrada, salida, ratio=0.006, textura_px=2048):
    """Millones de triángulos de Tripo → ~30 k con meshoptimizer y texturas a `textura_px`, fuera de Blender."""
    salida = Path(salida)
    if salida.exists() and salida.stat().st_size > 100_000:
        return salida
    salida.parent.mkdir(parents=True, exist_ok=True)
    gt = str(RAIZ / 'web/node_modules/.bin/gltf-transform')
    env = dict(os.environ, NODE_OPTIONS='--max-old-space-size=1536')
    tmp = salida.with_name(salida.stem + '_tmp.glb')
    subprocess.run([gt, 'simplify', str(entrada), str(tmp), '--ratio', str(ratio), '--error', '0.01'], check=True, env=env)
    subprocess.run([gt, 'resize', str(tmp), str(salida), '--width', str(textura_px), '--height', str(textura_px)],
                   check=True, env=env)
    tmp.unlink()
    return salida


def importar_malla(ruta, altura, nombre):
    """Importa la malla, aplica transformaciones y la deja de `altura` m con los pies en z=0. Devuelve (malla,
    coordenadas normalizadas a altura 1, en el mismo orden de vértices)."""
    bpy.ops.import_scene.gltf(filepath=str(ruta))
    malla = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.polygons))
    for o in list(bpy.data.objects):
        if o != malla:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.objects.active = malla
    malla.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    co = np.empty(len(malla.data.vertices) * 3, dtype=np.float64)
    malla.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    co[:, 2] -= co[:, 2].min()
    co /= co[:, 2].max()
    malla.data.vertices.foreach_set('co', (co * altura).ravel())
    malla.data.update()
    malla.name = nombre
    return malla, co


def triangulos(malla):
    if all(len(p.vertices) == 3 for p in malla.data.polygons):
        t = np.empty(len(malla.data.polygons) * 3, dtype=np.int64)
        malla.data.polygons.foreach_get('vertices', t)
        return t.reshape(-1, 3)
    return np.array([(p.vertices[0], p.vertices[i], p.vertices[i + 1])
                     for p in malla.data.polygons for i in range(1, len(p.vertices) - 1)])


def color_base_por_vertice(malla):
    """Color de la textura base (RGB 0..1) bajo cada vértice, leído en sus coordenadas UV."""
    me = malla.data
    uv = np.empty(len(me.loops) * 2, dtype=np.float32)
    me.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    vidx = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get('vertex_index', vidx)
    uv_v = np.zeros((len(me.vertices), 2), dtype=np.float32)
    uv_v[vidx] = uv
    mat = malla.active_material
    nodo = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    img = nodo.inputs['Base Color'].links[0].from_node.image
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    ix = np.clip((uv_v[:, 0] % 1.0 * w).astype(int), 0, w - 1)
    iy = np.clip((uv_v[:, 1] % 1.0 * h).astype(int), 0, h - 1)
    return px[iy, ix, :3].astype(np.float64)


def asignar_grupos(malla, nombres, W):
    for j, nombre in enumerate(nombres):
        vg = malla.vertex_groups.new(name=nombre)
        col = np.round(W[:, j], 3)
        for peso in np.unique(col[col > 0]):
            vg.add(np.nonzero(col == peso)[0].tolist(), float(peso), 'REPLACE')


def cortar_caras(malla, indices, motivo):
    if not len(indices):
        return
    bm = bmesh.new()
    bm.from_mesh(malla.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.asarray(indices).tolist()], context='FACES_ONLY')
    bm.to_mesh(malla.data)
    bm.free()
    print(f'Caras cortadas ({motivo}): {len(indices)}')


def desdoblar_costuras(malla, nombres, W, pieza, permitidos=()):
    """Las caras con que Tripo cose una pieza (antebrazo y mano) al cuerpo se desdoblan en dos copias: una va entera
    con el cuerpo y otra entera con la pieza. Al separarse no se estira una membrana (como sin cortar) ni quedan
    agujeros que se ven por transparencia (como al borrarlas). Devuelve los pesos con las filas de los vértices
    nuevos; se llama después de los cortes y antes de `asignar_grupos`."""
    piezas = [pieza] if isinstance(pieza, str) else list(pieza)
    en_pieza = W[:, [nombres.index(p) for p in piezas]].sum(axis=1) > 0.5
    dominante = np.array(nombres, dtype=object)[np.argmax(W, axis=1)]
    permitido = np.isin(dominante, list(permitidos)) & ~en_pieza
    bm = bmesh.new()
    bm.from_mesh(malla.data)
    bm.verts.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    filas = list(W)
    copias = {}

    def copia(v, lado, pesos):
        clave = (v.index, lado)
        if clave not in copias:
            nuevo = bm.verts.new(v.co)
            copias[clave] = nuevo
            filas.append(pesos)
        return copias[clave]

    caras = [f for f in bm.faces
             if any(en_pieza[v.index] for v in f.verts) and not all(en_pieza[v.index] for v in f.verts)
             and not any(permitido[v.index] for v in f.verts)]
    for f in caras:
        idx = [v.index for v in f.verts]
        de_pieza = [i for i in idx if en_pieza[i]]
        del_cuerpo = [i for i in idx if not en_pieza[i]]
        peso_cuerpo = np.mean([W[i] for i in del_cuerpo], axis=0)
        peso_pieza = np.mean([W[i] for i in de_pieza], axis=0)
        uvs = [l[uv].uv.copy() for l in f.loops] if uv else None
        for lado, peso in (('cuerpo', peso_cuerpo), ('pieza', peso_pieza)):
            otro = en_pieza if lado == 'cuerpo' else ~en_pieza
            vs = [copia(v, lado, peso) if otro[v.index] else v for v in f.verts]
            try:
                g = bm.faces.new(vs, f)
            except ValueError:
                continue
            if uvs:
                for l, c in zip(g.loops, uvs):
                    l[uv].uv = c
        bm.faces.remove(f)
    bm.to_mesh(malla.data)
    bm.free()
    print(f'Costuras desdobladas ({"+".join(piezas)}): {len(caras)} caras, {len(copias)} vértices nuevos')
    return np.array(filas)


def quitar_islas(malla, max_caras, z_max):
    """Borra las islas sueltas de pocas caras que quedan junto al suelo después de cortar costuras (restos del ruedo
    o de la tapa que, sin vecinos, se verían como esquirlas al moverse)."""
    bm = bmesh.new()
    bm.from_mesh(malla.data)
    bm.faces.ensure_lookup_table()
    visto, borrar = set(), []
    for f in bm.faces:
        if f.index in visto:
            continue
        isla, pila = [], [f]
        visto.add(f.index)
        while pila:
            g = pila.pop()
            isla.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in visto:
                        visto.add(h.index)
                        pila.append(h)
        if len(isla) <= max_caras and all(v.co.z < z_max for g in isla for v in g.verts):
            borrar.extend(isla)
    if borrar:
        bmesh.ops.delete(bm, geom=borrar, context='FACES_ONLY')
        bm.to_mesh(malla.data)
    bm.free()
    print(f'Islas sueltas borradas: {len(borrar)} caras')


# ---------------------------------------------------------------------------------------------------------------
# Retarget y apoyos
# ---------------------------------------------------------------------------------------------------------------

def huesos_desde_ual(ual, rig, clip, u, huesos, peso=1.0, referencia='Idle_Loop', alinear=False):
    """Copia a `huesos` la rotación de la UAL relativa a una pose de referencia (`'reposo'` = la de la UAL, o el
    cuadro 0 de un clip). Con `alinear`, antes endereza cada hueso del personaje hacia la dirección que tiene en la
    referencia (para mallas que no están en esa pose: brazo levantado, piernas abiertas).

    evaluar_en cambia el cuadro de la escena y Blender reevalúa la acción que se está horneando en el personaje: se
    guarda la pose armada hasta aquí y se repone antes de seguir."""
    guardada = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in rig.pose.bones}
    rots, _ = ual.evaluar_en(clip, u)
    rots_ref = ual.reposo_mundo if referencia == 'reposo' else ual.referencia_frame0(referencia)[0]
    for pb in rig.pose.bones:
        pb.location, pb.rotation_quaternion = guardada[pb.name]
    bpy.context.view_layer.update()
    eje_y = Vector((0.0, 1.0, 0.0))
    for b in huesos:
        delta = rots[b] @ rots_ref[b].inverted()
        if alinear:
            propio = rig.data.bones[b].matrix_local.to_quaternion() @ eje_y
            delta = delta @ propio.rotation_difference(rots_ref[b] @ eje_y)
        fijar_rotacion_mundo_desde_reposo(rig, b, IDENT.slerp(delta, peso))


def apoyar_pies(rig, puntos=('DEF-foot.L', 'DEF-foot.R', 'DEF-toe.L', 'DEF-toe.R'), altura_min=None, exacto=False,
                alzado=None):
    """Sube la cadera lo justo para que ningún punto de `puntos` quede por debajo de su altura de reposo (o de
    `altura_min`): al mezclar poses o enderezar piernas, la cadera puede bajar antes de que se doblen las rodillas.
    Con `exacto` también la baja: el punto más bajo queda justo a esa altura (pie de apoyo en el suelo).
    `alzado` ({hueso: m}): cuánto está levantado del suelo ese pie en la malla (un talón alzado a medio paso); de pie,
    ese pie se apoya igual que el otro."""
    bpy.context.view_layer.update()
    # Cabeza y cola de cada hueso (tobillo, metatarso, punta), cada una contra su propia altura de reposo
    # y también los huesos hijos movidos rígidamente con su padre (zapato entero pesado al pie: la punta real
    # la mueve el pie aunque el hueso de los dedos se doble)
    hundido = -1e9
    for n in puntos:
        pb, b = rig.pose.bones[n], rig.data.bones[n]
        deforma = pb.matrix @ b.matrix_local.inverted()
        alto = (alzado or {}).get(n, (alzado or {}).get(b.parent.name if b.parent else '', 0.0))
        hundido = max(hundido, (altura_min if altura_min is not None else b.head_local.z - alto) - pb.head.z,
                      b.tail_local.z - alto - pb.tail.z)
        for hijo in b.children_recursive:
            hundido = max(hundido, hijo.tail_local.z - alto - (deforma @ hijo.tail_local).z)
    if hundido > 0.0 or exacto:
        pb = rig.pose.bones['DEF-hips']
        pb.location = pb.location + rig.data.bones['DEF-hips'].matrix_local.to_quaternion().inverted() @ \
            Vector((0.0, 0.0, hundido))
        bpy.context.view_layer.update()


# ---------------------------------------------------------------------------------------------------------------
# Renders de control
# ---------------------------------------------------------------------------------------------------------------

def cortar_falda_y_pies(malla, co_norm, tris, nombres, W, altura, z_tapa=0.10, otras=()):
    """Personajes con falda o sotana hasta el suelo: corta la tapa con que Tripo cierra la prenda por abajo y las
    costuras entre el ruedo y cada pie (pie + tobillo), y borra las astillas sueltas que quedan junto al suelo. Sin
    esto, al caminar se estira una tabla entre el zapato y el ruedo. `otras`: más caras a cortar en la misma pasada
    (los índices cambian después de cada corte)."""
    cortar = [caras_tapa_inferior(co_norm, tris, nombres, W, z_tapa, excluir=PIES), *otras]
    for suf in ('.L', '.R'):
        cortar.append(caras_entre_piezas(tris, nombres, W, (f'DEF-foot{suf}', f'DEF-shin{suf}')))
    cortar_caras(malla, np.unique(np.concatenate(cortar)), 'tapa de la falda, costuras con los pies y otras')
    quitar_islas(malla, max_caras=40, z_max=0.12 * altura)


def cuerpo_desde_ual(ual, rig, clip, u, pesos, peso_piernas=1.0, brazos=(), peso_brazos=1.0, alinear_brazos=True,
                     pies_como_malla=False, alzado=None):
    """Cadera y torso de la UAL (`pesos` por grupo); muslos y canillas enderezados hacia la UAL y animados; pies
    planos como en el reposo de la UAL (si giraran talón y punta arrastrarían el ruedo) o, con `pies_como_malla`,
    con la misma orientación que en la malla (zapatos que ya están planos en el suelo); `brazos` (lista de huesos)
    desde la UAL; y pies apoyados en el suelo (`alzado`: ver `apoyar_pies`)."""
    ual.aplicar_a_rig(rig, clip, u, pesos_grupo=dict(pesos, piernas=0.0), piernas_relativas_f0=False)
    huesos_desde_ual(ual, rig, clip, u, MUSLOS, peso_piernas, referencia='reposo', alinear=True)
    if pies_como_malla:
        for hueso in PIES:
            bpy.context.view_layer.update()
            fijar_rotacion_mundo_desde_reposo(rig, hueso, IDENT)
    else:
        huesos_desde_ual(ual, rig, 'Idle_Loop', 0.0, PIES, 1.0, referencia='reposo', alinear=True)
    if brazos and peso_brazos > 0.0:
        huesos_desde_ual(ual, rig, clip, u, list(brazos), peso_brazos, referencia='Idle_Loop', alinear=alinear_brazos)
    apoyar_pies(rig, exacto=True, alzado=alzado)


def girar_cabeza(rig, pitch=0.0, roll=0.0, yaw=0.0, cuello=0.4):
    """Reparte un giro de cabeza (rad, ejes del mundo) entre el cuello (`cuello`) y la cabeza."""
    rotar_euler_mundo(rig, 'DEF-neck', pitch_x=pitch * 0.35, roll_y=roll * 0.3, yaw_z=yaw * cuello)
    rotar_euler_mundo(rig, 'DEF-head', pitch_x=pitch * 0.65, roll_y=roll * 0.7, yaw_z=yaw * (1.0 - cuello))


def mover_mano(rig, lado, objetivo, polo, peso=1.0, conservar_mano=True):
    """Lleva la muñeca (`lado` '.L' o '.R') hacia `objetivo` (mundo) con IK de dos huesos, mezclando con `peso` desde
    donde está. Con `conservar_mano`, la mano mantiene su dirección en el mundo: lo que sostiene no se tuerce."""
    bpy.context.view_layer.update()
    mano = rig.pose.bones[f'DEF-hand{lado}']
    direccion = (mano.tail - mano.head).normalized()
    obj = mano.head.lerp(Vector(objetivo), peso)
    ik_dos_huesos(rig, f'DEF-upper_arm{lado}', f'DEF-forearm{lado}', obj, polo)
    if conservar_mano:
        bpy.context.view_layer.update()
        apuntar_hueso(rig, f'DEF-hand{lado}', mano.head + direccion)


def muneca(rig, lado):
    bpy.context.view_layer.update()
    return rig.pose.bones[f'DEF-hand{lado}'].head.copy()


def preparar_render(ancho=480, alto=640):
    esc = bpy.context.scene
    esc.render.engine = 'BLENDER_WORKBENCH'
    esc.display.shading.light = 'STUDIO'
    esc.display.shading.color_type = 'TEXTURE'
    esc.render.resolution_x = ancho
    esc.render.resolution_y = alto
    if not esc.world:
        esc.world = bpy.data.worlds.new('Estudio')
    esc.world.color = (0.62, 0.58, 0.56)
    if 'Suelo' not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=5.0)
        bpy.context.active_object.name = 'Suelo'
    cd = bpy.data.cameras.new('CamControl')
    cd.lens = 50
    cam = bpy.data.objects.new('CamControl', cd)
    esc.collection.objects.link(cam)
    esc.camera = cam
    return cam


def tomar(cam, archivo, pos, mira):
    cam.location = Vector(pos)
    cam.rotation_euler = (Vector(mira) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.render.filepath = str(archivo)
    bpy.ops.render.render(write_still=True)


def renderizar_control(rig, pose, clips, tomas, camaras, carpeta):
    """tomas: [(archivo, clip, u, nombre_cámara)]; camaras: {nombre: (posición, punto mirado)}."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    cam = preparar_render()
    spec = {c['id']: c for c in clips}
    rig.animation_data_create()
    rig.animation_data.action = None
    for pista in rig.animation_data.nla_tracks:
        pista.mute = True
    for archivo, clip, u, vista in tomas:
        pose(rig, clip, u, spec[clip])
        tomar(cam, carpeta / f'{archivo}.png', *camaras[vista])
    bpy.data.objects.remove(bpy.data.objects['Suelo'], do_unlink=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    lamina_control(carpeta, [t[0] for t in tomas])


def lamina_control(carpeta, archivos, por_fila=6):
    """Une los renders en `lamina_control.png` (Pillow no está en el Python de Blender: se arma con numpy)."""
    imgs = []
    for a in archivos:
        ruta = Path(carpeta) / f'{a}.png'
        if ruta.exists():
            im = bpy.data.images.load(str(ruta))
            imgs.append(np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4))
            bpy.data.images.remove(im)
    if not imgs:
        return
    filas = [np.concatenate(imgs[i:i + por_fila] + [np.zeros_like(imgs[0])] * (por_fila - len(imgs[i:i + por_fila])),
                            axis=1) for i in range(0, len(imgs), por_fila)]
    total = np.concatenate(filas[::-1], axis=0)
    out = bpy.data.images.new('lamina', total.shape[1], total.shape[0], alpha=True)
    out.pixels[:] = total.ravel()
    out.filepath_raw = str(Path(carpeta) / 'lamina_control.png')
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)


# ---------------------------------------------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------------------------------------------

VISOR = RAIZ / 'web/public/models/ciudad/antigravity/personajes/aguatero'  # visor genérico de antigravity
CATALOGO = RAIZ / 'web/public/models/ciudad/claude/personajes/catalogo.json'


def exportar(rig, salida, id_, ficha, accion_blend, lamina=None, vista_previa=None, doble_cara=False):
    """GLB con una pista NLA por clip, .blend editable, ficha.json, visor HTML y entrada en el catálogo.
    `doble_cara`: material de dos caras. Tripo no modela la tela que tapa un brazo pegado al cuerpo; al moverlo queda
    un hueco que, con una sola cara, deja ver el fondo. Con dos caras se ve el interior de la prenda."""
    if doble_cara:
        for ob in rig.children:
            for mat in ob.data.materials if ob.type == 'MESH' else []:
                mat.use_backface_culling = False
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    limpiar_pose(rig)
    rig.animation_data.action = None
    bpy.context.scene.frame_set(0)
    ruta_glb = salida / f'{id_}.glb'
    bpy.ops.export_scene.gltf(
        filepath=str(ruta_glb), export_format='GLB', export_image_format='JPEG', export_jpeg_quality=88,
        export_yup=True, export_skins=True, export_all_influences=False, export_def_bones=False,
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_frame_range=False,
    )
    rig.animation_data.action = bpy.data.actions.get(accion_blend)
    for img in bpy.data.images:
        if not img.packed_file and img.filepath:
            try:
                img.pack()
            except Exception:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=str(salida / f'{id_}.blend'), compress=True)
    if lamina and Path(lamina).exists():
        shutil.copy2(lamina, salida / 'referencia.png')
    if vista_previa and Path(vista_previa).exists():
        shutil.copy2(vista_previa, salida / 'vista_previa.png')
    for nombre in ('index.html', 'visor.bundle.js', 'THREE-LICENSE.txt'):
        if (VISOR / nombre).exists():
            shutil.copy2(VISOR / nombre, salida / nombre)
    ficha = dict(ficha, glb=f'{id_}.glb', blend=f'{id_}.blend', referencia='referencia.png')
    (salida / 'ficha.json').write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + '\n')
    catalogo = json.loads(CATALOGO.read_text()) if CATALOGO.exists() else []
    catalogo = [c for c in catalogo if c['id'] != id_] + [{'id': id_, 'etiqueta': ficha['nombre']}]
    CATALOGO.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + '\n')
    print(f'OK: {ruta_glb} ({ruta_glb.stat().st_size / 2**20:.2f} MB), {len(ficha["clips"])} clips')
