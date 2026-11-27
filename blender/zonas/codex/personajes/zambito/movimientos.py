"""Marcha UAL en sitio y gestos de un acompañante que lleva la capa doblada."""
import math

import bpy
from mathutils import Quaternion, Vector

from kit_ual import (
    curva_puntos, fijar_rotacion_mundo_desde_reposo, ik_dos_huesos, limpiar_pose,
    rotar_euler_mundo,
)
from rig import coordenadas


def construir_pose(ual, s, malla):
    p = coordenadas(malla)
    suelas = {}
    for lado, izquierda in [('R', False), ('L', True)]:
        puntos = [v.co.copy() - s[f'DEF-foot.{lado}'][0]
                  for v, (x, _, z) in zip(malla.data.vertices, p) if z < .033 and (x > -.04) == izquierda]
        suelas[lado] = puntos

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        marcha = spec['ual'] == 'Walk_Loop'
        rapida = nombre == 'caminar_rapido'
        puntual = not spec['bucle']
        ual.aplicar_a_rig(
            rig, spec['ual'], 0 if puntual else u,
            pesos_grupo={
                'cadera': .54, 'torso': .68, 'cabeza': .47, 'piernas': 0,
                'brazo_der': .32 if marcha else 0,
                'brazo_izq': 0,
            },
            cuerpo_relativo_f0=True,
        )
        rotar_euler_mundo(rig, 'DEF-neck', yaw_z=.24)
        rotar_euler_mundo(rig, 'DEF-head', yaw_z=.39)
        cadera = rig.pose.bones['DEF-hips']
        q_cadera = cadera.bone.matrix_local.to_quaternion()
        cadera.location += q_cadera.inverted() @ Vector((0, 0, -.047 if marcha else -.006))
        bpy.context.view_layer.update()

        objetivos = []
        bajar = 0.
        for lado in ('R', 'L'):
            muslo, pierna, pie, dedo = [f'DEF-{h}.{lado}' for h in ('thigh', 'shin', 'foot', 'toe')]
            tobillo = s[pie][0].copy()
            inclinacion, alza = 0., 0.
            if marcha:
                fuente = ual.rig.matrix_world @ ual.rig.pose.bones[pie].head
                punta = ual.rig.matrix_world @ ual.rig.pose.bones[dedo].head
                tobillo.y += (fuente.y - .063) * .66
                alza = max(0., min(fuente.z - .104, punta.z - .015)) * .45
                inclinacion = .60 * (math.atan2(fuente.z - punta.z, abs(punta.y - fuente.y)) - .52)
            giro_pie = Quaternion((1, 0, 0), inclinacion)
            tobillo.z = alza - min((giro_pie @ v).z for v in suelas[lado])
            delta = rig.pose.bones[muslo].head - tobillo
            alcance = (rig.data.bones[muslo].length + rig.data.bones[pierna].length) * .993
            techo = math.sqrt(max(0, alcance * alcance - delta.x * delta.x - delta.y * delta.y))
            bajar = max(bajar, delta.z - techo)
            objetivos.append((muslo, pierna, pie, tobillo, giro_pie))
        cadera.location += q_cadera.inverted() @ Vector((0, 0, -bajar))
        for muslo, pierna, pie, tobillo, giro_pie in objetivos:
            ik_dos_huesos(rig, muslo, pierna, tobillo, s[pierna][0] + Vector((0, -.5, 0)))
            fijar_rotacion_mundo_desde_reposo(rig, pie, giro_pie)

        fase = u * math.tau
        acomodo = 0.
        izquierda = -.022
        if marcha:
            rotar_euler_mundo(rig, 'DEF-upper_arm.R', roll_y=.18)
            rotar_euler_mundo(rig, 'DEF-forearm.R', pitch_x=-.12 + .055 * math.sin(fase))
            izquierda -= .027 + .024 * math.sin(fase - .4)
            if rapida:
                rotar_euler_mundo(rig, 'DEF-spine.002', pitch_x=.055)
        elif nombre == 'cargar_bulto':
            acomodo = curva_puntos(u, [(0, 0), (.22, .68), (.43, 1), (.61, .66), (.81, .22), (1, 0)])
            rotar_euler_mundo(rig, 'DEF-head', pitch_x=.19 * acomodo, yaw_z=.39 * acomodo)
            izquierda -= .043 * acomodo
        elif nombre == 'mirar_atras':
            mira = curva_puntos(u, [(0, 0), (.16, .30), (.38, 1), (.57, 1), (.77, .32), (1, 0)])
            rotar_euler_mundo(rig, 'DEF-spine.002', yaw_z=-.28 * mira)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=-.16 * mira)
            rotar_euler_mundo(rig, 'DEF-neck', yaw_z=-.31 * mira)
            rotar_euler_mundo(rig, 'DEF-head', yaw_z=-.88 * mira, pitch_x=-.06 * mira)

        # La mano que agarra la capa sigue un punto sobre el pecho. El codo
        # resuelve la distancia sin despegar los dedos de la tela.
        bpy.context.view_layer.update()
        pecho = rig.pose.bones['DEF-spine.002']
        anclaje = pecho.matrix @ pecho.bone.matrix_local.inverted()
        muneca = s['DEF-hand.L'][0] + acomodo * Vector((-.020, -.011, .036))
        codo = s['DEF-forearm.L'][0] + acomodo * Vector((-.016, -.014, .006))
        ik_dos_huesos(rig, 'DEF-upper_arm.L', 'DEF-forearm.L', anclaje @ muneca, anclaje @ codo)
        giro_pecho = anclaje.to_quaternion()
        fijar_rotacion_mundo_desde_reposo(rig, 'DEF-hand.L', giro_pecho)
        giro_capa = giro_pecho @ Quaternion((0, 1, 0), izquierda)
        if marcha:
            giro_capa @= Quaternion((1, 0, 0), .075 * math.sin(fase + .9))
        fijar_rotacion_mundo_desde_reposo(rig, 'capa_doblada', giro_capa)

        # La vaina cuelga del cinturón. Acompaña la marcha sin copiar la flexión de la rodilla.
        giro_sable = Quaternion((0, 1, 0), .06)
        if marcha:
            giro_sable = Quaternion((0, 1, 0), .19 + .028 * math.sin(fase))
            giro_sable @= Quaternion((1, 0, 0), .068 * math.sin(fase + .5))
        fijar_rotacion_mundo_desde_reposo(rig, 'sable_envainado', giro_sable)
    return pose
