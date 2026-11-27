"""Rig UAL y máscaras medidas sobre el modelo estático del acompañante."""
import numpy as np
from mathutils import Vector

from kit_ual import dedos_mano_desde_muneca
from pesos_ual import guardar_pesos, segmento, suave

ALTURA = 1.59
ORIGEN = Vector((-.041, .035, .00003))
EXTRAS = [('capa_doblada', 'DEF-forearm.L'), ('sable_envainado', 'DEF-hips')]


def metros(p):
    return (Vector(p) - ORIGEN) * ALTURA


def segmentos():
    crudo = {
        'root': ((-.041, .035, .00003), (-.041, .035, .065)),
        'DEF-hips': ((-.031, .021, .499), (-.031, .024, .563)),
        'DEF-spine.001': ((-.031, .024, .563), (-.028, .018, .631)),
        'DEF-spine.002': ((-.028, .018, .631), (-.024, .018, .703)),
        'DEF-spine.003': ((-.024, .018, .703), (-.019, .023, .759)),
        'DEF-neck': ((-.019, .023, .759), (-.016, .019, .801)),
        'DEF-head': ((-.016, .019, .801), (-.029, .017, .89)),
        'DEF-shoulder.R': ((-.037, .024, .753), (-.098, .022, .749)),
        'DEF-upper_arm.R': ((-.098, .022, .749), (-.151, .010, .589)),
        'DEF-forearm.R': ((-.151, .010, .589), (-.167, .002, .451)),
        'DEF-hand.R': ((-.167, .002, .451), (-.177, -.005, .407)),
        'DEF-shoulder.L': ((.008, .025, .754), (.080, .032, .748)),
        'DEF-upper_arm.L': ((.080, .032, .748), (.124, .057, .601)),
        'DEF-forearm.L': ((.124, .057, .601), (.068, -.062, .616)),
        'DEF-hand.L': ((.068, -.062, .616), (.041, -.079, .620)),
        'DEF-thigh.R': ((-.081, .018, .492), (-.103, .003, .262)),
        'DEF-shin.R': ((-.103, .003, .262), (-.131, .015, .051)),
        'DEF-foot.R': ((-.131, .015, .051), (-.150, -.052, .019)),
        'DEF-toe.R': ((-.150, -.052, .019), (-.171, -.087, .016)),
        'DEF-thigh.L': ((.023, .028, .492), (.040, .032, .258)),
        'DEF-shin.L': ((.040, .032, .258), (.049, .056, .051)),
        'DEF-foot.L': ((.049, .056, .051), (.077, -.004, .020)),
        'DEF-toe.L': ((.077, -.004, .020), (.092, -.045, .017)),
        'capa_doblada': ((.096, .012, .618), (.120, .014, .371)),
        'sable_envainado': ((-.095, -.035, .471), (-.167, .013, .174)),
    }
    dedos_izq = {
        'f_index': [(.043, -.080, .631), (.031, -.087, .634), (.024, -.086, .629), (.027, -.079, .626)],
        'f_middle': [(.040, -.081, .620), (.025, -.089, .623), (.021, -.086, .617), (.026, -.080, .613)],
        'f_ring': [(.043, -.080, .609), (.029, -.086, .612), (.023, -.086, .607), (.029, -.079, .603)],
        'f_pinky': [(.051, -.074, .600), (.037, -.082, .601), (.031, -.081, .597), (.035, -.074, .593)],
        'thumb': [(.061, -.073, .628), (.054, -.078, .640), (.045, -.084, .642), (.035, -.085, .638)],
    }
    for nombre, puntos in dedos_izq.items():
        for i, (a, b) in enumerate(zip(puntos, puntos[1:]), 1):
            crudo[f'DEF-{nombre}.{i:02}.L'] = (a, b)
    s = {nombre: tuple(metros(p) for p in par) for nombre, par in crudo.items()}
    mano, nudillo = s['DEF-hand.R']
    s.update(dedos_mano_desde_muneca(mano, nudillo - mano, (.92, -.31, -.06), -1, .95))
    return s


def coordenadas(malla):
    return np.array([v.co for v in malla.data.vertices]) / ALTURA + np.array(ORIGEN)


def pigmento(malla):
    """Lee el albedo original para distinguir la capa oscura del calzón marrón."""
    mesh = malla.data
    nodos = mesh.materials[0].node_tree.nodes
    shader = next(n for n in nodos if n.type == 'BSDF_PRINCIPLED')
    imagen = shader.inputs['Base Color'].links[0].from_node.image
    pixeles = np.empty(len(imagen.pixels), dtype=np.float32)
    imagen.pixels.foreach_get(pixeles)
    pixeles = pixeles.reshape(imagen.size[1], imagen.size[0], 4)
    uv = np.array([loop.uv for loop in mesh.uv_layers.active.data])
    indices = np.clip((uv * imagen.size).astype(int), 0, np.array(imagen.size) - 1)
    muestra = pixeles[indices[:, 1], indices[:, 0], :3]
    vertices = np.array([l.vertex_index for l in mesh.loops])
    color = np.zeros((len(mesh.vertices), 3))
    np.add.at(color, vertices, muestra)
    return color / np.maximum(1, np.bincount(vertices, minlength=len(color)))[:, None]


def asignar_pesos(malla, rig, s, vaina):
    p = coordenadas(malla)
    x, y, z = p.T
    color = pigmento(malla)
    aristas = np.array([tuple(e.vertices) for e in malla.data.edges])
    huesos = list(rig.data.bones.keys())
    indices = {nombre: i for i, nombre in enumerate(huesos)}
    w = np.zeros((len(p), len(huesos)))

    def mezclar(grupo, cantidad):
        w[:] *= 1 - cantidad[:, None]
        for nombre, proporcion in grupo.items():
            w[:, indices[nombre]] += cantidad * proporcion

    ss = {n: tuple(np.array(a) / ALTURA + np.array(ORIGEN) for a in par) for n, par in s.items()}
    w[:, indices['DEF-hips']] = 1
    for nombre, abajo, arriba in [
        ('DEF-spine.001', .516, .616), ('DEF-spine.002', .596, .686),
        ('DEF-spine.003', .676, .767), ('DEF-neck', .762, .802), ('DEF-head', .782, .823),
    ]:
        mezclar({nombre: 1}, suave(abajo, arriba, z))

    lado_izq = suave(-.045, -.027, x)
    for lado, franja in [('R', 1 - lado_izq), ('L', lado_izq)]:
        muslo, canilla, pie, dedo = [f'DEF-{n}.{lado}' for n in ('thigh', 'shin', 'foot', 'toe')]
        rodilla = 1 - suave(.226, .291, z)
        tobillo = (1 - suave(.047, .093, z)) * rodilla
        punta = tobillo * .72 * suave(.28, .93, segmento(p, *ss[pie])[1])
        mezclar({muslo: 1 - rodilla, canilla: rodilla - tobillo, pie: tobillo - punta, dedo: punta},
                franja * (1 - suave(.396, .53, z)))

    for lado in ('R', 'L'):
        brazo, antebrazo, mano = [f'DEF-{n}.{lado}' for n in ('upper_arm', 'forearm', 'hand')]
        db, _ = segmento(p, *ss[brazo])
        da, ta = segmento(p, *ss[antebrazo])
        dm, _ = segmento(p, *ss[mano])
        if lado == 'R':
            lateral = suave(.087 + .35 * (z - .74), .117 + .35 * (z - .74), -x)
            lateral *= suave(.126, .153, -x) + suave(.51, .58, z) * (1 - suave(.126, .153, -x))
            superficie = lateral * suave(.345, .368, z) * (1 - suave(.736, .792, z))
            manga = superficie * (1 - suave(.040, .073, np.minimum(np.minimum(db, da), dm)))
            palma = superficie * (1 - suave(.445, .481, z))
        else:
            lateral = suave(.051, .095, x)
            ventana = suave(.535, .58, z) * (1 - suave(.733, .779, z))
            manga = lateral * ventana * (1 - suave(.034, .065, np.minimum(db, da)))
            mano_color = suave(.19, .29, color[:, 0] - color[:, 2])
            palma = (1 - suave(-.074, -.048, y)) * (1 - suave(.02, .043, dm)) * mano_color
        f_codo = suave(-.027, .026, db - da)
        f_mano = f_codo * suave(.69, .97, ta) * (1 - suave(.022, .046, dm))
        mezclar({brazo: 1 - f_codo, antebrazo: f_codo - f_mano, mano: f_mano}, manga)

        dedos = [n for n in huesos if n.endswith(f'.{lado}') and n.startswith(('DEF-f_', 'DEF-thumb'))]
        distancias = np.array([segmento(p, *ss[n])[0] for n in dedos]).T
        dmin = distancias.min(axis=1)
        falanges = np.exp(-.5 * ((distancias - dmin[:, None]) / .0045) ** 2)
        falanges /= falanges.sum(axis=1, keepdims=True)
        fraccion = .80 * (1 - suave(.006, .028, dmin))
        mezclar({mano: 1 - fraccion, **{n: falanges[:, i] * fraccion for i, n in enumerate(dedos)}},
                palma * (1 - suave(.027, .052, np.minimum(dmin, dm))))

    oscuridad = 1 - suave(.095, .172, color[:, 0] - color[:, 2])
    oscuridad = np.maximum(oscuridad, suave(.101, .137, x) * (1 - suave(.50, .56, z)))
    capa = suave(.021, .061, x) * suave(.29, .332, z) * (1 - suave(.64, .674, z)) * oscuridad
    caida = 1 - suave(.511, .622, z)
    mezclar({'capa_doblada': caida, 'DEF-forearm.L': 1 - caida}, capa)

    mezclar({'sable_envainado': 1}, vaina.astype(float))
    conservar = (z < .027) | (z > .823) | vaina
    guardar_pesos(malla, rig, huesos, aristas, w, conservar, pases=6)
