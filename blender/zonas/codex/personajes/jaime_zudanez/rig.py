"""Segmentos medidos sobre Jaime y pesos para su levita, manos y caja."""
import numpy as np
from mathutils import Vector

from kit_personaje import color_base_por_vertice, cortar_caras, triangulos
from kit_ual import dedos_mano_desde_muneca
from pesos_ual import guardar_pesos, segmento, suave

ORIGEN = Vector((-.065, .019, .00018665))
ALTURA = 1.78
EXTRAS = [
    ('caja_mantequilla', 'DEF-hand.L'),
    ('faldon_der', 'DEF-hips'),
    ('faldon_izq', 'DEF-hips'),
]


def metros(p):
    return (Vector(p) - ORIGEN) * ALTURA


def segmentos():
    crudo = {
        'root': ((-.065, .019, .00019), (-.065, .019, .065)),
        'DEF-hips': ((-.045, .028, .488), (-.038, .014, .543)),
        'DEF-spine.001': ((-.038, .014, .543), (-.028, .017, .609)),
        'DEF-spine.002': ((-.028, .017, .609), (-.019, .018, .69)),
        'DEF-spine.003': ((-.019, .018, .69), (-.016, .013, .771)),
        'DEF-neck': ((-.016, .013, .771), (-.027, .011, .813)),
        'DEF-head': ((-.027, .011, .813), (-.043, .005, .906)),
        'DEF-shoulder.R': ((-.036, .005, .755), (-.127, .017, .735)),
        'DEF-upper_arm.R': ((-.127, .017, .735), (-.175, .034, .585)),
        'DEF-forearm.R': ((-.175, .034, .585), (-.185, -.003, .444)),
        'DEF-hand.R': ((-.185, -.003, .444), (-.180, -.010, .404)),
        'DEF-shoulder.L': ((.000, .025, .752), (.104, .035, .734)),
        'DEF-upper_arm.L': ((.104, .035, .734), (.184, .009, .626)),
        'DEF-forearm.L': ((.184, .009, .626), (.135, -.080, .535)),
        'DEF-hand.L': ((.135, -.080, .535), (.097, -.095, .526)),
        'DEF-thigh.R': ((-.093, .029, .490), (-.103, .021, .243)),
        'DEF-shin.R': ((-.103, .021, .243), (-.134, .015, .054)),
        'DEF-foot.R': ((-.134, .015, .054), (-.166, -.033, .027)),
        'DEF-toe.R': ((-.166, -.033, .027), (-.19, -.059, .016)),
        'DEF-thigh.L': ((.023, .033, .49), (.048, .047, .237)),
        'DEF-shin.L': ((.048, .047, .237), (.065, .058, .057)),
        'DEF-foot.L': ((.065, .058, .057), (.074, .007, .027)),
        'DEF-toe.L': ((.074, .007, .027), (.091, -.029, .015)),
        'caja_mantequilla': ((.101, -.058, .55), (.106, -.059, .641)),
        'faldon_der': ((-.086, .018, .47), (-.124, .053, .24)),
        'faldon_izq': ((.013, .024, .47), (.076, .067, .24)),
    }
    s = {nombre: tuple(metros(p) for p in par) for nombre, par in crudo.items()}
    for lado, signo, normal, escala in [
        ('R', -1, (.85, -.39, -.11), 1.02),
        ('L', 1, (-.22, .65, .72), .91),
    ]:
        muneca, nudillo = s[f'DEF-hand.{lado}']
        s.update(dedos_mano_desde_muneca(muneca, nudillo - muneca, normal, signo, escala))
    return s


def coordenadas(malla):
    return np.array([v.co for v in malla.data.vertices]) / ALTURA + np.array(ORIGEN)


def asignar_pesos(malla, rig, segmentos_m):
    p = coordenadas(malla)
    x, y, z = p.T
    color = color_base_por_vertice(malla)
    huesos = list(rig.data.bones.keys())
    indices = {n: i for i, n in enumerate(huesos)}
    w = np.zeros((len(p), len(huesos)))
    crudo = {n: tuple(np.array(a) / ALTURA + np.array(ORIGEN) for a in par) for n, par in segmentos_m.items()}

    def mezclar(grupos, cantidad):
        w[:] *= 1 - cantidad[:, None]
        for hueso, influencia in grupos.items():
            w[:, indices[hueso]] += cantidad * influencia

    w[:, indices['DEF-hips']] = 1
    for n, desde, hasta in [
        ('DEF-spine.001', .50, .59), ('DEF-spine.002', .57, .67),
        ('DEF-spine.003', .67, .76), ('DEF-neck', .760, .797),
    ]:
        mezclar({n: 1}, suave(desde, hasta, z))
    piel = suave(.19, .30, color[:, 0] - color[:, 2]) * (1 - suave(.55, .66, color[:, 1]))
    menton = suave(.779, .797, z) * (1 - suave(-.029, -.014, y)) * piel
    cabeza = np.maximum(menton, suave(.788, .815, z))
    mezclar({'DEF-head': 1}, cabeza)

    # La reconstrucción de origen une las puntas de la mano derecha con
    # el faldón. El corte se limita a las caras que cruzan ese contacto.
    borde_manga = np.interp(z, [.35, .38, .41, .445, .48, .53, .57, .59, .74],
                           [.157, .154, .139, .147, .144, .131, .121, .115, .087])
    fondo_manga = np.interp(z, [.35, .38, .40, .419, .445, .52, .59],
                           [.011, .014, .026, .037, .052, .075, .093])
    antebrazo_libre = (-x > borde_manga) & (y < fondo_manga) & (z > .347)
    tris = triangulos(malla)
    contacto = antebrazo_libre[tris].any(axis=1) & ~antebrazo_libre[tris].all(axis=1)
    contacto &= ((z[tris] > .34) & (z[tris] < .54) & (x[tris] < -.09)).all(axis=1)
    cortar_caras(malla, np.flatnonzero(contacto), 'contacto entre la mano derecha y la levita')

    izquierda = suave(-.076, -.023, x)
    tonos_medias = suave(.22, .43, color[:, 0])
    d_piernas = []
    for lado, lateral in [('R', 1 - izquierda), ('L', izquierda)]:
        muslo, canilla, pie, dedo = [f'DEF-{h}.{lado}' for h in ('thigh', 'shin', 'foot', 'toe')]
        rodilla = 1 - suave(.212, .275, z)
        tobillo = rodilla * (1 - suave(.043, .076, z))
        punta = tobillo * .40 * suave(.52, 1, segmento(p, *crudo[pie])[1])
        mezclar({muslo: 1 - rodilla, canilla: rodilla - tobillo, pie: tobillo - punta, dedo: punta},
                lateral * (1 - suave(.443, .532, z)))
        d_piernas.append(np.minimum(segmento(p, *crudo[muslo])[0], segmento(p, *crudo[canilla])[0]))

    # Bajo de levita: peso independiente en los extremos y en la espalda.
    # Entre las piernas el paño acompaña a la cadera; las medias claras quedan con las canillas.
    exterior = suave(.048, .084, np.minimum(*d_piernas))
    espalda = suave(.057, .090, y)
    faldon = np.maximum(exterior, espalda) * suave(.197, .246, z) * (1 - suave(.45, .55, z))
    faldon *= 1 - tonos_medias * (1 - suave(.216, .29, z))
    mezclar({'faldon_der': 1 - izquierda, 'faldon_izq': izquierda}, faldon)

    for lado in ('R', 'L'):
        brazo, antebrazo, mano = [f'DEF-{h}.{lado}' for h in ('upper_arm', 'forearm', 'hand')]
        db, _ = segmento(p, *crudo[brazo])
        da, ta = segmento(p, *crudo[antebrazo])
        dm, _ = segmento(p, *crudo[mano])
        codo = suave(-.036, .036, db - da)
        muneca = codo * suave(.73, .96, ta) * (1 - suave(.032, .063, dm))
        if lado == 'R':
            manga = suave(borde_manga - .012, borde_manga + .02, -x)
            manga *= (1 - suave(.735, .780, z)) * (1 - suave(.073, .096, y))
            codo_visible = suave(.521, .566, z)
            manga = (1 - codo_visible) * antebrazo_libre + codo_visible * manga
            muneca = codo * (1 - suave(.428, .466, z))
        else:
            manga = suave(.070, .124, x) * (1 - suave(.052, .082, np.minimum(db, da)))
            manga *= suave(.489, .527, z) * (1 - suave(.738, .778, z))
            mano_visible = (1 - suave(.027, .061, dm)) * (1 - suave(-.069, -.038, y))
            mano_visible *= suave(.038, .065, x) * suave(.491, .511, z) * (1 - suave(.553, .574, z))
            manga = np.maximum(manga, mano_visible)
            muneca = np.maximum(muneca, .995 * mano_visible)
            codo = np.maximum(codo, muneca)
        mezclar({brazo: 1 - codo, antebrazo: codo - muneca, mano: muneca}, manga)

        dedos = [n for n in huesos if n.endswith(f'.{lado}') and n.startswith(('DEF-f_', 'DEF-thumb'))]
        dist = np.array([segmento(p, *crudo[n])[0] for n in dedos]).T
        cerca = dist.min(axis=1)
        afinidad = np.exp(-.5 * ((dist - cerca[:, None]) / .005) ** 2)
        afinidad /= afinidad.sum(axis=1, keepdims=True)
        fraccion = .75 * (1 - suave(.017, .034, cerca))
        mezclar({mano: 1 - fraccion, **{n: fraccion * afinidad[:, i] for i, n in enumerate(dedos)}},
                manga * muneca)

    # La caja apoya en la mano izquierda. Mantiene volumen incluso al caminar.
    madera = suave(.10, .23, color[:, 0] - color[:, 2])
    caja = suave(.043, .058, x) * (1 - suave(.148, .169, x))
    caja *= suave(.535, .555, z) * (1 - suave(.646, .667, z))
    caja *= 1 - suave(-.024, .029, y)
    caja *= np.maximum(madera, (1 - suave(-.066, -.043, y)) * suave(.556, .578, z))
    mezclar({'caja_mantequilla': 1}, caja)
    # El corte conserva las aristas sueltas en Blender. La difusión de pesos
    # usa las aristas de las caras que quedan para respetar la separación.
    caras = tris[~contacto]
    aristas = np.concatenate((caras[:, [0, 1]], caras[:, [1, 2]], caras[:, [2, 0]]))
    aristas = np.unique(np.sort(aristas, axis=1), axis=0)
    conservar = (z < .026) | (cabeza > .994) | (caja > .997)
    guardar_pesos(malla, rig, huesos, aristas, w, conservar)
