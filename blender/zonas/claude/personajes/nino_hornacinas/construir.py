"""Rig y animaciones del niño del caballito de palo (Guía #21, leyenda de las 14 hornacinas de San Francisco, M013).

Parte del modelo estático de Tripo (`personas/nino_hornacinas/Nino_ornacinas.glb`): no se modela nada de cero.
Esqueleto: los 53 huesos de la Universal Animation Library (UAL, CC0) + un hueso `palo` hijo de la mano izquierda
para el caballito. Las animaciones comunes salen de la UAL (piernas, cadera, torso y el brazo libre retargeteados);
las propias (`galopar_palo`, `huir`, `ocultarse`, `asomarse`, `reir`) se componen sobre la UAL con IK.

Uso (un solo Blender pesado a la vez; ~0,8 GB de memoria):
    ~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/nino_hornacinas/construir.py
    ... -- --prueba      solo renders de control de poses sueltas (sin hornear ni exportar)
    ... -- --sin-render  hornea y exporta sin renders de control
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector, Quaternion

BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE), str(BASE.parent)]

import kit_personaje as kp  # noqa: E402
from kit_personaje import RAIZ, huesos_desde_ual, apoyar_pies  # noqa: E402
from kit_ual import (  # noqa: E402  (kit de antigravity: esqueleto UAL, biblioteca y horneado)
    BibliotecaUAL, crear_armadura_ual, limpiar_pose, rotar_euler_mundo, apuntar_hueso, ik_dos_huesos,
    aplicar_delta_mundo, hornear_clips, suave, curva_puntos,
)
import anatomia  # noqa: E402

ARGS = kp.argumentos()
ID = 'nino_hornacinas'
ALTURA_M = 1.30  # con el tricornio; sin él ~1,22 m (guía §1.6: niños de 1,10 a 1,25 m)
H = ALTURA_M

ENTRADA = RAIZ / 'personas/nino_hornacinas/Nino_ornacinas.glb'
LAMINA = RAIZ / 'personas/nino_hornacinas/diseno.png'
MALLA_30K = kp.SCRATCH / 'nino_30k.glb'
SALIDA = RAIZ / f'web/public/models/ciudad/claude/personajes/{ID}'
REV = RAIZ / f'revisiones/claude/{ID}'

LARGO_PALO = 0.585 * H  # del agarre a la punta inferior

CLIPS = [
    # --- propios (guía #21) ---
    {'id': 'galopar_palo', 'nombre': 'Galopar en el caballito de palo', 'propio': True, 'bucle': True,
     'duracion': 0.667, 'velocidad_m_s': 2.0,
     'descripcion': 'Monta el palo entre las piernas con las dos manos y galopa a saltitos por la plazoleta; '
                    'la cabeza del caballito cabecea a cada salto.'},
    {'id': 'huir', 'nombre': 'Huir hacia la columna', 'propio': True, 'bucle': True,
     'duracion': 2.667, 'velocidad_m_s': 3.4,
     'descripcion': 'Corre agachado con el caballito apretado contra el pecho y mira una vez por encima del '
                    'hombro al que se acerca.'},
    {'id': 'ocultarse', 'nombre': 'Ocultarse tras la columna', 'propio': True, 'bucle': False,
     'duracion': 1.6, 'velocidad_m_s': 0.0,
     'descripcion': 'Frena, se encoge y se agacha abrazando el caballito, con una última mirada de reojo; '
                    'termina quieto para el fundido de desaparición.'},
    {'id': 'asomarse', 'nombre': 'Asomarse desde la columna', 'propio': True, 'bucle': True,
     'duracion': 3.2, 'velocidad_m_s': 0.0,
     'descripcion': 'Agachado tras la columna (que queda a su derecha), se asoma, sonríe y se vuelve a esconder.'},
    {'id': 'reir', 'nombre': 'Risa traviesa', 'propio': True, 'bucle': False,
     'duracion': 1.8, 'velocidad_m_s': 0.0,
     'descripcion': 'Se tapa la boca con la mano y se ríe sacudiendo los hombros, con la cabeza ladeada: '
                    'el aviso antes de echar a correr.'},
    # --- comunes (guía §1.6) ---
    {'id': 'reposo', 'nombre': 'Reposo con el caballito (UAL)', 'propio': False, 'bucle': True,
     'duracion': 2.5, 'velocidad_m_s': 0.0,
     'descripcion': 'Respira y cambia el peso de pie; mira de reojo y golpea una vez el palo contra el suelo.'},
    {'id': 'caminar', 'nombre': 'Caminar (UAL)', 'propio': False, 'bucle': True,
     'duracion': 1.333, 'velocidad_m_s': 0.85,
     'descripcion': 'Paso de niño en el sitio con el caballito en la mano y el otro brazo suelto.'},
    {'id': 'caminar_rapido', 'nombre': 'Trotar (UAL)', 'propio': False, 'bucle': True,
     'duracion': 0.933, 'velocidad_m_s': 1.9,
     'descripcion': 'Trote ligero en el sitio llevando el caballito de pie.'},
    {'id': 'sigilo', 'nombre': 'Andar a escondidas (UAL)', 'propio': False, 'bucle': True,
     'duracion': 2.0, 'velocidad_m_s': 0.5,
     'descripcion': 'Agachado, paso lento y largo, con el caballito pegado al cuerpo.'},
    {'id': 'mirar_atras', 'nombre': 'Mirar atrás', 'propio': False, 'bucle': False,
     'duracion': 1.6, 'velocidad_m_s': 0.0,
     'descripcion': 'Gira torso y cabeza por encima del hombro derecho y vuelve.'},
    {'id': 'hablar', 'nombre': 'Gesticular (UAL)', 'propio': False, 'bucle': True,
     'duracion': 2.933, 'velocidad_m_s': 0.0,
     'descripcion': 'Gestos de conversación con la mano libre mientras la ficha narra la leyenda.'},
    {'id': 'saludar', 'nombre': 'Saludar', 'propio': False, 'bucle': False,
     'duracion': 1.8, 'velocidad_m_s': 0.0,
     'descripcion': 'Agita la mano derecha a la altura de la cara.'},
    {'id': 'asentir', 'nombre': 'Asentir', 'propio': False, 'bucle': False,
     'duracion': 1.4, 'velocidad_m_s': 0.0,
     'descripcion': 'Dos cabeceos cortos.'},
    {'id': 'senalar', 'nombre': 'Señalar las hornacinas', 'propio': False, 'bucle': False,
     'duracion': 2.2, 'velocidad_m_s': 0.0,
     'descripcion': 'Señala hacia arriba y adelante, a la altura de las hornacinas del muro.'},
    {'id': 'silencio', 'nombre': 'Pedir silencio', 'propio': False, 'bucle': False,
     'duracion': 1.8, 'velocidad_m_s': 0.0,
     'descripcion': 'Se lleva el índice a los labios («chist») con una sonrisa.'},
    {'id': 'llamar_mano', 'nombre': 'Llamar con la mano', 'propio': False, 'bucle': False,
     'duracion': 2.0, 'velocidad_m_s': 0.0,
     'descripcion': 'Con la palma hacia arriba, invita a acercarse moviendo los dedos dos veces.'},
]

LADO_R = ['DEF-shoulder.R', 'DEF-upper_arm.R', 'DEF-forearm.R', 'DEF-hand.R']


def m(*v):
    """Punto normalizado → metros."""
    return Vector(v) * H


def construir_pose(ual):
    seg = anatomia.segmentos()

    def mirar(rig, factor=1.0, pitch=0.0, roll=0.0, yaw=0.0):
        """factor 1 = cara al frente; 0 = la cabeza girada de la malla (hacia su derecha, -X). yaw > 0 gira hacia su
        izquierda (+X)."""
        y = anatomia.GIRO_CABEZA_REPOSO * factor + yaw
        rotar_euler_mundo(rig, 'DEF-neck', pitch_x=pitch * 0.35, roll_y=roll * 0.3, yaw_z=y * 0.4)
        rotar_euler_mundo(rig, 'DEF-head', pitch_x=pitch * 0.65, roll_y=roll * 0.7, yaw_z=y * 0.6)

    def brazo_ual(rig, clip, u, peso=1.0, referencia='Idle_Loop'):
        """Brazo derecho (libre) desde la UAL, relativo a la pose de brazos caídos de `referencia`."""
        huesos_desde_ual(ual, rig, clip, u, LADO_R, peso, referencia)

    def cadera(rig):
        bpy.context.view_layer.update()
        return rig.pose.bones['DEF-hips'].head.copy()

    def palo_actual(rig):
        bpy.context.view_layer.update()
        pb = rig.pose.bones['palo']
        return pb.head.copy(), (pb.tail - pb.head).normalized()

    # Frente del caballito en el espacio del hueso `palo` (en reposo mira a -Y)
    frente_local = None

    def sujetar_palo(rig, agarre, direccion, polo, frente=Vector((0.0, -1.0, 0.0)), vueltas=4):
        """Lleva el puño izquierdo a `agarre` con el palo apuntando (del agarre a la punta) en `direccion` y el
        hocico del caballito hacia `frente`. Gira la muñeca (el puño y el palo son una sola pieza)."""
        nonlocal frente_local
        if frente_local is None:
            frente_local = rig.data.bones['palo'].matrix_local.to_quaternion().inverted() @ Vector((0.0, -1.0, 0.0))
        agarre = Vector(agarre)
        direccion = Vector(direccion).normalized()
        # La punta del palo nunca atraviesa el suelo: si haría falta, se inclina más (misma dirección en planta)
        z_min = 0.01 - agarre.z
        if direccion.z * LARGO_PALO < z_min:
            plano = Vector((direccion.x, direccion.y, 0.0))
            plano = plano.normalized() if plano.length > 1e-4 else Vector((0.0, 1.0, 0.0))
            dz = max(-1.0, min(1.0, z_min / LARGO_PALO))
            direccion = plano * math.sqrt(1.0 - dz * dz) + Vector((0.0, 0.0, dz))
        for _ in range(vueltas):
            bpy.context.view_layer.update()
            pb_m = rig.pose.bones['DEF-hand.L']
            cab, _ = palo_actual(rig)
            ik_dos_huesos(rig, 'DEF-upper_arm.L', 'DEF-forearm.L', agarre - (cab - pb_m.head), polo)
            _, d = palo_actual(rig)
            aplicar_delta_mundo(rig, 'DEF-hand.L', d.rotation_difference(direccion))
            bpy.context.view_layer.update()
            q = rig.pose.bones['palo'].matrix.to_quaternion()
            f_act = q @ frente_local
            f_act -= direccion * f_act.dot(direccion)
            f_obj = Vector(frente) - direccion * Vector(frente).dot(direccion)
            if f_act.length > 1e-4 and f_obj.length > 1e-4:
                aplicar_delta_mundo(rig, 'DEF-hand.L', f_act.normalized().rotation_difference(f_obj.normalized()))

    def mano_derecha_en_palo(rig, distancia, lateral=-0.022):
        """Mano derecha sobre el palo, `distancia` (normalizada) por encima del puño izquierdo."""
        cab, d = palo_actual(rig)
        obj = cab - d * (distancia * H) + Vector((lateral * H, -0.012 * H, 0.0))
        ik_dos_huesos(rig, 'DEF-upper_arm.R', 'DEF-forearm.R', obj, cab + m(-0.25, 0.10, -0.05))
        apuntar_hueso(rig, 'DEF-hand.R', obj + d * (0.02 * H) + Vector((0.03 * H, -0.05 * H, 0.0)))

    def palo_en_reposo(rig, golpe=0.0, balanceo=0.0):
        """El palo como en la malla: de pie junto al pie izquierdo (con un leve balanceo o un golpe al suelo)."""
        c = cadera(rig)
        base_c = Vector(seg['DEF-hips'][0]) * H
        agarre = Vector(anatomia.PALO_AGARRE) * H + (c - base_c) + Vector((0.0, 0.0, golpe * 0.05 * H))
        d0 = (Vector(anatomia.PALO_PIE) - Vector(anatomia.PALO_AGARRE)).normalized()
        d = (d0 + Vector((0.0, -balanceo, 0.0))).normalized()
        sujetar_palo(rig, agarre, d, agarre + m(0.25, 0.25, -0.05))

    def palo_al_pecho(rig, adelante=0.12, alto=0.10, inclinacion=0.55, lado=0.08):
        """Caballito apretado contra el pecho: la cabeza tallada arriba-adelante, la punta del palo atrás-abajo."""
        c = cadera(rig)
        agarre = c + m(lado, -adelante, alto)
        d = Vector((0.05, inclinacion, -1.0)).normalized()
        sujetar_palo(rig, agarre, d, agarre + m(0.25, 0.20, -0.10))
        return agarre

    def pose(rig, nombre, u, spec):
        limpiar_pose(rig)
        fase = math.tau * u

        if nombre == 'reposo':
            ual.aplicar_a_rig(rig, 'Idle_Loop', u, pesos_grupo={'cadera': 0.7, 'torso': 0.8, 'cabeza': 0.4,
                                                                 'piernas': 0.45}, piernas_relativas_f0=True)
            brazo_ual(rig, 'Idle_Loop', u, 0.8)
            golpe = math.sin(math.pi * np.clip((u - 0.62) / 0.16, 0, 1)) ** 2
            palo_en_reposo(rig, golpe=golpe, balanceo=0.03 * math.sin(fase))
            # Al frente la mayor parte del tiempo; a mitad del ciclo echa un vistazo de reojo a un lado
            frente = curva_puntos(u, [(0.0, 1.0), (0.30, 1.0), (0.42, 0.2), (0.58, 0.2), (0.70, 1.0), (1.0, 1.0)])
            mirar(rig, frente, pitch=-0.06 * golpe, roll=0.04 * math.sin(fase))

        elif nombre == 'galopar_palo':
            ual.aplicar_a_rig(rig, 'Jog_Fwd_Loop', u, pesos_grupo={'cadera': 1.0, 'torso': 0.5, 'cabeza': 0.3,
                                                                    'piernas': 1.0}, piernas_relativas_f0=False)
            salto = abs(math.sin(fase))
            pb = rig.pose.bones['DEF-hips']
            pb.location = pb.location + rig.data.bones['DEF-hips'].matrix_local.to_quaternion().inverted() @ \
                Vector((0.0, 0.0, 0.025 * H * salto))
            for suf, s in (('.L', 1.0), ('.R', -1.0)):  # piernas un poco abiertas para montar el palo
                rotar_euler_mundo(rig, f'DEF-thigh{suf}', roll_y=-0.07 * s)
            rotar_euler_mundo(rig, 'DEF-spine.001', pitch_x=-0.10)
            rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=-0.04)
            c = cadera(rig)
            cabeceo = 0.10 * math.sin(fase * 2.0 + 0.6)
            ang = math.radians(33.0) + cabeceo
            d = Vector((0.0, math.sin(ang), -math.cos(ang)))
            agarre = Vector((0.035 * H, c.y - 0.13 * H, c.z + 0.05 * H))
            sujetar_palo(rig, agarre, d, agarre + m(0.28, 0.15, -0.10))
            mano_derecha_en_palo(rig, 0.075)
            mirar(rig, 1.0, pitch=0.10 - 0.06 * salto, roll=0.05 * math.sin(fase))

        elif nombre == 'huir':
            k = (u * 4.0) % 1.0
            ual.aplicar_a_rig(rig, 'Sprint_Loop', k, pesos_grupo={'cadera': 1.0, 'torso': 0.8, 'cabeza': 0.3,
                                                                   'piernas': 1.0}, piernas_relativas_f0=False)
            brazo_ual(rig, 'Sprint_Loop', k, 0.9)
            rotar_euler_mundo(rig, 'DEF-spine.002', pitch_x=-0.10)
            palo_al_pecho(rig, adelante=0.11, alto=0.13, inclinacion=0.9)
            atras = curva_puntos(u, [(0.0, 0.0), (0.38, 0.0), (0.50, 1.0), (0.66, 1.0), (0.78, 0.0), (1.0, 0.0)])
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=-0.35 * atras)
            mirar(rig, 1.0, pitch=0.12 * (1 - atras), yaw=-1.25 * atras, roll=-0.10 * atras)

        elif nombre in ('ocultarse', 'asomarse'):
            if nombre == 'ocultarse':
                b = suave(u / 0.55)
                ual.aplicar_a_rig(rig, 'Crouch_Idle_Loop', 0.15 + 0.3 * u,
                                  pesos_grupo={'cadera': b, 'torso': b, 'cabeza': 0.3 * b, 'piernas': b},
                                  piernas_relativas_f0=False)
                apoyar_pies(rig)
                encogido = curva_puntos(u, [(0.0, 0.0), (0.25, 1.0), (0.6, 0.7), (1.0, 0.6)])
                reojo = curva_puntos(u, [(0.0, 0.0), (0.45, 0.0), (0.65, 1.0), (0.85, 1.0), (1.0, 0.25)])
                rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=-0.15 * encogido, yaw_z=-0.3 * reojo)
                for suf, s in (('.L', 1.0), ('.R', -1.0)):
                    rotar_euler_mundo(rig, f'DEF-shoulder{suf}', pitch_x=0.0, roll_y=0.10 * s * encogido)
                palo_al_pecho(rig, adelante=0.10, alto=0.10 + 0.04 * (1 - b), inclinacion=0.8 + 0.4 * b, lado=0.05)
                brazo_ual(rig, 'Crouch_Idle_Loop', 0.3, 0.6 * b)
                mirar(rig, 1.0, pitch=-0.10 * encogido + 0.05 * reojo, yaw=-1.1 * reojo)
            else:
                ual.aplicar_a_rig(rig, 'Crouch_Idle_Loop', u, pesos_grupo={'cadera': 1.0, 'torso': 1.0, 'cabeza': 0.3,
                                                                            'piernas': 1.0}, piernas_relativas_f0=False)
                asoma = curva_puntos(u, [(0.0, 0.0), (0.18, 0.0), (0.38, 1.0), (0.70, 1.0), (0.86, 0.0), (1.0, 0.0)])
                sonrisa = math.sin(math.pi * np.clip((u - 0.42) / 0.2, 0, 1))
                # Se inclina hacia su derecha (-X), donde está el borde de la columna
                rotar_euler_mundo(rig, 'DEF-spine.002', roll_y=-0.20 * asoma, yaw_z=-0.10 * asoma)
                rotar_euler_mundo(rig, 'DEF-spine.003', roll_y=-0.16 * asoma)
                palo_al_pecho(rig, adelante=0.10, alto=0.10, inclinacion=1.2, lado=0.05)
                brazo_ual(rig, 'Crouch_Idle_Loop', u, 0.6)
                # La mano derecha se apoya en la columna al asomarse
                c = cadera(rig)
                obj = c + m(-0.20 - 0.06 * asoma, -0.10, 0.22 + 0.05 * asoma)
                ik_dos_huesos(rig, 'DEF-upper_arm.R', 'DEF-forearm.R', obj, c + m(-0.30, 0.15, 0.10))
                mirar(rig, 1.0, pitch=0.06 * asoma, roll=0.25 * asoma - 0.06 * sonrisa, yaw=-0.25 * asoma)

        elif nombre == 'reir':
            ual.aplicar_a_rig(rig, 'Idle_Loop', u, pesos_grupo={'cadera': 0.6, 'torso': 0.7, 'cabeza': 0.3,
                                                                 'piernas': 0.4}, piernas_relativas_f0=True)
            env = suave(u / 0.2) * (1.0 - suave((u - 0.8) / 0.2))
            risa = math.sin(math.tau * 5.0 * u) * env
            rotar_euler_mundo(rig, 'DEF-spine.002', pitch_x=-0.10 * env + 0.03 * risa)
            rotar_euler_mundo(rig, 'DEF-spine.003', pitch_x=-0.06 * env)
            for suf in ('.L', '.R'):
                rotar_euler_mundo(rig, f'DEF-shoulder{suf}', pitch_x=0.0, yaw_z=0.0, roll_y=0.0)
                aplicar_delta_mundo(rig, f'DEF-shoulder{suf}', Quaternion(Vector((0, 1, 0)),
                                                                          (0.06 if suf == '.L' else -0.06) * abs(risa)))
            palo_en_reposo(rig)
            c = cadera(rig)
            boca = Vector(seg['DEF-head'][0]) * H + (c - Vector(seg['DEF-hips'][0]) * H) + m(-0.01, -0.09, 0.03)
            reposo_mano = Vector(seg['DEF-hand.R'][0]) * H
            ik_dos_huesos(rig, 'DEF-upper_arm.R', 'DEF-forearm.R', reposo_mano.lerp(boca, env),
                          c + m(-0.30, 0.10, 0.10))
            apuntar_hueso(rig, 'DEF-hand.R', reposo_mano.lerp(boca, env) + m(0.06 * env, -0.02, 0.04 * env - 0.06 * (1 - env)))
            mirar(rig, 0.4 + 0.6 * env, pitch=-0.12 * env + 0.04 * risa, roll=0.18 * env)

        elif nombre in ('caminar', 'caminar_rapido', 'sigilo'):
            clip, pesos = {
                'caminar': ('Walk_Loop', {'cadera': 0.9, 'torso': 0.8, 'cabeza': 0.5, 'piernas': 1.0}),
                'caminar_rapido': ('Jog_Fwd_Loop', {'cadera': 1.0, 'torso': 0.8, 'cabeza': 0.4, 'piernas': 1.0}),
                'sigilo': ('Crouch_Fwd_Loop', {'cadera': 1.0, 'torso': 0.9, 'cabeza': 0.3, 'piernas': 1.0}),
            }[nombre]
            ual.aplicar_a_rig(rig, clip, u, pesos_grupo=pesos, piernas_relativas_f0=False)
            brazo_ual(rig, clip, u, 0.9 if nombre != 'sigilo' else 0.5)
            if nombre == 'sigilo':
                palo_al_pecho(rig, adelante=0.10, alto=0.12, inclinacion=1.0, lado=0.06)
                mirar(rig, 1.0, pitch=0.10, yaw=0.25 * math.sin(fase))
            else:
                c = cadera(rig)
                onda = math.sin(fase)
                agarre = c + (Vector(anatomia.PALO_AGARRE) - Vector(seg['DEF-hips'][0])) * H + m(0.0, -0.02 - 0.02 * onda, 0.03)
                d = Vector((0.0, 0.35 + 0.10 * onda, -1.0)).normalized()  # la punta va un poco atrás, sin arrastrar
                sujetar_palo(rig, agarre, d, agarre + m(0.25, 0.25, -0.05))
                mirar(rig, 1.0, pitch=0.03)

        elif nombre == 'mirar_atras':
            ual.aplicar_a_rig(rig, 'Idle_Loop', u, pesos_grupo={'cadera': 0.6, 'torso': 0.7, 'cabeza': 0.3,
                                                                 'piernas': 0.4}, piernas_relativas_f0=True)
            brazo_ual(rig, 'Idle_Loop', u, 0.8)
            g = curva_puntos(u, [(0.0, 0.0), (0.3, 1.0), (0.7, 1.0), (1.0, 0.0)])
            rotar_euler_mundo(rig, 'DEF-spine.002', yaw_z=-0.25 * g)
            rotar_euler_mundo(rig, 'DEF-spine.003', yaw_z=-0.30 * g)
            palo_en_reposo(rig)
            mirar(rig, 1.0, yaw=-1.0 * g, pitch=0.05 * g)

        elif nombre == 'hablar':
            ual.aplicar_a_rig(rig, 'Idle_Talking_Loop', u, pesos_grupo={'cadera': 0.7, 'torso': 0.85, 'cabeza': 0.7,
                                                                         'piernas': 0.4}, piernas_relativas_f0=True)
            brazo_ual(rig, 'Idle_Talking_Loop', u, 1.0)
            palo_en_reposo(rig, balanceo=0.04 * math.sin(fase))
            mirar(rig, 1.0)

        elif nombre in ('saludar', 'senalar', 'silencio', 'llamar_mano', 'asentir'):
            ual.aplicar_a_rig(rig, 'Idle_Loop', u, pesos_grupo={'cadera': 0.6, 'torso': 0.7, 'cabeza': 0.3,
                                                                 'piernas': 0.4}, piernas_relativas_f0=True)
            palo_en_reposo(rig)
            env = suave(u / 0.25) * (1.0 - suave((u - 0.75) / 0.25))
            c = cadera(rig)
            dc = c - Vector(seg['DEF-hips'][0]) * H
            mano0 = Vector(seg['DEF-hand.R'][0]) * H + dc
            polo = c + m(-0.32, 0.12, 0.05)
            if nombre == 'asentir':
                brazo_ual(rig, 'Idle_Loop', u, 0.8)
                cab = math.sin(math.tau * 2.0 * np.clip((u - 0.1) / 0.8, 0, 1))
                mirar(rig, 1.0, pitch=-0.20 * max(0.0, cab) * env - 0.05 * env)
            else:
                if nombre == 'saludar':
                    obj = c + m(-0.20, -0.07, 0.42)
                    vaiven = math.sin(math.tau * 3.0 * u)
                    punta = obj + m(-0.03 * vaiven, -0.01, 0.10)
                    mirar(rig, 1.0, pitch=0.03, roll=0.06 * env)
                elif nombre == 'senalar':
                    obj = c + m(-0.16, -0.31, 0.33)
                    punta = obj + m(-0.03, -0.11, 0.05)
                    mirar(rig, 1.0, pitch=0.30 * env, yaw=-0.20 * env)
                elif nombre == 'silencio':
                    obj = Vector(seg['DEF-head'][0]) * H + dc + m(-0.035, -0.11, -0.02)
                    punta = obj + m(0.02, 0.0, 0.09)
                    mirar(rig, 1.0, pitch=-0.06 * env, roll=0.10 * env)
                else:  # llamar_mano
                    obj = c + m(-0.17, -0.17, 0.17)
                    dedos = math.sin(math.tau * 2.0 * np.clip((u - 0.25) / 0.5, 0, 1))
                    punta = obj + m(0.04, -0.04 + 0.02 * dedos, 0.03 + 0.05 * max(0.0, dedos))
                    mirar(rig, 1.0, pitch=-0.04, roll=0.12 * env)
                ik_dos_huesos(rig, 'DEF-upper_arm.R', 'DEF-forearm.R', mano0.lerp(obj, env), polo)
                apuntar_hueso(rig, 'DEF-hand.R', (mano0 + m(0.0, 0.0, -0.07)).lerp(punta, env))

        bpy.context.view_layer.update()

    return pose


# ---------------------------------------------------------------------------------------------------------------
# Renders de control, exportación
# ---------------------------------------------------------------------------------------------------------------


TOMAS = [  # (archivo, clip, u, cámara)
    ('01_reposo', 'reposo', 0.0, 'frente'),
    ('02_galopar_a', 'galopar_palo', 0.0, 'lado'),
    ('03_galopar_b', 'galopar_palo', 0.25, 'tres_cuartos'),
    ('04_huir', 'huir', 0.55, 'tres_cuartos'),
    ('05_ocultarse', 'ocultarse', 1.0, 'tres_cuartos'),
    ('06_asomarse', 'asomarse', 0.55, 'frente'),
    ('07_reir', 'reir', 0.5, 'frente'),
    ('08_caminar', 'caminar', 0.25, 'lado'),
    ('09_saludar', 'saludar', 0.5, 'frente'),
    ('10_silencio', 'silencio', 0.5, 'tres_cuartos'),
    ('11_senalar', 'senalar', 0.5, 'tres_cuartos'),
    ('12_sigilo', 'sigilo', 0.3, 'lado'),
]
CAMARAS = {
    'frente': ((0.0, -3.4, 0.85), (0.0, 0.0, 0.62)),
    'lado': ((3.4, -0.3, 0.80), (0.0, 0.0, 0.58)),
    'tres_cuartos': ((-2.3, -2.5, 0.95), (0.0, 0.0, 0.58)),
}


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    malla, co_norm = kp.importar_malla(kp.simplificar(ENTRADA, MALLA_30K), H, 'Nino_Hornacinas_Malla')
    seg = {n: (Vector(a) * H, Vector(b) * H) for n, (a, b) in anatomia.segmentos().items()}
    rig = crear_armadura_ual('GeneralSkeleton', seg, huesos_extra=anatomia.HUESOS_EXTRA)
    tris = kp.triangulos(malla)
    nombres, W = anatomia.calcular_pesos(co_norm, tris)
    kp.cortar_caras(malla, kp.caras_entre_piezas(tris, nombres, W, 'palo', permitidos=('DEF-hand.L',)),
                    'entre el palo y el cuerpo')
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
        'nombre': 'El niño del caballito de palo',
        'subtitulo': 'Leyenda de las 14 hornacinas de San Francisco (Guía #21 · C-1039-1)',
        'altura_m': ALTURA_M,
        'esqueleto': 'Universal Animation Library (53 huesos · GeneralSkeleton) + hueso «palo» (caballito) en la mano izquierda',
        'arquetipo': 'E · Horario (atardecer y noche), plazoleta de San Francisco (M013)',
        'clip_inicial': 'galopar_palo',
        'clips': CLIPS,
    }, accion_blend='galopar_palo', lamina=LAMINA, vista_previa=REV / '03_galopar_b.png')


if __name__ == '__main__':
    main()
