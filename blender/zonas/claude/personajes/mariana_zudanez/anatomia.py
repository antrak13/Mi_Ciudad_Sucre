"""Medidas de Mariana Zudáñez (Guía #3) sobre la malla Tripo, en unidades normalizadas (altura total = 1).
Ejes de Blender: torso hacia -Y, izquierda de ella +X, arriba +Z. Numpy puro.

La malla viene en la pose de la lámina: brazo izquierdo extendido señalando hacia +X, cabeza girada ~80° hacia ese
lado, mano derecha apretando el mantón contra el pecho y los pies muy abiertos (paso). Bajo la falda no hay piernas:
solo los zapatos. El eje del cuerpo no pasa por x = 0 (Tripo centra la caja, y el brazo la alarga): X0.
"""
import numpy as np

from pesos_envolvente import suave, Malla, pesos_envolvente, reparto_falda, mascaras_pies

X0 = -0.095                # eje vertical del cuerpo
GIRO_CABEZA_REPOSO = 1.35  # rad hacia su izquierda (+X); para mirar al frente se gira el cuello en sentido contrario
CABEZA_Z = 0.865           # debajo, el cuello; encima, cabeza, peinado y aretes rígidos


def _p(x, y, z):
    return (X0 + x, y, z)


def segmentos():
    s = {
        'root': (_p(0, 0, 0), _p(0, 0, 0.08)),
        'DEF-hips': (_p(0, 0.0, 0.495), _p(0, 0.0, 0.565)),
        'DEF-spine.001': (_p(0, 0.0, 0.565), _p(0, -0.005, 0.635)),
        'DEF-spine.002': (_p(0, -0.005, 0.635), _p(0, -0.005, 0.705)),
        'DEF-spine.003': (_p(0, -0.005, 0.705), _p(0, 0.0, 0.795)),
        'DEF-neck': (_p(0, 0.0, 0.795), _p(-0.003, 0.0, 0.862)),
        'DEF-head': (_p(-0.003, 0.0, 0.862), _p(-0.003, 0.0, 1.0)),

        # Brazo izquierdo extendido hacia +X (señalando)
        'DEF-shoulder.L': (_p(0.010, 0.0, 0.790), (0.020, 0.008, 0.792)),
        'DEF-upper_arm.L': ((0.020, 0.008, 0.792), (0.125, 0.008, 0.800)),
        'DEF-forearm.L': ((0.125, 0.008, 0.800), (0.240, -0.004, 0.826)),
        'DEF-hand.L': ((0.240, -0.004, 0.826), (0.300, -0.010, 0.840)),

        # Brazo derecho doblado bajo el mantón, puño en el pecho (no se anima: queda fijo al torso)
        'DEF-shoulder.R': (_p(-0.010, 0.0, 0.790), (-0.200, 0.008, 0.785)),
        'DEF-upper_arm.R': ((-0.200, 0.008, 0.785), (-0.240, 0.0, 0.640)),
        'DEF-forearm.R': ((-0.240, 0.0, 0.640), (-0.160, -0.080, 0.660)),
        'DEF-hand.R': ((-0.160, -0.080, 0.660), (-0.100, -0.100, 0.680)),

        # Piernas (ocultas por la falda): solo cuentan los zapatos y el vuelo del ruedo
        'DEF-thigh.R': ((-0.170, 0.0, 0.490), (-0.200, -0.010, 0.270)),
        'DEF-shin.R': ((-0.200, -0.010, 0.270), (-0.220, 0.030, 0.065)),
        'DEF-foot.R': ((-0.220, 0.030, 0.065), (-0.235, -0.060, 0.020)),
        'DEF-toe.R': ((-0.235, -0.060, 0.020), (-0.240, -0.103, 0.010)),
        'DEF-thigh.L': ((-0.020, 0.0, 0.490), (0.050, 0.0, 0.270)),
        'DEF-shin.L': ((0.050, 0.0, 0.270), (0.110, 0.012, 0.065)),
        'DEF-foot.L': ((0.110, 0.012, 0.065), (0.160, -0.020, 0.020)),
        'DEF-toe.L': ((0.160, -0.020, 0.020), (0.203, -0.045, 0.010)),
    }
    try:
        from kit_ual import dedos_mano_desde_muneca
        s.update(dedos_mano_desde_muneca((0.240, -0.004, 0.826), (1.0, -0.05, 0.12), (0.0, 0.0, -1.0), 1, 0.45))
        s.update(dedos_mano_desde_muneca((-0.160, -0.080, 0.660), (0.6, -0.3, 0.1), (0.0, 1.0, 0.0), -1, 0.45))
    except ImportError:  # fuera de Blender (pruebas de pesos)
        pass
    return s


HUESOS_EXTRA = []

RADIOS = {
    'DEF-hips': 0.09, 'DEF-spine.001': 0.08, 'DEF-spine.002': 0.08, 'DEF-spine.003': 0.09,
    'DEF-neck': 0.035, 'DEF-head': 0.07,
    'DEF-shoulder.L': 0.03, 'DEF-upper_arm.L': 0.035, 'DEF-forearm.L': 0.03, 'DEF-hand.L': 0.03,
}


def mascaras(malla, colores):
    P = malla.pos
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    seg = segmentos()

    # Mantón: textura clara, suavizada sobre la malla (los bordados oscuros quedan dentro)
    claro = (np.asarray(colores).mean(axis=1) > 0.33).astype(float)
    for _ in range(4):
        claro = 0.5 * claro + 0.5 * malla.promedio_vecinos(claro)
    cara_manos = (z > 0.80) | (x > 0.03)   # piel de la cara y la mano que señala no son mantón
    manton = (claro > 0.5) & ~cara_manos & (z > 0.25)

    # Brazo izquierdo: desde la mano, por todo lo que está a la derecha del hombro y por encima del mantón
    brazo_l = malla.inundar((0.30, -0.01, 0.84), (x > 0.022) & (z > 0.74)).astype(float)
    brazo_l = np.maximum(brazo_l, suave(-0.01, 0.03, x) * suave(0.74, 0.77, z) * (z < 0.86))

    compuertas = {}
    for h in ('DEF-upper_arm.L', 'DEF-forearm.L', 'DEF-hand.L'):
        compuertas[h] = brazo_l
    compuertas['DEF-shoulder.L'] = suave(X0 + 0.04, X0 + 0.09, x) * suave(0.74, 0.77, z)
    torso = 1.0 - brazo_l
    for h in ('DEF-hips', 'DEF-spine.001', 'DEF-spine.002', 'DEF-spine.003', 'DEF-neck'):
        compuertas[h] = np.clip(torso + 0.1, 0.0, 1.0)
    compuertas['DEF-head'] = suave(0.84, 0.87, z) * (1.0 - brazo_l)

    # Falda: cadera arriba; hacia el ruedo, cada lado sigue a su muslo y a su canilla (vuelo al caminar)
    falda = suave(0.58, 0.50, z) * (1.0 - manton)
    # Mantón: cuelga de los hombros (no de la cadera)
    alto = suave(0.45, 0.72, z)
    reparto_manton = {'DEF-spine.003': 0.45 + 0.35 * alto, 'DEF-spine.002': 0.55 - 0.35 * alto}

    # Zapatos y tobillos rígidos con su pierna (las costuras con el ruedo se cortan al construir)
    pies = mascaras_pies(P, seg, claro < 0.5)

    # La cara mira a +X: del lado de la cara la mandíbula baja hasta z≈0.84, así que el corte baja ahí (si no, la
    # barbilla se queda con el cuello y se estira como un pico al girar la cabeza)
    lado_cara = suave(X0 + 0.025, X0 + 0.045, x) * (x < 0.0)
    corte = CABEZA_Z - 0.024 * lado_cara
    cabeza = suave(corte - 0.008, corte + 0.006, z) * (1.0 - brazo_l) * (x < 0.0)

    mezclas = [(falda, reparto_falda(P, X0)), (manton.astype(float), reparto_manton)]
    rigidos = [
        ('DEF-head', cabeza),
        ('DEF-hand.L', brazo_l * suave(0.235, 0.25, x)),
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
