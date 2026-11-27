# Fray Domingo de Santo Tomás

Rig sobre `personas/domingo_de_santo_tomas/domingo.glb`, con los 53 huesos de la Universal Animation Library de Quaternius más un anclaje para el libro y dos para el hábito. La altura de referencia es 1,69 m. El GLB usa metros, frente +Z, vertical +Y y origen en el suelo. Las dos manos siguen el libro mediante cinemática inversa.

| Clip | Base UAL | Uso |
|---|---|---|
| `reposo` | `Idle_Loop` | Sostiene el libro abierto y respira con la vista baja. |
| `leer_libro` | `Idle_Loop` y gesto propio | Inclina el libro y recorre las páginas con la mirada. |
| `saludar` | `Idle_Loop` y gesto propio | Levanta la vista, hace una venia y vuelve a la lectura. |
| `hablar` | `Idle_Talking_Loop` | Explica con movimientos de cabeza y torso. |
| `caminar` | `Walk_Formal_Loop` | Marcha corta en sitio. Velocidad de referencia de 0,62 m/s. |

El [GLB animado](../../../../../personas/domingo_de_santo_tomas/domingo_de_santo_tomas_animado.glb) contiene los cinco clips a 24 fps. La [entrega web](../../../../../web/public/models/ciudad/codex/personajes/domingo_de_santo_tomas/) incluye el Blender editable, la ficha y el visor. Los gestos corresponden a la [ficha 25 de la guía](../../../../../personas/guiaPersonajes.md).

## Reproducir

Desde la raíz, con la biblioteca UAL instalada y las dependencias de `web/`.

```sh
revision_domingo=revisiones/codex/domingo_de_santo_tomas
mkdir -p "$revision_domingo"
NODE_OPTIONS=--max-old-space-size=1200 web/node_modules/.bin/gltf-transform simplify \
  personas/domingo_de_santo_tomas/domingo.glb "$revision_domingo/malla_reducida.glb" --ratio 0.008 --error 0.003
web/node_modules/.bin/gltf-transform resize \
  "$revision_domingo/malla_reducida.glb" "$revision_domingo/malla_1024.glb" --width 1024 --height 1024
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
  ~/apps/blender-5.2.3-linux-x64/blender -b --factory-startup -t 2 --python-exit-code 1 \
  -P blender/zonas/codex/personajes/domingo_de_santo_tomas/construir.py
python3 blender/zonas/codex/personajes/domingo_de_santo_tomas/preparar_visor.py
```
