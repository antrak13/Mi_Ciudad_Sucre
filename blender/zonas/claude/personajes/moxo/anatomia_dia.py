"""Medidas de Benito María de Moxó de día (Guía #24) sobre la malla Tripo, en unidades normalizadas (altura = 1).
Ejes de Blender: frente hacia -Y, izquierda de él +X, arriba +Z. Numpy puro.

La malla está de pie, de frente, con los dos antebrazos levantados delante del pecho: la mano derecha sostiene la lupa
y la izquierda la concha, a la altura del mentón. Sotana hasta los pies (solo asoman las punteras), roquete de encaje
hasta medio muslo y una capa morada larga que cuelga de los hombros hasta el suelo por detrás.
"""
import numpy as np

from pesos_envolvente import suave, dist_segmento, Malla, pesos_envolvente, reparto_falda, mascaras_pies

X0 = 0.04    # eje vertical del cuerpo (Tripo centra la caja; la concha y la capa la corren)
CORTE_CABEZA = 0.808  # debajo del mentón y encima del cuello de la sotana: de ahí arriba, cabeza rígida

LUPA = ((0.035, -0.205, 0.765), (0.095, -0.235, 0.840))  # del mango a la lente
CONCHA = (0.180, -0.215, 0.790)                          # centro de la concha, en la mano izquierda


def _p(x, y, z):
    return (X0 + x, y, z)


def segmentos():
    s = {
        'root': (_p(0, 0, 0), _p(0, 0, 0.08)),
        'DEF-hips': (_p(0, 0.0, 0.480), _p(0, 0.0, 0.550)),
        'DEF-spine.001': (_p(0, 0.0, 0.550), _p(0, 0.0, 0.620)),
        'DEF-spine.002': (_p(0, 0.0, 0.620), _p(0, 0.0, 0.690)),
        'DEF-spine.003': (_p(0, 0.0, 0.690), _p(0, -0.005, 0.780)),
        'DEF-neck': (_p(0, -0.005, 0.780), _p(0.005, -0.015, 0.840)),
        'DEF-head': (_p(0.005, -0.015, 0.840), _p(0.005, -0.015, 1.0)),

        # Brazo derecho: codo junto al cuerpo, mano con la lupa delante del mentón
        'DEF-shoulder.R': (_p(-0.020, 0.005, 0.770), _p(-0.105, 0.010, 0.765)),
        'DEF-upper_arm.R': (_p(-0.105, 0.010, 0.765), (-0.055, -0.060, 0.635)),
        'DEF-forearm.R': ((-0.055, -0.060, 0.635), (0.010, -0.165, 0.715)),
        'DEF-hand.R': ((0.010, -0.165, 0.715), (0.055, -0.210, 0.775)),

        # Brazo izquierdo: mano con la concha
        'DEF-shoulder.L': (_p(0.020, 0.005, 0.770), _p(0.110, 0.010, 0.765)),
        'DEF-upper_arm.L': (_p(0.110, 0.010, 0.765), (0.195, -0.050, 0.630)),
        'DEF-forearm.L': ((0.195, -0.050, 0.630), (0.180, -0.150, 0.710)),
        'DEF-hand.L': ((0.180, -0.150, 0.710), (0.170, -0.200, 0.770)),

        # Piernas bajo la sotana: cuentan las punteras y el vuelo del ruedo
        'DEF-thigh.R': (_p(-0.055, 0.0, 0.480), _p(-0.075, -0.005, 0.265)),
        'DEF-shin.R': (_p(-0.075, -0.005, 0.265), _p(-0.115, 0.020, 0.060)),
        'DEF-foot.R': (_p(-0.115, 0.020, 0.060), _p(-0.120, -0.070, 0.020)),
        'DEF-toe.R': (_p(-0.120, -0.070, 0.020), _p(-0.125, -0.120, 0.010)),
        'DEF-thigh.L': (_p(0.055, 0.0, 0.480), _p(0.075, -0.005, 0.265)),
        'DEF-shin.L': (_p(0.075, -0.005, 0.265), _p(0.100, 0.020, 0.060)),
        'DEF-foot.L': (_p(0.100, 0.020, 0.060), _p(0.110, -0.070, 0.020)),
        'DEF-toe.L': (_p(0.110, -0.070, 0.020), _p(0.115, -0.120, 0.010)),
    }
    try:
        from kit_ual import dedos_mano_desde_muneca
        s.update(dedos_mano_desde_muneca((0.010, -0.165, 0.715), (0.45, -0.45, 0.75), (-0.8, 0.0, 0.3), -1, 0.40))
        s.update(dedos_mano_desde_muneca((0.180, -0.150, 0.710), (-0.1, -0.55, 0.80), (0.9, 0.0, 0.2), 1, 0.40))
    except ImportError:  # fuera de Blender (pruebas de pesos)
        pass
    return s


HUESOS_EXTRA = []

# Antebrazo y mano (con la lupa o la concha) se despegan del pecho: Tripo los cose al torso y al cordón del pectoral.
# Esas caras se desdoblan (`kit_personaje.desdoblar_costuras`): ni membrana al bajar las manos ni agujeros en el pecho.
PIEZAS_SUELTAS = [
    (('DEF-hand.R', 'DEF-forearm.R'), ('DEF-upper_arm.R', 'DEF-shoulder.R')),
    (('DEF-hand.L', 'DEF-forearm.L'), ('DEF-upper_arm.L', 'DEF-shoulder.L')),
]

RADIOS = {
    'DEF-hips': 0.10, 'DEF-spine.001': 0.10, 'DEF-spine.002': 0.10, 'DEF-spine.003': 0.10,
    'DEF-neck': 0.035, 'DEF-head': 0.07,
    'DEF-shoulder.L': 0.035, 'DEF-upper_arm.L': 0.04, 'DEF-forearm.L': 0.035, 'DEF-hand.L': 0.035,
    'DEF-shoulder.R': 0.035, 'DEF-upper_arm.R': 0.04, 'DEF-forearm.R': 0.035, 'DEF-hand.R': 0.035,
}


def mascaras(malla, colores):
    P = malla.pos
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    seg = segmentos()
    claro = (np.asarray(colores).mean(axis=1) > 0.33).astype(float)
    for _ in range(2):
        claro = 0.5 * claro + 0.5 * malla.promedio_vecinos(claro)

    # Brazos: lo que queda cerca del antebrazo y la mano, conectado a la mano (las mangas del roquete van con el
    # antebrazo; el brazo de arriba lo tapa la capa, que sigue al hombro solo en parte)
    brazos = {}
    for suf in ('.L', '.R'):
        d_ante = np.minimum(dist_segmento(P, *seg[f'DEF-forearm{suf}']) / 0.05,
                            dist_segmento(P, *seg[f'DEF-hand{suf}']) / 0.075)  # la mano, con los dedos cerrados
        cerca = (d_ante < 1.0) & (y < -0.04)
        semilla = seg[f'DEF-hand{suf}'][0]
        brazos[suf] = malla.inundar(semilla, cerca).astype(float)
    lente = (np.linalg.norm(P - np.array(LUPA[1]), axis=1) < 0.065) & (x < 0.13) & (y < -0.17)  # aro inclinado
    lupa = (dist_segmento(P, *LUPA) < 0.032) | lente
    concha = np.linalg.norm(P - np.array(CONCHA), axis=1) < 0.045

    compuertas = {}
    torso = 1.0 - np.maximum(brazos['.L'], brazos['.R'])
    for suf in ('.L', '.R'):
        compuertas[f'DEF-forearm{suf}'] = brazos[suf]
        compuertas[f'DEF-hand{suf}'] = brazos[suf]
        compuertas[f'DEF-upper_arm{suf}'] = np.clip(brazos[suf] + 0.6 * suave(-0.02, -0.06, y), 0.0, 1.0)
    for h in ('DEF-hips', 'DEF-spine.001', 'DEF-spine.002', 'DEF-spine.003', 'DEF-neck'):
        compuertas[h] = np.clip(torso + 0.1, 0.0, 1.0)
    compuertas['DEF-head'] = suave(0.79, 0.82, z) * torso

    # Sotana y capa: arriba con la cadera; el ruedo de la sotana sigue a las piernas. La capa de atrás (y > 0,06)
    # cuelga de los hombros y no sigue a las piernas: va repartida entre la espalda y la cadera.
    detras = suave(0.04, 0.09, y) * (1.0 - suave(0.0, -0.02, y))
    falda = suave(0.50, 0.42, z) * (1.0 - detras)
    alto = suave(0.10, 0.72, z)
    reparto_capa = {'DEF-spine.003': 0.15 + 0.55 * alto, 'DEF-spine.002': 0.20 * alto, 'DEF-hips': 0.85 - 0.75 * alto}
    capa = detras * (z < 0.74) * torso
    # Roquete: cuelga del torso
    roquete = (claro > 0.5) * suave(0.62, 0.58, z) * (z > 0.40) * torso
    reparto_roquete = {'DEF-spine.001': 0.6, 'DEF-hips': 0.4}

    pies = mascaras_pies(P, seg, claro < 0.5)
    cabeza = suave(CORTE_CABEZA - 0.006, CORTE_CABEZA + 0.006, z) * torso * (y > -0.165)

    mezclas = [(falda, reparto_falda(P, X0)), (capa, reparto_capa), (roquete, reparto_roquete)]
    rigidos = [
        ('DEF-head', cabeza),
        ('DEF-hand.R', lupa.astype(float)),
        ('DEF-hand.L', concha.astype(float)),
        ('DEF-shin.R', pies['.R'][1].astype(float)),
        ('DEF-shin.L', pies['.L'][1].astype(float)),
        ('DEF-foot.R', pies['.R'][0].astype(float)),
        ('DEF-foot.L', pies['.L'][0].astype(float)),
    ]
    return compuertas, mezclas, rigidos


def calcular_pesos(verts_norm, tris, colores):
    malla = Malla(verts_norm, tris)
    col_u = np.zeros((malla.n, 3))
    col_u[malla.uid] = colores
    seg = segmentos()
    huesos = [(n, seg[n][0], seg[n][1], r) for n, r in RADIOS.items()]
    compuertas, mezclas, rigidos = mascaras(malla, col_u)
    return pesos_envolvente(malla, huesos, compuertas, rigidos, suavizado=3, mezclas=mezclas)
