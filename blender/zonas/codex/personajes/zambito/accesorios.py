"""Despega la vaina del calzón en las uniones de la malla de origen."""
from collections import defaultdict

import bpy
import numpy as np
from mathutils.geometry import tessellate_polygon

from rig import coordenadas, pigmento


def delimitar_vaina(malla, p):
    x, y, z = p.T
    alturas = [.166, .300, .393, .468, .564]
    eje_x = np.interp(z, alturas, [-.168, -.144, -.120, -.102, -.086])
    eje_y = np.interp(z, alturas, [.019, .001, -.014, -.034, -.029])
    radio = .015 + .031 * np.clip((z - .404) / .082, 0, 1)
    zona = (z >= .165) & (z < .57) & (np.hypot(x - eje_x, (y - eje_y) * .82) < radio)
    vecinos = [[] for _ in p]
    for arista in malla.data.edges:
        a, b = arista.vertices
        if zona[a] and zona[b]:
            vecinos[a].append(b)
            vecinos[b].append(a)
    punta = int(np.linalg.norm(p - (-.168, .019, .174), axis=1).argmin())
    seleccion = np.zeros(len(p), dtype=bool)
    cola = [punta]
    seleccion[punta] = True
    while cola:
        for v in vecinos[cola.pop()]:
            if not seleccion[v]:
                seleccion[v] = True
                cola.append(v)
    return seleccion


def separar_vaina(malla):
    """Duplica la costura y cierra las dos superficies internas. El exterior
    conserva las caras, posiciones, normales y UV del GLB de entrada.
    """
    origen = malla.data
    puntos = [v.co.copy() for v in origen.vertices]
    p = coordenadas(malla)
    color = pigmento(malla)
    seleccion = delimitar_vaina(malla, p)
    es_vaina = [sum(seleccion[i] for i in f.vertices) >= 2 for f in origen.polygons]
    if not .05 < np.mean(es_vaina) < .13:
        raise ValueError('La zona de la vaina no coincide con la malla de origen')

    caras = [tuple(f.vertices) for f in origen.polygons]
    frontera_cuerpo = {}
    aristas_vaina = set()
    uv_zona = defaultdict(list)
    normales_zona = {}
    normales = [n.vector.copy() for n in origen.corner_normals]
    for cara, dentro, f in zip(caras, es_vaina, origen.polygons):
        for v, loop in zip(cara, f.loop_indices):
            clave = (dentro, v)
            uv_zona[clave].append(origen.uv_layers.active.data[loop].uv.copy())
            if clave in normales_zona:
                normales_zona[clave] += normales[loop]
            else:
                normales_zona[clave] = normales[loop].copy()
        for a, b in zip(cara, cara[1:] + cara[:1]):
            clave = frozenset((a, b))
            if dentro:
                aristas_vaina.add(clave)
            else:
                frontera_cuerpo[clave] = (a, b)

    costura = [dire for clave, dire in frontera_cuerpo.items() if clave in aristas_vaina]
    siguiente = dict(costura)
    if len(siguiente) != len(costura) or set(siguiente) != set(siguiente.values()):
        raise ValueError('La costura de la vaina no forma contornos cerrados')

    # Compartir un índice de vértice solo si las dos caras pertenecen a la misma pieza.
    cuerpo = {v for cara, dentro in zip(caras, es_vaina) if not dentro for v in cara}
    pieza = {v for cara, dentro in zip(caras, es_vaina) if dentro for v in cara}
    duplicados = {}
    for i in sorted(cuerpo & pieza):
        duplicados[i] = len(puntos)
        puntos.append(puntos[i].copy())
    es_vertice_vaina = np.zeros(len(puntos), dtype=bool)
    for i in pieza:
        es_vertice_vaina[duplicados.get(i, i)] = True

    uv = [origen.uv_layers.active.data[l.index].uv.copy() for l in origen.loops]
    normales_cierres = []
    caras_nuevas = [
        tuple(duplicados.get(i, i) for i in cara) if dentro else cara
        for cara, dentro in zip(caras, es_vaina)
    ]
    ocupadas = {frozenset(f) for f in caras_nuevas}

    # Las superficies internas toman su color de un tramo intacto del calzón
    # o de la vaina. Extender los UV de la costura imprimiría metal en la tela.
    x, y, z = p.T
    tela = np.nonzero((x > -.116) & (x < -.058) & (z > .31) & (z < .447) & (y > .005))[0]
    tono_tela = np.median(color[tela], axis=0)
    punto_tela = min(
        (i for i in tela if i in cuerpo),
        key=lambda i: np.linalg.norm(color[i] - tono_tela) + .3 * np.linalg.norm(p[i] - (-.081, .022, .381)),
    )
    punto_vaina = min(pieza, key=lambda i: np.linalg.norm(p[i] - (-.155, .003, .256)))
    fondos = {False: uv_zona[(False, punto_tela)][0], True: uv_zona[(True, punto_vaina)][0]}
    while siguiente:
        semilla = next(iter(siguiente))
        contorno, i = [], semilla
        while True:
            contorno.append(i)
            i = siguiente.pop(i)
            if i == semilla:
                break
        # El contorno de la cara nueva debe tener orientación opuesta a la de
        # sus vecinas. La pieza usa la orientación inversa a la del calzón.
        for dentro, cont in [(False, contorno[::-1]), (True, contorno)]:
            for tri in tessellate_polygon([[puntos[i] for i in cont]]):
                original = [cont[j] for j in tri]
                cara = [duplicados.get(i, i) for i in original] if dentro else original
                clave = frozenset(cara)
                a, b, c = (puntos[i] for i in cara)
                if clave in ocupadas or (b - a).cross(c - a).length_squared < 1e-16:
                    continue
                ocupadas.add(clave)
                caras_nuevas.append(tuple(cara))
                u, v = fondos[dentro]
                uv.extend((u + puntos[i].y * .006, v + puntos[i].z * .003) for i in original)
                normales_cierres.extend(normales_zona[(dentro, i)].normalized() for i in original)

    mesh = bpy.data.meshes.new('Zambito')
    mesh.from_pydata(puntos, [], caras_nuevas)
    mesh.materials.append(origen.materials[0])
    atlas = mesh.uv_layers.new(name=origen.uv_layers.active.name)
    for loop, coord in zip(atlas.data, uv):
        loop.uv = coord
    for cara in mesh.polygons:
        cara.use_smooth = cara.index >= len(caras) or origen.polygons[cara.index].use_smooth
    mesh.update()
    mesh.normals_split_custom_set(normales + normales_cierres)
    mesh.validate(clean_customdata=False)
    malla.data = mesh
    bpy.data.meshes.remove(origen)
    return es_vertice_vaina
