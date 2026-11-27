# El zambito

Acompañante de Francisco Ríos, el Quitacapas, en la ficha 2 de [la guía de personajes](../../../../../personas/guiaPersonajes.md). El catálogo Q-0455-1 menciona que lo seguía cargando las armas y la capa.

El rig se construye sobre el GLB estático `personas/zambito/zambito.glb`. La copia animada conserva su apariencia y sus mapas del material, reducidos a 1024 px. La vaina se separó del calzón en los puntos donde la malla los unía. Usa los 53 huesos de la Universal Animation Library instalada más dos anclajes. `capa_doblada` sigue el antebrazo izquierdo y `sable_envainado` sigue la pelvis. La escala de 1,59 m con sombrero es una decisión de diseño del recurso.

| Clip | Base UAL | Uso |
| --- | --- | --- |
| `reposo` | `Idle_Loop` | Bucle de espera. |
| `caminar` | `Walk_Loop` | Marcha en sitio a 0,94 m/s de referencia. |
| `caminar_rapido` | `Walk_Loop` | Paso más rápido en sitio a 1,18 m/s. |
| `cargar_bulto` | `Idle_Loop` y gesto propio | Alza el brazo y acomoda la capa doblada. |
| `mirar_atras` | `Idle_Loop` y giro propio | Mira por encima del hombro y vuelve a reposo. |

Los archivos están en `web/public/models/ciudad/codex/personajes/zambito/`. El GLB incorpora los cinco clips horneados a 24 fps, malla deformable y texturas. El archivo Blender se abre en reposo y deja todas las Actions editables.

El importador nativo de Godot crea `AnimationPlayer` y `GeneralSkeleton/Skeleton3D`. Los clips comunes forman bucles según `ficha.json` y los gestos regresan a `reposo`. La raíz queda en el suelo, con frente +Z y vertical +Y en GLB. La escena del Quitacapas debe mover la raíz para que el acompañante siga la ruta con 1,5 s de retraso y se detenga dos pasos detrás. La guía lo describe como acompañante sin ficha propia.

## Reproducir

Desde la raíz del repositorio, con la UAL instalada y el kit UAL de Antigravity.

```sh
revision_zambito=revisiones/codex/zambito
mkdir -p "$revision_zambito"
NODE_OPTIONS=--max-old-space-size=1200 web/node_modules/.bin/gltf-transform simplify \
  personas/zambito/zambito.glb "$revision_zambito/malla_reducida.glb" --ratio 0.006 --error 0.004
web/node_modules/.bin/gltf-transform resize \
  "$revision_zambito/malla_reducida.glb" "$revision_zambito/malla_1024.glb" --width 1024 --height 1024
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
  ~/apps/blender-5.2.3-linux-x64/blender -b --factory-startup -t 2 --python-exit-code 1 \
  -P blender/zonas/codex/personajes/zambito/construir.py
python3 blender/zonas/codex/personajes/zambito/preparar_visor.py
```
