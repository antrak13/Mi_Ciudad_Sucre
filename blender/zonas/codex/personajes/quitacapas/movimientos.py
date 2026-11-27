"""Retarget de UAL, apoyo de las alpargatas y gestos de Francisco Ríos."""
import math

import bpy
from mathutils import Quaternion, Vector

from kit_ual import (
    curva_puntos, fijar_rotacion_mundo_desde_reposo, ik_dos_huesos, limpiar_pose, rotar_euler_mundo,
)
from rig import coordenadas


def construir_pose(ual, s, malla):
    suelas = {'R': [], 'L': []}
    for v, (x, _, z) in zip(malla.data.vertices, coordenadas(malla)):
        if z < .028:
            lado = 'L' if x > -.087 else 'R'
            suelas[lado].append(v.co.copy() - s[f'DEF-foot.{lado}'][0])

    piernas = {
        lado: tuple(f'DEF-{h}.{lado}' for h in ('thigh', 'shin', 'foot', 'toe'))
        for lado in suelas
    }

    def apoyar(rig, marcha):
        cadera = rig.pose.bones['DEF-hips']
        bajar = 0
        objetivos = []
        for lado, (muslo, canilla, pie, dedo) in piernas.items():
            tobillo = s[pie][0].copy()
            altura, angulo = 0., 0.
            if marcha:
                fuente = ual.rig.matrix_world @ ual.rig.pose.bones[pie].head
                punta = ual.rig.matrix_world @ ual.rig.pose.bones[dedo].head
                tobillo.y = (fuente.y - .063) * .71
                altura = max(0., min(fuente.z - .104, punta.z - .015)) * .57
                pendiente = math.atan2(fuente.z - punta.z, abs(punta.y - fuente.y))
                angulo = (pendiente - .52) * .48
            giro = Quaternion((1, 0, 0), angulo)
            tobillo.z = altura - min((giro @ v).z for v in suelas[lado])
            delta = rig.pose.bones[muslo].head - tobillo
            largo = (rig.data.bones[muslo].length + rig.data.bones[canilla].length) * .991
            alcance_z = math.sqrt(max(0, largo * largo - delta.x * delta.x - delta.y * delta.y))
            bajar = max(bajar, delta.z - alcance_z)
            objetivos.append((muslo, canilla, pie, tobillo, giro))

        cadera.location += cadera.bone.matrix_local.to_quaternion().inverted() @ Vector((0, 0, -bajar))
        for muslo, canilla, pie, tobillo, giro in objetivos:
            ik_dos_huesos(rig, muslo, canilla, tobillo, s[canilla][0] + Vector((0, -.55, 0)))
            fijar_rotacion_mundo_desde_reposo(rig, pie, giro)

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        marcha = nombre == 'fanfarron_caminar'
        fase = u * math.tau
        ual.aplicar_a_rig(
            rig, spec['ual'], u if spec['bucle'] else 0,
            pesos_grupo={'cadera': .48, 'torso': .66, 'cabeza': .44, 'piernas': 0,
                         'brazo_der': .52 if marcha else 0, 'brazo_izq': 0},
            cuerpo_relativo_f0=True,
        )

        alzar_llave, prepara, lanzar, roll_capa = 0., 0., 0., 0.
        if marcha:
            rotar_euler_mundo(rig, 'DEF-spine.002', pitch_x=-.09, yaw_z=.08 * math.sin(fase))
            rotar_euler_mundo(rig, 'DEF-head', pitch_x=-.08, yaw_z=.32)
            rotar_euler_mundo(rig, 'DEF-upper_arm.R', roll_y=.08)
            roll_capa = .058 * math.sin(fase - .65)
        elif nombre == 'hablar':
            frase = math.sin(fase) * math.sin(fase / 2)
            rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=.11 * frase)
            rotar_euler_mundo(rig, 'DEF-head', yaw_z=.22 * frase)
        elif nombre == 'mostrar_llave':
            alzar_llave = curva_puntos(u, [(0, 0), (.16, .24), (.39, 1), (.70, 1), (1, 0)])
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=.18 * alzar_llave)
            rotar_euler_mundo(rig, 'DEF-head', yaw_z=.39 * alzar_llave, pitch_x=.14 * alzar_llave)
        elif nombre == 'lanzar_monedas':
            prepara = curva_puntos(u, [(0, 0), (.22, 1), (.34, .15), (.48, 0)])
            lanzar = curva_puntos(u, [(0, 0), (.23, 0), (.34, 1), (.46, .90), (.62, .43), (1, 0)])
            rotar_euler_mundo(rig, 'DEF-spine.002', yaw_z=.20 * lanzar, pitch_x=.10 * lanzar)
            rotar_euler_mundo(rig, 'DEF-head', yaw_z=.42 * lanzar, pitch_x=-.09 * lanzar)
            roll_capa = .028 * lanzar
        elif nombre == 'reir':
            ataque = curva_puntos(u, [(0, 0), (.19, 1), (.62, 1), (1, 0)])
            pulso = (.57 + .43 * math.sin(fase * 3)) * ataque
            rotar_euler_mundo(rig, 'DEF-spine.002', pitch_x=-.15 * pulso)
            rotar_euler_mundo(rig, 'DEF-spine.003', roll_y=.07 * ataque, pitch_x=-.09 * pulso)
            rotar_euler_mundo(rig, 'DEF-head', pitch_x=-.28 * pulso, yaw_z=.26 * ataque)

        bpy.context.view_layer.update()
        apoyar(rig, marcha)

        # La mano izquierda mantiene el agarre aunque el tronco gire.
        pecho = rig.pose.bones['DEF-spine.003']
        matriz = pecho.matrix @ pecho.bone.matrix_local.inverted()
        ik_dos_huesos(rig, 'DEF-upper_arm.L', 'DEF-forearm.L',
                      matriz @ s['DEF-hand.L'][0], matriz @ s['DEF-forearm.L'][0])
        fijar_rotacion_mundo_desde_reposo(rig, 'DEF-hand.L', matriz.to_quaternion())

        if alzar_llave or prepara or lanzar:
            mano = s['DEF-hand.R'][0].copy()
            mano += Vector((-.067, -.32, .38)) * alzar_llave
            mano += Vector((-.095, .055, .21)) * prepara
            mano += Vector((-.25, -.37, .32)) * lanzar
            codo = s['DEF-forearm.R'][0] + Vector((-.09, .04, .025)) * (alzar_llave + prepara + lanzar)
            ik_dos_huesos(rig, 'DEF-upper_arm.R', 'DEF-forearm.R', mano, codo)
            giro = Quaternion((0, 0, 1), -.24 * alzar_llave - .53 * lanzar)
            giro @= Quaternion((1, 0, 0), -.86 * alzar_llave - .36 * prepara - .98 * lanzar)
            fijar_rotacion_mundo_desde_reposo(rig, 'DEF-hand.R', giro)
            rotar_euler_mundo(rig, 'DEF-f_index.02.R', pitch_x=-.2 * lanzar)
            rotar_euler_mundo(rig, 'DEF-thumb.02.R', yaw_z=.16 * lanzar)

        # El cuello de la capa sigue el tronco. El bajo oscila poco para no
        # barrer la pierna, mientras la llave se mantiene colgando del aro.
        fijar_rotacion_mundo_desde_reposo(rig, 'capa_caida',
                                         orientacion_capa(matriz, roll_capa, fase, marcha))
        inclinacion = .075 * math.sin(fase - .4) if marcha else (.10 * alzar_llave + .22 * lanzar) * math.sin(fase * 1.5)
        fijar_rotacion_mundo_desde_reposo(rig, 'llave', Quaternion((1, 0, 0), inclinacion))

    return pose


def orientacion_capa(matriz, balanceo, fase, marcha):
    giro = matriz.to_quaternion() @ Quaternion((0, 1, 0), balanceo)
    if marcha:
        giro @= Quaternion((1, 0, 0), -.075 + .05 * math.cos(fase))
    return giro
