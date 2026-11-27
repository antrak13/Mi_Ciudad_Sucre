"""Lectura, saludo y paso corto, con ambas manos apoyadas en el libro."""
import math

import bpy
from mathutils import Quaternion, Vector

from kit_personaje import cuerpo_desde_ual, girar_cabeza
from kit_ual import curva_puntos, fijar_rotacion_mundo_desde_reposo, ik_dos_huesos, limpiar_pose
from rig import coordenadas


def construir_pose(ual, s, malla):
    suelas = {'R': [], 'L': []}
    for vertice, (x, y, z) in zip(malla.data.vertices, coordenadas(malla)):
        if z < .018 and y < .111:
            suelas['L' if x > 0 else 'R'].append(vertice.co.copy())

    def apoyar(rig):
        alturas = []
        for lado, puntos in suelas.items():
            pie = rig.pose.bones[f'DEF-foot.{lado}']
            deforma = pie.matrix @ pie.bone.matrix_local.inverted()
            alturas.append(min((deforma @ p).z for p in puntos))
        cadera = rig.pose.bones['DEF-hips']
        cadera.location += cadera.bone.matrix_local.to_quaternion().inverted() @ Vector((0, 0, -min(alturas)))
        bpy.context.view_layer.update()

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        marcha = nombre == 'caminar'
        if marcha:
            cuerpo_desde_ual(
                ual, rig, spec['ual'], u, {'cadera': .36, 'torso': .42, 'cabeza': .34},
                peso_piernas=.54, pies_como_malla=True,
            )
        else:
            ual.aplicar_a_rig(
                rig, spec['ual'], u if spec['bucle'] else 0.,
                pesos_grupo={'cadera': .32, 'torso': .57, 'cabeza': .41, 'piernas': 0},
                cuerpo_relativo_f0=True,
            )
        apoyar(rig)

        fase = u * math.tau
        pitch, yaw, roll = .23, -.10, 0.
        inclina_libro, balancea_libro = -.015, 0.
        if marcha:
            pitch = .03
            balancea_libro = .032 * math.sin(fase)
            inclina_libro -= .023 * math.cos(fase)
        elif nombre == 'leer_libro':
            atencion = curva_puntos(u, [(0, 0), (.23, 1), (.78, 1), (1, 0)])
            lectura = math.sin(fase + .4) * atencion
            pitch += .26 * atencion + .042 * lectura
            yaw += .21 * lectura
            roll += .048 * lectura
            inclina_libro += .067 * atencion
            balancea_libro = -.033 * lectura
        elif nombre == 'saludar':
            mirada = curva_puntos(u, [(0, 0), (.20, 1), (.73, 1), (1, 0)])
            venia = curva_puntos(u, [(0, 0), (.27, 0), (.48, 1), (.66, 0), (1, 0)])
            pitch += -.37 * mirada + .27 * venia
            yaw -= .16 * mirada
            inclina_libro -= .068 * mirada
        elif nombre == 'hablar':
            acento = math.sin(fase)
            pitch = -.04 + .08 * acento
            yaw += .092 * math.cos(fase)
            inclina_libro -= .04 + .026 * acento
            balancea_libro = .025 * math.cos(fase)

        girar_cabeza(rig, pitch=pitch, yaw=yaw, roll=roll)
        bpy.context.view_layer.update()
        torso = rig.pose.bones['DEF-spine.003']
        pecho = torso.matrix @ torso.bone.matrix_local.inverted()
        giro = pecho.to_quaternion() @ Quaternion((1, 0, 0), inclina_libro)
        giro @= Quaternion((0, 1, 0), balancea_libro)
        fijar_rotacion_mundo_desde_reposo(rig, 'libro', giro)
        bpy.context.view_layer.update()
        libro = rig.pose.bones['libro']
        sostener = libro.matrix @ libro.bone.matrix_local.inverted()
        for lado in ('L', 'R'):
            antebrazo = f'DEF-forearm.{lado}'
            mano = f'DEF-hand.{lado}'
            ik_dos_huesos(rig, f'DEF-upper_arm.{lado}', antebrazo,
                          sostener @ s[mano][0], pecho @ s[antebrazo][0])
            fijar_rotacion_mundo_desde_reposo(rig, mano, giro)

        if marcha:
            for lado, prenda in [('L', 'habito_izq'), ('R', 'habito_der')]:
                muslo = rig.pose.bones[f'DEF-thigh.{lado}']
                delta = muslo.matrix.to_quaternion() @ muslo.bone.matrix_local.to_quaternion().inverted()
                fijar_rotacion_mundo_desde_reposo(rig, prenda, Quaternion().slerp(delta, .37))

    return pose
