# Francisco Ríos, el Quitacapas

El rig se construye sobre el GLB de Tripo en [personas/quitacapas](../../../../../personas/quitacapas/). Usa 53 huesos de la Universal Animation Library de Quaternius y cuatro anclajes para la caída de la capa, la vaina y la llave. La altura de referencia es 1,73 m. El GLB usa metros, frente +Z y vertical +Y, con la raíz en el suelo.

| Clip | Base UAL | Uso |
|---|---|---|
| `reposo` | `Idle_Loop` | Espera y respira. |
| `fanfarron_caminar` | `Walk_Loop` | Marcha en sitio con la barbilla alta y la capa al hombro. Velocidad de referencia de 1 m/s. |
| `hablar` | `Idle_Talking_Loop` | Acompaña el relato con cabeza, hombros y torso. |
| `mostrar_llave` | `Idle_Loop` y gesto propio | Alza la llave con la derecha y vuelve a reposo. |
| `lanzar_monedas` | `Idle_Loop` y gesto propio | Hace el gesto de esparcir monedas. La ficha marca el fotograma 17 a 24 fps para emitir las partículas desde la mano derecha. |
| `reir` | `Idle_Loop` y gesto propio | Sacude el torso e inclina la cabeza. |

La [entrega](../../../../../web/public/models/ciudad/codex/personajes/quitacapas/) contiene el GLB con seis clips a 24 fps, el Blender editable, el visor y la ficha para reproducir los movimientos. La ruta entre hitos y las partículas de monedas corresponden a la escena de la [guía de personajes](../../../../../personas/guiaPersonajes.md#2-francisco-ríos-el-quitacapas-y-el-zambito).

## Reproducir

Desde la raíz, con la biblioteca UAL instalada y las dependencias de `web/`.

```sh
revision_quitacapas=revisiones/codex/quitacapas
mkdir -p "$revision_quitacapas"
NODE_OPTIONS=--max-old-space-size=1200 web/node_modules/.bin/gltf-transform simplify \
  personas/quitacapas/quitacapas.glb "$revision_quitacapas/malla_reducida.glb" --ratio 0.008 --error 0.003
web/node_modules/.bin/gltf-transform resize \
  "$revision_quitacapas/malla_reducida.glb" "$revision_quitacapas/malla_1024.glb" --width 1024 --height 1024
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
  ~/apps/blender-5.2.3-linux-x64/blender -b --factory-startup -t 2 --python-exit-code 1 \
  -P blender/zonas/codex/personajes/quitacapas/construir.py
python3 blender/zonas/codex/personajes/quitacapas/preparar_visor.py
```
