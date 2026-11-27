#!/usr/bin/env python3
"""Personajes de la ciudad: junta la colocación (contenido/personajes.json) con el texto de los encuentros
(personas/encuentros/guiones.md) y copia los modelos a ciudad3d/datos/personajes/ (la web los baja a demanda).

    python3 ciudad3d/herramientas/personajes.py          → ciudad3d/datos/personajes.json + datos/personajes/<id>.bin

Formato de una línea de guion (ver la cabecera de guiones.md):
    - *(cronista)* **H2** «texto» `gesto` (fuentes)
El texto de los encuentros se edita en guiones.md, nunca en el JSON generado.
"""
import hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import cabezas

RAIZ = Path(__file__).resolve().parents[2]
COLOCACION = RAIZ / "contenido" / "personajes.json"
GUIONES = RAIZ / "personas" / "encuentros" / "guiones.md"
SALIDA = RAIZ / "ciudad3d" / "datos"
VOCES = RAIZ / "personas" / "encuentros" / "audio"

SECCIONES = {"P": "presentacion", "H": "historia", "C": "historia", "M": "mecanica", "E": "edificio",
             "D": "donacion", "G": "gracias", "R": "regreso"}
LINEA = re.compile(
    r"^- (?:\*\((?P<a1>[^)]*)\)\*\s*)?(?:\*\*(?P<tag>[A-Z])\d*(?: \([^)]*\))?\*\*\s*)?(?:\*\((?P<a2>[^)]*)\)\*\s*)?"
    r"«(?P<texto>.+?)»(?P<resto>.*)$")
GESTO = re.compile(r"`([a-z_]+)`")
FUENTES = re.compile(r"\(((?:[QRCG][ -]?p?\.? ?\d[^()]*?))\)")


def secciones_de_guion(texto: str) -> dict:
    """{id: [líneas del bloque]} para cada '### N. … `id` …'."""
    bloques, actual = {}, None
    for linea in texto.splitlines():
        if linea.startswith("## ") or linea.startswith("### "):
            actual = None
            if linea.startswith("### "):
                m = re.search(r"`([a-z_]+)`", linea)
                if m:
                    actual = bloques.setdefault(m.group(1), [])
            continue
        if actual is not None:
            actual.append(linea)
    return bloques


def guion(lineas: list) -> list:
    pasos = []
    for linea in lineas:
        m = LINEA.match(linea.strip())
        if not m:
            continue
        anot = " ".join(x for x in (m["a1"], m["a2"]) if x)
        quien = "cronista" if "cronista" in anot else "personaje"
        tag = m["tag"] or ("C" if quien == "cronista" else None)
        if tag not in SECCIONES:
            continue
        resto = m["resto"]
        paso = {"seccion": SECCIONES[tag], "quien": quien, "texto": m["texto"].strip()}
        g = GESTO.search(resto)
        if g:
            paso["gesto"] = g.group(1)
        f = FUENTES.findall(resto)
        if f:
            paso["fuentes"] = "; ".join(f)
        pasos.append(paso)
    return pasos


def fuentes_generales(lineas: list) -> str:
    for linea in lineas:
        m = re.match(r"^- \*\*Fuentes:\*\*\s*(.+)$", linea.strip())
        if m:
            return re.sub(r"[`*]", "", m.group(1)).split("; edificio")[0].strip().rstrip(".")
    return ""


# Voces (ver personas/encuentros/audio y audio_encuentros.py). El original de ElevenLabs (MP3 128 kbps) se recodifica:
#  - web: Ogg Opus 32 kbps mono (≈ ¼ del original; la página lo reproduce con <audio>, que lo va bajando mientras suena)
#  - APK/escritorio y navegadores sin Opus: MP3 48 kbps mono a 32 kHz (Godot lo decodifica; va dentro del paquete)
# Los dos llevan extensión propia + .bin (Godot no los importa y viajan tal cual). Solo se recodifica si cambió el original.
CODIFICACION = {
    "opus": ["-c:a", "libopus", "-b:a", "32k", "-application", "audio", "-f", "ogg"],
    "mp3": ["-ar", "32000", "-c:a", "libmp3lame", "-b:a", "48k", "-f", "mp3"],
}


def _duracion(archivo: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(archivo)],
                       capture_output=True, text=True, check=True)
    return round(float(r.stdout.strip()), 2)


def poner_voces(pid: str, pasos: list) -> int:
    """Codifica el audio de cada frase (personas/encuentros/audio/<id>/NN.mp3) en datos/personajes/voz/<id>/NN.<fmt>.bin
    y anota en el paso 'voz' (ruta sin formato), 'av' (versión) y 'dur' (s). Devuelve cuántas frases tienen voz."""
    carpeta = SALIDA / "personajes" / "voz" / pid
    indice_f = carpeta / "indice.json"
    indice = json.loads(indice_f.read_text()) if indice_f.exists() else {}
    vigentes = set()
    n = 0
    for i, paso in enumerate(pasos):
        origen = VOCES / pid / f"{i:02d}.mp3"
        if not origen.exists():
            continue
        av = hashlib.sha1(origen.read_bytes()).hexdigest()[:10]
        carpeta.mkdir(parents=True, exist_ok=True)
        clave = f"{i:02d}"
        for fmt, args in CODIFICACION.items():
            destino = carpeta / f"{clave}.{fmt}.bin"
            vigentes.add(destino.name)
            if indice.get(clave, {}).get("av") != av or not destino.exists():
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(origen), "-ac", "1", "-map_metadata", "-1", *args,
                                str(destino)], check=True)
        if indice.get(clave, {}).get("av") != av:
            indice[clave] = {"av": av, "dur": _duracion(origen)}
        paso["voz"] = f"personajes/voz/{pid}/{clave}"
        paso["av"] = av
        paso["dur"] = indice[clave]["dur"]
        n += 1
    if carpeta.exists():
        for f in carpeta.iterdir():          # restos de versiones anteriores (.bin sin formato, frases quitadas)
            if f.name != "indice.json" and f.name not in vigentes:
                f.unlink()
        indice_f.write_text(json.dumps(indice, indent=1))
    return n


def main() -> int:
    colocacion = json.loads(COLOCACION.read_text())
    bloques = secciones_de_guion(GUIONES.read_text())
    (SALIDA / "personajes").mkdir(parents=True, exist_ok=True)
    salida = []
    for p in colocacion["personajes"]:
        origen = RAIZ / p["modelo"]
        datos = cabezas.enderezar(origen.read_bytes())     # Tripo: cabezas giradas o caídas (ver cabezas.py)
        huella = hashlib.sha1(datos).hexdigest()[:10]
        destino = SALIDA / "personajes" / f"{p['id']}.bin"
        if not destino.exists() or destino.read_bytes() != datos:
            destino.write_bytes(datos)
        q = {k: v for k, v in p.items() if k != "modelo"}
        q["archivo"] = f"personajes/{p['id']}.bin"
        q["v"] = huella
        if "acompana" not in p:
            lineas = bloques.get(p["id"])
            if not lineas:
                print(f"falta el guion de {p['id']} en {GUIONES.name}", file=sys.stderr)
                return 1
            q["guion"] = guion(lineas)
            q["fuentes"] = fuentes_generales(lineas)
            con_voz = poner_voces(p["id"], q["guion"])
            cuenta = {}
            for paso in q["guion"]:
                cuenta[paso["seccion"]] = cuenta.get(paso["seccion"], 0) + 1
            print(f"{p['id']}: {cuenta}" + (f", voz en {con_voz}/{len(q['guion'])} frases" if con_voz else ""))
        salida.append(q)
    (SALIDA / "personajes.json").write_text(json.dumps({"personajes": salida}, ensure_ascii=False, indent=1))
    print(f"{len(salida)} personajes → {SALIDA / 'personajes.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
