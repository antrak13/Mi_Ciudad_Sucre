# Personajes de claude

Personajes de `personas/` que ya tienen modelo estático (GLB de Tripo): se riggean y animan, **no se modelan de cero**.
Esqueleto: los 53 huesos de la Universal Animation Library (`ciudad3d/personajes/animaciones/quaternius/`, CC0) +
huesos propios para objetos (p. ej. `palo`). Se reutiliza el kit de antigravity
(`blender/zonas/antigravity/personajes/kit_ual.py`: armadura UAL, retarget, IK y horneado).

| Pieza | Qué hace |
|---|---|
| `kit_personaje.py` | Común a todos: simplificar la malla, importar, color de textura por vértice, cortar caras e islas, retarget desde la UAL (`huesos_desde_ual`, con `alinear` para mallas que no están en pose neutra), `apoyar_pies`, renders de control y exportación (GLB, .blend, ficha, visor y catálogo). |
| `pesos_envolvente.py` | Pesos por envolventes con compuertas, mezclas fijas (falda, mantón) y piezas rígidas (numpy puro, se prueba sin Blender); `caras_entre_piezas` y `caras_tapa_inferior` (cortan lo que Tripo funde: objeto con el cuerpo, ruedo con el zapato, tapa bajo la falda). |
| `verificar_glb.py` | Reimporta un GLB exportado y mide por clip el cierre y el punto más bajo (nada bajo el suelo). |
| `<id>/anatomia.py` | Medidas del personaje en unidades normalizadas (altura = 1): huesos, radios, máscaras. |
| `<id>/construir.py` | Importa la malla simplificada, rig, pesos, clips (UAL + propios), renders de control y exportación. |

Salida: `web/public/models/ciudad/claude/personajes/<id>/` (`<id>.glb`, `.blend`, `ficha.json`, visor `index.html`).

## Niño de las hornacinas (Guía #21)

```
~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/nino_hornacinas/construir.py [-- --prueba]
```
~1,1 GB de memoria, ~80 s. `--prueba` solo renderiza las poses de control (`revisiones/claude/nino_hornacinas/`).

- 1,30 m con tricornio, 29 658 triángulos, texturas 2048 px, GLB 2,6 MB, 54 huesos, 16 clips a 24 fps.
- Propios: `galopar_palo` (bucle, 2,0 m/s), `huir` (bucle, 3,4 m/s, mira atrás una vez), `ocultarse` (termina
  agachado para el fundido), `asomarse` (bucle, la columna queda a su derecha), `reir` (gesto antes de huir).
- Comunes: `reposo`, `caminar`, `caminar_rapido`, `sigilo`, `mirar_atras`, `hablar`, `saludar`, `asentir`,
  `senalar`, `silencio`, `llamar_mano`. Los clips de desplazamiento son en el sitio: el avance lo pone el controlador.
- Comprobado al reimportar el GLB: bucles cerrados exactos, gestos que vuelven al reposo (< 1 mm), nada bajo el suelo.
- Pendiente del sistema común: ojos emisivos de noche, huella de garra (calcomanía) y el fundido son del lado Godot.

## Mariana Zudáñez (Guía #3)

```
~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/mariana_zudanez/construir.py [-- --prueba]
```
- 1,62 m, 28 414 triángulos, GLB 2,4 MB, 53 huesos, 11 clips. La malla viene en la pose de la lámina (brazo izquierdo
  señalando, cabeza girada ~80°, paso abierto): `senalar` la conserva; los demás enderezan piernas y brazo hacia la UAL.
- Propios: `reposo_inquieta` (bucle), `correr_falda` (bucle, 2,2 m/s), `gritar_brazo_alto`.
- Comunes: `reposo`, `caminar`, `caminar_rapido`, `senalar`, `mirar_atras`, `hablar`, `llamar_mano` («¡Sígame!»), `asentir`.
- La mano derecha aprieta el mantón en todos los clips (no se anima). Al caminar los pies van planos: si giraran talón
  y punta arrastrarían el ruedo. Mantón separado de la falda por el color de la textura.

## Benito María de Moxó (Guía #24): de día y de noche

```
~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/moxo/construir.py -- dia|noche [--prueba [clip…]] [--pesos]
```
- Dos GLB del usuario (`personas/moxo/moxo_dia.glb`, `moxo_noche.glb`), 1,58 m, 53 huesos. `construir.py` es el
  proceso común; `variante_dia.py` / `variante_noche.py` traen clips y poses, `anatomia_*.py` las medidas y pesos,
  `comun.py` lo compartido. `--pesos` pinta el hueso dominante de cada vértice.
- **Día** (9 clips): propios `examinar_lupa` (bucle) y `arrugar_papel`; comunes `reposo`, `caminar`, `hablar`,
  `saludar` (bendice), `asentir`, `mirar_atras`, `senalar` (con la lupa). Lupa y concha rígidas a cada mano.
- **Noche** (8 clips): propio `huir_mirando_atras` (bucle, 1,3 m/s); comunes `reposo` (espera nervioso), `caminar`,
  `caminar_rapido`, `mirar_atras`, `hablar`, `llamar_mano` (a los clérigos), `asentir`. La mano derecha aprieta la
  capa en todos. Sin `sigilo`: agachado, los zapatos asomaban sueltos detrás de la sotana.
- Pies: conservan la orientación de la malla (`pies_como_malla`) y el pie de atrás de la noche descuenta su alzado
  (`ALZADO`). Se borra el fondo interior de la sotana a ras del suelo (`caras_a_ras_del_suelo`).
- Brazos despegados del cuerpo: las costuras se desdoblan (`desdoblar_costuras`: una copia con el cuerpo y otra
  con el brazo) y el material va a doble cara (`exportar(..., doble_cara=True)`): Tripo no modela la tela bajo el
  brazo y, con una sola cara, el hueco dejaba ver el fondo.
- Signo: en la cabeza, `pitch_x` > 0 de `rotar_euler_mundo` baja la cara; las variantes lo invierten en `mirar`.

## Cochero de las carrozas

```
~/apps/blender-5.2.3-linux-x64/blender -b -P blender/zonas/claude/personajes/cochero/construir.py [-- --sin-render]
```
- El GLB del usuario (`personas/cochero/chofer.glb`, 4,9 M triángulos) ya viene sentado con las manos al frente: no se
  riggea. 6 370 triángulos, color de la textura por cara (facetado), 1,30 m sentado, origen en el apoyo de las nalgas.
- Extras: `pescante` (asiento en cada carroza, medido en `revisiones/claude/cochero/`) y `manos` (puños: de ahí salen
  las riendas). `web/scripts/preparar_vehiculos.mjs` lo funde al kit de las carrozas.
