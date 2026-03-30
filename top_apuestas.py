# top_apuestas.py
import logging
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL
from api_client import obtener_todos_los_partidos_completo
from cache import guardar, obtener

logger  = logging.getLogger(__name__)
cliente = genai.Client(api_key=GEMINI_API_KEY)


def generar_top_apuestas() -> str:
    cached = obtener("top_apuestas_hoy")
    if cached is not None:
        logger.info("Top apuestas: usando caché")
        return cached

    todos      = obtener_todos_los_partidos_completo()
    basketball = todos["basketball_programados"] + todos["basketball_vivo"]
    tenis      = todos["tenis_vivo"]

    if not basketball and not tenis:
        return "No hay partidos disponibles hoy para analizar."

    lista_partidos = ""
    for p in basketball[:8]:
        lista_partidos += f"🏀 {p['local']} vs {p['visitante']} — {p.get('hora', 'En vivo')}\n"
    for p in tenis[:5]:
        lista_partidos += f"🎾 {p['local']} vs {p['visitante']} — {p.get('liga', '')}\n"

    prompt = f"""
Eres un analista deportivo experto en apuestas de valor.

PARTIDOS DISPONIBLES HOY:
{lista_partidos}

Selecciona las 3 MEJORES oportunidades del día basándote en
forma reciente, lesiones, historial H2H y contexto del torneo.

Responde EXACTAMENTE en este formato:

TOP 3 APUESTAS DEL DÍA
═══════════════════════

1. [Equipo/Jugador a apostar]
   Partido: [Local vs Visitante]
   Deporte: [NBA/Tenis]
   Razonamiento: [2 oraciones máximo]
   Confianza: [ALTA/MEDIA/BAJA]

2. [Equipo/Jugador a apostar]
   Partido: [Local vs Visitante]
   Deporte: [NBA/Tenis]
   Razonamiento: [2 oraciones máximo]
   Confianza: [ALTA/MEDIA/BAJA]

3. [Equipo/Jugador a apostar]
   Partido: [Local vs Visitante]
   Deporte: [NBA/Tenis]
   Razonamiento: [2 oraciones máximo]
   Confianza: [ALTA/MEDIA/BAJA]

NOTA: [Una oración sobre el contexto general del día]

Máximo 300 palabras. Sin texto adicional fuera del formato.
"""

    try:
        respuesta = cliente.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=8192,
            )
        )
        texto = respuesta.text.strip()
        guardar("top_apuestas_hoy", texto, ttl_segundos=3600)
        logger.info("Top apuestas generadas correctamente")
        return texto

    except Exception as e:
        logger.error(f"Error generando top apuestas: {e}")
        return "No se pudieron generar las top apuestas en este momento."