"""Puntos anatómicos y pesos de la malla estática de Vergara."""

import numpy as np
from mathutils import Vector

from pesos_ual import guardar_pesos, segmento, suave

ALTURA = 1.88  # Mitra incluida. El cráneo llega a ~1,67 m.
ORIGEN = Vector((0., .027, .0000933))


def metros(p):
    return (Vector(p) - ORIGEN) * ALTURA


def segmentos():
    s = {
        'root': ((0, .027, 0), (0, .027, .06)),
        'DEF-hips': ((.013, .027, .491), (.015, .028, .554)),
        'DEF-spine.001': ((.015, .028, .554), (.026, .022, .624)),
        'DEF-spine.002': ((.026, .022, .624), (.028, .016, .694)),
        'DEF-spine.003': ((.028, .016, .694), (.032, .014, .758)),
        'DEF-neck': ((.032, .014, .758), (.037, .015, .801)),
        'DEF-head': ((.037, .015, .801), (.045, .020, .882)),
        'DEF-shoulder.R': ((.002, .013, .738), (-.083, .012, .722)),
        'DEF-upper_arm.R': ((-.083, .012, .722), (-.158, -.005, .552)),
        'DEF-forearm.R': ((-.158, -.005, .552), (-.196, -.112, .608)),
        'DEF-hand.R': ((-.196, -.112, .608), (-.221, -.146, .608)),
        'DEF-shoulder.L': ((.049, .014, .742), (.119, .020, .724)),
        'DEF-upper_arm.L': ((.119, .020, .724), (.155, .003, .551)),
        'DEF-forearm.L': ((.155, .003, .551), (.115, -.074, .606)),
        'DEF-hand.L': ((.115, -.074, .606), (.072, -.082, .629)),
        'DEF-thigh.R': ((-.060, .027, .491), (-.090, .012, .266)),
        'DEF-shin.R': ((-.090, .012, .266), (-.098, .025, .051)),
        'DEF-foot.R': ((-.098, .025, .051), (-.111, -.043, .017)),
        'DEF-toe.R': ((-.111, -.043, .017), (-.122, -.073, .014)),
        'DEF-thigh.L': ((.083, .027, .491), (.086, .035, .268)),
        'DEF-shin.L': ((.086, .035, .268), (.089, .051, .050)),
        'DEF-foot.L': ((.089, .051, .050), (.112, .000, .016)),
        'DEF-toe.L': ((.112, .000, .016), (.135, -.018, .012)),
        'incensario': ((-.215, -.130, .584), (-.215, -.130, .427)),
    }

    # Falanges trazadas sobre ambas manos tal como las trae la malla. La derecha
    # cierra sobre las cadenas y la izquierda descansa parcialmente sobre la capa.
    manos = {
        'R': {
            'f_index': [(-.222, -.149, .623), (-.229, -.151, .615), (-.224, -.141, .610), (-.218, -.136, .611)],
            'f_middle': [(-.227, -.152, .613), (-.23, -.150, .605), (-.221, -.141, .602), (-.216, -.135, .606)],
            'f_ring': [(-.228, -.150, .604), (-.228, -.146, .597), (-.219, -.140, .595), (-.215, -.135, .600)],
            'f_pinky': [(-.223, -.146, .596), (-.22, -.142, .590), (-.213, -.138, .588), (-.212, -.132, .592)],
            'thumb': [(-.206, -.130, .617), (-.211, -.130, .626), (-.218, -.137, .629), (-.223, -.144, .624)],
        },
        'L': {
            'f_index': [(.070, -.082, .638), (.056, -.084, .644), (.044, -.082, .650), (.035, -.079, .653)],
            'f_middle': [(.067, -.085, .631), (.051, -.087, .634), (.039, -.082, .639), (.030, -.080, .643)],
            'f_ring': [(.070, -.085, .623), (.055, -.086, .624), (.043, -.082, .629), (.034, -.076, .632)],
            'f_pinky': [(.074, -.082, .616), (.063, -.083, .615), (.053, -.081, .618), (.045, -.076, .621)],
            'thumb': [(.096, -.079, .621), (.089, -.08, .635), (.085, -.078, .647), (.081, -.075, .654)],
        },
    }
    for lado, dedos in manos.items():
        for nombre, puntos in dedos.items():
            for i, (a, b) in enumerate(zip(puntos, puntos[1:]), 1):
                s[f'DEF-{nombre}.{i:02}.{lado}'] = (a, b)

    return {nombre: tuple(metros(p) for p in par) for nombre, par in s.items()}


def zona_incensario(p, aristas):
    """Sigue la conectividad bajo el puño para separar cadena y manga."""
    x, y, z = p.T
    zona = (x < -.17) & (y < -.077) & (z < .585)
    vecinos = [[] for _ in p]
    for a, b in aristas[zona[aristas].all(axis=1)]:
        vecinos[a].append(b)
        vecinos[b].append(a)
    semilla = int(np.linalg.norm(p - (-.217, -.128, .445), axis=1).argmin())
    seleccion = np.zeros(len(p), dtype=bool)
    seleccion[semilla] = True
    cola = [semilla]
    while cola:
        for v in vecinos[cola.pop()]:
            if not seleccion[v]:
                seleccion[v] = True
                cola.append(v)
    if not 500 < np.count_nonzero(seleccion) < .2 * len(p):
        raise ValueError('No se pudo identificar el incensario en la malla de Vergara')
    return seleccion


def asignar_pesos(malla, rig, s):
    p = np.array([v.co for v in malla.data.vertices]) / ALTURA + np.array(ORIGEN)
    aristas = np.array([tuple(e.vertices) for e in malla.data.edges])
    x, y, z = p.T
    huesos = list(rig.data.bones.keys())
    indices = {nombre: i for i, nombre in enumerate(huesos)}
    w = np.zeros((len(p), len(huesos)))

    def mezclar(grupo, cantidad):
        w[:] *= 1 - cantidad[:, None]
        for nombre, proporcion in grupo.items():
            w[:, indices[nombre]] += cantidad * proporcion

    w[:, indices['DEF-hips']] = 1
    for nombre, inferior, superior in [
        ('DEF-spine.001', .475, .57), ('DEF-spine.002', .55, .65),
        ('DEF-spine.003', .64, .74), ('DEF-neck', .753, .794),
        ('DEF-head', .782, .82),
    ]:
        mezclar({nombre: 1}, suave(inferior, superior, z))

    # Capa y alba acompañan las piernas con poco peso. Los zapatos se mantienen
    # rígidos desde sus suelas y se funden con el alba en el nacimiento del tobillo.
    lado_izq = suave(-.09, .09, x)
    for lado, reparto in [('L', lado_izq), ('R', 1 - lado_izq)]:
        muslo, pierna, pie, dedo = [f'DEF-{n}.{lado}' for n in ('thigh', 'shin', 'foot', 'toe')]
        bajo = 1 - suave(.17, .39, z)
        mezclar({muslo: 1 - bajo, pierna: bajo}, reparto * .50 * (1 - suave(.13, .49, z)))
        signo = 1 if lado == 'L' else -1
        distancia, t = segmento(p, *(np.array(a) / ALTURA + ORIGEN for a in s[pie]))
        calzado = (
            (1 - suave(.049, .154, z)) * suave(.002, .054, signo * x)
            * (1 - suave(.052, .114, distancia)) * (1 - suave(.096, .156, y))
        )
        calzado[(z < .049) & (signo * x > .041)] = 1
        punta = .68 * suave(.65, 1, t) * (1 - suave(.022, .032, z))
        mezclar({pie: 1 - punta, dedo: punta}, calzado)

    for lado in ('R', 'L'):
        brazo, antebrazo, mano = [f'DEF-{n}.{lado}' for n in ('upper_arm', 'forearm', 'hand')]
        db, _ = segmento(p, *(np.array(a) / ALTURA + ORIGEN for a in s[brazo]))
        da, ta = segmento(p, *(np.array(a) / ALTURA + ORIGEN for a in s[antebrazo]))
        dm, tm = segmento(p, *(np.array(a) / ALTURA + ORIGEN for a in s[mano]))
        if lado == 'R':
            lateral = suave(.063, .167, -x)
            adelante = 1 - suave(-.018, .107, y)
            mano_total = suave(.172, .211, -x) * (1 - suave(-.106, -.077, y))
        else:
            lateral = suave(.091, .135, x)
            adelante = 1 - suave(.025, .094, y)
            mano_total = (1 - suave(.093, .125, x)) * (1 - suave(-.077, -.067, y))
        altura_manga = suave(.458, .566, z) * (1 - suave(.696, .786, z))
        manga = lateral * adelante * altura_manga * (1 - suave(.057, .110, np.minimum(db, da)))
        codo = suave(-.028, .030, db - da)
        muneca = codo * suave(.77, .99, ta) * (1 - suave(.019, .041, dm)) * (.5 + .5 * tm)
        mezclar({brazo: 1 - codo, antebrazo: codo - muneca, mano: muneca}, manga)

        dedos = [nombre for nombre in huesos if nombre.endswith(f'.{lado}')
                 and nombre.startswith(('DEF-f_', 'DEF-thumb'))]
        distancias = np.array([
            segmento(p, *(np.array(a) / ALTURA + ORIGEN for a in s[nombre]))[0]
            for nombre in dedos
        ]).T
        franja = suave(.573 if lado == 'R' else .596, .594 if lado == 'R' else .61, z)
        franja *= 1 - suave(.647, .666, z)
        superficie = mano_total * franja * (1 - suave(.019, .039, distancias.min(axis=1)))
        dmin = distancias.min(axis=1)
        falanges = np.exp(-.5 * ((distancias - dmin[:, None]) / .006) ** 2)
        falanges /= falanges.sum(axis=1, keepdims=True)
        dedos_total = .78 * (1 - suave(.007, .024, dmin))
        mezclar({mano: 1 - dedos_total, **{
            n: falanges[:, i] * dedos_total for i, n in enumerate(dedos)
        }}, superficie)

    prop = zona_incensario(p, aristas)
    agarre = (1 - suave(.566, .586, z)) * prop
    mezclar({'incensario': 1}, agarre)

    # Suavizar las transiciones sobre las aristas de la malla. Mitra, suelas y
    # metal conservan sus afinidades rígidas al suavizar la tela vecina.
    conservar = (z > .82) | (z < .041) | (agarre > .99)
    guardar_pesos(malla, rig, huesos, aristas, w, conservar)
