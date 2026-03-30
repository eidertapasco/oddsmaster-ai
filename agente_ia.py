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
    
    en_vivo = analisis_elo.get("en_vivo", False)
    if en_vivo:
        pts_l   = analisis_elo.get("puntos_local", "-")
        pts_v   = analisis_elo.get("puntos_visitante", "-")
        periodo = analisis_elo.get("periodo", 0)
        try:
            diferencia = abs(int(pts_l) - int(pts_v))
            diff_texto = f"{diferencia} puntos de diferencia"
        except:
            diff_texto = "diferencia no disponible"

        contexto_vivo = (
            f"\nPARTIDO EN CURSO — MARCADOR ACTUAL:\n"
            f"- {local}: {pts_l} puntos\n"
            f"- {visitante}: {pts_v} puntos\n"
            f"- Período actual: {periodo}\n"
            f"- {diff_texto}\n\n"
            f"IMPORTANTE: El marcador actual es MÁS RELEVANTE que el modelo ELO.\n"
            f"Una ventaja de 15+ puntos en el 3er o 4to período es casi definitiva.\n"
            f"Las cuotas en vivo ya reflejan el marcador — tenlo en cuenta al evaluar el edge.\n"
        )
    else:
        contexto_vivo = "Partido aún no iniciado — análisis pre-partido.\n"

    return f"""
Eres un analista deportivo experto en NBA.

PARTIDO: {local} vs {visitante}
{contexto_vivo}
DATOS DEL MODELO PREDICTIVO:
- Probabilidad {local}: {prob_local}%
- Probabilidad {visitante}: {prob_vis}%
- Cuota de mercado {local}: {cuota_l} (mercado estima {round(100/cuota_l,1)}%)
- Cuota de mercado {visitante}: {cuota_v} (mercado estima {round(100/cuota_v,1)}%)
- {resumen_elo}

Genera un informe con este formato exacto:

CONTEXTO RECIENTE:
[2-3 hechos relevantes. Si el partido está en curso, comenta
el desarrollo actual y si el marcador tiene sentido.]

FACTORES CLAVE:
[El factor más importante. Si hay partido en vivo, el marcador
actual debe ser el factor principal de tu análisis.]

VEREDICTO DEL ANALISTA:
[FAVORABLE / DESFAVORABLE / PENDIENTE DE INFORMACIÓN]
[Una oración. Si el favorito por ELO va perdiendo por mucho,
di DESFAVORABLE aunque el edge sea alto.]

CONFIANZA: [ALTA / MEDIA / BAJA]

IMPORTANTE: Responde en máximo 200 palabras. Sin texto adicional fuera del formato.
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