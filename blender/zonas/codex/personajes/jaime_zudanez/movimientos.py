"""Movimientos de Jaime sobre UAL y contacto de los dedos con la caja."""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

from kit_personaje import cuerpo_desde_ual, girar_cabeza
from kit_ual import curva_puntos, fijar_rotacion_mundo_desde_reposo, ik_dos_huesos, limpiar_pose, rotar_euler_mundo
from rig import coordenadas, metros


def base_palma(direccion, normal):
    longitudinal = Vector(direccion).normalized()
    transversal = Vector(normal).cross(longitudinal).normalized()
    return Matrix((longitudinal, transversal, longitudinal.cross(transversal))).transposed()


def construir_pose(ual, s, malla):
    suelas = {'R': [], 'L': []}
    for vertice, (x, _, z) in zip(malla.data.vertices, coordenadas(malla)):
        if z < .023:
            suelas['L' if x > -.055 else 'R'].append(vertice.co.copy())

    muneca, nudillos = s['DEF-hand.R']
    palma_reposo = base_palma(nudillos - muneca, (.85, -.39, -.11))
    giro_tap = (base_palma((.88, .42, -.12), (0, 0, -1)) @ palma_reposo.transposed()).to_quaternion()
    punta_indice = s['DEF-f_index.03.R'][1] - muneca
    punta_medio = s['DEF-f_middle.03.R'][1] - muneca
    tapa = metros((.077, -.082, .6308))

    def apoyar_zapatos(rig):
        planta = []
        for lado, puntos in suelas.items():
            pb = rig.pose.bones[f'DEF-foot.{lado}']
            deforma = pb.matrix @ pb.bone.matrix_local.inverted()
            planta.append(min((deforma @ p).z for p in puntos))
        cadera = rig.pose.bones['DEF-hips']
        corregir = Vector((0, 0, -min(planta)))
        cadera.location += cadera.bone.matrix_local.to_quaternion().inverted() @ corregir
        bpy.context.view_layer.update()

    def tamborilear(rig, u):
        acerca = curva_puntos(u, [(0, 0), (.12, .2), (.30, 1), (.71, 1), (.89, .3), (1, 0)])
        if acerca == 0:
            return
        caja = rig.pose.bones['caja_mantequilla']
        deforma = caja.matrix @ caja.bone.matrix_local.inverted()
        indice = curva_puntos(u, [(0, 0), (.31, 0), (.38, 1), (.43, 0), (.52, 0), (.58, 1), (.65, 0), (1, 0)])
        medio = curva_puntos(u, [(0, 0), (.42, 0), (.49, 1), (.54, 0), (.61, 0), (.67, .75), (.72, 0), (1, 0)])
        contacto = max(indice, medio)
        giro = deforma.to_quaternion() @ giro_tap
        giro_total = Quaternion().slerp(giro, acerca)
        dedo = punta_indice.lerp(punta_medio, medio * (1 - indice))
        objetivo = deforma @ (tapa + Vector((0, 0, .006 + .027 * (1 - contacto))))
        palma_objetivo = objetivo - giro @ dedo
        mano = rig.pose.bones['DEF-hand.R'].head.lerp(palma_objetivo, acerca)
        mano += Vector((-.032, -.24, .032)) * math.sin(math.pi * acerca)
        codo = s['DEF-forearm.R'][0] + Vector((-.10, -.24, .035)) * acerca
        ik_dos_huesos(rig, 'DEF-upper_arm.R', 'DEF-forearm.R', mano, codo)
        fijar_rotacion_mundo_desde_reposo(rig, 'DEF-hand.R', giro_total)
        rotar_euler_mundo(rig, 'DEF-f_index.02.R', pitch_x=-.13 * indice)
        rotar_euler_mundo(rig, 'DEF-f_middle.02.R', pitch_x=-.12 * medio)

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        en_marcha = nombre == 'caminar'
        if en_marcha:
            cuerpo_desde_ual(
                ual, rig, spec['ual'], u, {'cadera': .40, 'torso': .50, 'cabeza': .32},
                peso_piernas=.68, brazos=('DEF-upper_arm.R', 'DEF-forearm.R', 'DEF-hand.R'),
                peso_brazos=.34, alinear_brazos=False, pies_como_malla=True,
            )
        else:
            ual.aplicar_a_rig(
                rig, spec['ual'], u if spec['bucle'] else 0.,
                pesos_grupo={'cadera': .38, 'torso': .59, 'cabeza': .45, 'piernas': 0,
                             'brazo_der': .19 if nombre == 'hablar' else 0},
                cuerpo_relativo_f0=True,
            )
        apoyar_zapatos(rig)

        mirada = .47
        inclinacion = 0
        if nombre == 'negar':
            mirada += curva_puntos(u, [(0, 0), (.18, .33), (.36, -.38), (.54, .28), (.69, -.18), (1, 0)])
            inclinacion -= .043 * math.sin(math.tau * u)
        elif nombre == 'hablar':
            mirada += .12 * math.sin(math.tau * u)
        elif nombre == 'tamborilear_caja':
            atencion = curva_puntos(u, [(0, 0), (.23, .70), (.43, 1), (.69, .94), (1, 0)])
            mirada += .37 * atencion
            inclinacion += .20 * atencion
        girar_cabeza(rig, yaw=mirada, pitch=inclinacion)

        # La caja queda apoyada en la mano izquierda y acompaña el pecho.
        bpy.context.view_layer.update()
        pecho = rig.pose.bones['DEF-spine.003']
        matriz = pecho.matrix @ pecho.bone.matrix_local.inverted()
        ik_dos_huesos(rig, 'DEF-upper_arm.L', 'DEF-forearm.L',
                      matriz @ s['DEF-hand.L'][0], matriz @ s['DEF-forearm.L'][0])
        fijar_rotacion_mundo_desde_reposo(rig, 'DEF-hand.L', matriz.to_quaternion())
        if nombre == 'tamborilear_caja':
            tamborilear(rig, u)

        if en_marcha:
            for lado, faldon in [('R', 'faldon_der'), ('L', 'faldon_izq')]:
                muslo = rig.pose.bones[f'DEF-thigh.{lado}']
                giro = muslo.matrix.to_quaternion() @ muslo.bone.matrix_local.to_quaternion().inverted()
                fijar_rotacion_mundo_desde_reposo(rig, faldon, Quaternion().slerp(giro, .37))

    return pose
