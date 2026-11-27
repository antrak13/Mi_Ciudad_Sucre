"""Pesos de piel con transiciones topológicas y cuatro influencias por vértice."""
import numpy as np


def suave(a, b, x):
    u = np.clip((x - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def segmento(p, a, b):
    eje = b - a
    t = np.clip((p - a) @ eje / (eje @ eje), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * eje), axis=1), t


def guardar_pesos(malla, rig, huesos, aristas, w, conservar, pases=5):
    a, b = np.concatenate((aristas, aristas[:, ::-1]), axis=0).T
    grado = np.maximum(1, np.bincount(a, minlength=len(w)))
    for _ in range(pases):
        promedio = np.zeros_like(w)
        np.add.at(promedio, a, w[b])
        w[~conservar] = .60 * w[~conservar] + .40 * (promedio / grado[:, None])[~conservar]
    mejores = np.argsort(w, axis=1)[:, -4:]
    valores = np.take_along_axis(w, mejores, axis=1)
    valores[valores < .0005] = 0
    valores /= valores.sum(axis=1, keepdims=True)

    grupos = {i: malla.vertex_groups.new(name=huesos[i]) for i in np.unique(mejores[valores > 0])}
    for vertice, (ii, vv) in enumerate(zip(mejores, valores)):
        for i, v in zip(ii, vv):
            if v:
                grupos[i].add([vertice], float(v), 'REPLACE')
    mod = malla.modifiers.new('Deformación UAL', 'ARMATURE')
    mod.object = rig
