"""Retarget UAL, apoyo de pies y gesto propio del incensario."""
import math

from mathutils import Quaternion, Vector

from kit_ual import (
    apuntar_hueso, aplicar_delta_mundo, curva_puntos, fijar_rotacion_mundo_desde_reposo, ik_dos_huesos,
    limpiar_pose, rotar_euler_mundo,
)


def construir_pose(ual, s):
    pista_caminata = 'Walk_Formal_Loop'

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        pasos = spec['ual'] == pista_caminata
        gesto = spec.get('propio') or nombre == 'asentir'
        tiempo_ual = 0 if gesto else u
        ual.aplicar_a_rig(
            rig, spec['ual'], tiempo_ual,
            pesos_grupo={
                'cadera': .57 if pasos else .45,
                'torso': .62 if pasos else .68,
                'cabeza': .48 if pasos else .57,
                'piernas': 0,
                'brazo_izq': 0,
                'brazo_der': 0,
            },
            piernas_relativas_f0=True,
        )
        rotar_euler_mundo(rig, 'DEF-head', yaw_z=.35)
        cadera = rig.pose.bones['DEF-hips']
        q_cadera = cadera.bone.matrix_local.to_quaternion()
        cadera.location += q_cadera.inverted() @ Vector((0, 0, -.035 if pasos else -.012))

        for lado in ('R', 'L'):
            muslo, pierna, pie, dedo = [f'DEF-{h}.{lado}' for h in ('thigh', 'shin', 'foot', 'toe')]
            tobillo = s[pie][0].copy()
            inclinacion = 0.
            if pasos:
                fuente = ual.rig.matrix_world @ ual.rig.pose.bones[pie].head
                punta = ual.rig.matrix_world @ ual.rig.pose.bones[dedo].head
                tobillo.y += (fuente.y - .075) * .53
                tobillo.z += max(0., fuente.z - .104) * .40
                angulo = math.atan2(punta.z - fuente.z, abs(punta.y - fuente.y))
                # El giro se apaga cerca del suelo. La suela mantiene su apoyo real.
                inclinacion = .23 * (angulo + .52) * min(1., (tobillo.z - s[pie][0].z) / .035)
            ik_dos_huesos(rig, muslo, pierna, tobillo, s[pierna][0] + Vector((0, -.5, 0)))
            fijar_rotacion_mundo_desde_reposo(rig, pie, Quaternion((1, 0, 0), inclinacion))

        pecho = rig.pose.bones['DEF-spine.002']
        anclaje = pecho.matrix @ pecho.bone.matrix_local.inverted()
        ik_dos_huesos(rig, 'DEF-upper_arm.L', 'DEF-forearm.L',
                      anclaje @ s['DEF-hand.L'][0], anclaje @ s['DEF-forearm.L'][0])
        fijar_rotacion_mundo_desde_reposo(rig, 'DEF-hand.L', anclaje.to_quaternion())

        fase = u * math.tau
        pendulo, lateral = .026 * math.sin(fase), .022 * math.sin(fase)
        if pasos:
            rotar_euler_mundo(rig, 'DEF-forearm.R', pitch_x=.065 * math.sin(fase))
            pendulo = .19 * math.sin(fase * 2 - .65)
            lateral = .075 * math.sin(fase + .8)
        elif nombre == 'hablar':
            # El brazo que sostiene el incensario toma solo una parte del gesto
            # de UAL. La otra mano permanece apoyada sobre el pecho.
            muestra = ual.rig.matrix_world @ ual.rig.pose.bones['DEF-forearm.R'].matrix
            neutra = ual.referencia_frame0(spec['ual'])[0]['DEF-forearm.R']
            delta = muestra.to_quaternion() @ neutra.inverted()
            aplicar_delta_mundo(rig, 'DEF-forearm.R', Quaternion().slerp(delta, .15))
            pendulo = .058 * math.sin(fase * 2 - .6)
        elif nombre == 'incensar':
            prepara = curva_puntos(u, [(0, 0), (.18, 1), (.71, 1), (.98, 0)])
            golpe = curva_puntos(u, [(0, 0), (.23, 0), (.33, 1), (.43, 0),
                                     (.47, 0), (.57, .82), (.67, 0), (1, 0)])
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=-.12 * prepara)
            rotar_euler_mundo(rig, 'DEF-head', pitch_x=.08 * prepara, yaw_z=.13 * prepara)
            muneca = s['DEF-hand.R'][0] + Vector((-.030 * prepara, -.105 * prepara - .040 * golpe,
                                                   .066 * prepara + .034 * golpe))
            # La trayectoria parte de la mano animada en reposo para enlazar sin salto.
            if prepara > 0:
                mano = rig.pose.bones['DEF-hand.R']
                destino = mano.head.lerp(muneca, prepara)
                direccion = (mano.tail - mano.head).lerp(s['DEF-hand.R'][1] - s['DEF-hand.R'][0], prepara)
                codo = rig.pose.bones['DEF-forearm.R'].head + prepara * Vector((-.025, -.03, -.025))
                ik_dos_huesos(rig, 'DEF-upper_arm.R', 'DEF-forearm.R', destino, codo)
                apuntar_hueso(rig, 'DEF-hand.R', destino + direccion, -.10 * prepara)
            pendulo = curva_puntos(u, [(0, 0), (.24, -.12), (.36, -.56), (.45, .21),
                                      (.49, -.08), (.60, -.47), (.70, .22), (.80, -.13),
                                      (.88, .055), (.97, 0)])
            lateral = .09 * prepara
        elif nombre == 'asentir':
            inclinacion = curva_puntos(u, [(0, 0), (.24, 1), (.48, .82), (.72, .10), (1, 0)])
            rotar_euler_mundo(rig, 'DEF-neck', pitch_x=.06 * inclinacion)
            rotar_euler_mundo(rig, 'DEF-head', pitch_x=.17 * inclinacion)
            pendulo = lateral = 0

        # La cadena conserva su longitud. Su pivote sigue el puño, pero el
        # ángulo de oscilación se calcula en mundo para respetar la gravedad.
        giro = Quaternion((0, 1, 0), lateral) @ Quaternion((1, 0, 0), pendulo)
        fijar_rotacion_mundo_desde_reposo(rig, 'incensario', giro)

    return pose
