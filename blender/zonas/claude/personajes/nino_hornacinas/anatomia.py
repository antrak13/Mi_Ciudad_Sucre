"""Medidas del niño de las hornacinas (Guía #21) sobre la malla Tripo, en unidades normalizadas (altura total = 1,
sombrero incluido). Ejes de Blender: frente -Y, izquierda del niño +X, arriba +Z. Numpy puro.

Medido sobre `personas/nino_hornacinas/Nino_ornacinas.glb` simplificada a 30 k triángulos: cortes por altura y
vistas ortográficas con cuadrícula (revisiones/claude/nino_hornacinas/). El palo del caballito va en la mano izquierda.
"""
import numpy as np

from pesos_envolvente import suave, dist_segmento, Malla, pesos_envolvente

# Eje del palo (de la punta en el suelo al cuello del caballito) y punto donde lo agarra el puño izquierdo
PALO_PIE = (0.104, 0.044, -0.01)
PALO_CUELLO = (0.108, -0.045, 0.66)
PALO_AGARRE = (0.108, -0.036, 0.585)
RADIO_PALO = 0.0115

# Cabeza tallada del caballito (crin incluida)
CABALLO_CAJA = {'x_min': 0.075, 'y_max': 0.0, 'z_min': 0.645, 'z_max': 0.845}

# La malla tiene la cabeza girada ~20° hacia su derecha (-X): para mirar al frente se gira hacia +X
GIRO_CABEZA_REPOSO = 0.34


def _dedos(muneca, direccion, normal, signo_x, escala):
    """Dedos de la UAL (sin peso en esta malla: el puño y la mano abierta van enteros con DEF-hand)."""
    from kit_ual import dedos_mano_desde_muneca
    return dedos_mano_desde_muneca(muneca, direccion, normal, signo_x=signo_x, escala=escala)


def segmentos():
    """Cabeza y cola de los 53 huesos UAL + el palo, normalizados."""
    s = {
        'root': ((0.0, 0.0, 0.0), (0.0, 0.0, 0.10)),
        'DEF-hips': ((0.0, 0.030, 0.470), (0.0, 0.030, 0.530)),
        'DEF-spine.001': ((0.0, 0.030, 0.530), (0.0, 0.028, 0.600)),
        'DEF-spine.002': ((0.0, 0.028, 0.600), (0.0, 0.026, 0.665)),
        'DEF-spine.003': ((0.0, 0.026, 0.665), (0.0, 0.030, 0.735)),
        'DEF-neck': ((0.0, 0.030, 0.735), (0.0, 0.030, 0.795)),
        'DEF-head': ((0.0, 0.030, 0.795), (0.0, 0.030, 0.960)),

        'DEF-shoulder.R': ((-0.020, 0.030, 0.712), (-0.112, 0.035, 0.705)),
        'DEF-upper_arm.R': ((-0.112, 0.035, 0.705), (-0.155, 0.032, 0.535)),
        'DEF-forearm.R': ((-0.155, 0.032, 0.535), (-0.148, 0.010, 0.425)),
        'DEF-hand.R': ((-0.148, 0.010, 0.425), (-0.146, 0.008, 0.350)),

        'DEF-shoulder.L': ((0.020, 0.030, 0.712), (0.118, 0.035, 0.705)),
        'DEF-upper_arm.L': ((0.118, 0.035, 0.705), (0.155, 0.085, 0.575)),
        'DEF-forearm.L': ((0.155, 0.085, 0.575), (0.135, -0.005, 0.590)),
        'DEF-hand.L': ((0.135, -0.005, 0.590), (0.112, -0.050, 0.600)),

        'DEF-thigh.R': ((-0.050, 0.030, 0.465), (-0.082, 0.022, 0.255)),
        'DEF-shin.R': ((-0.082, 0.022, 0.255), (-0.113, 0.045, 0.072)),
        'DEF-foot.R': ((-0.113, 0.045, 0.072), (-0.135, -0.020, 0.020)),
        'DEF-toe.R': ((-0.135, -0.020, 0.020), (-0.140, -0.068, 0.012)),

        'DEF-thigh.L': ((0.050, 0.030, 0.465), (0.062, 0.025, 0.255)),
        'DEF-shin.L': ((0.062, 0.025, 0.255), (0.062, 0.065, 0.072)),
        'DEF-foot.L': ((0.062, 0.065, 0.072), (0.078, 0.000, 0.020)),
        'DEF-toe.L': ((0.078, 0.000, 0.020), (0.082, -0.050, 0.012)),

        # Hueso propio: el palo con el caballito, hijo de la mano izquierda (cabeza en el agarre, cola en el pie)
        'palo': (PALO_AGARRE, PALO_PIE),
    }
    try:
        s.update(_dedos((-0.148, 0.010, 0.425), (0.0, -0.05, -1.0), (1.0, 0.0, 0.0), -1, 0.40))
        s.update(_dedos((0.135, -0.005, 0.590), (-0.45, -0.88, 0.10), (0.0, 0.0, 1.0), 1, 0.40))
    except ImportError:  # fuera de Blender (pruebas de pesos) no hacen falta los dedos
        pass
    return s


HUESOS_EXTRA = [('palo', 'DEF-hand.L')]

# Radios de las envolventes (normalizados)
RADIOS = {
    'DEF-hips': 0.075, 'DEF-spine.001': 0.070, 'DEF-spine.002': 0.075, 'DEF-spine.003': 0.080,
    'DEF-neck': 0.035, 'DEF-head': 0.060,
    'DEF-shoulder.R': 0.035, 'DEF-upper_arm.R': 0.034, 'DEF-forearm.R': 0.030, 'DEF-hand.R': 0.030,
    'DEF-shoulder.L': 0.035, 'DEF-upper_arm.L': 0.034, 'DEF-forearm.L': 0.030, 'DEF-hand.L': 0.032,
    'DEF-thigh.R': 0.055, 'DEF-shin.R': 0.040, 'DEF-foot.R': 0.032, 'DEF-toe.R': 0.026,
    'DEF-thigh.L': 0.055, 'DEF-shin.L': 0.040, 'DEF-foot.L': 0.032, 'DEF-toe.L': 0.026,
}


def mascaras(malla):
    """Piezas y compuertas sobre las posiciones únicas de la malla normalizada."""
    P = malla.pos
    x, y, z = P[:, 0], P[:, 1], P[:, 2]

    d_palo = dist_segmento(P, PALO_PIE, PALO_CUELLO)
    c = CABALLO_CAJA
    caja_caballo = (x > c['x_min']) & (y < c['y_max']) & (z > c['z_min']) & (z < c['z_max'])
    # Tripo fundió el palo con el zapato y la pierna izquierda: el radio de captura cambia por tramos (medido con la
    # prueba de separación, que aparta el palo 28 cm y muestra qué queda pegado al cuerpo)
    radio = np.select([z < 0.07, z < 0.20, z < 0.45], [0.0145, 0.017, 0.0135], RADIO_PALO + 0.002)
    palo = ((d_palo < radio) & ~((z >= 0.07) & (z < 0.20) & (x < 0.098))) | caja_caballo

    # Puño izquierdo: componente conexa desde el puño, delante del cuerpo y fuera del palo
    puno_cond = (~palo) & (((x > 0.085) & (y < 0.005) & (z > 0.52) & (z < 0.645)) | ((x > 0.122) & (z > 0.53) & (z < 0.70)))
    brazo_l = malla.inundar((0.135, -0.055, 0.60), puno_cond).astype(float)
    # Mano derecha colgando: separada de la casaca por debajo del codo
    brazo_r_cond = (~palo) & (x < -0.108) & (z > 0.33) & (z < 0.72)
    brazo_r = malla.inundar((-0.150, 0.010, 0.37), brazo_r_cond).astype(float)
    # Hombros: transición suave hacia el torso
    hombro_l = suave(0.095, 0.125, x) * suave(0.62, 0.66, z) * suave(0.76, 0.73, z)
    hombro_r = suave(-0.090, -0.120, x) * suave(0.62, 0.66, z) * suave(0.76, 0.73, z)
    brazo_l = np.maximum(brazo_l, hombro_l)
    brazo_r = np.maximum(brazo_r, hombro_r)

    lado_izq = suave(-0.025, 0.005, x)        # piernas: la separación va un poco a la derecha del eje (pies abiertos)
    piernas = suave(0.52, 0.44, z)
    no_brazos = 1.0 - np.maximum(brazo_l, brazo_r)

    compuertas = {}
    for suf, m in (('.L', brazo_l), ('.R', brazo_r)):
        for h in ('upper_arm', 'forearm', 'hand'):
            compuertas[f'DEF-{h}{suf}'] = m
    compuertas['DEF-shoulder.L'] = suave(0.02, 0.07, x) * suave(0.64, 0.68, z)
    compuertas['DEF-shoulder.R'] = suave(-0.02, -0.07, x) * suave(0.64, 0.68, z)
    for h in ('thigh', 'shin', 'foot', 'toe'):
        compuertas[f'DEF-{h}.L'] = lado_izq * piernas * no_brazos
        compuertas[f'DEF-{h}.R'] = (1.0 - lado_izq) * piernas * no_brazos
    for h in ('DEF-hips', 'DEF-spine.001', 'DEF-spine.002', 'DEF-spine.003', 'DEF-neck'):
        compuertas[h] = np.clip(no_brazos + 0.15, 0.0, 1.0)
    compuertas['DEF-head'] = suave(0.75, 0.78, z)

    # Rígido desde el borde del cuello de la camisa: la barbilla y la mandíbula (z≈0,78-0,81) se mueven solo con la
    # cabeza (pedido del usuario: la quijada no debe deformarse nunca). Por encima de z=0,775 no hay hombros.
    cabeza = suave(0.772, 0.782, z) * (1.0 - palo) * (1.0 - brazo_l)
    rigidos = [
        ('DEF-head', cabeza),
        ('DEF-hand.L', brazo_l * suave(0.150, 0.135, x) * suave(0.020, -0.015, y) * suave(0.53, 0.55, z)),
        ('palo', palo.astype(float)),
    ]
    return compuertas, rigidos


def calcular_pesos(verts_norm, tris):
    """Pesos (nombres, W por vértice) de la malla normalizada."""
    malla = Malla(verts_norm, tris)
    seg = segmentos()
    huesos = [(n, seg[n][0], seg[n][1], r) for n, r in RADIOS.items()]
    compuertas, rigidos = mascaras(malla)
    return pesos_envolvente(malla, huesos, compuertas, rigidos, suavizado=3)
