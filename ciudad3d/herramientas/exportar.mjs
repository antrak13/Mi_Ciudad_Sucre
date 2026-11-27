#!/usr/bin/env node
// Arma la ciudad Godot de punta a punta: datos (empaquetar.py + vehiculos.mjs) y exportación.
//   node ciudad3d/herramientas/exportar.mjs web   → web/public/ciudad3d/ (sucre.wasm/.pck/.js + datos/ descargados a demanda)
//   node ciudad3d/herramientas/exportar.mjs apk   → movil/build/MiCiudad-Sucre.apk (datos dentro del paquete)
//   --sin-datos: solo exporta (si los datos ya están al día)
// Godot: variable GODOT, o ~/apps/godot/Godot_v4.7.2-stable_linux.x86_64. Desde web/: npm run ciudad | npm run ciudad:apk.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "../..");
const PROYECTO = join(RAIZ, "ciudad3d");
const GODOT = process.env.GODOT ?? join(homedir(), "apps/godot/Godot_v4.7.2-stable_linux.x86_64");
const destino = process.argv[2] ?? "web";
const conDatos = !process.argv.includes("--sin-datos");

const correr = (cmd, args, cwd = RAIZ) => {
  console.log("→", [cmd, ...args].join(" "));
  execFileSync(cmd, args, { cwd, stdio: "inherit" });
};

if (!existsSync(GODOT)) throw new Error(`No encuentro Godot en ${GODOT} (variable GODOT)`);
if (!existsSync(join(PROYECTO, "export_presets.cfg"))) {
  throw new Error("Falta ciudad3d/export_presets.cfg (no se versiona: lleva la clave del APK). Ver ciudad3d/LEEME.md");
}
if (conDatos) {
  correr("python3", ["ciudad3d/herramientas/empaquetar.py"]);
  correr("node", ["ciudad3d/herramientas/vehiculos.mjs"]);
}
// personajes y textos de sus encuentros (rápido: siempre, para que un cambio en guiones.md entre en cada exportación)
correr("python3", ["ciudad3d/herramientas/personajes.py"]);
// tour guiado (guion, voces cortadas, láminas y figurantes de la procesión; lo que no cambió sale de su caché)
correr("python3", ["ciudad3d/herramientas/tour.py"]);
// importar recursos nuevos (texturas, scripts) antes de exportar
correr(GODOT, ["--headless", "--path", PROYECTO, "--import"]);

if (destino === "web") {
  const salida = join(RAIZ, "web/public/ciudad3d");
  mkdirSync(salida, { recursive: true });
  correr(GODOT, ["--headless", "--path", PROYECTO, "--export-release", "Web", join(salida, "sucre.html")]);
  // los datos van aparte (no dentro del .pck): se descargan a demanda alrededor del caminante
  rmSync(join(salida, "datos"), { recursive: true, force: true });
  cpSync(join(PROYECTO, "datos"), join(salida, "datos"), { recursive: true });
  // el minimapa de la página (React) es el mismo del APK (npm run ciudad:minimapa lo regenera)
  cpSync(join(PROYECTO, "texturas/minimapa.webp"), join(salida, "datos/minimapa.webp"));
  // programas de shader para que la página los precompile (capturar_shaders.mjs): solo si cambió lo que los define
  // (shaders, scripts que arman materiales, ajustes del proyecto o Godot); tarda ~1 min
  const huella = createHash("sha1");
  for (const dir of ["shaders", "scripts"]) {
    for (const f of readdirSync(join(PROYECTO, dir), { recursive: true }).sort()) {
      const r = join(PROYECTO, dir, f);
      if (statSync(r).isFile()) huella.update(f).update(readFileSync(r));
    }
  }
  huella.update(readFileSync(join(PROYECTO, "project.godot"))).update(GODOT);
  const h = huella.digest("hex").slice(0, 12);
  const previa = existsSync(join(salida, "shaders.json")) ? JSON.parse(readFileSync(join(salida, "shaders.json"), "utf8")).huella : null;
  if (previa !== h && !process.argv.includes("--sin-shaders")) correr("node", ["ciudad3d/herramientas/capturar_shaders.mjs", "--huella", h]);
  const mb = (f) => (statSync(join(salida, f)).size / 1e6).toFixed(1);
  console.log(`listo: web/public/ciudad3d (wasm ${mb("sucre.wasm")} MB, pck ${mb("sucre.pck")} MB)`);
} else if (destino === "apk") {
  mkdirSync(join(RAIZ, "movil/build"), { recursive: true });
  correr(GODOT, ["--headless", "--path", PROYECTO, "--export-release", "Android", join(RAIZ, "movil/build/MiCiudad-Sucre.apk")]);
  const apk = join(RAIZ, "movil/build/MiCiudad-Sucre.apk");
  console.log(`listo: movil/build/MiCiudad-Sucre.apk (${(statSync(apk).size / 1e6).toFixed(1)} MB)`);
  if (existsSync(join(RAIZ, "web/public/descargas"))) {
    cpSync(apk, join(RAIZ, "web/public/descargas/MiCiudad-Sucre.apk"));
    console.log("copiado a web/public/descargas/ (descarga para testers)");
  }
} else {
  throw new Error(`destino desconocido: ${destino} (web | apk)`);
}
