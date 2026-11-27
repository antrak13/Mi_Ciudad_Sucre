"""Ajuste de la armadura UAL al hábito y al libro abierto de fray Domingo."""
import numpy as np
from mathutils import Vector

from kit_personaje import color_base_por_vertice
from kit_ual import dedos_mano_desde_muneca
from pesos_ual import guardar_pesos, segmento, suave

ORIGEN = Vector((-.008, .045, .00009333))
ALTURA = 1.69
EXTRAS = [
    ('libro', 'DEF-spine.003'),
    ('habito_der', 'DEF-hips'),
    ('habito_izq', 'DEF-hips'),
]


def metros(p):
    return (Vector(p) - ORIGEN) * ALTURA


def segmentos():
    crudo = {
        'root': ((-.008, .045, .00009333), (-.008, .045, .058)),
        'DEF-hips': ((-.006, .047, .469), (-.005, .043, .532)),
        'DEF-spine.001': ((-.005, .043, .532), (-.003, .034, .612)),
        'DEF-spine.002': ((-.003, .034, .612), (-.007, .022, .697)),
        'DEF-spine.003': ((-.007, .022, .697), (-.010, .005, .801)),
        'DEF-neck': ((-.010, .005, .801), (-.017, -.007, .864)),
        'DEF-head': ((-.017, -.007, .864), (-.023, -.014, .963)),
        'DEF-shoulder.R': ((-.044, .006, .778), (-.110, .023, .747)),
        'DEF-upper_arm.R': ((-.110, .023, .747), (-.155, -.018, .562)),
        'DEF-forearm.R': ((-.155, -.018, .562), (-.124, -.101, .611)),
        'DEF-hand.R': ((-.124, -.101, .611), (-.095, -.134, .620)),
        'DEF-shoulder.L': ((.017, .018, .774), (.104, .043, .754)),
        'DEF-upper_arm.L': ((.104, .043, .754), (.160, .006, .557)),
        'DEF-forearm.L': ((.160, .006, .557), (.106, -.098, .585)),
        'DEF-hand.L': ((.106, -.098, .585), (.071, -.122, .585)),
        'DEF-thigh.R': ((-.062, .042, .474), (-.086, .026, .257)),
        'DEF-shin.R': ((-.086, .026, .257), (-.108, .020, .045)),
        'DEF-foot.R': ((-.108, .020, .045), (-.112, -.032, .017)),
        'DEF-toe.R': ((-.112, -.032, .017), (-.128, -.063, .015)),
        'DEF-thigh.L': ((.060, .057, .474), (.082, .060, .265)),
        'DEF-shin.L': ((.082, .060, .265), (.095, .072, .046)),
        'DEF-foot.L': ((.095, .072, .046), (.096, .017, .019)),
        'DEF-toe.L': ((.096, .017, .019), (.104, -.021, .016)),
        'libro': ((-.008, -.133, .627), (-.008, -.161, .697)),
        'habito_der': ((-.073, .071, .465), (-.101, .090, .162)),
        'habito_izq': ((.074, .073, .465), (.100, .108, .162)),
    }
    s = {n: tuple(metros(p) for p in par) for n, par in crudo.items()}
    for lado, signo, normal, escala in [('R', -1, (.13, .95, .12), .93), ('L', 1, (.27, .93, .03), .87)]:
        mano, nudillos = s[f'DEF-hand.{lado}']
        s.update(dedos_mano_desde_muneca(mano, nudillos - mano, normal, signo, escala))
    return s


def coordenadas(malla):
    return np.array([v.co for v in malla.data.vertices]) / ALTURA + np.array(ORIGEN)


def asignar_pesos(malla, rig, s):
    p = coordenadas(malla)
    x, y, z = p.T
    color = color_base_por_vertice(malla)
    aristas = np.array([tuple(arista.vertices) for arista in malla.data.edges if not arista.is_loose])
    huesos = list(rig.data.bones.keys())
    indices = {n: i for i, n in enumerate(huesos)}
    w = np.zeros((len(p), len(huesos)))
    crudo = {n: tuple(np.array(a) / ALTURA + np.array(ORIGEN) for a in par) for n, par in s.items()}

    def mezclar(grupos, cantidad):
        w[:] *= 1 - cantidad[:, None]
        for hueso, peso in grupos.items():
            w[:, indices[hueso]] += cantidad * peso

    w[:, indices['DEF-hips']] = 1
    for n, desde, hasta in [
        ('DEF-spine.001', .473, .573), ('DEF-spine.002', .555, .657),
        ('DEF-spine.003', .635, .770),
    ]:
        mezclar({n: 1}, suave(desde, hasta, z))

    # La capucha levantada se queda con el torso aunque la barba se incline.
    barba = suave(.792, .829, z) * (1 - suave(-.014, .025, y))
    capucha = suave(.042, .107, y) * (1 - suave(.881, .916, z))
    cuello = suave(.774, .851, z) * (1 - capucha)
    cabeza = np.maximum(barba, suave(.853, .894, z)) * (1 - capucha)
    mezclar({'DEF-neck': 1}, cuello)
    mezclar({'DEF-head': 1}, cabeza)

    izquierda = suave(-.085, .075, x)
    faldon = (1 - suave(.352, .493, z)) * suave(.022, .059, z)
    mezclar({'habito_der': 1 - izquierda, 'habito_izq': izquierda}, faldon)

    # Los zapatos toman una sola orientación en la planta. El ruedo conserva
    # su peso sobre el hábito y acompaña los pasos con una apertura leve.
    for lado in ('R', 'L'):
        pie, punta = [f'DEF-{h}.{lado}' for h in ('foot', 'toe')]
        dist, _ = segmento(p, *crudo[pie])
        corte = (1 - suave(.044, .085, z)) * (1 - suave(.031, .058, dist))
        corte *= 1 - suave(.083 if lado == 'R' else .122, .125 if lado == 'R' else .160, y)
        bajo = (z < .026) & (np.abs(x - crudo[pie][0][0]) < .064) & (y < .111)
        corte[bajo] = 1
        mezclar({pie: 1}, corte)

    # En el volumen por delante del pecho, los bordes y las páginas se
    # ponderan como una pieza rígida. La piel de los dedos queda con su mano.
    libro = (1 - suave(-.087, -.058, y)) * (1 - suave(.106, .130, np.abs(x + .009)))
    libro *= suave(.550, .570, z) * (1 - suave(.729, .746, z))
    mezclar({'libro': 1}, libro)

    for lado in ('R', 'L'):
        brazo, antebrazo, mano = [f'DEF-{h}.{lado}' for h in ('upper_arm', 'forearm', 'hand')]
        db, _ = segmento(p, *crudo[brazo])
        da, ta = segmento(p, *crudo[antebrazo])
        dm, _ = segmento(p, *crudo[mano])
        lateral = x if lado == 'L' else -x
        piel = suave(.16, .32, color[:, 0] - color[:, 2]) * suave(.23, .42, color[:, 0])
        palma = (1 - suave(.023, .050, dm)) * piel * suave(.019, .049, lateral)
        palma *= (1 - suave(-.074, -.034, y)) * (1 - suave(.635, .663, z))
        codo = suave(-.048, .037, db - da)
        muneca = codo * suave(.59, .95, ta) * (1 - suave(.025, .057, dm))
        muneca = np.maximum(muneca, palma)
        codo = np.maximum(codo, muneca)
        manga = suave(.070, .128, lateral) * (1 - suave(.072, .123, np.minimum(db, da)))
        manga *= suave(.473, .536, z) * (1 - suave(.681, .757, z))
        manga *= 1 - .95 * libro
        influencia = np.maximum(manga, palma)
        mezclar({brazo: 1 - codo, antebrazo: codo - muneca, mano: muneca}, influencia)

        dedos = [n for n in huesos if n.endswith(f'.{lado}') and n.startswith(('DEF-f_', 'DEF-thumb'))]
        d = np.array([segmento(p, *crudo[n])[0] for n in dedos]).T
        cerca = d.min(axis=1)
        afinidad = np.exp(-.5 * ((d - cerca[:, None]) / .006) ** 2)
        afinidad /= afinidad.sum(axis=1, keepdims=True)
        falanges = .62 * (1 - suave(.012, .032, cerca))
        mezclar({mano: 1 - falanges, **{n: afinidad[:, i] * falanges for i, n in enumerate(dedos)}}, palma)

    indice_libro = indices['libro']
    conservar = (z < .024) | (cabeza > .995) | (w[:, indice_libro] > .996)
    guardar_pesos(malla, rig, huesos, aristas, w, conservar)
