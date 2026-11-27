"""Endereza las cabezas de los personajes de Tripo (giradas o dobladas en sus clips).

Los modelos de Tripo traen la cabeza mirando a un costado (o caída) en casi todos sus clips: el rig automático y el
retargeting de las animaciones la dejan con un giro fijo. Este módulo mide, en el espacio del modelo (frente +Z), hacia
dónde mira la cabeza en cada clip y corrige las claves de rotación del hueso de la cabeza para que mire al frente:
- clips comunes: se quita el giro medio del clip (los gestos de la cabeza dentro del clip se conservan);
- clips en los que mirar a otro lado ES el gesto (mirar_atras, negar...): se quita el giro típico del personaje.
La inclinación hacia abajo se conserva en los clips que la piden (leer, examinar, pintar...) y en el resto se limita.
Trabaja sobre los bytes del GLB y devuelve los bytes corregidos (mismo tamaño: solo cambian floats en su lugar).
Uso suelto: python3 cabezas.py <modelo.glb> → informe de giros por clip.
"""
import json, math, struct, sys
import numpy as np

HUESOS_CABEZA = ["DEF-head", "cabeza", "head", "Head"]
GESTO_GIRO = {"mirar_atras", "negar", "asomarse", "rodear_jugador", "apartarse", "huir", "ocultarse"}
GESTO_BAJAR = {"leer_libro", "examinar_lupa", "pintar", "llenar_botija", "tamborilear_caja", "arrugar_papel",
               "asentir", "reverencia_anfitrion", "cargar_bulto", "mostrar_forro", "lanzar_monedas", "mostrar_llave",
               "ocultarse", "sentado_carruaje", "sentada_carruaje", "mover_cola", "mirar_atento"}
UMBRAL_GIRO = math.radians(6)          # menos que esto no se toca
TOPE_BAJAR = math.radians(12)          # cabeza caída más que esto (fuera de los gestos que la bajan) se levanta

# ---------------------------------------------------------------- cuaterniones (x, y, z, w como glTF)
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx,
                     aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz])
def qinv(q):
    return np.array([-q[0], -q[1], -q[2], q[3]]) / np.dot(q, q)
def qrot(q, v):
    return qmul(qmul(q, np.array([v[0], v[1], v[2], 0.0])), qinv(q))[:3]
def qeje(eje, ang):
    eje = np.asarray(eje, float) / np.linalg.norm(eje)
    return np.array([*(eje * math.sin(ang / 2)), math.cos(ang / 2)])
def qnorm(q):
    return q / np.linalg.norm(q)

class Glb:
    def __init__(self, datos: bytes):
        self.datos = bytearray(datos)
        n = struct.unpack("<I", datos[12:16])[0]
        self.j = json.loads(datos[20:20 + n])
        self.bin0 = 20 + n + 8                    # comienzo del bloque BIN
        self.padre = {}
        for i, nd in enumerate(self.j["nodes"]):
            for h in nd.get("children", []):
                self.padre[h] = i

    def _acc(self, i):
        a = self.j["accessors"][i]; bv = self.j["bufferViews"][a["bufferView"]]
        nc = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[a["type"]]
        o = self.bin0 + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        assert a["componentType"] == 5126 and bv.get("byteStride", nc * 4) == nc * 4
        return o, np.frombuffer(bytes(self.datos[o:o + a["count"] * nc * 4]), dtype="<f4").reshape(-1, nc).astype(float)

    def _acc_mat(self, i):
        a = self.j["accessors"][i]; bv = self.j["bufferViews"][a["bufferView"]]
        o = self.bin0 + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return o, np.frombuffer(bytes(self.datos[o:o + a["count"] * 64]), dtype="<f4").reshape(-1, 16).astype(float)

    def escribir(self, i, valores):
        o, _ = self._acc(i)
        self.datos[o:o + valores.size * 4] = valores.astype("<f4").tobytes()

    def reposo(self, nodo):
        nd = self.j["nodes"][nodo]
        return (np.array(nd.get("translation", [0, 0, 0]), float), np.array(nd.get("rotation", [0, 0, 0, 1]), float),
                np.array(nd.get("scale", [1, 1, 1]), float))

def _muestra(t, v, x, interp):
    if x <= t[0]: return v[0]
    if x >= t[-1]: return v[-1]
    k = int(np.searchsorted(t, x)) - 1
    if interp == "STEP": return v[k]
    u = (x - t[k]) / (t[k + 1] - t[k])
    a, b = v[k], v[k + 1]
    if len(a) == 4:
        if np.dot(a, b) < 0: b = -b
        return qnorm(a * (1 - u) + b * u)
    return a * (1 - u) + b * u

class Clip:
    def __init__(self, g: Glb, an):
        self.g, self.nombre, self.pistas = g, an["name"], {}
        for ch in an["channels"]:
            s = an["samplers"][ch["sampler"]]
            _, t = g._acc(s["input"]); _, v = g._acc(s["output"])
            self.pistas[(ch["target"].get("node"), ch["target"]["path"])] = (t[:, 0], v, s.get("interpolation", "LINEAR"), s["output"])

    def local(self, nodo, x):
        tr, rot, esc = self.g.reposo(nodo)
        for camino in ("translation", "rotation", "scale"):
            p = self.pistas.get((nodo, camino))
            if p is not None:
                val = _muestra(p[0], p[1], x, p[2])
                if camino == "translation": tr = val
                elif camino == "rotation": rot = val
                else: esc = val
        return tr, rot, esc

    def global_rot(self, nodo, x):
        """Rotación del nodo en el espacio de la escena (las escalas de los ancestros se asumen uniformes)."""
        q = np.array([0, 0, 0, 1.0])
        cadena = []
        while nodo is not None:
            cadena.append(nodo); nodo = self.g.padre.get(nodo)
        for n in reversed(cadena):
            q = qmul(q, self.local(n, x)[1])
        return qnorm(q)

def _reposo_global(g: Glb, nodo):
    q = np.array([0, 0, 0, 1.0]); cadena = []
    while nodo is not None:
        cadena.append(nodo); nodo = g.padre.get(nodo)
    for n in reversed(cadena):
        q = qmul(q, g.reposo(n)[1])
    return qnorm(q)

def _rot_de_matriz(m):
    m = m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
    t = np.trace(m)
    if t > 0:
        w = math.sqrt(1 + t) / 2
        return qnorm(np.array([(m[2, 1] - m[1, 2]) / (4 * w), (m[0, 2] - m[2, 0]) / (4 * w), (m[1, 0] - m[0, 1]) / (4 * w), w]))
    i = int(np.argmax(np.diag(m))); j, k = (i + 1) % 3, (i + 2) % 3
    r = math.sqrt(1 + m[i, i] - m[j, j] - m[k, k])
    q = np.zeros(4); q[i] = r / 2; q[j] = (m[j, i] + m[i, j]) / (2 * r); q[k] = (m[k, i] + m[i, k]) / (2 * r)
    q[3] = (m[k, j] - m[j, k]) / (2 * r)
    return qnorm(q)

def _bind_global(g: Glb, nodo):
    """Rotación del hueso en la pose de modelado (inversa de su inverseBindMatrix, llevada a la escena por el nodo de
    la malla que usa la piel). Sin piel: su reposo."""
    for si, piel in enumerate(g.j.get("skins", [])):
        if nodo in piel["joints"] and "inverseBindMatrices" in piel:
            k = piel["joints"].index(nodo)
            o, m = g._acc_mat(piel["inverseBindMatrices"])
            ibm = m[k].reshape(4, 4).T            # glTF: columnas
            q = _rot_de_matriz(np.linalg.inv(ibm))
            malla = next((i for i, nd in enumerate(g.j["nodes"]) if nd.get("skin") == si), None)
            return qnorm(qmul(_reposo_global(g, malla), q)) if malla is not None else q
    return _reposo_global(g, nodo)

_TIPOS = {5126: "<f4", 5121: "u1", 5123: "<u2"}
def _acc_gen(g: Glb, i):
    a = g.j["accessors"][i]; bv = g.j["bufferViews"][a["bufferView"]]
    nc = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]; dt = np.dtype(_TIPOS[a["componentType"]])
    o = g.bin0 + bv.get("byteOffset", 0) + a.get("byteOffset", 0); paso = bv.get("byteStride", nc * dt.itemsize)
    crudo = np.frombuffer(bytes(g.datos[o:o + paso * a["count"]]), dtype="u1").reshape(a["count"], paso)[:, :nc * dt.itemsize]
    v = np.frombuffer(crudo.tobytes(), dtype=dt).reshape(-1, nc).astype(float)
    if a.get("normalized") and dt != np.float32:
        v /= 255 if dt == np.uint8 else 65535
    return v

def cara_modelado(g: Glb, cab) -> float:
    """Hacia dónde mira la cara en la pose de modelado: el plano vertical de mejor simetría de los vértices pegados a la
    cabeza (Tripo genera muchas cabezas ya giradas en la malla). Grados, 0 = +Z; se busca entre −90° y +90°."""
    pts = []
    for nd in g.j["nodes"]:
        if "mesh" not in nd or "skin" not in nd:
            continue
        piel = g.j["skins"][nd["skin"]]
        if cab not in piel["joints"]:
            continue
        k = piel["joints"].index(cab)
        for pr in g.j["meshes"][nd["mesh"]]["primitives"]:
            at = pr["attributes"]
            p, j, w = _acc_gen(g, at["POSITION"]), _acc_gen(g, at["JOINTS_0"]), _acc_gen(g, at["WEIGHTS_0"])
            pts.append(p[(w * (j == k)).sum(1) > 0.6])
    if not pts or sum(len(p) for p in pts) < 50:
        return 0.0
    p = np.vstack(pts)
    if len(p) > 1500:
        p = p[np.random.default_rng(0).choice(len(p), 1500, replace=False)]
    q = p - p.mean(0)
    mejor = (INF := float("inf"), 0.0)
    for th in np.radians(np.arange(-90, 91, 2)):
        n = np.array([math.cos(th), 0, -math.sin(th)])
        r = q - 2 * np.outer(q @ n, n)
        s = float(np.sqrt(((r[:, None, :] - q[None, :, :]) ** 2).sum(-1).min(1)).mean())
        if s < mejor[0]:
            mejor = (s, float(th))
    return math.degrees(mejor[1])

def _angulos(d):
    """Giro (alrededor de +Y, 0 = frente +Z) e inclinación (+ hacia abajo) de una dirección."""
    return math.atan2(d[0], d[2]), -math.asin(max(-1.0, min(1.0, d[1])))

def enderezar(datos: bytes, informe=None, cara=None) -> bytes:
    """cara: hacia dónde mira la cara en la pose de modelado (grados, 0 = +Z, + hacia +X). None: se estima por la
    simetría de la cabeza (ver cara_modelado)."""
    g = Glb(datos)
    nombres = {nd.get("name"): i for i, nd in enumerate(g.j["nodes"])}
    cab = next((nombres[h] for h in HUESOS_CABEZA if h in nombres), None)
    if cab is None or not g.j.get("animations"):
        return bytes(datos)
    padre = g.padre.get(cab)
    # frente de la cabeza en su espacio local: en la pose de modelado (bind, la de inverseBindMatrices) la cara mira al
    # frente del modelo (+Z). La pose de reposo de los nodos NO sirve: en los rigs de Tripo ya trae la cabeza girada.
    if cara is None:
        cara = cara_modelado(g, cab)
    frente = qrot(qinv(_bind_global(g, cab)), [math.sin(math.radians(cara)), 0, math.cos(math.radians(cara))])
    clips = [Clip(g, an) for an in g.j["animations"]]
    medidas = {}
    for c in clips:
        p = c.pistas.get((cab, "rotation"))
        if p is None:
            continue
        tiempos = p[0]
        angs = [_angulos(qrot(c.global_rot(cab, x), frente)) for x in tiempos]
        medidas[c.nombre] = (float(np.mean([a[0] for a in angs])), float(np.mean([a[1] for a in angs])))
    if not medidas:
        return bytes(datos)
    comunes = [m[0] for n, m in medidas.items() if n not in GESTO_GIRO]
    tipico = float(np.median(comunes)) if comunes else 0.0
    for c in clips:
        if c.nombre not in medidas:
            continue
        giro, baja = medidas[c.nombre]
        corr_giro = -(tipico if c.nombre in GESTO_GIRO else giro)
        corr_baja = 0.0
        if c.nombre not in GESTO_BAJAR and abs(baja) > TOPE_BAJAR:
            corr_baja = -(baja - math.copysign(TOPE_BAJAR, baja))
        if informe is not None:
            informe.append(f"{c.nombre:24s} giro {math.degrees(giro):+6.1f}° incl {math.degrees(baja):+6.1f}°"
                           f" → corrige {math.degrees(corr_giro):+6.1f}° / {math.degrees(corr_baja):+6.1f}°")
        if abs(corr_giro) < UMBRAL_GIRO and abs(corr_baja) < UMBRAL_GIRO:
            continue
        t, v, interp, salida = c.pistas[(cab, "rotation")]
        nuevos = v.copy()
        for k, x in enumerate(t):
            qp = c.global_rot(padre, x) if padre is not None else np.array([0, 0, 0, 1.0])
            qg = qmul(qp, v[k])
            # giro alrededor del vertical del mundo y, después, inclinación alrededor del eje lateral de la cabeza
            r = qeje([0, 1, 0], corr_giro)
            if corr_baja:
                d = qrot(qmul(r, qg), frente)
                lado = np.cross([0, 1, 0], d)
                if np.linalg.norm(lado) > 1e-6:
                    r = qmul(qeje(lado, corr_baja), r)
            nuevos[k] = qnorm(qmul(qinv(qp), qmul(r, qg)))
        g.escribir(salida, nuevos)
    if informe is not None:
        informe.append(f"giro típico {math.degrees(tipico):+.1f}°")
    return bytes(g.datos)

if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        inf = []
        datos = open(ruta, "rb").read()
        nuevo = enderezar(datos, inf)
        g0 = Glb(datos); nm = {nd.get("name"): i for i, nd in enumerate(g0.j["nodes"])}
        inf.insert(0, "cara en el modelado %+.0f°" % cara_modelado(g0, next(nm[h] for h in HUESOS_CABEZA if h in nm)))
        print(ruta.split("/")[-1]); print("  " + "\n  ".join(inf))
        inf2 = []; enderezar(nuevo, inf2)
        print("  después: " + "; ".join(l.split(" →")[0].split()[0] + l.split("giro")[1].split("°")[0] for l in inf2 if "→" in l))
