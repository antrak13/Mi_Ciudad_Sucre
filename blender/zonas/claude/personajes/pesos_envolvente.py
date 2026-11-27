"""Pesos de piel por envolventes para personajes estáticos (Tripo y similares) que se riggean con el esqueleto UAL.

Numpy puro (sin bpy): se puede probar fuera de Blender. Cada hueso tiene un segmento (cabeza, cola) y un radio; el peso
crudo de un vértice cae con la distancia al segmento medida en radios. Las *compuertas* (máscaras 0..1 por hueso)
impiden que un hueso tome vértices que no le tocan (el brazo no agarra la casaca, la pierna izquierda no agarra la
derecha) y las *piezas rígidas* (sombrero, palo, cabeza) van enteras a un hueso. Los vértices duplicados en las
costuras de UV comparten peso (se trabaja sobre posiciones únicas), así la malla nunca se abre.
"""
from collections import deque

import numpy as np


def suave(a, b, x):
    """Escalón suave de 0 (x=a) a 1 (x=b); admite a > b para el escalón invertido."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def dist_segmento(pts, a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / max(1e-12, float(ab @ ab)), 0.0, 1.0)
    return np.linalg.norm(pts - (a + t[:, None] * ab), axis=1)


def param_segmento(pts, a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    ab = b - a
    return ((pts - a) @ ab) / max(1e-12, float(ab @ ab))


class Malla:
    """Posiciones únicas (soldadas) y su grafo de vecinos, a partir de vértices y triángulos."""

    def __init__(self, verts, tris, decimales=5):
        self.verts = np.asarray(verts, dtype=np.float64)
        self.uid = np.unique(self.verts.round(decimales), axis=0, return_inverse=True)[1].ravel()
        self.n = int(self.uid.max()) + 1
        self.pos = np.zeros((self.n, 3))
        self.pos[self.uid] = self.verts
        t = self.uid[np.asarray(tris, dtype=np.int64)]
        aristas = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
        aristas = np.concatenate([aristas, aristas[:, ::-1]])
        aristas = aristas[aristas[:, 0] != aristas[:, 1]]
        aristas = np.unique(aristas, axis=0)
        orden = np.argsort(aristas[:, 0], kind='stable')
        self.vec_dst = aristas[orden, 1]
        self.vec_ini = np.searchsorted(aristas[orden, 0], np.arange(self.n + 1))
        self.grado = np.diff(self.vec_ini)

    def vecinos(self, i):
        return self.vec_dst[self.vec_ini[i]:self.vec_ini[i + 1]]

    def promedio_vecinos(self, valores):
        """Media de los vecinos de cada posición única (valores: (n,) o (n, k))."""
        src = np.repeat(np.arange(self.n), self.grado)
        suma = np.zeros_like(valores, dtype=np.float64)
        np.add.at(suma, src, valores[self.vec_dst])
        div = np.maximum(self.grado, 1).reshape((-1,) + (1,) * (valores.ndim - 1))
        return suma / div

    def inundar(self, semilla_xyz, condicion):
        """Componente conexa desde la posición más cercana a `semilla_xyz`, avanzando solo por donde `condicion`
        (máscara booleana sobre posiciones únicas) es verdadera. Devuelve una máscara booleana sobre posiciones únicas."""
        s = int(np.argmin(np.linalg.norm(self.pos - np.asarray(semilla_xyz), axis=1)))
        vis = np.zeros(self.n, dtype=bool)
        vis[s] = True
        cola = deque([s])
        while cola:
            u = cola.popleft()
            for v in self.vecinos(u):
                if not vis[v] and condicion[v]:
                    vis[v] = True
                    cola.append(v)
        return vis

    def a_vertices(self, valores_unicos):
        return valores_unicos[self.uid]


def pesos_envolvente(malla, huesos, compuertas=None, rigidos=None, suavizado=3, max_influencias=4, potencia=4.0,
                     mezclas=None):
    """Calcula la matriz de pesos (vértices × huesos) normalizada a `max_influencias` por vértice.

    huesos: lista de (nombre, cabeza, cola, radio), en las mismas unidades que la malla.
    compuertas: {nombre: máscara (n_unicos,) 0..1}; sin compuerta, el hueso puede tomar cualquier vértice.
    mezclas: lista ordenada de (máscara (n_unicos,) 0..1, {nombre: peso o arreglo (n_unicos,)}): reparto fijo (falda,
        mantón) que reemplaza a la envolvente donde la máscara vale 1; se aplican después del suavizado.
    rigidos: lista ordenada de (nombre, máscara (n_unicos,) 0..1); se aplican al final, la última manda.
    Devuelve (nombres, W) con W de forma (n_vertices, n_huesos).
    """
    compuertas = compuertas or {}
    rigidos = rigidos or []
    mezclas = mezclas or []
    nombres = [h[0] for h in huesos]
    for nombre in [r[0] for r in rigidos] + [n for _, rep in mezclas for n in rep]:
        if nombre not in nombres:
            nombres.append(nombre)
    idx = {n: i for i, n in enumerate(nombres)}
    P = malla.pos
    W = np.zeros((malla.n, len(nombres)))
    for nombre, a, b, r in huesos:
        d = dist_segmento(P, a, b) / r
        W[:, idx[nombre]] = compuertas.get(nombre, 1.0) / (1.0 + d ** potencia)
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-12)
    for _ in range(suavizado):
        W = 0.5 * W + 0.5 * malla.promedio_vecinos(W)
        for nombre, m in compuertas.items():  # el suavizado no puede cruzar una compuerta cerrada
            W[:, idx[nombre]] *= np.clip(m, 0.0, 1.0) ** 0.5
        W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-12)
    for m, reparto in mezclas:
        objetivo = np.zeros_like(W)
        for nombre, w in reparto.items():
            objetivo[:, idx[nombre]] = w
        objetivo /= np.maximum(objetivo.sum(axis=1, keepdims=True), 1e-12)
        m = np.clip(m, 0.0, 1.0)[:, None]
        W = (1.0 - m) * W + m * objetivo
    for nombre, m in rigidos:
        m = np.clip(m, 0.0, 1.0)[:, None]
        uno = np.zeros(len(nombres))
        uno[idx[nombre]] = 1.0
        W = (1.0 - m) * W + m * uno
    # Quedarse con las `max_influencias` mayores y normalizar
    if W.shape[1] > max_influencias:
        corte = np.partition(W, -max_influencias, axis=1)[:, -max_influencias][:, None]
        W = np.where(W >= corte, W, 0.0)
    W[W < 0.01] = 0.0
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-12)
    return nombres, malla.a_vertices(W)


def caras_entre_piezas(tris, nombres, W, pieza, permitidos=()):
    """Triángulos que cosen una pieza rígida (p. ej. el palo; `pieza` puede ser un hueso o una lista de huesos) con el
    resto de la malla, salvo con los huesos
    `permitidos` (la mano que la sujeta). Tripo funde las piezas que se tocan; si no se cortan esas caras, se
    estiran como una membrana cuando la pieza se separa del cuerpo."""
    tris = np.asarray(tris)
    piezas = [pieza] if isinstance(pieza, str) else list(pieza)  # varios huesos = una sola pieza (pie + canilla)
    en_pieza = W[:, [nombres.index(p) for p in piezas]].sum(axis=1) > 0.5
    dominante = np.array(nombres, dtype=object)[np.argmax(W, axis=1)]
    permitido = np.isin(dominante, list(permitidos)) & ~en_pieza  # solo cuentan los vértices de fuera de la pieza
    mezcla = en_pieza[tris].any(axis=1) & ~en_pieza[tris].all(axis=1)
    toca_permitido = permitido[tris].any(axis=1)
    return np.nonzero(mezcla & ~toca_permitido)[0]


def caras_tapa_inferior(verts, tris, nombres, W, z_max, excluir=()):
    """Triángulos de una «tapa» que cierra por abajo una prenda larga (Tripo cierra la falda con una superficie
    horizontal): bajos (todos sus vértices por debajo de `z_max`), mirando al suelo y sin vértices de los huesos
    `excluir` (las suelas de los zapatos también miran al suelo)."""
    verts = np.asarray(verts)
    tris = np.asarray(tris)
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    n = np.cross(b - a, c - a)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    bajo = (verts[tris][:, :, 2] < z_max).all(axis=1)
    js = [nombres.index(e) for e in excluir if e in nombres]
    de_excluido = (W[:, js].max(axis=1) > 0.3) if js else np.zeros(len(verts), dtype=bool)
    return np.nonzero(bajo & (n[:, 2] < -0.5) & ~de_excluido[tris].any(axis=1))[0]


def reparto_falda(P, x0, y0=0.0, z_cadera=0.52, z_ruedo=0.08, muslo=0.32, canilla=0.10):
    """Reparto fijo de una falda o sotana larga: arriba va con la cadera; hacia el ruedo cada lado sigue a su muslo y a
    su canilla (vuelo al caminar). El ruedo de adelante y de atrás sigue menos a la pierna: al girar el muslo bajaría
    por debajo del suelo. Devuelve {hueso: peso (n,)} para usar en `mezclas`."""
    x, y, z = P[:, 0], P[:, 1] - y0, P[:, 2]
    lado_l = suave(x0 - 0.06, x0 + 0.06, x)
    extremos = suave(0.06, 0.16, np.abs(y))
    t = muslo * suave(z_cadera, z_ruedo, z) * (1.0 - 0.75 * extremos)
    c = canilla * suave(0.25, 0.06, z) * (1.0 - 0.75 * extremos)
    return {
        'DEF-hips': np.clip(1.0 - t - c, 0.0, 1.0) + 1e-6,
        'DEF-thigh.L': t * lado_l, 'DEF-thigh.R': t * (1.0 - lado_l),
        'DEF-shin.L': c * lado_l, 'DEF-shin.R': c * (1.0 - lado_l),
    }


def mascaras_pies(P, seg, oscuro, z_zapato=0.075, radio_pie=0.045, radio_tobillo=0.03, z_tobillo=0.15,
                  z_suela=None):
    """Pie visible bajo una prenda larga: el zapato (oscuro, junto al pie y el tacón) y el tobillo (junto al eje de
    la canilla, debajo del ruedo). Devuelve {'.L'|'.R': (zapato, tobillo)} como máscaras booleanas; van rígidos con
    su pie y su canilla, y las caras que los cosen al ruedo se cortan con `caras_entre_piezas`. `z_suela`: lo que
    está más bajo que eso junto al pie es suela y tacón, del color que sea."""
    z = P[:, 2]
    pies = {}
    for suf in ('.L', '.R'):
        tobillo_p = np.array(seg[f'DEF-foot{suf}'][0])
        d_pie = np.minimum(dist_segmento(P, tobillo_p, seg[f'DEF-toe{suf}'][1]),          # empeine y punta
                           dist_segmento(P, tobillo_p, tobillo_p * [1, 1, 0]) + 0.012)  # tacón, al suelo
        a, b = np.array(seg[f'DEF-shin{suf}'][0]), np.array(seg[f'DEF-shin{suf}'][1])
        d_canilla = dist_segmento(P, b + (a - b) * 0.35, b)
        tobillo = (d_canilla < radio_tobillo) & (z < z_tobillo) & (z >= 0.055)
        zapato = (z < z_zapato) & (d_pie < radio_pie) & (oscuro | (d_canilla < radio_tobillo)) & ~tobillo
        if z_suela is not None:
            zapato |= (z < z_suela) & (d_pie < radio_pie)
        pies[suf] = (zapato, tobillo)
    return pies


def caras_a_ras_del_suelo(verts, tris, nombres, W, z_max, segmentos_pie, radio, excluir=()):
    """Triángulos a ras del suelo (todos sus vértices bajo `z_max`) junto a los pies que no son zapato: el fondo con
    que Tripo cierra por dentro una sotana o una falda. Se quedarían en el suelo como tiras al levantar el pie."""
    verts = np.asarray(verts)
    tris = np.asarray(tris)
    cerca = np.zeros(len(verts), dtype=bool)
    for a, b in segmentos_pie:
        cerca |= dist_segmento(verts, a, b) < radio
    js = [nombres.index(e) for e in excluir if e in nombres]
    de_excluido = (W[:, js].max(axis=1) > 0.3) if js else np.zeros(len(verts), dtype=bool)
    bajo = (verts[tris][:, :, 2] < z_max).all(axis=1)
    return np.nonzero(bajo & cerca[tris].all(axis=1) & ~de_excluido[tris].any(axis=1))[0]
