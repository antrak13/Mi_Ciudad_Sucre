"""Personajes de la Asamblea de 1825 (Escena 1 de juego/) con MPFB: cuerpo de MakeHuman, ropa de época y animaciones.

Reutiliza el armado de blender/personajes_1809.py (cuerpo, esqueleto "game_engine", casaca, chaleco, corbatín,
texturas livianas para la web) y exporta a juego/assets/personajes/<nombre>.gltf (+ .bin y texturas/ compartidas).

Uso:
    blender -b --python blender/personajes_1825.py                # todos
    blender -b --python blender/personajes_1825.py -- serrano     # solo algunos
(no usar --factory-startup: hace falta la extensión MPFB y sus assets CC0 instalados; ver docs/CIUDAD_CHARCAS_1809.md)

La vestimenta es la de un letrado o diputado de 1825: levita oscura larga, chaleco claro, corbatín blanco, pantalón y
zapatos. Los colores y las edades son aproximaciones (no hay retratos de cuerpo entero de todos): conviene validarlos
con la Casa de la Libertad antes de presentarlos como reconstrucción fiel.
"""
import sys
import traceback
from math import sin
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import personajes_1809 as base  # noqa: E402  (se importa sin ejecutar: su main() solo corre como script)
from personajes_1809 import rx, rz  # noqa: E402

base.SALIDA = base.RAIZ / "juego" / "assets" / "personajes"

BLANCO = base.BLANCO
NEGRO_AZULADO = (0.05, 0.06, 0.1)
PARDO = (0.2, 0.13, 0.08)
VERDE_BOTELLA = (0.06, 0.12, 0.08)
AZUL_NOCHE = (0.06, 0.08, 0.18)
GRIS_PIZARRA = (0.16, 0.17, 0.19)
CREMA = (0.8, 0.75, 0.62)
GAMUZA = (0.66, 0.56, 0.38)
GRANATE = (0.3, 0.07, 0.07)
PANTALON_OSCURO = (0.1, 0.1, 0.11)
PANTALON_GRIS = (0.28, 0.27, 0.25)


# ---------------------------------------------------------------- animaciones propias

def hablar(t, f):
    """Conversa con el jugador: la mano derecha acompaña lo que dice y la cabeza asiente."""
    g, p = base.reposo(t, f)
    s = sin(f)
    g["upperarm_r"] = rx(-24 - 6 * s) @ rz(6)
    g["lowerarm_r"] = rx(-58 - 14 * sin(2 * f))
    g["hand_r"] = rx(-12) @ rz(14 * sin(2 * f + 0.6))
    g["upperarm_l"] = rx(-6)
    g["lowerarm_l"] = rx(-14)
    g["head"] = rz(4 * sin(f * 0.5)) @ rx(3 * sin(2 * f))
    return g, p


def orador(t, f):
    """Discurso: el brazo derecho se eleva con énfasis y el torso se inclina hacia el público."""
    g, p = base.reposo(t, f)
    s = 0.5 + 0.5 * sin(f)
    g["spine_02"] = rx(-5) @ rz(-3)
    g["upperarm_r"] = rx(-55 - 25 * s) @ rz(10)
    g["lowerarm_r"] = rx(-30 - 15 * s)
    g["hand_r"] = rx(-20 * s)
    g["upperarm_l"] = rx(-10)
    g["lowerarm_l"] = rx(-35)
    g["head"] = rx(-6) @ rz(6 * sin(f * 0.5))
    return g, p


def manos_juntas(t, f):
    """Secretario en espera: manos juntas delante del cuerpo, peso que se mueve apenas."""
    g, p = base.reposo(t, f)
    for lado, sx in (("l", 1), ("r", -1)):
        g[f"upperarm_{lado}"] = rx(-10) @ rz(-sx * 20)
        g[f"lowerarm_{lado}"] = rx(-72) @ rz(-sx * 16)
        g[f"hand_{lado}"] = rx(6)
    return g, p


base.ANIMACIONES.update({
    "hablar": (2.4, hablar),
    "orador": (3.2, orador),
    "manos_juntas": (4.0, manos_juntas),
})


# ---------------------------------------------------------------- elenco de la Escena 1

def caballero(edad, raza, piel, pelo, levita, vueltas, chaleco, pantalon, zapatos, animaciones, peso=0.5, altura=0.5,
              musculo=0.45):
    return dict(
        macro=dict(gender=1.0, age=edad, muscle=musculo, weight=peso, height=altura),
        raza=raza, piel=piel, pelo=pelo,
        ropa={"rehmanpolanski_viking_pants": pantalon, zapatos: None},
        casaca=dict(color=levita, vueltas=vueltas, largo=0.55, chaleco_color=chaleco), corbatin=BLANCO,
        animaciones=animaciones)


# Edad en la escala de MakeHuman: 0,5 = 25 años y 1,0 = 90 años.
ELENCO = {
    # Mariano Serrano, presidente de la Asamblea (nacido en 1788: 37 años en 1825)
    "serrano": caballero(0.59, dict(caucasian=0.7, asian=0.25, african=0.05), "middleage_caucasian_male", "short04",
                         NEGRO_AZULADO, NEGRO_AZULADO, CREMA, PANTALON_OSCURO, "shoes03", ["reposo", "hablar"],
                         peso=0.52, altura=0.52),
    # José Mariano Mendizábal, secretario: de más edad, en espera junto a la mesa
    "mendizabal": caballero(0.74, dict(caucasian=0.75, asian=0.2, african=0.05), "old_caucasian_male", "short01",
                            PARDO, PARDO, GAMUZA, PANTALON_GRIS, "shoes03", ["manos_juntas", "hablar"],
                            peso=0.58, altura=0.46, musculo=0.38),
    # Casimiro Olañeta, el orador (nacido en 1795: 30 años en 1825)
    "olaneta": caballero(0.54, dict(caucasian=0.75, asian=0.2, african=0.05), "young_caucasian_male", "short02",
                         VERDE_BOTELLA, VERDE_BOTELLA, CREMA, PANTALON_OSCURO, "shoes03", ["orador", "reposo", "hablar"],
                         peso=0.45, altura=0.55, musculo=0.5),
    # Diputado del Perú (personaje ficticio)
    "diputado_peru": caballero(0.64, dict(caucasian=0.45, asian=0.5, african=0.05), "middleage_asian_male", "short02",
                               AZUL_NOCHE, AZUL_NOCHE, GRANATE, PANTALON_OSCURO, "culturalibre_male_boots",
                               ["reposo", "hablar"], peso=0.55, altura=0.47),
    # El cronista: narrador que acompaña al jugador (personaje ficticio). Mayor, levita gris de viaje y sombrero de ala ancha.
    "cronista": dict(caballero(0.78, dict(caucasian=0.7, asian=0.25, african=0.05), "old_caucasian_male", "short01",
                               (0.24, 0.23, 0.22), (0.18, 0.17, 0.16), (0.55, 0.5, 0.42), PANTALON_OSCURO,
                               "culturalibre_male_boots", ["reposo", "caminar", "hablar"], peso=0.5, altura=0.5,
                               musculo=0.35), sombrero="ala_ancha"),
    # Diputado del Río de la Plata (personaje ficticio)
    "diputado_rioplata": caballero(0.62, dict(caucasian=0.85, asian=0.1, african=0.05), "young_caucasian_male2",
                                   "short03", GRIS_PIZARRA, GRIS_PIZARRA, BLANCO, PANTALON_GRIS, "culturalibre_male_boots",
                                   ["reposo", "hablar"], peso=0.48, altura=0.58),
}


def main():
    pedidos = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    errores = 0
    for nombre, spec in ELENCO.items():
        if pedidos and nombre not in pedidos:
            continue
        try:
            base.armar(nombre, spec, detalle_alto=True)
        except Exception:
            traceback.print_exc()
            print(f"[error] {nombre}")
            errores += 1
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
