# Sirviente de los Lemoine · low poly v2

Reconstruido desde **`personas/sirviente_mudo/Simplified low-poly historical messenger (1).png`**: sombrero octogonal inclinado
hacia la nuca, cabeza angular con ojos planos, nariz de cuña y pelo en masas; chaqueta de hombros continuos y
**dos botones**, camisa cruda sin tapeta añadida, calzón largo con vueltas, pantorrillas cortas y zapatos bajos.
La cabeza, el pelo, el sombrero y el vestuario tienen geometría reconstruida para esta lámina.
El forro granate lleva puntadas claras y un bolsillo con un borde de papel asomando. Al mostrarlo se puede leer
la firma **Parra**; los renglones de la textura son trazos gráficos, no una transcripción histórica inventada.

## Archivos

| Archivo | Uso |
|---|---|
| `sirviente.glb` | Personaje con piel deformable, huesos, materiales, texturas y diez clips embebidos. |
| `sirviente.blend` | Maestro editable con diseño original y texturas empaquetados, estudio de iluminación y Actions/NLA. |
| `sirviente_color.png` | Atlas original de 1024 × 1024; filtro de vecino más cercano. |
| `carta_parra.png` | Papel original de 256 × 512 con firma legible al acercarse. |
| `sirviente.json` | Paleta, decisiones de diseño, velocidades, clips y puntos de integración. |
| `index.html` | Visor independiente con vistas, gestos, fotograma, esqueleto, malla y descargas. |
| `personaje_animado.mjs` | Adaptador Three.js para instancias, locomoción, gestos y fundidos. |
| `referencia.png` | Copia sin alterar de la lámina del usuario. |
| `vista_previa.png` | Render del modelo a tres cuartos. |
| `comparacion.png` | Nueva referencia y render real, con recorte y escala uniforme. |
| `entrega.json` | Métricas, comprobaciones y hashes de esta versión. |

Escala: metros. Altura aproximada con sombrero: **1,86 m**, una elección de diseño, no un dato biográfico.
Frente en GLB **+Z**, vertical **+Y**, origen en el suelo. En Blender frente −Y y vertical +Z.
Dos mallas skinned, dos materiales, dos texturas. La carta conserva su malla propia. La ropa forma parte de la
malla principal. 57 huesos con tres falanges por dedo; máximo cuatro influencias por vértice.

Las partes ocultas y la anatomía en movimiento se interpretan desde las dos vistas disponibles. La lámina no es
un escaneo ni un plano medido. La edad y el origen no se convierten en afirmaciones históricas.

## Abrir y animar en Blender

Abrir `sirviente.blend`; el objeto **Sirviente** contiene el armature. Al reproducir se ve el clip `reposo`.
Las otras nueve Actions se eligen en Action Editor. También están en pistas NLA individuales silenciadas;
activar solamente la pista que se desee previsualizar y quitar la Action activa para no sumarlas.
El rig exportado usa rotaciones horneadas: el motor no necesita resolver constraints ni complementos de Blender.

Jerarquía: `raiz → pelvis → columna → pecho → cuello → cabeza`; brazos desde las clavículas, piernas desde
la pelvis. `solapa_izq` depende de `pecho` y `carta` depende de `solapa_izq`. Ojos y mandíbula tienen huesos propios.
Las manos, incluidos pulgares, se pueden posar por falange. El hueso de mandíbula queda reservado para trabajo
facial posterior; la malla actual del rostro sigue la cabeza y no tiene animación de habla.

## Clips

| Nombre | Duración aproximada | Bucle | Velocidad de referencia |
|---|---:|---|---:|
| `reposo` | 3 s | Sí | 0 |
| `caminar` | 1 s | Sí | 1,20 m/s |
| `caminar_rapido` | 0,708 s | Sí | 1,80 m/s |
| `sigilo` | 1,583 s | Sí | 0,55 m/s |
| `asentir` | 2 s | No | — |
| `silencio` | 2,792 s | No | — |
| `senalar` | 2,792 s | No | — |
| `mirar_atras` | 2,583 s | No | — |
| `apartarse` | 2 s | No | — |
| `mostrar_forro` | 3,417 s | No | — |

Todos son **en sitio**, sin traslación de `raiz`. Locomoción con apoyo y elevación alternos de los pies,
balanceo de la mano libre y mano izquierda protegiendo la carta. Los gestos contienen entrada y salida a reposo.
La frecuencia de exportación es 24 fps; el motor interpola entre muestras.

## Integración Three.js

Usar la versión de Three del proyecto. Servir estos archivos por HTTP (por ejemplo, desde `web/public`);
el visor funciona también con `python3 -m http.server --directory web/public 3024`.

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { PersonajeAnimado } from './personaje_animado.mjs';

const base = '/models/ciudad/codex/personajes/sirviente/';
const [gltf, configuracion] = await Promise.all([
  new GLTFLoader().loadAsync(base + 'sirviente.glb'),
  fetch(base + 'sirviente.json').then(r => r.json()),
]);
const sirviente = new PersonajeAnimado(gltf, configuracion);
scene.add(sirviente.objeto);

// Por fotograma, después de resolver navegación y colisiones:
sirviente.caminar(velocidadRealEnMetrosPorSegundo, estaEnSigilo);
sirviente.actualizar(dtEnSegundos);

// La navegación mueve y orienta el Group completo, no un hueso individual.
sirviente.objeto.position.copy(posicionDelAgente);
sirviente.objeto.rotation.y = rumboEnRadianes;

// Un gesto termina y regresa a la locomoción previa:
sirviente.gesto('silencio');
```

`caminar` ajusta la frecuencia de pasos a la velocidad real; detener la navegación implica `caminar(0)`.
La clase clona el esqueleto con SkeletonUtils: dos instancias no comparten sus poses. No fusionar sus mallas
con edificios ni procesarlas como modelos urbanos estáticos. Conservar UV, textura con filtro cercano,
pesos y jerarquía. Los materiales y la geometría se comparten como recursos de solo lectura.

El contrato incluye una cápsula sugerida de radio 0,23 m y altura 1,70 m. La cápsula es un dato para el motor:
no se exporta como objeto visible. `apartarse` es una reacción corporal; el motor decide el paso lateral seguro.
La raíz del GLB debe seguir la posición del suelo. Las pendientes y escaleras necesitan ajuste de pies/IK en el motor.

### Forro, carta y misión

`mostrar_forro` abre el panel y eleva la carta para inspeccionarla. `Carta_Parra` puede seleccionarse por raycast.
Una interacción de juego puede reproducir el clip, marcar `forro_descosido` y abrir una ficha de lectura.
El estado de inventario, el minijuego de descoser, las rondas, detección de soldados y oidores, seguimiento,
diálogos de interfaz y la misión no forman parte del archivo de personaje.

La ruta narrativa suministrada es Lemoine → Cuéllar → Zudáñez → Lemoine. Sus coordenadas deben determinarse
en el mundo; aquí no se inventan emplazamientos ni se añade el personaje al tráfico o al visor de la ciudad.

## Reproducir la construcción

Desde la raíz del repositorio:

```sh
python3 blender/zonas/codex/personajes/sirviente/texturas.py
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
  ~/apps/blender-5.2.3-linux-x64/blender -b --factory-startup --threads 2 \
  -P blender/zonas/codex/personajes/sirviente/construir.py
node blender/zonas/codex/personajes/sirviente/preparar_visor.cjs
python3 blender/zonas/codex/personajes/sirviente/comparar_diseno.py
node blender/zonas/codex/personajes/sirviente/validar.cjs
```

`construir.py --sin-render` omite las vistas; `--vistas frente,rostro` permite elegirlas.
`validar.cjs` usa gltf-validator instalado en una carpeta temporal; `GLTF_VALIDATOR` permite indicar su ruta.
No se añaden dependencias a `web/package.json`. Los informes y las capturas quedan en
`revisiones/codex/sirviente_v2/`. La revisión del navegador usa Chrome/CDP en el puerto 9348 y HTTP en 3024.

Para revisar la forma antes de exportar: `texturas.py --salida revisiones/codex/sirviente_v2/activos` y ejecutar
`estudio.py` con Blender. Este paso genera cuerpo, rostro y espalda y no sustituye los activos públicos.

Las funciones reutilizables de malla, esqueleto y animación están en módulos separados; proporciones y
construcción de este personaje en `modelo.py`, datos de diseño en `diseno.json`. El atlas y el papel son
originales dibujados por código. Referencia del usuario preservada. Three.js conserva su licencia MIT adjunta.
