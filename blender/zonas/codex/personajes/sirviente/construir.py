"""Generar .blend, GLB y vistas de estudio. Solo un personaje, sin cargar la ciudad."""
import json
import math
import sys
import shutil
from pathlib import Path
import bpy
from mathutils import Vector

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
RAIZ=BASE.parents[4]
SALIDA=RAIZ/'web/public/models/ciudad/codex/personajes/sirviente'
REV=RAIZ/'revisiones/codex/sirviente_v2'
from modelo import crear as crear_modelo
from esqueleto import crear as crear_rig
from animaciones import crear as crear_clips,pose,limpiar
from malla import Malla


def material_imagen(nombre,archivo):
    mat=bpy.data.materials.new(nombre)
    mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.91
    shader.inputs['Specular IOR Level'].default_value=.22
    textura=mat.node_tree.nodes.new('ShaderNodeTexImage')
    textura.image=bpy.data.images.load(str(archivo),check_existing=True)
    textura.image.pack()
    textura.interpolation='Closest'
    mat.node_tree.links.new(textura.outputs['Color'],shader.inputs['Base Color'])
    return mat


def crear_carta(rig):
    m=Malla()
    # La parte inferior queda oculta por el bolsillo; el rectángulo superior sigue la nueva lámina.
    m.poligono([(.078,-.130,1.148),(.130,-.127,1.153),(.126,-.127,1.250),(.074,-.130,1.245)],'papel','carta')
    m.uvs[-1]=[(0,0),(1,0),(1,1),(0,1)]
    # Reverso independiente a 0,7 mm: sin parpadeo, visible al sacar la carta.
    m.poligono([(.074,-.1293,1.245),(.126,-.1263,1.250),(.130,-.1263,1.153),(.078,-.1293,1.148)],'papel','carta')
    m.uvs[-1]=[(0,1),(1,1),(1,0),(0,0)]
    mat=material_imagen('Carta_de_Parra',SALIDA/'carta_parra.png')
    return m.objeto('Carta_Parra',mat,rig)


def estudio():
    escena=bpy.context.scene
    escena.render.engine='CYCLES'
    escena.cycles.samples=28
    escena.cycles.use_denoising=True
    try:
        pref=bpy.context.preferences.addons['cycles'].preferences
        pref.compute_device_type='CUDA'
        pref.get_devices()
        for dev in pref.devices:
            dev.use=dev.type=='CUDA'
        escena.cycles.device='GPU'
    except Exception as exc:
        print('CUDA no disponible:',exc)
    escena.render.resolution_x=900
    escena.render.resolution_y=1100
    escena.render.resolution_percentage=100
    escena.world.color=(.20,.20,.20)
    escena.world.use_nodes=True
    escena.world.node_tree.nodes['Background'].inputs[0].default_value=(.39,.34,.31,1)
    escena.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    escena.view_settings.view_transform='AgX'
    def area(nombre,pos,potencia,color,tamano):
        bpy.ops.object.light_add(type='AREA',location=pos)
        obj=bpy.context.object;obj.name=nombre
        obj.data.energy=potencia;obj.data.color=color;obj.data.shape='DISK';obj.data.size=tamano
        obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
    area('Estudio_principal',(-3,-4,5),350,(1,.87,.72),4)
    area('Estudio_relleno',(3,-2,3),180,(.78,.85,1),3)
    area('Estudio_contra',(1,3,4),420,(1,.90,.78),3)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002))
    suelo=bpy.context.object;suelo.name='Estudio_suelo'
    mat=bpy.data.materials.new('Estudio_fondo');mat.diffuse_color=(.32,.28,.26,1)
    mat.use_nodes=True
    mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.32,.28,.26,1)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=1
    suelo.data.materials.append(mat)
    bpy.ops.object.camera_add()
    camara=bpy.context.object;camara.name='Estudio_camara'
    camara.data.type='ORTHO';camara.data.ortho_scale=2.08
    escena.camera=camara
    return camara


def renderizar(rig,datos,camara):
    opciones=[('tres_cuartos',(-2.5,-5,1.95),(0,0,.91),'reposo',0,1.96),
              ('frente',(0,-5,1.40),(0,0,.91),'reposo',0,1.96),
              ('espalda',(2.5,5,1.80),(0,0,.91),'reposo',0,1.96),
              ('rostro',(-1.3,-4,1.83),(0,-.01,1.58),'reposo',0,.52),
              ('caminar',(-2.5,-5,2.25),(0,0,.91),'caminar',.2,1.96),
              ('silencio',(-1,-5,1.8),(0,0,1.3),'silencio',.5,1.18),
              ('forro',(3,-4,1.8),(.10,-.05,1.20),'mostrar_forro',.5,.85)]
    for nombre,pos,mira,clip,t,escala in opciones:
        if '--vistas' in sys.argv:
            elegidas=sys.argv[sys.argv.index('--vistas')+1].split(',')
            if nombre not in elegidas:continue
        pose(rig,clip,t,datos)
        camara.location=pos
        camara.rotation_euler=(Vector(mira)-camara.location).to_track_quat('-Z','Y').to_euler()
        camara.data.ortho_scale=escala
        bpy.context.scene.render.filepath=str(REV/(nombre+'.png'))
        bpy.ops.render.render(write_still=True)
        if nombre=='tres_cuartos':
            shutil.copy2(REV/'tres_cuartos.png',SALIDA/'vista_previa.png')


def main():
    datos=json.loads((BASE/'diseno.json').read_text())
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    SALIDA.mkdir(parents=True,exist_ok=True);REV.mkdir(parents=True,exist_ok=True)
    rig=crear_rig()
    mat=material_imagen('Sirviente_low_poly_v2',SALIDA/'sirviente_color.png')
    obj=crear_modelo(mat,rig)
    carta=crear_carta(rig)
    # Fuente original empaquetada para comparar dentro de Blender.
    ruta_referencia=RAIZ/datos['referencia']
    if not ruta_referencia.exists():ruta_referencia=SALIDA/'referencia.png'
    referencia=bpy.data.images.load(str(ruta_referencia))
    referencia.pack()
    crear_clips(rig,datos)
    rig['configuracion']=json.dumps(datos,ensure_ascii=False)
    bpy.ops.object.select_all(action='DESELECT')
    for o in (rig,obj,carta):o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(SALIDA/'sirviente.glb'),use_selection=True,
         export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',
         export_frame_range=False,export_force_sampling=True,export_skins=True,
         export_all_influences=False,export_def_bones=False,export_morph=False,
         export_extras=True,export_yup=True,export_cameras=False,export_lights=False,
         export_optimize_animation_size=True,export_optimize_animation_keep_anim_armature=True)
    camara=estudio()
    pose(rig,'reposo',0,datos)
    camara.location=(-2.5,-5,2.25)
    camara.rotation_euler=(Vector((0,0,.94))-camara.location).to_track_quat('-Z','Y').to_euler()
    for o in (obj,carta):o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    # Vista material al abrir, luz de estudio y modelo editable con clips NLA nombrados.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_distance=2.8
                area.spaces.active.region_3d.view_location=(0,0,1)
                area.spaces.active.shading.type='MATERIAL'
    # Al abrir el maestro y pulsar reproducir se ve reposo; los demás clips siguen
    # disponibles como Actions y en las pistas NLA, que permanecen silenciadas.
    rig.animation_data.action=bpy.data.actions['reposo']
    bpy.context.scene.frame_start=0
    bpy.context.scene.frame_end=72
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(SALIDA/'sirviente.blend'),compress=True)
    rig.animation_data.action=None
    informe={'vertices':len(obj.data.vertices),'triangulos':sum(len(p.vertices)-2 for p in obj.data.polygons)+4,
             'huesos':len(rig.data.bones),'materiales':2,'texturas':2,
             'clips':list(datos['movimiento']),'altura_reposo':max(v.co.z for v in obj.data.vertices)}
    (REV/'construccion.json').write_text(json.dumps(informe,indent=2))
    (SALIDA/'sirviente.json').write_text(json.dumps(datos,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(informe,ensure_ascii=False))
    if '--sin-render' not in sys.argv:
        renderizar(rig,datos,camara)
    print('SIRVIENTE_TERMINADO',flush=True)


if __name__=='__main__':
    main()
