"use client";

// Lo primero que se ve: la ciudad girando lentamente detrás de un velo, con el nombre y la barra de carga (la carga
// ES la presentación). Cuando termina, dos puertas: verla desde el aire o caminarla.
import type { Modo } from "../tipos";

export default function PantallaInicio({ fraccion, detalle, lista, error, alEntrar }: {
  fraccion: number;
  detalle: string;
  lista: boolean;
  error?: string;
  alEntrar: (m: Modo | "tour") => void;
}) {
  return (
    <div className={`absolute inset-0 z-30 flex items-center justify-center p-6 transition-colors duration-700 ${lista ? "bg-sucre-cal/35" : "bg-sucre-cal"}`}>
      <div className="panel relative w-full max-w-lg overflow-hidden px-8 pb-8 pt-9 text-center">
        <AspaBorgona />
        <p className="relative text-xs font-semibold uppercase tracking-[0.25em] text-sucre-rojo">Bolivia · Centro histórico</p>
        <h1 className="relative mt-2 font-[family-name:var(--font-titulo)] text-6xl font-semibold leading-none text-sucre-tinta">Sucre</h1>
        <p className="relative mt-2 font-[family-name:var(--font-titulo)] text-xl italic text-sucre-tinta-suave">La Ciudad Blanca, en 3D</p>
        <div className="relative mx-auto mt-5 h-[3px] w-16 rounded bg-sucre-oro" />

        {error ? (
          <p className="relative mt-6 text-sm text-sucre-rojo-oscuro">No se pudo cargar la ciudad: {error}</p>
        ) : !lista ? (
          <div className="relative mt-7" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(fraccion * 100)}>
            <div className="h-1.5 overflow-hidden rounded-full bg-sucre-rojo-claro">
              <div className="h-full rounded-full bg-sucre-rojo transition-[width] duration-300" style={{ width: `${fraccion * 100}%` }} />
            </div>
            <p className="mt-2 text-xs text-sucre-tinta-suave">{detalle}</p>
          </div>
        ) : (
          <div className="relative mt-7 grid gap-2.5 whitespace-nowrap sm:grid-cols-2">
            <button autoFocus onClick={() => alEntrar("tour")} className="boton boton-rojo py-3">
              <IconoTourInicio /> Hacer el tour guiado
            </button>
            <button onClick={() => alEntrar("peaton")} className="boton boton-cal py-3">
              <IconoPie /> Caminar sus calles
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/** La cruz de Borgoña de la bandera, muy tenue, como fondo del panel. */
function AspaBorgona() {
  return (
    <svg viewBox="0 0 100 60" preserveAspectRatio="none" aria-hidden className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.07]">
      <path d="M0 0 L14 0 L100 52 L100 60 L86 60 L0 8 Z M100 0 L86 0 L0 52 L0 60 L14 60 L100 8 Z" fill="#d9171a" />
    </svg>
  );
}

export function IconoMapa() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" aria-hidden>
      <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z" /><path d="M9 4v14M15 6v14" />
    </svg>
  );
}

export function IconoTourInicio() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <polygon points="3 11 22 2 13 21 11 13 3 11" />
    </svg>
  );
}

export function IconoPie() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="13" cy="4" r="2" /><path d="m9 21 3-7 3 3v4M7 12l3-4h4l2 4 3 1M12 14l-1-6" />
    </svg>
  );
}
