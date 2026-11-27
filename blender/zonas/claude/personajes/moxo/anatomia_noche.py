"""Medidas de Moxó de noche (Guía #24, huida del 25 de mayo de 1809) sobre la malla Tripo, normalizadas (altura = 1).
Ejes de Blender: frente hacia -Y, izquierda de él +X, arriba +Z. Numpy puro.

La malla está a medio paso (pie izquierdo adelante), con la mano derecha apretando la capa oscura contra el pecho y el
brazo izquierdo caído, un poco abierto. Sin roquete: sotana morada hasta los tobillos y capa marrón hasta el suelo.
"""
import numpy as np

from pesos_envolvente import (
    suave, dist_segmento, Malla, pesos_envolvente, reparto_falda, mascaras_pies, caras_a_ras_del_suelo,
)

X0 = 0.03            # eje vertical del cuerpo
CORTE_CABEZA = 0.815  # debajo del mentón, encima del cuello de la sotana


def _p(x, y, z):
    return (X0 + x, y, z)


def segmentos():
    s = {
        'root': (_p(0, 0, 0), _p(0, 0, 0.08)),
        'DEF-hips': (_p(0, -0.010, 0.480), _p(0, -0.010, 0.550)),
        'DEF-spine.001': (_p(0, -0.010, 0.550), _p(0.005, -0.012, 0.620)),
        'DEF-spine.002': (_p(0.005, -0.012, 0.620), _p(0.012, -0.015, 0.690)),
        'DEF-spine.003': (_p(0.012, -0.015, 0.690), _p(0.025, -0.025, 0.790)),
        'DEF-neck': (_p(0.025, -0.025, 0.790), _p(0.032, -0.040, 0.845)),
        'DEF-head': (_p(0.032, -0.040, 0.845), _p(0.035, -0.040, 1.0)),

        # Brazo derecho: puño en el pecho apretando la capa (no se anima)
        'DEF-shoulder.R': (_p(0.010, -0.010, 0.775), _p(-0.075, -0.005, 0.765)),
        'DEF-upper_arm.R': (_p(-0.075, -0.005, 0.765), (-0.045, -0.050, 0.620)),
        'DEF-forearm.R': ((-0.045, -0.050, 0.620), (0.050, -0.115, 0.680)),
        'DEF-hand.R': ((0.050, -0.115, 0.680), (0.085, -0.135, 0.735)),

        # Brazo izquierdo: caído, algo abierto
        'DEF-shoulder.L': (_p(0.040, -0.010, 0.775), (0.140, 0.000, 0.765)),
        'DEF-upper_arm.L': ((0.140, 0.000, 0.765), (0.165, 0.010, 0.615)),
        'DEF-forearm.L': ((0.165, 0.010, 0.615), (0.200, 0.020, 0.515)),
        'DEF-hand.L': ((0.200, 0.020, 0.515), (0.235, 0.020, 0.450)),

        # Piernas a medio paso: la izquierda adelante, la derecha atrás
        'DEF-thigh.L': (_p(0.060, -0.020, 0.480), (0.135, -0.090, 0.270)),
        'DEF-shin.L': ((0.135, -0.090, 0.270), (0.165, -0.125, 0.070)),
        'DEF-foot.L': ((0.165, -0.125, 0.070), (0.195, -0.195, 0.025)),
        'DEF-toe.L': ((0.195, -0.195, 0.025), (0.215, -0.230, 0.012)),
        'DEF-thigh.R': (_p(-0.060, -0.005, 0.480), (-0.090, 0.040, 0.270)),
        'DEF-shin.R': ((-0.090, 0.040, 0.270), (-0.135, 0.115, 0.080)),
        'DEF-foot.R': ((-0.135, 0.115, 0.080), (-0.155, 0.055, 0.030)),
        'DEF-toe.R': ((-0.155, 0.055, 0.030), (-0.165, 0.020, 0.015)),
    }
    try:
        from kit_ual import dedos_mano_desde_muneca
        s.update(dedos_mano_desde_muneca((0.050, -0.115, 0.680), (0.5, -0.4, 0.75), (-0.6, -0.6, 0.2), -1, 0.40))
        s.update(dedos_mano_desde_muneca((0.200, 0.020, 0.515), (0.45, 0.0, -0.9), (-0.3, -0.9, 0.0), 1, 0.40))
    except ImportError:  # fuera de Blender (pruebas de pesos)
        pass
    return s


HUESOS_EXTRA = []
ALZADO = {'DEF-foot.R': 0.015}  # el pie de atrás, a medio paso, apenas levantado del suelo

# El brazo izquierdo se despega de la capa al llamar a los clérigos: costuras desdobladas, como en el de día.
PIEZAS_SUELTAS = [
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
    col = np.asarray(colores)
    lum = col.mean(axis=1)
    # Sotana morada (más azul que verde) y piel; la capa es marrón (más verde que azul)
    morado = (col[:, 2] > col[:, 1]).astype(float)
    for _ in range(2):
        morado = 0.5 * morado + 0.5 * malla.promedio_vecinos(morado)
    piel = col[:, 0] > 0.45

    # Brazo izquierdo: desde la mano, lo que está cerca del antebrazo, la mano y el brazo, por fuera de la capa
    d_l = np.minimum.reduce([dist_segmento(P, *seg['DEF-upper_arm.L']) / 0.045,
                             dist_segmento(P, *seg['DEF-forearm.L']) / 0.045,
                             dist_segmento(P, *seg['DEF-hand.L']) / 0.06])
    # Por encima del codo la capa tapa el brazo: allí solo la manga morada y la piel van con el brazo
    brazo_l = malla.inundar(seg['DEF-hand.L'][1], (d_l < 1.0) & (x > 0.115) &
                            ((z < 0.66) | (morado > 0.5) | piel)).astype(float)
    # Puño derecho: la mano y la capa que aprieta van con el pecho (el brazo derecho no se anima)
    compuertas = {}
    for h in ('DEF-upper_arm.L', 'DEF-forearm.L', 'DEF-hand.L'):
        compuertas[h] = brazo_l
    for h in ('DEF-upper_arm.R', 'DEF-forearm.R', 'DEF-hand.R', 'DEF-shoulder.R'):
        compuertas[h] = np.zeros_like(x)
    torso = 1.0 - brazo_l
    for h in ('DEF-hips', 'DEF-spine.001', 'DEF-spine.002', 'DEF-spine.003', 'DEF-neck'):
        compuertas[h] = np.clip(torso + 0.1, 0.0, 1.0)
    compuertas['DEF-head'] = suave(0.80, 0.83, z) * torso

    # Sotana: el ruedo sigue a las piernas. Capa: cuelga de los hombros; por detrás y a los lados no sigue a las piernas.
    detras = suave(0.04, 0.10, y)
    falda = suave(0.52, 0.44, z) * (1.0 - detras)
    alto = suave(0.10, 0.74, z)
    reparto_capa = {'DEF-spine.003': 0.15 + 0.55 * alto, 'DEF-spine.002': 0.20 * alto, 'DEF-hips': 0.85 - 0.75 * alto}
    capa = detras * (z < 0.76) * torso

    pies = mascaras_pies(P, seg, (lum < 0.3) & (morado < 0.5), radio_pie=0.07, z_suela=0.035)
    cabeza = suave(CORTE_CABEZA - 0.006, CORTE_CABEZA + 0.006, z) * torso

    mezclas = [(falda, reparto_falda(P, X0, y0=-0.02)), (capa, reparto_capa)]
    rigidos = [
        ('DEF-head', cabeza),
        ('DEF-hand.L', brazo_l * (dist_segmento(P, *seg['DEF-hand.L']) < 0.05)),
        ('DEF-shin.R', pies['.R'][1].astype(float)),
        ('DEF-shin.L', pies['.L'][1].astype(float)),
        ('DEF-foot.R', pies['.R'][0].astype(float)),
        ('DEF-foot.L', pies['.L'][0].astype(float)),
    ]
    return compuertas, mezclas, rigidos


def caras_extra(verts_norm, tris, nombres, W):
    """El fondo interior de la sotana, a ras del suelo junto a los zapatos (ver `caras_a_ras_del_suelo`)."""
    seg = segmentos()
    pies = [(seg[f'DEF-foot{s}'][0], seg[f'DEF-toe{s}'][1]) for s in ('.L', '.R')]
    return caras_a_ras_del_suelo(verts_norm, tris, nombres, W, 0.045, pies, 0.11,
                                 excluir=('DEF-foot.L', 'DEF-foot.R', 'DEF-shin.L', 'DEF-shin.R'))


def calcular_pesos(verts_norm, tris, colores):
    malla = Malla(verts_norm, tris)
    col_u = np.zeros((malla.n, 3))
    col_u[malla.uid] = colores
    seg = segmentos()
    huesos = [(n, seg[n][0], seg[n][1], r) for n, r in RADIOS.items()]
    compuertas, mezclas, rigidos = mascaras(malla, col_u)
    return pesos_envolvente(malla, huesos, compuertas, rigidos, suavizado=3, mezclas=mezclas)
