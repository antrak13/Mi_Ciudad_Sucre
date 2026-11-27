"""Anatomía, capa y accesorios del GLB de Francisco Ríos."""
import numpy as np
from mathutils import Vector

from kit_personaje import color_base_por_vertice
from kit_ual import dedos_mano_desde_muneca
from pesos_ual import guardar_pesos, segmento, suave

ALTURA = 1.73
ORIGEN = Vector((-.073, .003, .00028014))
EXTRAS = [
    ('capa_hombro', 'DEF-spine.003'),
    ('capa_caida', 'capa_hombro'),
    ('sable_envainado', 'DEF-hips'),
    ('llave', 'DEF-hand.R'),
]


def segmentos():
    puntos = {
        'root': ((-.073, .003, .00028), (-.073, .003, .065)),
        'DEF-hips': ((-.061, .023, .521), (-.062, .020, .567)),
        'DEF-spine.001': ((-.062, .020, .567), (-.058, .019, .640)),
        'DEF-spine.002': ((-.058, .019, .640), (-.054, .021, .728)),
        'DEF-spine.003': ((-.054, .021, .728), (-.048, .022, .815)),
        'DEF-neck': ((-.048, .022, .815), (-.050, .008, .862)),
        'DEF-head': ((-.050, .008, .862), (-.043, .002, .958)),
        'DEF-shoulder.R': ((-.071, .002, .793), (-.155, -.048, .785)),
        'DEF-upper_arm.R': ((-.155, -.048, .785), (-.209, -.074, .611)),
        'DEF-forearm.R': ((-.209, -.074, .611), (-.232, -.109, .482)),
        'DEF-hand.R': ((-.232, -.109, .482), (-.226, -.122, .449)),
        'DEF-shoulder.L': ((-.027, .036, .797), (.050, .049, .791)),
        'DEF-upper_arm.L': ((.050, .049, .791), (.095, -.013, .622)),
        'DEF-forearm.L': ((.095, -.013, .622), (.049, -.073, .703)),
        'DEF-hand.L': ((.049, -.073, .703), (.022, -.085, .727)),
        'DEF-thigh.R': ((-.119, .005, .526), (-.136, -.060, .281)),
        'DEF-shin.R': ((-.136, -.060, .281), (-.198, -.064, .063)),
        'DEF-foot.R': ((-.198, -.064, .063), (-.199, -.130, .025)),
        'DEF-toe.R': ((-.199, -.130, .025), (-.200, -.179, .017)),
        'DEF-thigh.L': ((.006, .034, .520), (-.010, .060, .282)),
        'DEF-shin.L': ((-.010, .060, .282), (-.012, .078, .062)),
        'DEF-foot.L': ((-.012, .078, .062), (.045, .026, .027)),
        'DEF-toe.L': ((.045, .026, .027), (.071, -.009, .018)),
        'capa_hombro': ((.054, .042, .782), (.104, .095, .557)),
        'capa_caida': ((.104, .095, .557), (.134, .096, .293)),
        'sable_envainado': ((.040, -.072, .550), (.084, -.048, .347)),
        'llave': ((-.219, -.129, .417), (-.240, -.132, .281)),
    }
    s = {nombre: tuple((Vector(v) - ORIGEN) * ALTURA for v in par) for nombre, par in puntos.items()}
    for lado, normal, signo, escala in [('R', (-.40, -.91, .05), -1, .92),
                                         ('L', (-.16, -.75, -.62), 1, .84)]:
        muneca, nudillos = s[f'DEF-hand.{lado}']
        s.update(dedos_mano_desde_muneca(muneca, nudillos - muneca, normal, signo, escala))
    return s


def coordenadas(malla):
    return np.array([v.co for v in malla.data.vertices]) / ALTURA + np.array(ORIGEN)


def asignar_pesos(malla, rig, s):
    p = coordenadas(malla)
    x, y, z = p.T
    color = color_base_por_vertice(malla)
    aristas = np.array([tuple(arista.vertices) for arista in malla.data.edges])
    huesos = list(rig.data.bones.keys())
    indices = {n: i for i, n in enumerate(huesos)}
    w = np.zeros((len(p), len(huesos)))
    crudo = {n: tuple(np.array(a) / ALTURA + np.array(ORIGEN) for a in par) for n, par in s.items()}

    def mezclar(grupo, cantidad):
        w[:] *= 1 - cantidad[:, None]
        for nombre, proporcion in grupo.items():
            w[:, indices[nombre]] += cantidad * proporcion

    w[:, indices['DEF-hips']] = 1
    for nombre, abajo, arriba in [
        ('DEF-spine.001', .529, .605), ('DEF-spine.002', .608, .690),
        ('DEF-spine.003', .696, .787), ('DEF-neck', .806, .856), ('DEF-head', .834, .879),
    ]:
        mezclar({nombre: 1}, suave(abajo, arriba, z))

    izq = suave(-.097, -.067, x)
    for lado, reparto in [('L', izq), ('R', 1 - izq)]:
        muslo, canilla, pie, dedo = [f'DEF-{h}.{lado}' for h in ('thigh', 'shin', 'foot', 'toe')]
        bajo_rodilla = 1 - suave(.244, .321, z)
        bajo_tobillo = bajo_rodilla * (1 - suave(.047, .085, z))
        punta = bajo_tobillo * .68 * suave(.50, .99, segmento(p, *crudo[pie])[1])
        mezclar({muslo: 1 - bajo_rodilla, canilla: bajo_rodilla - bajo_tobillo,
                 pie: bajo_tobillo - punta, dedo: punta}, reparto * (1 - suave(.468, .554, z)))

    # La tela sigue su hombro, con peso progresivo hacia el bajo. El color
    # ayuda a distinguir la manga clara y la mano del paño oscuro en el pecho.
    oscuro = 1 - suave(.27, .46, color.max(axis=1))
    rojo = suave(.038, .125, color[:, 0] - color[:, 1]) * (1 - suave(.16, .34, color[:, 1]))
    fuera = suave(.075, .145, x)
    espalda = suave(.054, .088, y) * suave(-.079, -.038, x)
    borde = suave(-.005, .067, x) * suave(.48, .64, z)
    capa = np.maximum(fuera, np.maximum(espalda, borde * np.maximum(oscuro, rojo)))
    capa *= suave(.193, .217, z) * (1 - suave(.81, .855, z))
    capa = np.maximum(capa, suave(.072, .10, y) * suave(-.053, -.032, x)
                      * suave(.198, .214, z) * (1 - suave(.27, .34, z)))
    caida = 1 - suave(.40, .74, z)
    mezclar({'capa_hombro': 1 - caida, 'capa_caida': caida}, capa)

    for lado in ('R', 'L'):
        brazo, antebrazo, mano = [f'DEF-{h}.{lado}' for h in ('upper_arm', 'forearm', 'hand')]
        db, _ = segmento(p, *crudo[brazo])
        da, ta = segmento(p, *crudo[antebrazo])
        dm, _ = segmento(p, *crudo[mano])
        distancia = np.minimum(np.minimum(db, da), dm)
        codo = suave(-.034, .035, db - da)
        muneca = codo * suave(.72, 1, ta) * (1 - suave(.026, .055, dm))
        if lado == 'R':
            limite = np.interp(z, [.41, .51, .60, .66, .79], [.184, .181, .158, .136, .107])
            manga = suave(limite - .017, limite + .007, -x)
            manga *= suave(.389, .412, z) * (1 - suave(.786, .822, z))
            muneca = codo * (1 - suave(.463, .501, z))
        else:
            brazo_visible = (1 - suave(.028, .070, distancia)) * (1 - .84 * capa)
            piel = suave(.17, .27, color[:, 0] - color[:, 2])
            palma_visible = (1 - suave(.023, .048, dm)) * (1 - suave(-.072, -.052, y))
            palma_visible *= piel
            manga = np.maximum(brazo_visible, palma_visible) * suave(.564, .603, z)
            manga *= 1 - suave(.753, .806, z)
            muneca = np.maximum(muneca, codo * palma_visible * suave(.676, .707, z))
        mezclar({brazo: 1 - codo, antebrazo: codo - muneca, mano: muneca}, manga)
        dedos = [n for n in huesos if n.endswith(f'.{lado}') and n.startswith(('DEF-f_', 'DEF-thumb'))]
        d = np.array([segmento(p, *crudo[n])[0] for n in dedos]).T
        cerca = d.min(axis=1)
        afinidad = np.exp(-.5 * ((d - cerca[:, None]) / .006) ** 2)
        afinidad /= afinidad.sum(axis=1, keepdims=True)
        falanges = .60 * (1 - suave(.013, .033, cerca))
        mezclar({mano: 1 - falanges, **{n: afinidad[:, i] * falanges for i, n in enumerate(dedos)}},
                manga * (1 - suave(.023, .050, dm)) * suave(.67, .97, ta))

    # Herrajes apoyados en la pelvis y en la mano, con transición solo en la unión.
    distancia_sable, _ = segmento(p, *crudo['sable_envainado'])
    sable = (1 - suave(.030, .058, distancia_sable)) * suave(.326, .347, z)
    sable *= (1 - suave(.590, .613, z)) * (1 - suave(-.037, -.012, y))
    borde_llave = np.interp(z, [.276, .33, .38, .41], [.218, .208, .177, .185])
    fondo_llave = np.interp(z, [.276, .33, .38, .41], [-.134, -.132, -.127, -.125])
    llave = suave(borde_llave - .004, borde_llave + .003, -x) * suave(.268, .277, z)
    llave *= (1 - suave(.403, .422, z)) * (1 - suave(.017, .024, np.abs(y - fondo_llave)))
    mezclar({'sable_envainado': 1}, sable)
    mezclar({'llave': 1}, llave)

    conservar = (z < .030) | (z > .883) | (llave > .995) | (sable > .995)
    guardar_pesos(malla, rig, huesos, aristas, w, conservar)
