"""Esqueleto deformable completo, manos de tres falanges y cadena para carta/forro."""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion

DEDOS = ['pulgar', 'indice', 'medio', 'anular', 'menique']


def datos_mano(signo):
    """Dedos en abanico leve; muñeca y palma en reposo de brazos bajos."""
    x = signo*.292
    dedos = {}
    # Cuatro dedos: distribución transversal en X, pulgar hacia el torso y delante.
    for nombre, dx, largo in [('indice', -.023, .064), ('medio', -.007, .071),
                              ('anular', .010, .065), ('menique', .025, .052)]:
        a = Vector((x+signo*dx*1.12, -.030, .745))
        b = a+Vector((signo*dx*.2, -.006, -largo*.45))
        c = b+Vector((0, -.009, -largo*.33))
        d = c+Vector((0, -.011, -largo*.22))
        dedos[nombre] = [a,b,c,d]
    dedos['pulgar'] = [Vector((x-signo*.030,-.018,.807)), Vector((x-signo*.054,-.023,.782)),
                       Vector((x-signo*.058,-.032,.757)), Vector((x-signo*.057,-.041,.740))]
    return dedos


def crear():
    arm = bpy.data.armatures.new('Sirviente_esqueleto')
    rig = bpy.data.objects.new('Sirviente', arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    def hueso(nombre, cabeza, cola, padre=None, conectar=False):
        b = arm.edit_bones.new(nombre)
        b.head, b.tail = cabeza, cola
        if padre:
            b.parent = arm.edit_bones[padre]
            b.use_connect = conectar
        return b
    hueso('raiz', (0,0,0),(0,0,.15))
    hueso('pelvis', (0,0,.92),(0,0,1.025),'raiz')
    hueso('columna', (0,0,1.025),(0,0,1.20),'pelvis',True)
    hueso('pecho', (0,0,1.20),(0,0,1.375),'columna',True)
    hueso('cuello', (0,0,1.375),(0,0,1.484),'pecho',True)
    hueso('cabeza', (0,0,1.484),(0,0,1.75),'cuello',True)
    hueso('mandibula', (0,-.0506,1.5566),(0,-.0715,1.4906),'cabeza')
    for suf,sg in [('izq',1),('der',-1)]:
        hueso('clavicula_'+suf, (sg*.035,0,1.375),(sg*.181,0,1.352),'pecho')
        hueso('brazo_'+suf, (sg*.181,0,1.352),(sg*.256,-.005,1.09),'clavicula_'+suf,True)
        hueso('antebrazo_'+suf, (sg*.256,-.005,1.09),(sg*.292,-.025,.842),'brazo_'+suf,True)
        hueso('mano_'+suf, (sg*.292,-.025,.842),(sg*.292,-.030,.745),'antebrazo_'+suf,True)
        for nombre, puntos in datos_mano(sg).items():
            for i in range(3):
                hueso(f'{nombre}_{i+1}_{suf}', puntos[i], puntos[i+1], 'mano_'+suf if i==0 else f'{nombre}_{i}_{suf}', i>0)
        hueso('muslo_'+suf, (sg*.092,0,.92),(sg*.117,-.008,.465),'pelvis')
        hueso('pierna_'+suf, (sg*.117,-.008,.465),(sg*.122,0,.135),'muslo_'+suf,True)
        hueso('pie_'+suf, (sg*.122,0,.135),(sg*.122,-.16,.065),'pierna_'+suf,True)
        hueso('dedo_pie_'+suf,(sg*.122,-.16,.065),(sg*.122,-.22,.055),'pie_'+suf,True)
        hueso('ojo_'+suf, (sg*.04485,-.0946,1.6369),(sg*.04485,-.1386,1.6369),'cabeza')
    hueso('solapa_izq',(.10,-.10,1.30),(.14,-.12,.97),'pecho')
    hueso('carta',(.105,-.13,1.19),(.105,-.13,1.25),'solapa_izq')
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_in_front = True
    arm.display_type = 'OCTAHEDRAL'
    for b in rig.pose.bones:
        b.rotation_mode = 'QUATERNION'
    rig['personaje'] = 'sirviente_lemoine'
    rig['frente_blender'] = '-Y'
    rig['carta_firma'] = 'Parra'
    rig['origen_historico'] = 'no documentado'
    return rig


def orientar(rig, nombre, destino):
    """Orientar un hueso hacia un punto de mundo preservando su roll de reposo."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[nombre]
    origen = pb.head.copy()
    local = pb.bone.matrix_local.to_quaternion()
    direccion = pb.bone.tail_local-pb.bone.head_local
    q = direccion.rotation_difference(Vector(destino)-origen) @ local
    deseada = Matrix.LocRotScale(origen,q,Vector((1,1,1)))
    if pb.parent:
        base = pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
    else:
        base = pb.bone.matrix_local
    pb.matrix_basis = base.inverted() @ deseada
    bpy.context.view_layer.update()


def ik_dos(rig, superior, inferior, objetivo, polo):
    bpy.context.view_layer.update()
    a = rig.pose.bones[superior].head.copy()
    objetivo, polo = Vector(objetivo), Vector(polo)
    l1, l2 = rig.data.bones[superior].length, rig.data.bones[inferior].length
    distancia = (objetivo-a).length
    d = max(.001,min(distancia, l1+l2-.0001))
    u = (objetivo-a).normalized()
    v = polo-a-u*(polo-a).dot(u)
    v.normalize()
    proyeccion = (l1*l1-l2*l2+d*d)/(2*d)
    altura = math.sqrt(max(0,l1*l1-proyeccion*proyeccion))
    codo = a+u*proyeccion+v*altura
    orientar(rig,superior,codo)
    orientar(rig,inferior,objetivo)


def rotar(rig,nombre,x=0,y=0,z=0):
    from mathutils import Euler
    q=Euler((x,y,z),'XYZ').to_quaternion()
    if nombre in ('pelvis','columna','pecho','cuello','cabeza'):
        # En un hueso vertical Y local apunta arriba: Z local NO es el yaw de la cabeza.
        base=rig.data.bones[nombre].matrix_local.to_quaternion()
        q=base.inverted() @ q @ base
    rig.pose.bones[nombre].rotation_quaternion=q


def desplazar(rig,nombre,x=0,y=0,z=0):
    base=rig.data.bones[nombre].matrix_local.to_quaternion()
    rig.pose.bones[nombre].location=base.inverted() @ Vector((x,y,z))


def dedos(rig,suf,curvar=.35,indice=None):
    for nombre in DEDOS:
        valor = indice if nombre=='indice' and indice is not None else curvar
        for i in range(1,4):
            rotar(rig,f'{nombre}_{i}_{suf}', valor*(.8 if i==1 else 1),0,0)
