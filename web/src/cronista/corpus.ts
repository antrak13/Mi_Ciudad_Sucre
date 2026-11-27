// Fuentes del cronista (solo en el servidor): las fichas verificadas del juego, los datos catalogados de los libros
// (contenido/catalogo/*.jsonl, con su página) y las notas de lugares (contenido/lugares/*.md). La búsqueda es BM25 sobre
// palabras sin tildes: no usa IA y es también la "alternativa sin IA" con la que se compara el cronista (criterio B).
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";

export type Fragmento = {
  id: string;
  tipo: "ficha" | "catalogo" | "lugar";
  titulo: string;
  texto: string;
  /** Cómo se cita: "Casa de la Libertad: Salón de la Independencia" o "Querejazu, pág. PDF 159". */
  fuente: string;
  url?: string;
};

/** cobertura: fracción de las palabras clave de la pregunta que aparecen en el fragmento (0–1). */
export type Resultado = Fragmento & { puntaje: number; cobertura: number };

const RAIZ = path.resolve(process.cwd(), "..");

const LIBROS: Record<string, string> = {
  querejazu: "Querejazu",
  revilla: "Revilla",
  cofre: "Cofre de encantos",
};

// Palabras vacías del castellano (y del inglés, para preguntas en inglés)
const VACIAS = new Set(
  ("a al algo ante antes como con contra cual cuando de del desde donde el ella ellas ellos en entre era eran es esa ese " +
    "eso esta este esto estos fue fueron ha han hasta hay la las le les lo los mas me mi muy nada ni no nos o otra otro " +
    "para pero por que quien se sea segun ser si sin sobre su sus tambien te tiene tu un una uno unos y ya yo " +
    "about after and are as at be by did does for from has have how in is it its of on or the this to was were what " +
    "when where which who why with " +
    "cuente cuentame dime explica explicame sabes podrias puedes hizo paso pasa quiero saber").split(" "),
);

export function palabras(texto: string): string[] {
  return texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .split(/[^a-z0-9ñ]+/)
    .filter((p) => p.length > 2 || /^\d+$/.test(p))
    .filter((p) => !VACIAS.has(p));
}

function leerFichas(): Fragmento[] {
  const fuentes = new Map<string, { titulo: string; institucion: string; url: string }>();
  const f = JSON.parse(readFileSync(path.join(RAIZ, "juego/data/fuentes.json"), "utf-8"));
  for (const x of f.fuentes ?? f) fuentes.set(x.id, x);
  const d = JSON.parse(readFileSync(path.join(RAIZ, "juego/data/fichas.json"), "utf-8"));
  return (d.fichas ?? d).map((ficha: { id: string; titulo: string; texto: string; fuentes: string[] }) => {
    const primera = fuentes.get(ficha.fuentes?.[0] ?? "");
    return {
      id: ficha.id,
      tipo: "ficha",
      titulo: ficha.titulo,
      texto: ficha.texto,
      fuente: primera ? `${primera.institucion}: ${primera.titulo}` : "Ficha del juego",
      url: primera?.url,
    } satisfies Fragmento;
  });
}

function leerCatalogo(): Fragmento[] {
  const carpeta = path.join(RAIZ, "contenido/catalogo");
  const salida: Fragmento[] = [];
  for (const archivo of readdirSync(carpeta).filter((a) => a.endsWith(".jsonl")).sort()) {
    for (const linea of readFileSync(path.join(carpeta, archivo), "utf-8").split("\n")) {
      if (!linea.trim()) continue;
      const x = JSON.parse(linea) as { id: string; libro: string; pag_pdf: number; resumen: string; cita?: string; lugares?: string[]; personajes?: string[] };
      const extra = [...(x.lugares ?? []), ...(x.personajes ?? [])].join(", ");
      salida.push({
        id: x.id,
        tipo: "catalogo",
        titulo: extra || (LIBROS[x.libro] ?? x.libro),
        texto: x.cita ? `${x.resumen} «${x.cita}»` : x.resumen,
        fuente: `${LIBROS[x.libro] ?? x.libro}, pág. PDF ${x.pag_pdf}`,
      });
    }
  }
  return salida;
}

function leerLugares(): Fragmento[] {
  const carpeta = path.join(RAIZ, "contenido/lugares");
  const salida: Fragmento[] = [];
  for (const archivo of readdirSync(carpeta).filter((a) => a.endsWith(".md")).sort()) {
    const md = readFileSync(path.join(carpeta, archivo), "utf-8");
    const lugar = (md.match(/^#\s+(.+)$/m)?.[1] ?? archivo.replace(/\.md$/, "")).trim();
    let n = 0;
    for (const linea of md.split("\n")) {
      // filas de la línea de tiempo: | año | hecho | fuente |
      const fila = linea.match(/^\|\s*([^|]+?)\s*\|\s*([^|]{20,}?)\s*\|\s*([^|]*?)\s*\|\s*$/);
      if (!fila || /^-+$/.test(fila[1]) || fila[1] === "Año") continue;
      salida.push({
        id: `${archivo.replace(/\.md$/, "")}#${++n}`,
        tipo: "lugar",
        titulo: `${lugar} (${fila[1]})`,
        texto: fila[2].replace(/\*\*/g, ""),
        fuente: `Notas de ${lugar}${fila[3] ? ` · ${fila[3]}` : ""}`,
      });
    }
  }
  return salida;
}

type Indice = { fragmentos: Fragmento[]; terminos: Map<string, number>[]; largos: number[]; df: Map<string, number>; medio: number };
let indice: Indice | null = null;

function construir(): Indice {
  const fragmentos = [...leerFichas(), ...leerCatalogo(), ...leerLugares()];
  const terminos = fragmentos.map((f) => {
    const m = new Map<string, number>();
    // el título pesa doble
    for (const p of [...palabras(f.titulo), ...palabras(f.titulo), ...palabras(f.texto)]) m.set(p, (m.get(p) ?? 0) + 1);
    return m;
  });
  const largos = terminos.map((m) => [...m.values()].reduce((a, b) => a + b, 0));
  const df = new Map<string, number>();
  for (const m of terminos) for (const p of m.keys()) df.set(p, (df.get(p) ?? 0) + 1);
  return { fragmentos, terminos, largos, df, medio: largos.reduce((a, b) => a + b, 0) / Math.max(1, largos.length) };
}

/** Los k fragmentos más pertinentes para la pregunta (BM25, k1 = 1,2, b = 0,75). Las fichas verificadas pesan un 30 % más. */
export function buscar(pregunta: string, k = 6): Resultado[] {
  indice ??= construir();
  const { fragmentos, terminos, largos, df, medio } = indice;
  const q = [...new Set(palabras(pregunta))];
  const N = fragmentos.length;
  const res: Resultado[] = [];
  for (let i = 0; i < N; i++) {
    let s = 0;
    let tocadas = 0;
    for (const p of q) {
      const tf = terminos[i].get(p);
      if (!tf) continue;
      tocadas++;
      const n = df.get(p) ?? 0;
      const idf = Math.log(1 + (N - n + 0.5) / (n + 0.5));
      s += idf * ((tf * 2.2) / (tf + 1.2 * (0.25 + (0.75 * largos[i]) / medio)));
    }
    if (s > 0) res.push({ ...fragmentos[i], puntaje: fragmentos[i].tipo === "ficha" ? s * 1.3 : s, cobertura: tocadas / q.length });
  }
  return res.sort((a, b) => b.puntaje - a.puntaje).slice(0, k);
}

export function totalFragmentos(): number {
  indice ??= construir();
  return indice.fragmentos.length;
}
