# agente_ia.py — versión con la librería nueva
import logging
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# Nueva forma de inicializar
cliente = genai.Client(api_key=GEMINI_API_KEY)


def _construir_prompt_basketball(analisis_elo: dict) -> str:
    local      = analisis_elo["local"]
    visitante  = analisis_elo["visitante"]
    prob_local = analisis_elo["prob_local"]
    prob_vis   = analisis_elo["prob_visitante"]
    cuota_l    = analisis_elo["cuota_local"]
    cuota_v    = analisis_elo["cuota_visitante"]
    valor_l    = round(analisis_elo["valor_local"] * 100, 1)
    valor_v    = round(analisis_elo["valor_visitante"] * 100, 1)
    hay_valor  = analisis_elo["hay_valor"]

    resumen_elo = (
        f"Edge {local}: {valor_l}% | Edge {visitante}: {valor_v}%"
        if hay_valor else "Sin edge estadístico detectado"
    )

    return f"""
Eres un analista experto en apuestas deportivas de valor (value betting) en NBA.
Tu análisis debe ser preciso, basado en hechos recientes y accionable.

PARTIDO A ANALIZAR:
- Local: {local}
- Visitante: {visitante}

ANÁLISIS ESTADÍSTICO (modelo ELO):
- Probabilidad {local}: {prob_local}%
- Probabilidad {visitante}: {prob_vis}%
- Cuota {local}: {cuota_l} (implica {round(100/cuota_l, 1)}%)
- Cuota {visitante}: {cuota_v} (implica {round(100/cuota_v, 1)}%)
- {resumen_elo}

TU TAREA — responde EXACTAMENTE en este formato:

CONTEXTO RECIENTE:
[2-3 hechos concretos sobre forma reciente, lesiones o noticias clave
de ambos equipos en los últimos 7 días.]

FACTORES CLAVE:
[El factor más importante que CONFIRMA o INVALIDA el edge estadístico.
Máximo 2 oraciones.]

VEREDICTO FINAL:
[APOSTAR / NO APOSTAR / ESPERAR]
[Una oración explicando el veredicto.]

CONFIANZA: [ALTA / MEDIA / BAJA]

IMPORTANTE: Responde en máximo 200 palabras total. Sin texto adicional fuera del formato.
"""


def _construir_prompt_tenis(analisis_elo: dict) -> str:
    local      = analisis_elo["local"]
    visitante  = analisis_elo["visitante"]
    prob_local = analisis_elo["prob_local"]
    prob_vis   = analisis_elo["prob_visitante"]
    cuota_l    = analisis_elo["cuota_local"]
    cuota_v    = analisis_elo["cuota_visitante"]
    valor_l    = round(analisis_elo["valor_local"] * 100, 1)
    valor_v    = round(analisis_elo["valor_visitante"] * 100, 1)

    return f"""
Eres un analista experto en apuestas de tenis profesional (ATP/WTA).

PARTIDO:
- Jugador 1: {local}
- Jugador 2: {visitante}

ANÁLISIS ESTADÍSTICO:
- Probabilidad {local}: {prob_local}%
- Probabilidad {visitante}: {prob_vis}%
- Cuota {local}: {cuota_l} (implica {round(100/cuota_l, 1)}%)
- Cuota {visitante}: {cuota_v} (implica {round(100/cuota_v, 1)}%)
- Edge {local}: {valor_l}% | Edge {visitante}: {valor_v}%

TU TAREA — responde EXACTAMENTE en este formato:

CONTEXTO RECIENTE:
[Forma reciente, lesiones, historial H2H y superficie. Máximo 3 hechos.]

FACTORES CLAVE:
[El factor decisivo para este partido. Máximo 2 oraciones.]

VEREDICTO FINAL:
[APOSTAR / NO APOSTAR / ESPERAR]
[Una oración con el razonamiento.]

CONFIANZA: [ALTA / MEDIA / BAJA]

IMPORTANTE: Responde en máximo 200 palabras total. Sin texto adicional fuera del formato.
"""


def consultar_agente(analisis_elo: dict) -> dict:
    deporte = analisis_elo.get("deporte", "basketball")
    prompt  = (_construir_prompt_basketball(analisis_elo)
               if deporte == "basketball"
               else _construir_prompt_tenis(analisis_elo))
    try:
        logger.info(f"Consultando Gemini: {analisis_elo['local']} vs {analisis_elo['visitante']}")

        respuesta = cliente.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=8192,  # reducido para respuesta más rápida
            )
        )

        # Verificamos que haya respuesta real
        if not respuesta or not respuesta.text:
            logger.error("Gemini devolvió respuesta vacía")
            return {"exito": False, "texto": "⚠️ Agente IA devolvió respuesta vacía"}

        texto = respuesta.text.strip()
        logger.info(f"Gemini respondió: {texto[:50]}...")
        return {"exito": True, "texto": texto}

    except Exception as e:
        logger.error(f"Error consultando Gemini: {type(e).__name__}: {e}")
        print(f"ERROR COMPLETO GEMINI: {type(e).__name__}: {e}")
        return {"exito": False, "texto": f"⚠️ Agente IA no disponible: {type(e).__name__}"}


def analisis_completo(
    nombre_local: str,
    nombre_visitante: str,
    cuota_local: float,
    cuota_visitante: float,
    deporte: str = "basketball",
    bankroll: float = 100
) -> dict:
    from motor_estadistico import analizar_partido

    analisis_elo = analizar_partido(
        nombre_local=nombre_local,
        nombre_visitante=nombre_visitante,
        cuota_local=cuota_local,
        cuota_visitante=cuota_visitante,
        deporte=deporte,
        bankroll=bankroll
    )

    respuesta_ia        = consultar_agente(analisis_elo)
    analisis_elo["ia_texto"] = respuesta_ia["texto"]
    analisis_elo["ia_exito"] = respuesta_ia["exito"]
    return analisis_elo