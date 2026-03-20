# odds_client.py
import requests
import logging
from config import ODDS_API_KEY, ODDS_API_URL
from cache import guardar, obtener

logger = logging.getLogger(__name__)

# Mercados que nos interesan — Moneyline = ganador del partido
# h2h = head to head = apuesta directa sin empate
MERCADO = "h2h"

# Deportes disponibles en The Odds API
DEPORTES = {
    "basketball": "basketball_nba",
    "tenis":      "tennis_atp_french_open"  # cambia según torneo activo
}


def obtener_cuotas_nba() -> dict:
    """
    Obtiene cuotas reales de casas de apuestas para partidos NBA.
    Retorna diccionario: {"Lakers vs Nuggets": {"local": 2.10, "visitante": 1.75}}
    """
    cached = obtener("odds_nba")
    if cached is not None:
        logger.info("Odds NBA: usando caché")
        return cached

    try:
        respuesta = requests.get(
            f"{ODDS_API_URL}/sports/basketball_nba/odds",
            params={
                "apiKey":  ODDS_API_KEY,
                "regions": "eu",        # Europa tiene mejores cuotas decimales
                "markets": MERCADO,
                "oddsFormat": "decimal"
            },
            timeout=10
        )

        # The Odds API devuelve el número de peticiones restantes en headers
        restantes = respuesta.headers.get("x-requests-remaining", "?")
        usadas    = respuesta.headers.get("x-requests-used", "?")
        logger.info(f"Odds API: {usadas} usadas, {restantes} restantes del mes")

        if not respuesta.ok:
            logger.error(f"Odds API error: {respuesta.status_code}")
            return {}

        datos = respuesta.json()
        cuotas_por_partido = {}

        for partido in datos:
            equipo_local    = partido.get("home_team", "")
            equipo_visitante = partido.get("away_team", "")

            if not equipo_local or not equipo_visitante:
                continue

            # Tomamos las cuotas del primer bookmaker disponible
            # En una versión avanzada promediarías todos los bookmakers
            bookmakers = partido.get("bookmakers", [])
            if not bookmakers:
                continue

            mercados = bookmakers[0].get("markets", [])
            if not mercados:
                continue

            outcomes = mercados[0].get("outcomes", [])
            cuota_local     = None
            cuota_visitante = None

            for outcome in outcomes:
                if outcome["name"] == equipo_local:
                    cuota_local = outcome["price"]
                elif outcome["name"] == equipo_visitante:
                    cuota_visitante = outcome["price"]

            if cuota_local and cuota_visitante:
                # Clave normalizada para buscar por nombre parcial
                clave = f"{equipo_local}|{equipo_visitante}"
                cuotas_por_partido[clave] = {
                    "local":      cuota_local,
                    "visitante":  cuota_visitante,
                    "local_name": equipo_local,
                    "vis_name":   equipo_visitante
                }

        # Caché de 10 minutos — las cuotas cambian pero no tan rápido
        guardar("odds_nba", cuotas_por_partido, ttl_segundos=600)
        logger.info(f"Odds NBA: {len(cuotas_por_partido)} partidos con cuotas")
        return cuotas_por_partido

    except Exception as e:
        logger.error(f"Error obteniendo odds: {e}")
        return {}


def buscar_cuotas_partido(
    nombre_local: str,
    nombre_visitante: str,
    cuotas_disponibles: dict
) -> dict | None:
    """
    Busca las cuotas de un partido específico.
    Usa búsqueda flexible porque los nombres no siempre coinciden exacto.
    Ej: API devuelve "LA Lakers", odds API devuelve "Los Angeles Lakers"
    """
    local_lower = nombre_local.lower()
    vis_lower   = nombre_visitante.lower()

    for clave, cuotas in cuotas_disponibles.items():
        local_od = cuotas["local_name"].lower()
        vis_od   = cuotas["vis_name"].lower()

        # Verificamos si hay coincidencia parcial en ambos equipos
        local_match = (local_lower in local_od or
                      local_od in local_lower or
                      _apellido(local_lower) in local_od)

        vis_match   = (vis_lower in vis_od or
                      vis_od in vis_lower or
                      _apellido(vis_lower) in vis_od)

        if local_match and vis_match:
            return cuotas

    return None


def _apellido(nombre: str) -> str:
    """
    Extrae la última palabra del nombre — útil para matching.
    "Los Angeles Lakers" → "lakers"
    "Denver Nuggets"     → "nuggets"
    """
    partes = nombre.strip().split()
    return partes[-1] if partes else nombre