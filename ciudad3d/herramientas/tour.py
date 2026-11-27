#!/usr/bin/env python3
"""Tour guiado del centro histórico: empaqueta el guion (tour/guion.json) para la ciudad 3D.

    python3 ciudad3d/herramientas/tour.py          → ciudad3d/datos/tour.json + datos/tour/…

- Voz: cada locución (tour/audio/<id>.mp3, ElevenLabs) se corta en sus frases (pausas halladas con silencedetect y
  repartidas según el largo de cada frase del texto) y cada frase se codifica como las voces de los encuentros:
  Ogg Opus 32 kbps para la web (el <audio> la va bajando mientras suena) y MP3 48 kbps para el APK/escritorio.
  Así la carta muestra una frase por vez, al ritmo de la voz, y el guion elige qué frases entran (se pueden saltar
  las que no se sostienen con las fuentes del proyecto).
- Frases de personajes ya grabadas (datos/personajes.json): se citan con {"personaje": id, "frase": n} y suenan con su
  propia voz y su camafeo.
- Láminas (fotos y grabados de archivo, recursos/originales/tour/): se reducen a ≤ 1280 px, JPEG calidad 82, en
  datos/tour/laminas/<id>.jpg.bin (la web las baja a demanda, con la versión en la dirección).
- Figurantes de la procesión: GLB aligerados (solo los clips que usa el tour, malla reducida, texturas JPEG; ver
  web/scripts/figurante_tour.mjs) y cabezas enderezadas, en datos/tour/figurantes/.
"""
import hashlib, io, json, re, subprocess, sys, shutil, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import cabezas
from personajes import CODIFICACION, _duracion

RAIZ = Path(__file__).resolve().parents[2]
GUION = RAIZ / "tour" / "guion.json"
AUDIO = RAIZ / "tour" / "audio"
SALIDA = RAIZ / "ciudad3d" / "datos"
DESTINO = SALIDA / "tour"
LADO_LAMINA = 1280


def huella(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()[:10]


# ------------------------------------------------------------------------------------------------ voz
def frases_de(texto: str) -> list:
    """Divide un texto en frases (punto, signo de cierre) sin cortar iniciales como 'M. Fontaine'."""
    partes, actual = [], ""
    for trozo in re.split(r"(?<=[.!?…])\s+", texto.strip()):
        actual = (actual + " " + trozo).strip() if actual else trozo
        if re.search(r"(?:^|\s)[A-ZÁÉÍÓÚ]\.$", actual):       # inicial suelta: sigue la misma frase
            continue
        partes.append(actual)
        actual = ""
    if actual:
        partes.append(actual)
    return partes


def silencios(origen: Path) -> list:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(origen), "-af", "silencedetect=n=-38dB:d=0.18", "-f", "null", "-"],
                       capture_output=True, text=True)
    ini, res = None, []
    for linea in r.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", linea)
        if m:
            ini = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", linea)
        if m and ini is not None:
            res.append((ini, float(m.group(1))))
            ini = None
    return res


def cortes(origen: Path, frases: list) -> list:
    """Instantes de corte entre frases: la pausa más cercana al momento esperado (proporcional a las letras)."""
    dur = _duracion(origen)
    pausas = silencios(origen)
    inicio = pausas[0][1] if pausas and pausas[0][0] < 0.05 else 0.0
    fin = pausas[-1][0] if pausas and pausas[-1][1] > dur - 0.05 else dur
    letras = [len(f) for f in frases]
    total = sum(letras)
    res, acum, previo = [], 0, inicio
    for k in range(len(frases) - 1):
        acum += letras[k]
        esperado = inicio + (fin - inicio) * acum / total
        candidatas = [p for p in pausas if p[0] > previo + 0.8 and p[1] < fin - 0.5]
        if not candidatas:
            raise SystemExit(f"{origen.name}: no hay pausa para el corte {k + 1}")
        mejor = min(candidatas, key=lambda p: abs((p[0] + p[1]) / 2 - esperado) - 0.6 * (p[1] - p[0]))
        medio = (mejor[0] + mejor[1]) / 2
        if abs(medio - esperado) > 3.0:
            print(f"  aviso {origen.name}: corte {k + 1} a {medio:.2f}s (esperado {esperado:.2f}s)", file=sys.stderr)
        res.append(medio)
        previo = medio
    return [0.0] + res + [dur]


def voz_de_locucion(lid: str, indice: dict, vigentes: set) -> list:
    """[{texto, voz, av, dur}] de cada frase de la locución tour/audio/<lid>.mp3."""
    origen = AUDIO / f"{lid}.mp3"
    texto = json.loads((AUDIO / "textos.json").read_text())[lid]
    frases = frases_de(texto)
    av_origen = huella(origen.read_bytes())
    previo = indice.get(lid, {})
    if previo.get("av") == av_origen and len(previo.get("frases", [])) == len(frases) and \
            all((DESTINO / "voz" / f"{lid}_{i:02d}.{fmt}.bin").exists() for i in range(len(frases)) for fmt in CODIFICACION):
        res = previo["frases"]
    else:
        t = cortes(origen, frases)
        res = []
        for i, f in enumerate(frases):
            a, b = t[i], t[i + 1]
            for fmt, args in CODIFICACION.items():
                destino = DESTINO / "voz" / f"{lid}_{i:02d}.{fmt}.bin"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(origen),
                                "-ac", "1", "-map_metadata", "-1", "-af", "afade=t=in:d=0.03,areverse,afade=t=in:d=0.06,areverse",
                                *args, str(destino)], check=True)
            mp3 = DESTINO / "voz" / f"{lid}_{i:02d}.mp3.bin"
            res.append({"texto": f, "voz": f"tour/voz/{lid}_{i:02d}",
                        "av": huella(mp3.read_bytes()), "dur": round(b - a, 2)})
        indice[lid] = {"av": av_origen, "frases": res}
    for i in range(len(res)):
        for fmt in CODIFICACION:
            vigentes.add(f"{lid}_{i:02d}.{fmt}.bin")
    return res


# ------------------------------------------------------------------------------------------------ láminas
def lamina(lid: str, d: dict) -> dict:
    from PIL import Image, ImageOps
    origen = RAIZ / d["archivo"]
    im = ImageOps.exif_transpose(Image.open(origen)).convert("RGB")
    if "recorte" in d:                       # [x0, y0, x1, y1] en fracciones de la imagen
        x0, y0, x1, y1 = d["recorte"]
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    im.thumbnail((LADO_LAMINA, LADO_LAMINA), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=82, optimize=True, progressive=False)
    datos = b.getvalue()
    destino = DESTINO / "laminas" / f"{lid}.jpg.bin"
    if not destino.exists() or destino.read_bytes() != datos:
        destino.write_bytes(datos)
    return {"archivo": f"tour/laminas/{lid}.jpg.bin", "v": huella(datos), "ancho": im.width, "alto": im.height,
            "pie": d["pie"], "fuente": d.get("fuente", "")}


# ------------------------------------------------------------------------------------------------ figurantes
def figurante(fid: str, d: dict) -> dict:
    """d = {modelo, triangulos (proporción que queda), lado (textura), clips}: ver web/scripts/figurante_tour.mjs."""
    origen = RAIZ / d["modelo"]
    destino = DESTINO / "figurantes" / f"{fid}.bin"
    marca = DESTINO / "figurantes" / f"{fid}.origen"
    h = huella(origen.read_bytes() + json.dumps(d, sort_keys=True).encode())
    if not destino.exists() or not marca.exists() or marca.read_text() != h:
        with tempfile.TemporaryDirectory() as tmp:
            reducido = Path(tmp) / "r.glb"
            subprocess.run(["node", str(RAIZ / "web" / "scripts" / "figurante_tour.mjs"), str(origen), str(reducido),
                            str(d.get("triangulos", 1)), str(d.get("lado", 1024)), ",".join(d.get("clips", []))],
                           check=True, cwd=RAIZ / "web")
            datos = reducido.read_bytes()
        try:
            datos = cabezas.enderezar(datos)
        except Exception as e:                # la Virgen y otros sin esqueleto de Tripo
            print(f"  {fid}: sin enderezar ({e})", file=sys.stderr)
        destino.write_bytes(datos)
        marca.write_text(h)
    datos = destino.read_bytes()
    return {"archivo": f"tour/figurantes/{fid}.bin", "v": huella(datos), "kb": len(datos) // 1024}


# ------------------------------------------------------------------------------------------------ guion
def main() -> int:
    g = json.loads(GUION.read_text())
    personajes = {p["id"]: p for p in json.loads((SALIDA / "personajes.json").read_text())["personajes"]}
    for sub in ("voz", "laminas", "figurantes"):
        (DESTINO / sub).mkdir(parents=True, exist_ok=True)
    indice_f = DESTINO / "voz" / "indice.json"
    indice = json.loads(indice_f.read_text()) if indice_f.exists() else {}
    vigentes = set()
    locuciones = {}
    usadas_lam = set()
    for parada in g["paradas"]:
        for toma in parada["tomas"]:
            pasos = []
            for f in toma.get("frases", []):
                if "locucion" in f:
                    lid = f["locucion"]
                    if lid not in locuciones:
                        locuciones[lid] = voz_de_locucion(lid, indice, vigentes)
                    todas = locuciones[lid]
                    elegidas = f.get("frases", list(range(len(todas))))
                    for i in elegidas:
                        p = dict(todas[i])
                        p["quien"] = "cronista"
                        pasos.append(p)
                elif "personaje" in f:
                    pj = personajes[f["personaje"]]
                    frase = pj["guion"][f["frase"]]
                    p = {k: frase[k] for k in ("texto", "voz", "av", "dur") if k in frase}
                    p["quien"] = frase["quien"]
                    if frase["quien"] != "cronista":
                        p["nombre"] = pj["nombre"]
                        p["retrato"] = pj.get("retrato", "")
                    pasos.append(p)
                else:                          # solo texto (sin voz grabada: la carta va por tiempo de lectura)
                    pasos.append({"texto": f["texto"], "quien": f.get("quien", "cronista")})
                for clave in ("lamina", "sonido", "escena", "fundido"):
                    if clave in f:
                        pasos[-1][clave] = f[clave]
                        if clave in ("lamina", "fundido"):
                            usadas_lam.add(f[clave] if isinstance(f[clave], str) else f[clave]["id"])
            toma["pasos"] = pasos
            toma.pop("frases", None)
    laminas = {}
    for lid, d in g.get("laminas", {}).items():
        if lid in usadas_lam:
            laminas[lid] = lamina(lid, d)
    faltan = usadas_lam - set(laminas)
    if faltan:
        print("láminas sin definir:", faltan, file=sys.stderr)
        return 1
    g["laminas"] = laminas
    figs = {}
    for fid, d in g.get("figurantes", {}).items():
        figs[fid] = figurante(fid, d)
    g["figurantes"] = figs
    sonidos = {}
    for sid, ruta in g.get("sonidos", {}).items():
        origen = RAIZ / ruta
        for fmt, args in CODIFICACION.items():
            destino = DESTINO / "voz" / f"son_{sid}.{fmt}.bin"
            vigentes.add(destino.name)
            if not destino.exists() or destino.stat().st_mtime < origen.stat().st_mtime:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(origen), "-ac", "1", "-map_metadata", "-1", *args,
                                str(destino)], check=True)
        sonidos[sid] = {"voz": f"tour/voz/son_{sid}", "av": huella((DESTINO / "voz" / f"son_{sid}.mp3.bin").read_bytes()),
                        "dur": _duracion(origen)}
    g["sonidos"] = sonidos
    for f in (DESTINO / "voz").iterdir():
        if f.name != "indice.json" and f.name not in vigentes:
            f.unlink()
    for f in (DESTINO / "laminas").iterdir():
        if f.name.removesuffix(".jpg.bin") not in laminas:
            f.unlink()
    indice_f.write_text(json.dumps({k: v for k, v in indice.items() if k in locuciones}, indent=1, ensure_ascii=False))
    (SALIDA / "tour.json").write_text(json.dumps(g, ensure_ascii=False, indent=1))
    peso = sum(f.stat().st_size for f in DESTINO.rglob("*.bin"))
    n = sum(len(t["pasos"]) for p in g["paradas"] for t in p["tomas"])
    print(f"tour: {len(g['paradas'])} paradas, {n} frases, {len(laminas)} láminas, {len(figs)} figurantes, "
          f"{peso / 1e6:.1f} MB en datos/tour/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
