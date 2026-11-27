"""Rig y animaciones de Mariana Zudáñez (Guía #3, 25 de mayo de 1809, arquetipo B «Sígueme»).

Parte del modelo estático de Tripo (`personas/mariana_zudanez/mariana_zudanes.glb`): no se modela nada de cero.
Esqueleto: los 53 huesos de la Universal Animation Library. La malla está en la pose de la lámina (brazo izquierdo
señalando, cabeza girada, pies en paso): para caminar y correr, piernas y brazo se enderezan hacia la pose de la UAL
(`alinear`) antes de aplicar el clip. El brazo derecho no se anima: aprieta el mantón contra el pecho en todos los
clips, como en la lámina.

Uso (un solo Blender pesado a la vez; ~1,1 GB de memoria):
    ~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/mariana_zudanez/construir.py
    ... -- --prueba [clip…]   solo renders de control (sin hornear ni exportar)
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE), str(BASE.parent)]

import kit_personaje as kp  # noqa: E402
from kit_personaje import RAIZ, cuerpo_desde_ual, girar_cabeza  # noqa: E402
from kit_ual import (  # noqa: E402
    BibliotecaUAL, crear_armadura_ual, limpiar_pose, rotar_euler_mundo, apuntar_hueso, ik_dos_huesos,
    hornear_clips, suave, curva_puntos,
)
import anatomia  # noqa: E402

ARGS = kp.argumentos()
ID = 'mariana_zudanez'
ALTURA_M = 1.62
H = ALTURA_M

ENTRADA = RAIZ / 'personas/mariana_zudanez/mariana_zudanes.glb'
LAMINA = RAIZ / 'personas/mariana_zudanez/diseno.png'
MALLA_30K = kp.SCRATCH / 'mariana_30k.glb'
SALIDA = RAIZ / f'web/public/models/ciudad/claude/personajes/{ID}'
REV = RAIZ / f'revisiones/claude/{ID}'

CLIPS = [
    # --- propios (guía #3) ---
    {'id': 'reposo_inquieta', 'nombre': 'Esperar angustiada', 'propio': True, 'bucle': True,
     'duracion': 4.0, 'velocidad_m_s': 0.0,
     'descripcion': 'En el hito 0, sin poder quedarse quieta: busca con la mirada a un lado y al otro, se lleva la '
                    'mano al pecho junto al mantón y cambia el peso de pie.'},
    {'id': 'correr_falda', 'nombre': 'Correr con la falda larga', 'propio': True, 'bucle': True,
     'duracion': 0.933, 'velocidad_m_s': 2.2,
     'descripcion': 'Carrera hacia el portón de la Audiencia, inclinada hacia adelante, con la mano derecha '
                    'sujetando el mantón y el ruedo de la falda siguiendo a cada pierna.'},
    {'id': 'gritar_brazo_alto', 'nombre': 'Gritar con el brazo en alto', 'propio': True, 'bucle': False,
     'duracion': 2.6, 'velocidad_m_s': 0.0,
     'descripcion': '«¡Paisanos, defiendan a mi hermano!»: alza el brazo izquierdo, lo sacude dos veces y echa la '
                    'cabeza atrás al gritar.'},
    # --- comunes (guía §1.6) ---
    {'id': 'reposo', 'nombre': 'Reposo (UAL)', 'propio': False, 'bucle': True,
     'duracion': 2.5, 'velocidad_m_s': 0.0,
     'descripcion': 'De pie, el brazo izquierdo caído y la mano derecha en el mantón.'},
    {'id': 'caminar', 'nombre': 'Caminar (UAL)', 'propio': False, 'bucle': True,
     'duracion': 1.333, 'velocidad_m_s': 1.1,
     'descripcion': 'Paso normal en el sitio.'},
    {'id': 'caminar_rapido', 'nombre': 'Paso apurado (UAL)', 'propio': False, 'bucle': True,
     'duracion': 1.333, 'velocidad_m_s': 1.5,
     'descripcion': 'Paso largo y decidido en el sitio.'},
    {'id': 'senalar', 'nombre': 'Señalar el portón', 'propio': False, 'bucle': False,
     'duracion': 2.4, 'velocidad_m_s': 0.0,
     'descripcion': 'La pose de la lámina: extiende el brazo izquierdo hacia el portón, con la mirada en él, y '
                    'remarca el gesto dos veces.'},
    {'id': 'mirar_atras', 'nombre': 'Mirar atrás (¿la sigue?)', 'propio': False, 'bucle': False,
     'duracion': 1.8, 'velocidad_m_s': 0.0,
     'descripcion': 'Gira el torso y la cabeza por encima del hombro izquierdo para ver si el jugador la sigue.'},
    {'id': 'hablar', 'nombre': 'Hablar (UAL)', 'propio': False, 'bucle': True,
     'duracion': 2.933, 'velocidad_m_s': 0.0,
     'descripcion': 'Cuenta el arresto gesticulando con la mano izquierda.'},
    {'id': 'llamar_mano', 'nombre': '«¡Sígame, por favor!»', 'propio': False, 'bucle': False,
     'duracion': 2.0, 'velocidad_m_s': 0.0,
     'descripcion': 'Tiende la mano izquierda hacia el jugador y la recoge dos veces, llamándolo.'},
    {'id': 'asentir', 'nombre': 'Asentir', 'propio': False, 'bucle': False,
     'duracion': 1.4, 'velocidad_m_s': 0.0,
     'descripcion': 'Dos cabeceos firmes.'},
]

LADO_L = ['DEF-shoulder.L', 'DEF-upper_arm.L', 'DEF-forearm.L', 'DEF-hand.L']
SIN_PIERNAS = {'piernas': 0.0}


def m(*v):
    return Vector(v) * H


def construir_pose(ual):

    def mirar(rig, factor=1.0, pitch=0.0, roll=0.0, yaw=0.0):
        """factor 1 = al frente; 0 = como en la lámina (mirando lo que señala, a su izquierda)."""
        girar_cabeza(rig, pitch, roll, -anatomia.GIRO_CABEZA_REPOSO * factor + yaw, cuello=0.45)

    def base(rig, clip, u, pesos, peso_piernas=1.0, peso_brazo=1.0):
        """Cadera y torso de la UAL; piernas y brazo izquierdo enderezados hacia la UAL y luego animados."""
        cuerpo_desde_ual(ual, rig, clip, u, pesos, peso_piernas, brazos=LADO_L, peso_brazos=peso_brazo)

    def mano_izq(rig, objetivo, apuntar=None):
        bpy.context.view_layer.update()
        hombro = rig.pose.bones['DEF-upper_arm.L'].head
        ik_dos_huesos(rig, 'DEF-upper_arm.L', 'DEF-forearm.L', objetivo, hombro + m(0.10, 0.20, -0.25))
        if apuntar is not None:
            apuntar_hueso(rig, 'DEF-hand.L', apuntar)

    def hombro_izq(rig):
        bpy.context.view_layer.update()
        return rig.pose.bones['DEF-upper_arm.L'].head.copy()

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        fase = math.tau * u
        reposo_pesos = {'cadera': 0.7, 'torso': 0.8, 'cabeza': 0.3}

        if nombre == 'reposo_inquieta':
            base(rig, 'Idle_Loop', (u * 2.0) % 1.0, reposo_pesos)
            # La mano izquierda sube al pecho (junto al puño del mantón) y vuelve a caer, dos veces por ciclo
            pecho = curva_puntos(u, [(0.0, 0.0), (0.12, 1.0), (0.38, 1.0), (0.50, 0.0), (0.62, 0.0), (0.74, 1.0),
                                     (0.90, 1.0), (1.0, 0.0)])
            if pecho > 1e-3:
                hombro = hombro_izq(rig)
                caida = rig.pose.bones['DEF-hand.L'].head.copy()
                obj = caida.lerp(hombro + m(-0.06, -0.10, -0.11), pecho)
                mano_izq(rig, obj, obj + m(-0.06, -0.02, 0.02) * pecho + m(0.0, 0.0, -0.06) * (1 - pecho))
            busca = math.sin(fase) * 0.75 + 0.25 * math.sin(3.0 * fase)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=0.12 * busca)
            mirar(rig, 1.0, pitch=0.04 + 0.04 * math.sin(2.0 * fase), yaw=0.70 * busca, roll=-0.05 * busca)
            # Se pone de puntillas un instante al buscar
            pb = rig.pose.bones['DEF-hips']
            pb.location = pb.location + rig.data.bones['DEF-hips'].matrix_local.to_quaternion().inverted() @ \
                Vector((0.0, 0.0, 0.012 * H * max(0.0, math.sin(2.0 * fase))))

        elif nombre == 'correr_falda':
            base(rig, 'Jog_Fwd_Loop', u, {'cadera': 1.0, 'torso': 0.7, 'cabeza': 0.3}, peso_piernas=0.7)
            rotar_euler_mundo(rig, 'DEF-spine.001', pitch_x=-0.10)
            rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=-0.04)
            mirar(rig, 1.0, pitch=0.10, roll=0.03 * math.sin(fase))

        elif nombre == 'gritar_brazo_alto':
            base(rig, 'Idle_Loop', u, reposo_pesos)
            env = suave(u / 0.22) * (1.0 - suave((u - 0.82) / 0.18))
            sacude = math.sin(math.tau * 2.0 * min(1.0, max(0.0, (u - 0.25) / 0.5)))
            grito = curva_puntos(u, [(0.0, 0.0), (0.25, 0.3), (0.35, 1.0), (0.70, 1.0), (0.85, 0.0), (1.0, 0.0)])
            rotar_euler_mundo(rig, 'DEF-spine.002', pitch_x=0.06 * grito)
            rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=0.06 * grito, roll_y=0.05 * env)
            hombro = hombro_izq(rig)
            caida = rig.pose.bones['DEF-hand.L'].head.copy()
            obj = caida.lerp(hombro + m(0.10, -0.10, 0.27 + 0.03 * sacude), env)
            mano_izq(rig, obj, obj + m(0.03, -0.04, 0.08) * env + m(0.0, 0.0, -0.06) * (1 - env))
            mirar(rig, 1.0, pitch=0.30 * grito, yaw=0.20 * env, roll=0.06 * env)

        elif nombre == 'reposo':
            base(rig, 'Idle_Loop', u, reposo_pesos)
            mirar(rig, 0.85, pitch=0.03 * math.sin(fase))

        elif nombre in ('caminar', 'caminar_rapido'):
            clip = 'Walk_Loop' if nombre == 'caminar' else 'Walk_Formal_Loop'
            base(rig, clip, u, {'cadera': 0.9, 'torso': 0.8, 'cabeza': 0.4}, peso_piernas=0.85)
            if nombre == 'caminar_rapido':
                rotar_euler_mundo(rig, 'DEF-spine.001', pitch_x=-0.05)
            mirar(rig, 1.0, pitch=0.03)

        elif nombre == 'senalar':
            # La pose de la lámina: brazo y piernas como en la malla, la cabeza en lo que señala
            ual.aplicar_a_rig(rig, 'Idle_Loop', u, pesos_grupo={'cadera': 0.4, 'torso': 0.5, 'cabeza': 0.0,
                                                                 'piernas': 0.2}, piernas_relativas_f0=True)
            remarca = math.sin(math.tau * 2.0 * min(1.0, max(0.0, (u - 0.2) / 0.6))) * suave(u / 0.2) * \
                (1.0 - suave((u - 0.8) / 0.2))
            rotar_euler_mundo(rig, 'DEF-upper_arm.L', pitch_x=0.0, roll_y=-0.05 * remarca)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=0.05 * remarca)
            mirar(rig, 0.0, pitch=0.03 * remarca)

        elif nombre == 'mirar_atras':
            base(rig, 'Idle_Loop', u, reposo_pesos)
            g = curva_puntos(u, [(0.0, 0.0), (0.3, 1.0), (0.7, 1.0), (1.0, 0.0)])
            rotar_euler_mundo(rig, 'DEF-spine.002', yaw_z=0.25 * g)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=0.30 * g)
            mirar(rig, 1.0, yaw=0.95 * g, pitch=0.04 * g)

        elif nombre == 'hablar':
            base(rig, 'Idle_Talking_Loop', u, {'cadera': 0.7, 'torso': 0.85, 'cabeza': 0.6})
            mirar(rig, 1.0)

        elif nombre == 'llamar_mano':
            base(rig, 'Idle_Loop', u, reposo_pesos)
            env = suave(u / 0.22) * (1.0 - suave((u - 0.8) / 0.2))
            recoge = max(0.0, math.sin(math.tau * 2.0 * min(1.0, max(0.0, (u - 0.2) / 0.6))))
            hombro = hombro_izq(rig)
            caida = rig.pose.bones['DEF-hand.L'].head.copy()
            obj = caida.lerp(hombro + m(0.07, -0.24 + 0.08 * recoge, -0.10 + 0.03 * recoge), env)
            mano_izq(rig, obj, obj + m(0.02, -0.06, 0.04 + 0.04 * recoge) * env + m(0.0, 0.0, -0.06) * (1 - env))
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=-0.08 * env)
            mirar(rig, 1.0, pitch=0.02, yaw=0.10 * env, roll=0.08 * env)

        elif nombre == 'asentir':
            base(rig, 'Idle_Loop', u, reposo_pesos)
            env = suave(u / 0.2) * (1.0 - suave((u - 0.8) / 0.2))
            cab = math.sin(math.tau * 2.0 * min(1.0, max(0.0, (u - 0.1) / 0.8)))
            mirar(rig, 1.0, pitch=-0.20 * max(0.0, cab) * env - 0.05 * env)

        bpy.context.view_layer.update()

    return pose


TOMAS = [
    ('01_senalar', 'senalar', 0.0, 'frente'),
    ('02_reposo', 'reposo', 0.0, 'frente'),
    ('03_inquieta', 'reposo_inquieta', 0.25, 'tres_cuartos'),
    ('04_correr_a', 'correr_falda', 0.0, 'lado'),
    ('05_correr_b', 'correr_falda', 0.25, 'tres_cuartos'),
    ('06_gritar', 'gritar_brazo_alto', 0.5, 'frente'),
    ('07_caminar', 'caminar', 0.25, 'lado'),
    ('08_mirar_atras', 'mirar_atras', 0.5, 'tres_cuartos'),
    ('09_hablar', 'hablar', 0.4, 'frente'),
    ('10_llamar', 'llamar_mano', 0.35, 'tres_cuartos'),
    ('11_espalda', 'correr_falda', 0.5, 'espalda'),
    ('12_inquieta_b', 'reposo_inquieta', 0.75, 'frente'),
]
CAMARAS = {
    'frente': ((-0.15, -4.2, 1.05), (-0.15, 0.0, 0.80)),
    'lado': ((4.0, -0.4, 1.0), (-0.15, 0.0, 0.75)),
    'tres_cuartos': ((-2.9, -3.0, 1.15), (-0.15, 0.0, 0.75)),
    'espalda': ((-0.15, 4.2, 1.05), (-0.15, 0.0, 0.80)),
}


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    malla, co_norm = kp.importar_malla(kp.simplificar(ENTRADA, MALLA_30K), H, 'Mariana_Zudanez_Malla')
    seg = {n: (Vector(a) * H, Vector(b) * H) for n, (a, b) in anatomia.segmentos().items()}
    rig = crear_armadura_ual('GeneralSkeleton', seg, huesos_extra=anatomia.HUESOS_EXTRA)
    tris = kp.triangulos(malla)
    nombres, W = anatomia.calcular_pesos(co_norm, tris, kp.color_base_por_vertice(malla))
    kp.cortar_falda_y_pies(malla, co_norm, tris, nombres, W, H)
    kp.asignar_grupos(malla, nombres, W)
    malla.parent = rig
    malla.modifiers.new(name='Armature', type='ARMATURE').object = rig

    ual = BibliotecaUAL()
    pose = construir_pose(ual)
    if '--prueba' in ARGS:
        solo = [a for a in ARGS if not a.startswith('--')]
        kp.renderizar_control(rig, pose, CLIPS, [t for t in TOMAS if not solo or t[1] in solo], CAMARAS, REV)
        return
    hornear_clips(rig, CLIPS, pose, fps=24)
    if '--sin-render' not in ARGS:
        kp.renderizar_control(rig, pose, CLIPS, TOMAS, CAMARAS, REV)
    ual.limpiar_escena()
    kp.exportar(rig, SALIDA, ID, {
        'id': ID,
        'nombre': 'Mariana Zudáñez',
        'subtitulo': '«¡Paisanos, defiendan a mi hermano!» · 25 de mayo de 1809 (Guía #3 · Q-0448-2)',
        'altura_m': ALTURA_M,
        'esqueleto': 'Universal Animation Library (53 huesos · GeneralSkeleton); falda con vuelo por pierna',
        'arquetipo': 'B · «Sígueme»: de la boca de calle frente a M055 al portón de la Audiencia (atardecer)',
        'clip_inicial': 'reposo_inquieta',
        'clips': CLIPS,
    }, accion_blend='reposo_inquieta', lamina=LAMINA, vista_previa=REV / '05_correr_b.png')


if __name__ == '__main__':
    main()
