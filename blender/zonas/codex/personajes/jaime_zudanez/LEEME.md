# Jaime Zudáñez

El rig parte de `personas/jaime_zudanez/jaime_zudanes.glb`. Usa los 53 huesos de la Universal Animation Library de Quaternius, un anclaje en la mano izquierda para la caja y dos huesos para los faldones de la levita. La altura con sombrero es 1,78 m. El GLB mide en metros, con frente +Z, vertical +Y y raíz en el suelo.

| Clip | Base UAL | Uso |
|---|---|---|
| `reposo` | `Idle_Loop` | Respira y sostiene la caja. |
| `caminar` | `Walk_Formal_Loop` | Marcha en sitio a 0,78 m/s de referencia. |
| `hablar` | `Idle_Talking_Loop` | Acompaña el relato con un movimiento discreto de hombros, cabeza y mano. |
| `negar` | `Idle_Loop` y gesto propio | Niega con la cabeza al consultar la versión del alguacil Tardío. |
| `tamborilear_caja` | `Idle_Loop` y gesto propio | Acerca la mano derecha, alterna índice y medio sobre la tapa y vuelve a reposo. |

El [GLB animado](../../../../../personas/jaime_zudanez/jaime_zudanez_animado.glb) contiene los cinco clips a 24 fps. La [entrega web](../../../../../web/public/models/ciudad/codex/personajes/jaime_zudanez/) incluye el Blender editable, la ficha y el visor. La interacción sigue la [ficha 9 de la guía](../../../../../personas/guiaPersonajes.md).

## Reproducir

Desde la raíz, con la biblioteca UAL instalada y las dependencias de `web/`.

```sh
revision_jaime=revisiones/codex/jaime_zudanez
mkdir -p "$revision_jaime"
NODE_OPTIONS=--max-old-space-size=1200 web/node_modules/.bin/gltf-transform simplify \
  personas/jaime_zudanez/jaime_zudanes.glb "$revision_jaime/malla_reducida.glb" --ratio 0.008 --error 0.003
web/node_modules/.bin/gltf-transform resize \
  "$revision_jaime/malla_reducida.glb" "$revision_jaime/malla_1024.glb" --width 1024 --height 1024
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
  ~/apps/blender-5.2.3-linux-x64/blender -b --factory-startup -t 2 --python-exit-code 1 \
  -P blender/zonas/codex/personajes/jaime_zudanez/construir.py
python3 blender/zonas/codex/personajes/jaime_zudanez/preparar_visor.py
```
