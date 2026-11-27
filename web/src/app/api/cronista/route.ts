// POST /api/cronista {pregunta, idioma?: "es" | "en"} → {respuesta, fuentes, modo, modelo?, ms}
// La usan el juego de la Asamblea de 1825 (juego/, tecla C) y cualquier página que quiera preguntarle al cronista.
// La clave de Gemini vive solo aquí, en el servidor (GEMINI_API_KEY en web/.env.local).
import { NextResponse } from "next/server";
import { responder, type Idioma } from "@/cronista/responder";

export const runtime = "nodejs";

const CORS = { "access-control-allow-origin": "*", "access-control-allow-headers": "content-type" };

export function OPTIONS() {
  return new NextResponse(null, { headers: CORS });
}

export async function POST(req: Request) {
  let cuerpo: { pregunta?: unknown; idioma?: unknown };
  try {
    cuerpo = await req.json();
  } catch {
    return NextResponse.json({ error: "JSON inválido" }, { status: 400, headers: CORS });
  }
  const pregunta = typeof cuerpo.pregunta === "string" ? cuerpo.pregunta.trim().slice(0, 500) : "";
  if (!pregunta) return NextResponse.json({ error: "Falta la pregunta" }, { status: 400, headers: CORS });
  const idioma: Idioma = cuerpo.idioma === "en" ? "en" : "es";
  return NextResponse.json(await responder(pregunta, idioma), { headers: CORS });
}
