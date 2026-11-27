"use client";

// La Asamblea de 1825: el juego "Vive la Historia" (proyecto Godot juego/, Escena 1) exportado a web en
// public/asamblea/ (npm run asamblea). Se llega desde el museo de la ciudad: en el Salón de la Independencia de la Casa
// de la Libertad, la tecla H (ciudad3d/escenas_historicas/casa_libertad/portal_1825.gd). "Volver a la ciudad" regresa
// a /ciudad, que deja al caminante frente a la Casa de la Libertad (posición guardada en la sesión).
import { useEffect, useRef, useState } from "react";

export default function PaginaAsamblea() {
  const marco = useRef<HTMLIFrameElement>(null);
  const [estado, setEstado] = useState<"buscando" | "listo" | "falta">("buscando");

  useEffect(() => {
    fetch("/asamblea/index.html", { method: "HEAD", cache: "no-store" })
      .then((r) => setEstado(r.ok ? "listo" : "falta"))
      .catch(() => setEstado("falta"));
  }, []);

  return (
    <main className="relative h-dvh w-full overflow-hidden bg-black text-white">
      {estado === "listo" && (
        <iframe ref={marco} src="/asamblea/index.html" title="Casa de la Libertad · Asamblea de 1825"
          className="absolute inset-0 h-full w-full border-0" allow="autoplay; fullscreen"
          onLoad={() => marco.current?.contentWindow?.focus()} />
      )}
      {estado === "falta" && (
        <div className="absolute inset-0 flex items-center justify-center p-8 text-center">
          <div className="max-w-lg space-y-3">
            <p className="text-2xl font-semibold">La Asamblea de 1825 todavía no está exportada</p>
            <p className="opacity-80">Desde la carpeta <code>web/</code>, ejecuta <code>npm run asamblea</code> y recarga esta página.</p>
          </div>
        </div>
      )}
      <a href="/ciudad" className="absolute right-4 top-4 z-10 rounded-md bg-black/60 px-3 py-2 text-sm font-semibold backdrop-blur hover:bg-black/80">
        Volver a la ciudad →
      </a>
    </main>
  );
}
