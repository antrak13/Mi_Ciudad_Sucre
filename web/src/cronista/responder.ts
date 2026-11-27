// El cronista responde con lo que encuentra en sus fuentes (corpus.ts).
// - Con GEMINI_API_KEY: Gemini redacta la respuesta SOLO a partir de los fragmentos, con citas [n], y dice que no sabe si
//   no están. GEMINI_MODELO fija el modelo; si no, se usa el Flash estable más nuevo que ofrezca la cuenta.
// - Sin clave (o si Gemini falla): respuesta extractiva con los dos fragmentos más pertinentes. Es la alternativa sin IA.
import { buscar, type Resultado } from "./corpus";

export type Idioma = "es" | "en";
export type Respuesta = {
  respuesta: string;
  fuentes: { n: number; titulo: string; fuente: string; url?: string }[];
  modo: "ia" | "sin_ia";
  modelo?: string;
  ms: number;
};

const API = "https://generativelanguage.googleapis.com/v1beta";
const PUNTAJE_MINIMO = 2.5;   // por debajo, no hay nada pertinente: "no lo sé"
const COBERTURA_MINIMA = 0.6; // el mejor fragmento debe tocar al menos el 60 % de las palabras clave

function pertinente(r: Resultado[]): boolean {
  return r.length > 0 && r[0].puntaje >= PUNTAJE_MINIMO && Math.max(...r.slice(0, 3).map((x) => x.cobertura)) >= COBERTURA_MINIMA;
}

const SIN_FUENTE: Record<Idioma, string> = {
  es: "No lo sé: no tengo una fuente que hable de eso. Pregúntame por la Asamblea de 1825, la Casa de la Libertad o los lugares de Charcas.",
  en: "I don't know: none of my sources covers that. Ask me about the 1825 Assembly, the Casa de la Libertad or the places of Charcas.",
};

function instrucciones(idioma: Idioma): string {
  const lengua = idioma === "en" ? "English" : "español";
  return [
    "Eres el Cronista de Chuquisaca, un narrador que acompaña a estudiantes por la historia de Sucre (Bolivia).",
    `Responde en ${lengua}, en 2 a 4 frases claras para un estudiante de colegio, tuteando.`,
    "Usa SOLO la información de los fragmentos numerados. Cita cada dato con su número entre corchetes, por ejemplo [2].",
    "Si los fragmentos no responden la pregunta, dilo con honestidad (\"no lo sé\" / \"I don't know\") y no inventes nada.",
    "Si las fuentes no coinciden entre sí, dilo. No opines sobre política actual.",
  ].join("\n");
}

let modeloElegido: string | null = null;

/** GEMINI_MODELO o, si no está, el Flash estable más nuevo que la cuenta pueda usar con generateContent. */
async function modelo(clave: string): Promise<string> {
  if (process.env.GEMINI_MODELO) return process.env.GEMINI_MODELO;
  if (modeloElegido) return modeloElegido;
  const r = await fetch(`${API}/models?pageSize=200`, { headers: { "x-goog-api-key": clave } });
  const d = (await r.json()) as { models?: { name: string; supportedGenerationMethods?: string[] }[] };
  const flash = (d.models ?? [])
    .filter((m) => m.supportedGenerationMethods?.includes("generateContent"))
    .map((m) => m.name.replace(/^models\//, ""))
    .filter((n) => /^gemini-\d+(\.\d+)?-flash$/.test(n))   // estables: sin -lite, -preview, -exp, -image, -tts
    .sort((a, b) => parseFloat(b.split("-")[1]) - parseFloat(a.split("-")[1]));
  if (!flash.length) throw new Error("La cuenta no ofrece ningún modelo gemini-*-flash con generateContent");
  modeloElegido = flash[0];
  return modeloElegido;
}

function listaFuentes(r: Resultado[]) {
  return r.map((x, i) => ({ n: i + 1, titulo: x.titulo, fuente: x.fuente, url: x.url }));
}

function sinIA(r: Resultado[], idioma: Idioma, t0: number): Respuesta {
  if (!pertinente(r)) return { respuesta: SIN_FUENTE[idioma], fuentes: [], modo: "sin_ia", ms: Date.now() - t0 };
  const dos = r.slice(0, 2);
  const cuerpo = dos.map((x, i) => `${x.texto.length > 320 ? x.texto.slice(0, 317) + "…" : x.texto} [${i + 1}]`).join(" ");
  const intro = idioma === "en" ? "This is what my sources say (in Spanish): " : "Esto dicen mis fuentes: ";
  return { respuesta: intro + cuerpo, fuentes: listaFuentes(dos), modo: "sin_ia", ms: Date.now() - t0 };
}

export async function responder(pregunta: string, idioma: Idioma = "es"): Promise<Respuesta> {
  const t0 = Date.now();
  const r = buscar(pregunta, 6);
  const clave = process.env.GEMINI_API_KEY;
  if (!clave || !pertinente(r)) return sinIA(r, idioma, t0);
  try {
    const nombre = await modelo(clave);
    const fragmentos = r.map((x, i) => `[${i + 1}] ${x.titulo} — ${x.texto} (Fuente: ${x.fuente})`).join("\n");
    const resp = await fetch(`${API}/models/${nombre}:generateContent`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": clave },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: instrucciones(idioma) }] },
        contents: [{ role: "user", parts: [{ text: `Fragmentos:\n${fragmentos}\n\nPregunta del estudiante: ${pregunta}` }] }],
        generationConfig: { temperature: 0.3, maxOutputTokens: 400 },
      }),
      signal: AbortSignal.timeout(20000),
    });
    if (!resp.ok) throw new Error(`Gemini respondió ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
    const d = (await resp.json()) as { candidates?: { content?: { parts?: { text?: string }[] } }[] };
    const texto = (d.candidates?.[0]?.content?.parts ?? []).map((p) => p.text ?? "").join("").trim();
    if (!texto) throw new Error("Gemini no devolvió texto");
    // solo las fuentes que la respuesta cita
    const citadas = new Set([...texto.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1])));
    const fuentes = listaFuentes(r).filter((f) => citadas.has(f.n));
    return { respuesta: texto, fuentes, modo: "ia", modelo: nombre, ms: Date.now() - t0 };
  } catch (e) {
    console.error("[cronista]", e);
    return sinIA(r, idioma, t0);
  }
}
