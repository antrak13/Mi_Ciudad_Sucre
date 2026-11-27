// La ciudad 3D es un proyecto Godot (ciudad3d/, exportado a WebAssembly en public/ciudad3d/). Esta clase la carga en un
// <canvas> y la conecta con la interfaz de la página:
//  - Godot → página: eventos 'sucre' en window ({tipo: "progreso" | "lista" | "posicion" | "captura" | "elegida"}),
//    que actualizan EstadoVista (posición, rumbo, rendimiento) sin pasar por React;
//  - página → Godot: window.sucreGodot.{entrar, ir, toma, capturar, marcas, origen, calidad, hora, pausar, tour}.
// Las órdenes de EstadoVista (ir, toma, norte) se traducen a esas llamadas; la captura de las revisiones también.
import type { DatosEscena } from "../revision/tipos";
import type { EstadoVista, ServicioCaptura } from "./EstadoVista";
import { precompilarShaders } from "./precompilar";

type FuncionesGodot = {
  entrar(): void;
  ir(x: number, z: number): void;
  toma(x: number, y: number, z: number, rumbo: number, inclinacion: number): void;
  capturar(x0: number, y0: number, x1: number, y1: number): void;
  marcas(json: string): void;
  origen(nombre: string, visible: boolean): void;
  calidad(nivel: string): void;
  hora(): void;
  pausar(si: boolean): void;
  tour(): void;
};

type MotorGodotJS = { startGame(o: { onProgress?: (a: number, t: number) => void }): Promise<void> };
type EngineCtor = new (config: Record<string, unknown>) => MotorGodotJS;

export type EventoGodot = { tipo: string; [k: string]: unknown };

const RAIZ = "/ciudad3d/";
const EJECUTABLE = "sucre";

// una sola descarga por script aunque la página monte el motor dos veces (React en desarrollo): la segunda espera a la primera
const scripts = new Map<string, Promise<void>>();
function cargarScript(src: string): Promise<void> {
  let p = scripts.get(src);
  if (!p) {
    p = new Promise<void>((ok, mal) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = () => ok();
      s.onerror = () => {
        scripts.delete(src);
        s.remove();
        mal(new Error("no se pudo cargar " + src));
      };
      document.head.appendChild(s);
    });
    scripts.set(src, p);
  }
  return p;
}

// Un solo motor por página: Godot web no admite dos instancias. React en desarrollo monta la página dos veces y la
// segunda arrancaba otro motor sobre el mismo lienzo ("Couldn't load project data… .pck missing?"): la ciudad quedaba
// dibujada pero congelada, sin teclado ni ratón. La segunda llamada espera al arranque de la primera.
let arranque: Promise<void> | null = null;
let avanceActual: (f: number) => void = () => undefined;

export class MotorGodot {
  private oyentes = new Set<(e: EventoGodot) => void>();
  private quitarOrdenes: (() => void) | null = null;
  private capturaPendiente: ((e: EventoGodot) => void) | null = null;

  constructor(private readonly vista: EstadoVista) {}

  private get godot(): FuncionesGodot | undefined {
    return (window as unknown as { sucreGodot?: FuncionesGodot }).sucreGodot;
  }

  /** Descarga el motor y arranca la ciudad en el lienzo. 'alAvanzar' recibe la fracción de la descarga del motor. */
  async iniciar(lienzo: HTMLCanvasElement, alAvanzar: (f: number) => void) {
    window.addEventListener("sucre", this.alEvento as EventListener);
    this.quitarOrdenes = this.vista.alOrdenar((o) => {
      const g = this.godot;
      if (!g) return;
      if (o.tipo === "ir") g.ir(o.x, o.z);
      else if (o.tipo === "toma") g.toma(o.x, o.y, o.z, o.rumbo, o.inclinacion);
      else if (o.tipo === "norte") g.toma(this.vista.x, this.vista.y, this.vista.z, 0, this.vista.inclinacion);
    });
    this.vista.captura = this.servicioCaptura;
    avanceActual = alAvanzar;
    arranque ??= (async () => {
      // los shaders se compilan en paralelo mientras baja el motor; se sueltan un rato después de "lista" (los de los
      // vehículos se piden recién al aparecer a pie)
      // (?sin_precompilar: para medir la diferencia)
      const pedir = new URLSearchParams(location.search).has("sin_precompilar") ? Promise.resolve(null) : precompilarShaders(`${RAIZ}shaders.json`);
      pedir.then((pre) => {
        if (!pre) return;
        const alLista = (ev: Event) => {
          if ((ev as CustomEvent<EventoGodot>).detail?.tipo !== "lista") return;
          window.removeEventListener("sucre", alLista);
          setTimeout(() => pre.soltar(), 30000);
        };
        window.addEventListener("sucre", alLista);
      }).catch(() => undefined);
      await cargarScript(`${RAIZ}${EJECUTABLE}.js`);
      const Engine = (window as unknown as { Engine: EngineCtor }).Engine;
      const motor = new Engine({
        executable: RAIZ + EJECUTABLE,
        mainPack: `${RAIZ}${EJECUTABLE}.pck`,
        canvas: lienzo,
        canvasResizePolicy: 2,          // ocupa toda la ventana (la página es de pantalla completa)
        focusCanvas: true,
        args: [],
        ensureCrossOriginIsolationHeaders: false,
        fileSizes: {},
      });
      await motor.startGame({ onProgress: (a, t) => t > 0 && avanceActual(a / t) });
    })().catch((e) => {
      arranque = null;
      throw e;
    });
    await arranque;
  }

  detener() {
    window.removeEventListener("sucre", this.alEvento as EventListener);
    this.quitarOrdenes?.();
    if (this.vista.captura === this.servicioCaptura) this.vista.captura = null;
  }

  escuchar(f: (e: EventoGodot) => void) {
    this.oyentes.add(f);
    return () => void this.oyentes.delete(f);
  }

  entrar() { this.godot?.entrar(); }
  pausar(si: boolean) { this.godot?.pausar(si); }
  cambiarHora() { this.godot?.hora(); }
  /** Empieza el tour guiado (o lo termina si está en curso): lo dirige Godot y avisa {tipo: "tour", activo}. */
  tour() { this.godot?.tour(); }
  calidad(nivel: string) { this.godot?.calidad(nivel); }
  mostrarOrigen(origen: string, visible: boolean) { this.godot?.origen(origen, visible); }
  marcas(lista: { id: string; x: number; y: number; z: number; estado: string; elegida: boolean }[]) {
    this.godot?.marcas(JSON.stringify(lista));
  }

  private alEvento = (ev: CustomEvent<EventoGodot>) => {
    const e = ev.detail;
    if (e.tipo === "posicion") {
      const v = this.vista;
      v.modo = "peaton";
      v.x = e.x as number;
      v.y = e.y as number;
      v.z = e.z as number;
      v.rumbo = e.rumbo as number;
      v.inclinacion = e.inclinacion as number;
      v.rendimiento = { fps: e.fps as number, llamadas: e.llamadas as number, triangulos: e.triangulos as number };
    } else if (e.tipo === "captura" && this.capturaPendiente) {
      this.capturaPendiente(e);
      this.capturaPendiente = null;
    }
    this.oyentes.forEach((f) => f(e));
  };

  /** Captura para las revisiones: Godot devuelve la pantalla (JPEG) y lo que sabe del encuadre. */
  private servicioCaptura: ServicioCaptura = {
    capturar: (marco) => new Promise((resolver, rechazar) => {
      const g = this.godot;
      if (!g) return rechazar(new Error("la ciudad no está lista"));
      this.capturaPendiente = async (e) => {
        const img = new Image();
        img.src = "data:image/jpeg;base64," + (e.captura as string);
        await img.decode();
        const lienzo = document.createElement("canvas");
        lienzo.width = img.naturalWidth;
        lienzo.height = img.naturalHeight;
        lienzo.getContext("2d")!.drawImage(img, 0, 0);
        resolver({ lienzo, datos: e.datos as DatosEscena });
      };
      g.capturar(marco.x0, marco.y0, marco.x1, marco.y1);
    }),
  };
}
