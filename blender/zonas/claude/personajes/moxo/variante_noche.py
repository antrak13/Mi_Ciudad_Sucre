"""Moxó de noche (25 de mayo de 1809): huye a pie con dos clérigos hacia la salida de la ciudad, mirando atrás.

La malla está a medio paso, con la mano derecha apretando la capa contra el pecho y el brazo izquierdo caído. La mano
derecha no se anima en ningún clip (sujeta la capa); las piernas y el brazo izquierdo se enderezan hacia la UAL.
"""
import math

import bpy
from mathutils import Vector

from kit_personaje import RAIZ, girar_cabeza, mover_mano
from kit_ual import limpiar_pose, rotar_euler_mundo, suave, curva_puntos
from comun import ALTURA_M, cuerpo_desde_ual
import anatomia_noche as anatomia

ID = 'moxo_noche'
H = ALTURA_M
ENTRADA = RAIZ / 'personas/moxo/moxo_noche.glb'
LAMINA = RAIZ / 'personas/moxo/diseno_noche.png'
VISTA_PREVIA = '01_huir.png'

CLIPS = [
    # --- propio (mecánica de la guía #24: «camina con dos clérigos hacia la salida, mirando atrás») ---
    {'id': 'huir_mirando_atras', 'nombre': 'Huir mirando atrás', 'propio': True, 'bucle': True,
     'duracion': 2.667, 'velocidad_m_s': 1.3,
     'descripcion': 'Paso apurado, encogido bajo la capa, con la mano en el pecho; a mitad del ciclo gira la cabeza '
                    'por encima del hombro izquierdo para ver si lo siguen.'},
    # --- comunes (guía §1.6) ---
    {'id': 'reposo', 'nombre': 'Esperar nervioso', 'propio': False, 'bucle': True,
     'duracion': 3.0, 'velocidad_m_s': 0.0,
     'descripcion': 'Espera en la loma hasta las tres de la mañana: aprieta la capa y mira a un lado y al otro.'},
    {'id': 'caminar', 'nombre': 'Caminar (UAL)', 'propio': False, 'bucle': True,
     'duracion': 1.333, 'velocidad_m_s': 1.0,
     'descripcion': 'Paso corto, con la capa apretada contra el pecho.'},
    {'id': 'caminar_rapido', 'nombre': 'Paso apurado (UAL)', 'propio': False, 'bucle': True,
     'duracion': 1.333, 'velocidad_m_s': 1.4,
     'descripcion': 'Paso largo, inclinado hacia adelante.'},
    {'id': 'mirar_atras', 'nombre': 'Mirar atrás', 'propio': False, 'bucle': False,
     'duracion': 1.8, 'velocidad_m_s': 0.0,
     'descripcion': 'Se detiene y mira por encima del hombro izquierdo, asustado.'},
    {'id': 'hablar', 'nombre': 'Hablar (UAL)', 'propio': False, 'bucle': True,
     'duracion': 2.933, 'velocidad_m_s': 0.0,
     'descripcion': '«Dejaré la mitra si se retiran»: habla gesticulando con la mano izquierda.'},
    {'id': 'llamar_mano', 'nombre': 'Llamar a los clérigos', 'propio': False, 'bucle': False,
     'duracion': 2.0, 'velocidad_m_s': 0.0,
     'descripcion': 'Con la mano izquierda llama a los dos clérigos para que lo sigan.'},
    {'id': 'asentir', 'nombre': 'Asentir', 'propio': False, 'bucle': False,
     'duracion': 1.4, 'velocidad_m_s': 0.0,
     'descripcion': 'Dos cabeceos rápidos.'},
]

LADO_L = ['DEF-shoulder.L', 'DEF-upper_arm.L', 'DEF-forearm.L', 'DEF-hand.L']


def m(*v):
    return Vector(v) * H


def construir_pose(ual):
    reposo_pesos = {'cadera': 0.6, 'torso': 0.7, 'cabeza': 0.2}

    def mirar(rig, pitch=0.0, roll=0.0, yaw=0.0):
        """pitch > 0 levanta la vista (en el mundo, un giro positivo en X inclina la cabeza hacia adelante)."""
        girar_cabeza(rig, -pitch, roll, yaw)

    def base(rig, clip, u, pesos, peso_piernas=1.0, peso_brazo=1.0):
        cuerpo_desde_ual(anatomia, ual, rig, clip, u, pesos, peso_piernas, brazos=LADO_L, peso_brazos=peso_brazo)

    def polo_izq(rig):
        bpy.context.view_layer.update()
        return rig.pose.bones['DEF-upper_arm.L'].head + m(0.25, 0.10, -0.25)

    def encogido(rig, k):
        """Hombros encogidos bajo la capa."""
        rotar_euler_mundo(rig, 'DEF-spine.001', pitch_x=0.06 * k)
        rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=0.04 * k)

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        fase = math.tau * u

        if nombre == 'huir_mirando_atras':
            base(rig, 'Walk_Formal_Loop', (2.0 * u) % 1.0, {'cadera': 1.0, 'torso': 0.7, 'cabeza': 0.2},
                 peso_piernas=0.9, peso_brazo=0.8)
            encogido(rig, 1.0)
            atras = curva_puntos(u, [(0.0, 0.0), (0.35, 0.0), (0.47, 1.0), (0.63, 1.0), (0.75, 0.0), (1.0, 0.0)])
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=0.25 * atras)
            mirar(rig, pitch=-0.06 * (1 - atras), yaw=1.05 * atras, roll=0.06 * atras)

        elif nombre == 'reposo':
            base(rig, 'Idle_Loop', (2.0 * u) % 1.0, reposo_pesos)
            encogido(rig, 0.6)
            busca = math.sin(fase) * 0.8 + 0.2 * math.sin(3.0 * fase)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=0.10 * busca)
            mirar(rig, pitch=0.03 * math.sin(2.0 * fase), yaw=0.65 * busca)

        elif nombre in ('caminar', 'caminar_rapido'):
            clip = 'Walk_Loop' if nombre == 'caminar' else 'Walk_Formal_Loop'
            base(rig, clip, u, {'cadera': 0.9, 'torso': 0.8, 'cabeza': 0.3}, peso_piernas=0.85)
            encogido(rig, 0.5 if nombre == 'caminar' else 1.0)
            mirar(rig, pitch=-0.03)

        elif nombre == 'mirar_atras':
            base(rig, 'Idle_Loop', u, reposo_pesos)
            g = curva_puntos(u, [(0.0, 0.0), (0.3, 1.0), (0.7, 1.0), (1.0, 0.0)])
            rotar_euler_mundo(rig, 'DEF-spine.002', yaw_z=0.22 * g)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=0.28 * g)
            encogido(rig, 0.6 * g)
            mirar(rig, yaw=1.0 * g, pitch=0.04 * g)

        elif nombre == 'hablar':
            base(rig, 'Idle_Talking_Loop', u, {'cadera': 0.7, 'torso': 0.85, 'cabeza': 0.6})
            mirar(rig)

        elif nombre == 'llamar_mano':
            base(rig, 'Idle_Loop', u, reposo_pesos)
            env = suave(u / 0.22) * (1.0 - suave((u - 0.8) / 0.2))
            recoge = max(0.0, math.sin(math.tau * 2.0 * min(1.0, max(0.0, (u - 0.2) / 0.6))))
            hombro = rig.pose.bones['DEF-upper_arm.L'].head.copy()
            obj = hombro + m(0.12, 0.05 - 0.10 * recoge, -0.12 + 0.05 * recoge)
            mover_mano(rig, '.L', obj, polo_izq(rig), peso=env, conservar_mano=False)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=0.15 * env)
            mirar(rig, yaw=0.60 * env, pitch=0.02)

        elif nombre == 'asentir':
            base(rig, 'Idle_Loop', u, reposo_pesos)
            env = suave(u / 0.2) * (1.0 - suave((u - 0.8) / 0.2))
            cab = math.sin(math.tau * 2.0 * min(1.0, max(0.0, (u - 0.1) / 0.8)))
            mirar(rig, pitch=-0.18 * max(0.0, cab) * env)

        bpy.context.view_layer.update()

    return pose


TOMAS = [
    ('01_huir', 'huir_mirando_atras', 0.12, 'tres_cuartos'),
    ('02_huir_atras', 'huir_mirando_atras', 0.55, 'tres_cuartos'),
    ('03_huir_lado', 'huir_mirando_atras', 0.25, 'lado'),
    ('04_reposo', 'reposo', 0.25, 'frente'),
    ('05_caminar', 'caminar', 0.25, 'lado'),
    ('06_rapido', 'caminar_rapido', 0.5, 'tres_cuartos'),
    ('07_rapido_lado', 'caminar_rapido', 0.25, 'lado'),
    ('08_mirar_atras', 'mirar_atras', 0.5, 'tres_cuartos'),
    ('09_hablar', 'hablar', 0.4, 'frente'),
    ('10_llamar', 'llamar_mano', 0.35, 'tres_cuartos'),
    ('11_espalda', 'caminar', 0.5, 'espalda'),
    ('12_reposo_b', 'reposo', 0.75, 'tres_cuartos'),
]
CAMARAS = {
    'frente': ((0.05, -4.0, 1.0), (0.05, 0.0, 0.78)),
    'lado': ((3.9, -0.3, 0.95), (0.05, 0.0, 0.75)),
    'tres_cuartos': ((-2.6, -2.9, 1.1), (0.05, 0.0, 0.75)),
    'espalda': ((0.05, 4.0, 1.0), (0.05, 0.0, 0.78)),
}

FICHA = {
    'id': ID,
    'nombre': 'Benito María de Moxó (de noche)',
    'subtitulo': 'La huida del 25 de mayo de 1809: «esperó en la loma hasta las tres de la mañana y huyó a pie» '
                 '(Guía #24)',
    'altura_m': ALTURA_M,
    'esqueleto': 'Universal Animation Library (53 huesos · GeneralSkeleton); sotana con vuelo por pierna, capa de '
                 'los hombros',
    'arquetipo': 'B y E · la noche del 25 (época 1809): de la plaza a la plazuela de San Agustín y la salida',
    'clip_inicial': 'huir_mirando_atras',
    'clips': CLIPS,
}
