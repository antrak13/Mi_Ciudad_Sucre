"use client";

// La experiencia completa en la PC: la ciudad 3D (proyecto Godot, ciudad3d/, en un <canvas>) con la interfaz de la
// página encima: pantalla de carga, marca, nombre de la calle, minimapa, ayuda de teclas, Día/Noche, revisiones (V/B) y
// taller (T). La escena no vive en React: MotorGodot la conecta con EstadoVista (posición, rumbo, órdenes, capturas).
// En celular y tableta no se llega aquí (SoloEscritorio invita a instalar la app, que es el mismo proyecto Godot).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Buscador } from "@/mapa/busqueda";
import type { Calle } from "@/mapa/tipos";
import { CatalogoModelos } from "./datos/CatalogoModelos";
import { EstadoVista } from "./motor/EstadoVista";
import { MotorGodot } from "./motor/MotorGodot";
import { AyudaTeclas } from "./interfaz/Controles";
import Minimapa from "./interfaz/Minimapa";
import PanelTaller from "./interfaz/PanelTaller";
import PantallaInicio from "./interfaz/PantallaInicio";
import { useCalleActual } from "./interfaz/useCalleActual";
import BarraRevision from "./interfaz/revision/BarraRevision";
import Enmarcador from "./interfaz/revision/Enmarcador";
import FormularioRevision from "./interfaz/revision/FormularioRevision";
import PanelRevisiones from "./interfaz/revision/PanelRevisiones";
import { useRevision } from "./interfaz/revision/useRevision";
import { usePosicionGuardada } from "./interfaz/usePosicionGuardada";
import type { Modelo } from "./tipos";

/** Área que cubre la imagen del minimapa si su JSON no dice otra cosa (mundo: x este, z = −norte). */
const LIMITES_MINIMAPA = { x0: -650, z0: -460, x1: 250, z1: 760 };

export default function Experiencia() {
  const vista = useMemo(() => new EstadoVista(), []);
  const motor = useMemo(() => new MotorGodot(vista), [vista]);
  const lienzo = useRef<HTMLCanvasElement>(null);
  const [fraccion, setFraccion] = useState(0);
  const [detalle, setDetalle] = useState("Descargando el motor…");
  const [error, setError] = useState("");
  const [lista, setLista] = useState(false);
  const [entrado, setEntrado] = useState(false);
  // portada incrustada (/ciudad?embebido dentro de /inicio): carga a escondidas y espera la orden de entrar
  const [embebido, setEmbebido] = useState(false);
  const [noche, setNoche] = useState(false);
  const [taller, setTaller] = useState(false);
  const [visibles, setVisibles] = useState<Record<string, boolean>>({ claude: true, codex: true });
  const [volumenes, setVolumenes] = useState(true);
  const [nivel, setNivel] = useState<"alta" | "media" | "baja">("alta");
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [centros, setCentros] = useState<Map<string, { x: number; z: number }>>(new Map());
  const [buscador, setBuscador] = useState<Buscador | null>(null);
  const calle = useCalleActual(vista, buscador, 14);
  const rev = useRevision(vista);
  const { fase, enmarcar, alternar } = rev;

  // arranque del motor y eventos de la ciudad
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setEmbebido(q.has("embebido"));
    setTaller(q.has("taller"));
    setNoche((q.get("hora") ?? "") === "noche");
    // embebida en la portada: el avance se le pasa a la transición para que la luz no parezca detenida
    const avisar = (f: number) => {
      if (q.has("embebido")) window.parent.postMessage({ sucre: "avance", fraccion: f }, window.location.origin);
    };
    const quitar = motor.escuchar((e) => {
      if (e.tipo === "progreso") {
        setFraccion(0.5 + (e.fraccion as number) * 0.5);
        avisar(0.5 + (e.fraccion as number) * 0.5);
        setDetalle("Armando la ciudad…");
      } else if (e.tipo === "lista") {
        setLista(true);
        if (q.has("embebido")) window.parent.postMessage({ sucre: "lista" }, window.location.origin);
      } else if (e.tipo === "posicion") {
        setNivel(e.calidad as "alta" | "media" | "baja");
      } else if (e.tipo === "hora") {
        setNoche(e.hora === "noche");
      } else if (e.tipo === "elegida") {
        rev.elegir(e.id as string);
      } else if (e.tipo === "viajar" && e.destino === "asamblea_1825") {
        // [H] en el Salón de la Independencia del museo (portal_1825.gd): el juego de la Asamblea de 1825
        window.location.assign("/asamblea");
      }
    });
    motor.iniciar(lienzo.current!, (f) => { setFraccion(f * 0.5); avisar(f * 0.5); setDetalle("Descargando el motor…"); })
      .catch((e) => setError(String(e?.message ?? e)));
    return () => { quitar(); motor.detener(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [motor]);

  // datos de la interfaz: calles (nombre de la calle), imagen del minimapa, modelos de los agentes (taller). Se piden
  // cuando la ciudad ya está lista: antes competían con el motor y las teselas (el minimapa solo pesa 2,2 MB).
  useEffect(() => {
    if (!lista) return;
    fetch("/mapa/calles.json").then((r) => r.json()).then((c: Calle[]) => setBuscador(new Buscador(c, [])));
    new CatalogoModelos().cargar().then(setModelos).catch(() => undefined);
    fetch("/ciudad3d/datos/ciudad.json", { cache: "no-store" }).then((r) => r.json()).then((d) => {
      const m = new Map<string, { x: number; z: number }>();
      for (const [k, c] of Object.entries(d.modelos ?? {}) as [string, number[]][]) m.set(k, { x: c[0], z: c[2] });
      setCentros(m);
    }).catch(() => undefined);
    Promise.all([
      fetch("/ciudad3d/datos/minimapa.json").then((r) => (r.ok ? r.json() : null)).catch(() => null),
      new Promise<HTMLImageElement>((ok, mal) => { const i = new Image(); i.onload = () => ok(i); i.onerror = mal; i.src = "/ciudad3d/datos/minimapa.webp"; }),
    ]).then(([info, img]) => {
      const c = document.createElement("canvas");
      c.width = img.naturalWidth;
      c.height = img.naturalHeight;
      c.getContext("2d")!.drawImage(img, 0, 0);
      vista.ponerMapa({ lienzo: c, limites: info?.limites ?? LIMITES_MINIMAPA });
    }).catch(() => undefined);
  }, [vista, lista]);

  // al terminar de cargar se entra a pie (la portada ya es la presentación); incrustada, espera la orden
  useEffect(() => {
    if (lista && !embebido) setEntrado(true);
  }, [lista, embebido]);
  useEffect(() => {
    if (!embebido) return;
    const alMensaje = (e: MessageEvent) => {
      if (e.origin !== window.location.origin || e.data?.sucre !== "entrar") return;
      setEntrado(true);
      motor.entrar();
      lienzo.current?.focus();
    };
    window.addEventListener("message", alMensaje);
    return () => window.removeEventListener("message", alMensaje);
  }, [embebido, motor]);
  usePosicionGuardada(vista, lista && !embebido, entrado, () => setEntrado(true));

  // el teclado siempre va a la ciudad: al entrar (la pantalla de inicio se cierra sola y el foco caía en el <body>) y si
  // una tecla llega fuera del lienzo (foco perdido), se devuelve el foco y se le reenvía la tecla a Godot
  useEffect(() => {
    if (!entrado) return;
    const c = lienzo.current;
    c?.focus({ preventScroll: true });
    const reenviar = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (!c || t === c || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) || t.isContentEditable) return;
      c.focus({ preventScroll: true });
      c.dispatchEvent(new KeyboardEvent(e.type, e));
    };
    window.addEventListener("keydown", reenviar);
    window.addEventListener("keyup", reenviar);
    return () => { window.removeEventListener("keydown", reenviar); window.removeEventListener("keyup", reenviar); };
  }, [entrado]);

  // teclas globales: T abre el taller, V modo revisión, B enmarcar
  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      const escribiendo = ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) || t.isContentEditable;
      if (!entrado || escribiendo || fase.tipo !== "navegar" || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.code === "KeyT") setTaller((v) => !v);
      else if (e.code === "KeyV") alternar();
      else if (e.code === "KeyB") enmarcar();
    };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [entrado, fase, alternar, enmarcar]);

  // revisiones marcadas en la escena (en coordenadas del lienzo)
  useEffect(() => {
    if (!lista) return;
    // un alfiler DONDE ESTABA PARADO quien la hizo (la corrección dice "desde aquí debería verse así")
    motor.marcas(rev.activo ? rev.revisiones.filter((r) => r.estado === "pendiente" || r.estado === "en_curso" || r.id === rev.elegida)
      .map((r) => ({ id: r.id, x: r.escena.camara.lienzo.x, y: r.escena.camara.lienzo.y, z: r.escena.camara.lienzo.z - 0.25,
        estado: r.estado, elegida: r.id === rev.elegida })) : []);
  }, [motor, lista, rev.activo, rev.revisiones, rev.elegida]);

  // taller: agentes visibles y volúmenes del lienzo
  const cambiarVisibles = useCallback((v: Record<string, boolean>) => {
    setVisibles(v);
    for (const [a, ver] of Object.entries(v)) motor.mostrarOrigen(a, ver);
  }, [motor]);
  const cambiarVolumenes = useCallback((v: boolean) => {
    setVolumenes(v);
    motor.mostrarOrigen("lienzo_volumen", v);
  }, [motor]);

  const cambiarHora = useCallback(() => motor.cambiarHora(), [motor]);

  return (
    <main className="relative h-dvh w-full select-none overflow-hidden bg-[#cfe3ef] text-sucre-tinta">
      <canvas ref={lienzo} id="ciudad3d" tabIndex={0} className="absolute inset-0 block h-full w-full outline-none"
        onContextMenu={(e) => e.preventDefault()} />

      {!entrado && !embebido && (
        <PantallaInicio fraccion={fraccion} detalle={detalle} lista={lista} error={error || undefined} alEntrar={() => setEntrado(true)} />
      )}

      {entrado && (
        <div className="pointer-events-none absolute inset-0 z-10">
          <div className="absolute left-4 top-4 flex flex-col items-start gap-2">
            <Marca />
            {taller && (
              <PanelTaller vista={vista} modelos={modelos} centros={centros} visibles={visibles}
                setVisibles={cambiarVisibles} volumenes={volumenes} setVolumenes={cambiarVolumenes} nivel={nivel}
                alCerrar={() => setTaller(false)} />
            )}
          </div>

          {calle && (
            <div key={calle} className="absolute left-1/2 top-5 -translate-x-1/2 animate-[aparecer_400ms_ease-out]">
              <div className="panel border-t-[3px] border-t-sucre-rojo px-5 py-2 text-center">
                <p className="font-[family-name:var(--font-titulo)] text-xl font-semibold leading-tight">{calle}</p>
              </div>
            </div>
          )}

          <div className="absolute bottom-4 left-4">
            <Minimapa vista={vista} calle="" />
          </div>

          <div className="absolute bottom-4 left-1/2 hidden -translate-x-1/2 md:block">
            <AyudaTeclas modo="peaton" />
          </div>

          <div className="absolute right-4 top-4 flex flex-col items-end gap-2">
            <button onClick={cambiarHora} className="boton boton-cal pointer-events-auto shadow-[var(--shadow-panel)]"
              title={noche ? "Cambiar a día" : "Cambiar a noche"}>
              {noche ? <IconoSol /> : <IconoLuna />} {noche ? "Día" : "Noche"}
            </button>
            <BarraRevision activo={rev.activo} pendientes={rev.revisiones.filter((r) => r.estado === "pendiente").length}
              lista={rev.lista} alAlternar={rev.alternar} alEnmarcar={rev.enmarcar} alLista={() => rev.setLista(!rev.lista)} />
            {rev.activo && rev.lista && fase.tipo === "navegar" && (
              <PanelRevisiones revisiones={rev.revisiones} elegida={rev.elegida} alElegir={rev.elegir} alIr={rev.irA}
                alCerrar={() => rev.setLista(false)} />
            )}
            {fase.tipo === "formulario" && (
              <FormularioRevision encuadre={fase.encuadre} cliente={rev.cliente} alGuardar={rev.guardada} alCancelar={rev.cancelar} />
            )}
          </div>
          {rev.aviso && (
            <div className="panel absolute bottom-20 left-1/2 -translate-x-1/2 animate-[aparecer_300ms_ease-out] px-4 py-2 text-sm font-semibold">
              {rev.aviso}
            </div>
          )}
          {fase.tipo === "enmarcar" && <Enmarcador alMarcar={rev.marcar} alCancelar={rev.cancelar} />}
        </div>
      )}
    </main>
  );
}

function IconoLuna() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" aria-hidden>
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
    </svg>
  );
}

function IconoSol() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

/** Marca: la bandera de Sucre en miniatura y el nombre. */
function Marca() {
  return (
    <div className="panel pointer-events-auto flex items-center gap-2.5 py-1.5 pl-2 pr-3.5">
      <svg width="30" height="20" viewBox="0 0 30 20" aria-hidden className="rounded-[3px] ring-1 ring-sucre-tinta/15">
        <rect width="30" height="20" fill="#fff" />
        <path d="M1 0h3l25 17v3h-3L1 3zM29 0h-3L1 17v3h3L29 3z" fill="#d9171a" />
        <circle cx="15" cy="10" r="2.6" fill="#eac102" />
      </svg>
      <span className="font-[family-name:var(--font-titulo)] text-lg font-semibold leading-none">Sucre <span className="text-sucre-rojo">3D</span></span>
    </div>
  );
}
