"""Moxó de día (1807-1809): asomado al balcón del Arzobispado, mirando una concha con la lupa.

La malla tiene los dos antebrazos levantados delante del pecho (lupa en la derecha, concha en la izquierda) y la cabeza
inclinada hacia la concha. Esa es la pose de base de todos los clips: las manos solo dejan de sostener la lupa y la
concha para arrugar el pasquín y para bendecir.
"""
import math

import bpy
from mathutils import Vector

from kit_personaje import RAIZ, girar_cabeza, mover_mano, muneca, huesos_desde_ual
from kit_ual import limpiar_pose, rotar_euler_mundo, suave, curva_puntos
from comun import ALTURA_M, cuerpo_desde_ual
import anatomia_dia as anatomia

ID = 'moxo_dia'
H = ALTURA_M
ENTRADA = RAIZ / 'personas/moxo/moxo_dia.glb'
LAMINA = RAIZ / 'personas/moxo/diseno.png'
VISTA_PREVIA = '01_examinar.png'

# La cabeza de la malla mira la concha: abajo y hacia su izquierda. Para mirar al frente se levanta y se gira.
FRENTE = {'pitch': 0.30, 'yaw': 0.0}

CLIPS = [
    # --- propios (guía #24) ---
    {'id': 'examinar_lupa', 'nombre': 'Examinar con la lupa', 'propio': True, 'bucle': True,
     'duracion': 4.0, 'velocidad_m_s': 0.0,
     'descripcion': 'Acerca la lupa a la concha, gira la concha para verla por todos lados, se inclina y asiente '
                    'satisfecho: «tengo en el palacio un museo de los tres reinos».'},
    {'id': 'arrugar_papel', 'nombre': 'Arrugar el pasquín', 'propio': True, 'bucle': False,
     'duracion': 4.5, 'velocidad_m_s': 0.0,
     'descripcion': 'Baja las manos a la servilleta, encuentra un pasquín, lo mira, lo arruga con las dos manos, lo '
                    'tira a un lado sacudiendo la cabeza y vuelve a la concha.'},
    # --- comunes (guía §1.6) ---
    {'id': 'reposo', 'nombre': 'Reposo (UAL)', 'propio': False, 'bucle': True,
     'duracion': 2.5, 'velocidad_m_s': 0.0,
     'descripcion': 'De pie con la lupa y la concha; de vez en cuando levanta la vista.'},
    {'id': 'caminar', 'nombre': 'Caminar (UAL)', 'propio': False, 'bucle': True,
     'duracion': 1.333, 'velocidad_m_s': 0.9,
     'descripcion': 'Paso corto y pausado, con la lupa y la concha delante del pecho.'},
    {'id': 'hablar', 'nombre': 'Hablar (UAL)', 'propio': False, 'bucle': True,
     'duracion': 2.933, 'velocidad_m_s': 0.0,
     'descripcion': 'Habla con voz meliflua, gesticulando con la mano de la lupa.'},
    {'id': 'saludar', 'nombre': 'Bendecir', 'propio': False, 'bucle': False,
     'duracion': 2.4, 'velocidad_m_s': 0.0,
     'descripcion': 'Saludo de arzobispo: traza la señal de la cruz en el aire con la mano derecha.'},
    {'id': 'asentir', 'nombre': 'Asentir', 'propio': False, 'bucle': False,
     'duracion': 1.4, 'velocidad_m_s': 0.0,
     'descripcion': 'Dos cabeceos lentos.'},
    {'id': 'mirar_atras', 'nombre': 'Mirar atrás', 'propio': False, 'bucle': False,
     'duracion': 1.8, 'velocidad_m_s': 0.0,
     'descripcion': 'Gira la cabeza y el torso por encima del hombro derecho (¿quién mete los pasquines?).'},
    {'id': 'senalar', 'nombre': 'Señalar con la lupa', 'propio': False, 'bucle': False,
     'duracion': 2.2, 'velocidad_m_s': 0.0,
     'descripcion': 'Señala algo de la plaza con la lupa y vuelve a la concha.'},
]

LADO_R = ['DEF-shoulder.R', 'DEF-upper_arm.R', 'DEF-forearm.R', 'DEF-hand.R']


def m(*v):
    return Vector(v) * H


def construir_pose(ual):
    reposo_pesos = {'cadera': 0.6, 'torso': 0.6, 'cabeza': 0.0}

    def mirar(rig, frente=1.0, pitch=0.0, roll=0.0, yaw=0.0):
        """frente 1 = cara al frente; 0 = mirando la concha, como la malla. pitch > 0 levanta la vista (en el mundo,
        un giro positivo en X inclina la cabeza hacia adelante: de ahí el signo)."""
        girar_cabeza(rig, -(FRENTE['pitch'] * frente + pitch), roll, FRENTE['yaw'] * frente + yaw)

    def polo(rig, lado):
        """Codo hacia afuera y abajo."""
        bpy.context.view_layer.update()
        hombro = rig.pose.bones[f'DEF-upper_arm{lado}'].head
        return hombro + m(0.25 if lado == '.L' else -0.25, 0.05, -0.30)

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        fase = math.tau * u

        if nombre == 'examinar_lupa':
            cuerpo_desde_ual(anatomia, ual, rig, 'Idle_Loop', (2.0 * u) % 1.0, reposo_pesos)
            acerca = 0.5 - 0.5 * math.cos(fase)          # la lupa va y viene una vez por ciclo
            gira = math.sin(fase + 0.6)                     # la concha gira a un lado y al otro
            rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=-0.05 * acerca)
            mover_mano(rig, '.R', muneca(rig, '.R') + m(0.012, -0.006, 0.012) * acerca, polo(rig, '.R'))
            mover_mano(rig, '.L', muneca(rig, '.L') + m(-0.006, -0.004, 0.010) * (0.5 + 0.5 * gira), polo(rig, '.L'))
            rotar_euler_mundo(rig, 'DEF-hand.L', roll_y=0.25 * gira, yaw_z=0.20 * gira)
            asiente = max(0.0, math.sin(2.0 * fase)) ** 2 * suave((u - 0.45) / 0.1) * (1 - suave((u - 0.95) / 0.05))
            mirar(rig, 0.0, pitch=-0.05 * acerca - 0.08 * asiente, roll=0.04 * gira)

        elif nombre == 'arrugar_papel':
            cuerpo_desde_ual(anatomia, ual, rig, 'Idle_Loop', u, reposo_pesos)
            baja = curva_puntos(u, [(0.0, 0.0), (0.14, 1.0), (0.70, 1.0), (0.86, 0.0), (1.0, 0.0)])
            arruga = curva_puntos(u, [(0.0, 0.0), (0.30, 0.0), (0.36, 1.0), (0.56, 1.0), (0.60, 0.0), (1.0, 0.0)])
            tira = curva_puntos(u, [(0.0, 0.0), (0.58, 0.0), (0.64, 1.0), (0.70, 0.0), (1.0, 0.0)])
            centro = Vector(anatomia.segmentos()['DEF-hips'][0]) * H + m(0.0, -0.17, 0.11)
            cerca = 0.03 * arruga
            vibra = math.sin(math.tau * 6.0 * u) * arruga
            obj_r = centro + m(-0.045 + cerca, 0.0, 0.01 * vibra)
            obj_l = centro + m(0.045 - cerca, 0.0, -0.01 * vibra) + m(0.10, -0.06, -0.08) * tira
            mover_mano(rig, '.R', obj_r, polo(rig, '.R'), peso=baja, conservar_mano=False)
            mover_mano(rig, '.L', obj_l, polo(rig, '.L'), peso=baja, conservar_mano=False)
            rotar_euler_mundo(rig, 'DEF-hand.R', roll_y=0.35 * vibra)
            rotar_euler_mundo(rig, 'DEF-hand.L', roll_y=-0.35 * vibra, pitch_x=-0.6 * tira)
            rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=-0.08 * baja)
            niega = math.sin(math.tau * 2.0 * min(1.0, max(0.0, (u - 0.66) / 0.2))) * \
                curva_puntos(u, [(0.0, 0.0), (0.64, 0.0), (0.68, 1.0), (0.84, 1.0), (0.88, 0.0), (1.0, 0.0)])
            mirar(rig, 0.0, pitch=-0.12 * baja + 0.10 * tira, yaw=0.25 * niega + 0.25 * tira)

        elif nombre == 'reposo':
            cuerpo_desde_ual(anatomia, ual, rig, 'Idle_Loop', u, reposo_pesos)
            alza = curva_puntos(u, [(0.0, 0.0), (0.35, 0.0), (0.48, 0.8), (0.72, 0.8), (0.85, 0.0), (1.0, 0.0)])
            mirar(rig, alza, yaw=0.10 * alza * math.sin(fase))

        elif nombre == 'caminar':
            cuerpo_desde_ual(anatomia, ual, rig, 'Walk_Loop', u, {'cadera': 0.8, 'torso': 0.7, 'cabeza': 0.3},
                             peso_piernas=0.75)
            mirar(rig, 0.8)

        elif nombre == 'hablar':
            cuerpo_desde_ual(anatomia, ual, rig, 'Idle_Talking_Loop', u, {'cadera': 0.6, 'torso': 0.8, 'cabeza': 0.5})
            huesos_desde_ual(ual, rig, 'Idle_Talking_Loop', u, LADO_R, 0.7, referencia='Idle_Talking_Loop')
            mirar(rig, 1.0)

        elif nombre == 'saludar':
            cuerpo_desde_ual(anatomia, ual, rig, 'Idle_Loop', u, reposo_pesos)
            env = suave(u / 0.2) * (1.0 - suave((u - 0.8) / 0.2))
            # Señal de la cruz: de arriba abajo y de izquierda a derecha, delante de la cara
            k = min(1.0, max(0.0, (u - 0.2) / 0.6))
            vert = curva_puntos(k, [(0.0, 0.0), (0.12, 1.0), (0.38, -1.0), (0.5, 0.0), (1.0, 0.0)])
            horiz = curva_puntos(k, [(0.0, 0.0), (0.5, 0.0), (0.62, -1.0), (0.88, 1.0), (1.0, 0.0)])
            hombro = rig.pose.bones['DEF-upper_arm.R'].head.copy()
            obj = hombro + m(0.07 + 0.06 * horiz, -0.36, 0.05 + 0.07 * vert)
            mover_mano(rig, '.R', obj, polo(rig, '.R'), peso=env, conservar_mano=False)
            mirar(rig, 1.0, pitch=0.03 * env)

        elif nombre == 'asentir':
            cuerpo_desde_ual(anatomia, ual, rig, 'Idle_Loop', u, reposo_pesos)
            env = suave(u / 0.2) * (1.0 - suave((u - 0.8) / 0.2))
            cab = math.sin(math.tau * 2.0 * min(1.0, max(0.0, (u - 0.1) / 0.8)))
            mirar(rig, env, pitch=-0.18 * max(0.0, cab) * env)

        elif nombre == 'mirar_atras':
            cuerpo_desde_ual(anatomia, ual, rig, 'Idle_Loop', u, reposo_pesos)
            g = curva_puntos(u, [(0.0, 0.0), (0.3, 1.0), (0.7, 1.0), (1.0, 0.0)])
            rotar_euler_mundo(rig, 'DEF-spine.002', yaw_z=-0.20 * g)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=-0.25 * g)
            mirar(rig, g, yaw=-0.95 * g)

        elif nombre == 'senalar':
            cuerpo_desde_ual(anatomia, ual, rig, 'Idle_Loop', u, reposo_pesos)
            env = suave(u / 0.25) * (1.0 - suave((u - 0.75) / 0.25))
            hombro = rig.pose.bones['DEF-upper_arm.R'].head.copy()
            mover_mano(rig, '.R', hombro + m(-0.10, -0.36, -0.02), polo(rig, '.R'), peso=env, conservar_mano=False)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=-0.08 * env)
            mirar(rig, env, yaw=-0.15 * env)

        bpy.context.view_layer.update()

    return pose


TOMAS = [
    ('01_examinar', 'examinar_lupa', 0.5, 'tres_cuartos'),
    ('02_examinar_b', 'examinar_lupa', 0.0, 'frente'),
    ('03_arrugar_baja', 'arrugar_papel', 0.25, 'frente'),
    ('04_arrugar', 'arrugar_papel', 0.45, 'tres_cuartos'),
    ('05_arrugar_tira', 'arrugar_papel', 0.64, 'frente'),
    ('06_reposo', 'reposo', 0.6, 'frente'),
    ('07_caminar', 'caminar', 0.25, 'lado'),
    ('08_hablar', 'hablar', 0.4, 'tres_cuartos'),
    ('09_bendecir', 'saludar', 0.35, 'frente'),
    ('10_mirar_atras', 'mirar_atras', 0.5, 'tres_cuartos'),
    ('11_senalar', 'senalar', 0.5, 'tres_cuartos'),
    ('12_espalda', 'caminar', 0.5, 'espalda'),
]
CAMARAS = {
    'frente': ((0.06, -4.0, 1.0), (0.06, 0.0, 0.78)),
    'lado': ((3.9, -0.3, 0.95), (0.06, 0.0, 0.75)),
    'tres_cuartos': ((-2.6, -2.9, 1.1), (0.06, 0.0, 0.75)),
    'espalda': ((0.06, 4.0, 1.0), (0.06, 0.0, 0.78)),
}

FICHA = {
    'id': ID,
    'nombre': 'Benito María de Moxó (de día)',
    'subtitulo': '«Poco le falta para que vivamos en una perfecta anarquía» · 1807-1809 (Guía #24 · R-0722-1)',
    'altura_m': ALTURA_M,
    'esqueleto': 'Universal Animation Library (53 huesos · GeneralSkeleton); sotana con vuelo por pierna, capa de '
                 'los hombros',
    'arquetipo': 'C · balcón del Palacio Arzobispal (día); de noche, ver moxo_noche',
    'clip_inicial': 'examinar_lupa',
    'clips': CLIPS,
}
