# api_client.py — versión final con endpoints confirmados
import requests
import logging
from cache import guardar, obtener
from config import RAPIDAPI_KEY

logger = logging.getLogger(__name__)

BASKETBALL_HOST = "basketapi1.p.rapidapi.com"
TENNIS_HOST     = "tennisapi1.p.rapidapi.com"

# ✅ Endpoints confirmados funcionando
BASKETBALL_URL = f"https://{BASKETBALL_HOST}/api/basketball/matches/live"
TENNIS_URL     = f"https://{TENNIS_HOST}/api/tennis/events/live"


def hacer_peticion(url, host, params={}):
    headers = {
        "X-RapidAPI-Key":  RAPIDAPI_KEY,
        "X-RapidAPI-Host": host
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if not r.ok:
            logger.error(f"Error {r.status_code} en {url} — {r.text[:200]}")
            return None
        return r.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión: {e}")
        return None


def _parsear_eventos(datos: dict, deporte: str) -> list[dict]:
    """
    Función interna compartida — basketball y tenis tienen
    exactamente la misma estructura JSON (mismo proveedor REcodeX).
    En Java esto sería un método privado reutilizado por dos servicios.
    """
    if not datos or "events" not in datos:
        return []

    partidos = []
    for evento in datos["events"]:
        liga = evento.get("tournament", {}).get("name", "")

        # Filtramos por deporte para no mezclar ligas raras
        if deporte == "🏀" and ("NBA G League" in liga or "NBA" not in liga):
            continue

        local     = evento.get("homeTeam", {}).get("name", "Desconocido")
        visitante = evento.get("awayTeam", {}).get("name", "Desconocido")
        estado    = evento.get("status", {}).get("description", "En curso")
        periodo   = evento.get("status", {}).get("period", 0)

        pts_local     = evento.get("homeScore", {}).get("current", "-")
        pts_visitante = evento.get("awayScore", {}).get("current", "-")

        partidos.append({
            "id":               evento.get("id", ""),
            "local":            local,
            "visitante":        visitante,
            "puntos_local":     pts_local,
            "puntos_visitante": pts_visitante,
            "estado":           estado,
            "periodo":          periodo,
            "liga":             liga,
            "deporte":          deporte
        })

    return partidos


def obtener_partidos_basketball_hoy() -> list[dict]:
    
    # Primero revisamos caché
    cached = obtener("basketball_hoy")
    
    if cached is not None:
        logger.info("Basketball: usando caché")
        return cached
    
    # Si no hay caché, hacemos la petición real
    datos = hacer_peticion(BASKETBALL_URL, BASKETBALL_HOST)
    
    if not datos or "events" not in datos:
        logger.warning("Basketball: sin datos")
        return []
    
    partidos_formateados = []
    for evento in datos["events"]:
        liga = evento.get("tournament", {}).get("name", "")
        if "NBA G League" in liga or "NBA" not in liga:
            continue
        
        local     = evento.get("homeTeam", {}).get("name", "Desconocido")
        visitante = evento.get("awayTeam", {}).get("name", "Desconocido")
        estado    = evento.get("status", {}).get("description", "En curso")
        periodo   = evento.get("status", {}).get("period", 0)
        pts_l     = evento.get("homeScore", {}).get("current", "-")
        pts_v     = evento.get("awayScore", {}).get("current", "-")
        
        partidos_formateados.append({
            "id":               evento.get("id", ""),
            "local":            local,
            "visitante":        visitante,
            "puntos_local":     pts_l,
            "puntos_visitante": pts_v,
            "estado":           estado,
            "periodo":          periodo,
            "liga":             liga,
            "deporte":          "🏀"
        })
        
    # Guardamos en caché por 5 minutos
    guardar("basketball_hoy", partidos_formateados, ttl_segundos=1800)
    logger.info(f"Basketball: {len(partidos_formateados)} partidos (API real)")
    return partidos_formateados


def obtener_partidos_tenis_hoy() -> list[dict]:
    
    cached = obtener("tenis_hoy")
    if cached is not None:
        logger.info("Tenis: usando caché")
        return cached
    
    datos = hacer_peticion(TENNIS_URL, TENNIS_HOST)
    
    if not datos or "events" not in datos:
        logger.warning("Tenis: sin datos")
        return []
    
    
    partidos_formateados = []
    for evento in datos["events"][:10]:
        local     = evento.get("homeTeam", {}).get("name", "Desconocido")
        visitante = evento.get("awayTeam", {}).get("name", "Desconocido")
        torneo    = evento.get("tournament", {}).get("name", "Torneo")
        estado    = evento.get("status", {}).get("description", "En curso")
        pts_l     = evento.get("homeScore", {}).get("current", "-")
        pts_v     = evento.get("awayScore", {}).get("current", "-")
        
        partidos_formateados.append({
            "id":               evento.get("id", ""),
            "local":            local,
            "visitante":        visitante,
            "puntos_local":     pts_l,
            "puntos_visitante": pts_v,
            "estado":           estado,
            "liga":             torneo,
            "deporte":          "🎾"
        })
    
    guardar("tenis_hoy", partidos_formateados, ttl_segundos=1800)
    logger.info(f"Tenis: {len(partidos_formateados)} partidos (API real)")
    return partidos_formateados

# api_client.py — agrega estas dos funciones nuevas

def obtener_partidos_basketball_programados() -> list[dict]:
    """Usa nba_api oficial en vez de REcodeX que no tiene este endpoint"""
    
    from nba_schedule import obtener_partidos_nba_hoy
    todos = obtener_partidos_nba_hoy()
    
    return [p for p in todos if p.get("programado", False)]


def obtener_partidos_tenis_programados() -> list[dict]:
    """Partidos de tenis programados que aún no empezaron"""
    from datetime import date
    hoy = date.today().strftime("%Y-%m-%d")

    cached = obtener("tenis_programados")
    if cached is not None:
        return cached

    datos = hacer_peticion(
        url=f"https://{TENNIS_HOST}/api/tennis/matches/scheduled/{hoy}",
        host=TENNIS_HOST
    )

    if not datos or "events" not in datos:
        datos = hacer_peticion(
            url=f"https://{TENNIS_HOST}/api/tennis/events/scheduled/{hoy}",
            host=TENNIS_HOST
        )

    if not datos or "events" not in datos:
        logger.warning("Tenis programados: sin datos")
        return []

    partidos = []
    for evento in datos["events"][:15]:
        estado = evento.get("status", {}).get("description", "")
        if any(s in estado.lower() for s in ["progress", "ended", "finished"]):
            continue

        partidos.append({
            "id":        evento.get("id", ""),
            "local":     evento.get("homeTeam", {}).get("name", "Desconocido"),
            "visitante": evento.get("awayTeam", {}).get("name", "Desconocido"),
            "estado":    estado,
            "hora":      evento.get("startTimestamp", ""),
            "liga":      evento.get("tournament", {}).get("name", ""),
            "deporte":   "🎾",
            "en_vivo":   False
        })

    guardar("tenis_programados", partidos, ttl_segundos=1800)
    logger.info(f"Tenis programados: {len(partidos)} partidos")
    return partidos


def obtener_todos_los_partidos_completo() -> dict:
    from nba_schedule import obtener_nba_completo
    nba = obtener_nba_completo()
    return {
        "basketball_vivo":        nba["en_vivo"],
        "basketball_programados": nba["programados"],
        "basketball_finalizados": nba["finalizados"],
        "tenis_vivo":             obtener_partidos_tenis_hoy(),
        "tenis_programados":      []  # REcodeX no lo soporta
    }


def obtener_todos_los_partidos_hoy() -> dict:
    return {
        "basketball": obtener_partidos_basketball_hoy(),
        "tenis":      obtener_partidos_tenis_hoy()
    }