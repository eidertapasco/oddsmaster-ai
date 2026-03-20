# scanner.py — versión final con cuotas reales
import logging
from motor_estadistico import analizar_partido
from api_client import obtener_todos_los_partidos_hoy
from odds_client import obtener_cuotas_nba, buscar_cuotas_partido
from cache import obtener, guardar

logger = logging.getLogger(__name__)

CUOTA_NEUTRAL = 2.0
UMBRAL_ALERTA = 0.08


def escanear_value_bets() -> list[dict]:
    """
    Versión mejorada — usa cuotas reales cuando están disponibles,
    cuota neutral como fallback cuando no hay datos.
    """
    logger.info("Escaneando value bets...")

    todos   = obtener_todos_los_partidos_hoy()
    partidos = todos["basketball"] + todos["tenis"]

    if not partidos:
        logger.info("Scanner: no hay partidos en vivo")
        return []

    # Obtenemos cuotas reales una sola vez para todos los partidos
    # Así no hacemos múltiples llamadas a The Odds API
    cuotas_nba = obtener_cuotas_nba()
    logger.info(f"Cuotas disponibles: {len(cuotas_nba)} partidos NBA")

    alertas = []

    for partido in partidos:
        local     = partido["local"]
        visitante = partido["visitante"]
        deporte   = "basketball" if partido["deporte"] == "🏀" else "tenis"

        clave_partido = f"alerta_{local}_{visitante}".replace(" ", "_")
        if obtener(clave_partido) is not None:
            continue

        # Buscamos cuotas reales para este partido
        cuotas = buscar_cuotas_partido(local, visitante, cuotas_nba)

        if cuotas:
            cuota_l = cuotas["local"]
            cuota_v = cuotas["visitante"]
            fuente  = "real"
        else:
            # Fallback a cuota neutral
            cuota_l = CUOTA_NEUTRAL
            cuota_v = CUOTA_NEUTRAL
            fuente  = "neutral"

        logger.info(f"Analizando {local} vs {visitante} | cuotas {fuente}")

        try:
            analisis = analizar_partido(
                nombre_local=local,
                nombre_visitante=visitante,
                cuota_local=cuota_l,
                cuota_visitante=cuota_v,
                deporte=deporte
            )

            if analisis["hay_valor"]:
                for vb in analisis["value_bets"]:
                    if vb["valor"] >= UMBRAL_ALERTA:
                        alertas.append({
                            "partido":    f"{local} vs {visitante}",
                            "deporte":    partido["deporte"],
                            "equipo":     vb["equipo"],
                            "prob_real":  round(vb["prob_real"] * 100, 1),
                            "cuota":      vb["cuota"],
                            "edge":       round(vb["valor"] * 100, 1),
                            "kelly":      vb["kelly"],
                            "intensidad": vb["intensidad"],
                            "estado":     partido["estado"],
                            "fuente_odds": fuente
                        })
                        guardar(clave_partido, True, ttl_segundos=7200)
                        break

        except Exception as e:
            logger.error(f"Error analizando {local} vs {visitante}: {e}")
            continue

    logger.info(f"Scanner: {len(alertas)} alertas generadas")
    return alertas


def formatear_alerta(alerta: dict) -> str:
    fuente = "cuotas reales" if alerta["fuente_odds"] == "real" else "modelo ELO puro"
    return (
        f"🚨 VALUE BET DETECTADA\n"
        f"{'─' * 22}\n"
        f"{alerta['deporte']} {alerta['partido']}\n"
        f"Estado: {alerta['estado']}\n\n"
        f"{alerta['intensidad']}\n"
        f"Equipo: {alerta['equipo']}\n"
        f"Cuota: {alerta['cuota']}\n"
        f"Prob. real (ELO): {alerta['prob_real']}%\n"
        f"Edge: +{alerta['edge']}%\n"
        f"Kelly 25%: ${alerta['kelly']} de $100\n"
        f"Fuente: {fuente}\n\n"
        f"Usa /analizar para análisis completo con IA\n"
        f"⚠️ Solo análisis estadístico."
    )