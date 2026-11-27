import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // sin el indicador flotante de Next: las cuatro esquinas las usa la interfaz (los errores se siguen mostrando)
  devIndicators: false,
  // la portada (concepto B) es una página estática en /inicio; "Entrar a la ciudad" lleva a /ciudad
  async rewrites() {
    return { beforeFiles: [{ source: "/", destination: "/inicio/index.html" }], afterFiles: [], fallback: [] };
  },
  // el APK se descarga como instalador (no como documento): así Android lo abre con el instalador de paquetes y no con WPS o similares
  async headers() {
    return [
      // ciudad Godot (WebAssembly): el motor cambia solo al exportar → caché corta con revalidación; los datos llevan ?v=hash
      // (ciudad.json, sin hash, siempre se revalida)
      // (shaders.json: los programas que la página precompila mientras baja el motor, ver motor/precompilar.ts)
      { source: "/ciudad3d/shaders.json", headers: [{ key: "Cache-Control", value: "public, max-age=300, must-revalidate" }] },
      { source: "/ciudad3d/:archivo(sucre.wasm|sucre.pck|sucre.js|historica.pck)", headers: [{ key: "Cache-Control", value: "public, max-age=300, must-revalidate" }] },
      { source: "/ciudad3d/datos/:archivo*.bin", headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }] },
      { source: "/ciudad3d/datos/ciudad.json", headers: [{ key: "Cache-Control", value: "no-cache" }] },
      {
        source: "/descargas/:archivo*.apk",
        headers: [
          { key: "Content-Type", value: "application/vnd.android.package-archive" },
          { key: "Content-Disposition", value: 'attachment; filename="MiCiudad-Sucre.apk"' },
          { key: "X-Content-Type-Options", value: "nosniff" },
        ],
      },
    ];
  },
};

export default nextConfig;
