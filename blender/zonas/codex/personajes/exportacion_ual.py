"""Importación y exportación de mallas skinned con texturas del GLB de origen."""
import json
import struct

import bpy
import numpy as np
from mathutils import Vector

from kit_ual import limpiar_pose


def corregir_tangentes_uv(ruta):
    """Da una base ortonormal a los pocos UV degenerados del escaneo."""
    datos = bytearray(ruta.read_bytes())
    longitud, = struct.unpack_from('<I', datos, 12)
    gltf = json.loads(datos[20:20 + longitud])
    inicio_binario = 28 + longitud

    def leer(indice, columnas):
        accesor = gltf['accessors'][indice]
        vista = gltf['bufferViews'][accesor['bufferView']]
        offset = inicio_binario + vista.get('byteOffset', 0) + accesor.get('byteOffset', 0)
        return np.ndarray((accesor['count'], columnas), dtype='<f4', buffer=datos,
                          offset=offset, strides=(vista.get('byteStride', columnas * 4), 4))

    corregidas = 0
    for malla in gltf['meshes']:
        for primitiva in malla['primitives']:
            atributos = primitiva['attributes']
            tangentes = leer(atributos['TANGENT'], 4)
            nulas = np.linalg.norm(tangentes[:, :3], axis=1) < .1
            normales = leer(atributos['NORMAL'], 3)[nulas]
            eje = np.eye(3)[np.abs(normales).argmin(axis=1)]
            ortogonal = np.cross(normales, eje)
            tangentes[nulas, :3] = ortogonal / np.linalg.norm(ortogonal, axis=1, keepdims=True)
            corregidas += int(nulas.sum())
    if corregidas:
        ruta.write_bytes(datos)
        print('Tangentes degeneradas corregidas:', corregidas)


def importar_malla(ruta, nombre, origen, escala):
    bpy.ops.import_scene.gltf(filepath=str(ruta), merge_vertices=True)
    malla = next(o for o in bpy.data.objects if o.type == 'MESH')
    malla.name = nombre
    bpy.context.view_layer.objects.active = malla
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for v in malla.data.vertices:
        v.co = (v.co - origen) * escala
    malla.data.update()
    for material in malla.data.materials:
        for nodo in material.node_tree.nodes:
            if nodo.type == 'TEX_IMAGE':
                nodo.interpolation = 'Closest'
    return malla


def exportar_glb(ruta_glb, rig, malla):
    rig.animation_data.action = None
    bpy.context.scene.frame_set(0)
    limpiar_pose(rig)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    malla.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=str(ruta_glb), use_selection=True,
        export_format='GLB', export_yup=True, export_skins=True,
        export_all_influences=False, export_def_bones=False, export_tangents=True,
        export_animations=True, export_animation_mode='NLA_TRACKS',
        export_frame_range=False, export_force_sampling=True,
    )
    corregir_tangentes_uv(ruta_glb)


def renderizar_vistas(rig, acciones, revision, tomas):
    escena = bpy.context.scene
    escena.render.engine = 'BLENDER_WORKBENCH'
    escena.display.shading.light = 'STUDIO'
    escena.display.shading.color_type = 'TEXTURE'
    escena.display.shading.background_type = 'WORLD'
    escena.display.shading.show_cavity = True
    escena.display.shading.cavity_type = 'BOTH'
    escena.world = bpy.data.worlds.new('Estudio')
    escena.world.color = (.24, .195, .17)
    escena.render.resolution_x = 640
    escena.render.resolution_y = 750
    cam = bpy.data.objects.new('Cámara de revisión', bpy.data.cameras.new('Cámara de revisión'))
    escena.collection.objects.link(cam)
    escena.camera = cam
    cam.data.lens = 52
    for nombre, clip, frame, posicion, mira in tomas:
        rig.animation_data.action = acciones[clip]
        escena.frame_set(frame)
        cam.location = posicion
        cam.rotation_euler = (Vector(mira) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        escena.render.filepath = str(revision / f'{nombre}.png')
        bpy.ops.render.render(write_still=True)
    escena.camera = None
    bpy.data.objects.remove(cam, do_unlink=True)
