# Rendimiento de la entrada a la ciudad (web)

## Qué se descarga antes de ver la plaza

| Archivo | Antes | Ahora | Notas |
|---|---|---|---|
| `ciudad3d/sucre.wasm` | 39,5 MB (≈9 MB gzip) | igual | motor Godot; se comprime en tránsito |
| `ciudad3d/sucre.pck` | 21,5 MB | **9,0 MB** | ya viene comprimido (VRAM/WebP): gzip no lo reduce |
| `ciudad3d/historica.pck` | — (dentro de sucre.pck) | ≈12 MB, **después** | Casa de la Libertad: se baja en segundo plano con la plaza ya visible |

La portada empieza a descargar la ciudad (iframe `/ciudad?embebido`) apenas termina de dibujarse. Si el visitante entra
antes de que termine, la luz de la transición muestra el avance real de la descarga.

La escena histórica se monta con `ProjectSettings.load_resource_pack` (`ciudad3d/escenas_historicas/paquete_historico.gd`)
8 s después de arrancar. Si el visitante llega al portal del museo antes, la entrada espera y muestra el porcentaje.
En el APK y en escritorio los recursos siguen dentro del paquete principal. Para sumar otra escena pesada, agrega sus
recursos al `exclude_filter` del preset `Web` y a `export_files` del preset `WebHistorica`.

## Servidor (EC2, nginx delante de Next)

Hoy Next comprime `sucre.wasm` con gzip **en cada pedido** (CPU de la instancia) y el resto de los recursos pasan por
Node. Conviene que nginx sirva `/ciudad3d/` directo del disco, con compresión y caché:

```nginx
location /ciudad3d/ {
    alias /ruta/al/repo/web/public/ciudad3d/;
    gzip on;
    gzip_static on;               # usa sucre.wasm.gz si existe (gzip -9k sucre.wasm al desplegar)
    gzip_types application/wasm application/javascript application/json;
    types { application/wasm wasm; }
    add_header Cache-Control "public, max-age=300, must-revalidate";
}
location /ciudad3d/datos/ {
    alias /ruta/al/repo/web/public/ciudad3d/datos/;
    add_header Cache-Control "public, max-age=31536000, immutable";
}
```

Además: `shaders.json` daba 404 en producción, así que la precompilación de shaders (`motor/precompilar.ts`) no actuaba
y la primera visita sufría tirones de compilación. Hay que desplegarlo junto con `sucre.*`.
