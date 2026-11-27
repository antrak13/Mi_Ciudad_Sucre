# Alonso Ramírez de Vergara

Obispo de Charcas en la procesión de Guadalupe de 1602. La sección 7.4 de [la guía](../../../../../personas/guiaPersonajes.md) describe la procesión. [La ficha de diseño](../../../../../personas/procesion_guadalupe/LEEME.md) recoge las fuentes sobre el obispo y el gesto de incensar.

El rig parte de `personas/alonso_ramirez_de_vergara/alonso_ramirez_de_vergara.glb`. La copia para animación conserva la silueta, los UV y los tres mapas del modelo estático, con 34.038 triángulos y mapas de hasta 1024 px. Tiene 53 huesos UAL, tres falanges por dedo y un hueso adicional para el incensario, hijo de la mano derecha. La mano izquierda sigue la capa a la altura del pecho, donde las superficies están unidas en el original. El personaje mide 1,88 m con mitra por decisión de escala del recurso.

## Clips

| Clip | Base | Reproducción |
| --- | --- | --- |
| `reposo` | UAL `Idle_Loop` | Bucle. |
| `caminar` | UAL `Walk_Formal_Loop` | Bucle en sitio. El motor mueve la raíz a 0,56 m/s para acompañar el paso. |
| `hablar` | UAL `Idle_Talking_Loop` | Bucle de gesto y mirada. |
| `incensar` | `Idle_Loop` con trayectoria y oscilación propias | Dos impulsos y vuelta a reposo. |
| `asentir` | `Idle_Loop` con reverencia propia | Gesto único y vuelta a reposo. |

## Archivos

Los archivos públicos están en `web/public/models/ciudad/codex/personajes/alonso_ramirez_de_vergara/`. El GLB incorpora piel, texturas y los cinco clips horneados a 24 fps. El Blender editable se abre en `reposo`. Los clips y sus duraciones se detallan en `ficha.json` y se pueden inspeccionar en `index.html` servido por HTTP desde `web/public`.

En Godot, el importador nativo crea el `AnimationPlayer` y el esqueleto bajo `GeneralSkeleton/Skeleton3D`. Los clips horneados se reproducen por nombre. Configurar `Animation.LOOP_LINEAR` para las tres entradas marcadas como bucle en la ficha. El GLB usa +Z de frente, +Y hacia arriba y el origen en el suelo. La colocación y la ruta de la procesión corresponden a la escena de la ciudad.

## Reproducir

Desde la raíz del proyecto, con la UAL instalada en `ciudad3d/personajes/animaciones/quaternius/` y el kit UAL de Antigravity.

```sh
revision=revisiones/codex/alonso_ramirez_de_vergara
mkdir -p "$revision"
NODE_OPTIONS=--max-old-space-size=1200 web/node_modules/.bin/gltf-transform simplify \
  personas/alonso_ramirez_de_vergara/alonso_ramirez_de_vergara.glb \
  "$revision/malla_reducida.glb" --ratio 0.007 --error 0.004
web/node_modules/.bin/gltf-transform resize \
  "$revision/malla_reducida.glb" "$revision/malla_1024.glb" --width 1024 --height 1024
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
  ~/apps/blender-5.2.3-linux-x64/blender -b --factory-startup -t 2 --python-exit-code 1 \
  -P blender/zonas/codex/personajes/alonso_ramirez_de_vergara/construir.py
python3 blender/zonas/codex/personajes/alonso_ramirez_de_vergara/preparar_visor.py
```
