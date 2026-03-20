# nba_schedule.py — versión corregida
import logging
from datetime import date
from cache import guardar, obtener

logger = logging.getLogger(__name__)

def obtener_partidos_nba_hoy() -> list[dict]:
    cached = obtener("nba_schedule_hoy")
    if cached is not None:
        logger.info("NBA schedule: usando caché")
        return cached

    try:
        from nba_api.stats.endpoints import scoreboardv2

        hoy   = date.today().strftime("%m/%d/%Y")
        board = scoreboardv2.ScoreboardV2(game_date=hoy, league_id="00")

        # Vemos todas las columnas disponibles para encontrar los nombres
        games_df    = board.game_header.get_data_frame()
        linescores  = board.line_score.get_data_frame()

        logger.info(f"Columnas game_header: {list(games_df.columns)}")
        logger.info(f"Columnas line_score: {list(linescores.columns)}")

        partidos = []
        for _, row in games_df.iterrows():
            game_id    = str(row.get("GAME_ID", ""))
            status_id  = int(row.get("GAME_STATUS_ID", 1))
            hora_texto = str(row.get("GAME_STATUS_TEXT", "")).strip()

            # Buscamos los equipos en line_score usando GAME_ID
            equipos = linescores[linescores["GAME_ID"] == game_id]

            if len(equipos) >= 2:
                equipo_1 = equipos.iloc[0]
                equipo_2 = equipos.iloc[1]

                # line_score tiene TEAM_CITY_NAME y TEAM_NICKNAME
                nombre_1 = (str(equipo_1.get("TEAM_CITY_NAME", "")) + " " +
                            str(equipo_1.get("TEAM_NICKNAME", ""))).strip()
                nombre_2 = (str(equipo_2.get("TEAM_CITY_NAME", "")) + " " +
                            str(equipo_2.get("TEAM_NICKNAME", ""))).strip()

                pts_1 = equipo_1.get("PTS", "-")
                pts_2 = equipo_2.get("PTS", "-")

                # Si PTS es NaN (partido no empezado) ponemos "-"
                import math
                if isinstance(pts_1, float) and math.isnan(pts_1):
                    pts_1 = "-"
                if isinstance(pts_2, float) and math.isnan(pts_2):
                    pts_2 = "-"
            else:
                # Fallback — intentamos con columnas de game_header
                nombre_1 = str(row.get("HOME_TEAM_NAME", "Equipo Local"))
                nombre_2 = str(row.get("VISITOR_TEAM_NAME", "Equipo Visitante"))
                pts_1    = "-"
                pts_2    = "-"

            estado_texto = {
                1: hora_texto,      # programado — mostramos la hora
                2: "En vivo",
                3: "Finalizado"
            }.get(status_id, hora_texto)

            partidos.append({
                "id":               game_id,
                "local":            nombre_1,
                "visitante":        nombre_2,
                "puntos_local":     pts_1,
                "puntos_visitante": pts_2,
                "estado":           estado_texto,
                "hora":             hora_texto,
                "liga":             "NBA",
                "deporte":          "basketball",
                "en_vivo":          status_id == 2,
                "programado":       status_id == 1,
                "finalizado":       status_id == 3,
                "status_id":        status_id,
                "periodo":          0
            })

        guardar("nba_schedule_hoy", partidos, ttl_segundos=1800)
        logger.info(f"NBA schedule: {len(partidos)} partidos hoy")
        return partidos

    except Exception as e:
        logger.error(f"Error obteniendo NBA schedule: {e}")
        import traceback
        traceback.print_exc()
        return []


def obtener_marcadores_nba_vivo() -> list[dict]:
    cached = obtener("nba_live_scores")
    if cached is not None:
        return cached

    try:
        from nba_api.live.nba.endpoints import scoreboard

        board    = scoreboard.ScoreBoard()
        games    = board.games.get_dict()
        partidos = []

        for game in games:
            home = game.get("homeTeam", {})
            away = game.get("awayTeam", {})

            nombre_local    = (home.get("teamCity", "") + " " +
                              home.get("teamName", "")).strip()
            nombre_visitante = (away.get("teamCity", "") + " " +
                               away.get("teamName", "")).strip()

            partidos.append({
                "id":               game.get("gameId", ""),
                "local":            nombre_local,
                "visitante":        nombre_visitante,
                "puntos_local":     home.get("score", "-"),
                "puntos_visitante": away.get("score", "-"),
                "estado":           game.get("gameStatusText", ""),
                "periodo":          game.get("period", 0),
                "liga":             "NBA",
                "deporte":          "🏀",
                "en_vivo":          game.get("gameStatus", 1) == 2,
                "status_id":        game.get("gameStatus", 1)
            })

        guardar("nba_live_scores", partidos, ttl_segundos=60)
        logger.info(f"NBA live: {len(partidos)} partidos")
        return partidos

    except Exception as e:
        logger.error(f"Error obteniendo NBA live: {e}")
        return []


def obtener_nba_completo() -> dict:
    todos   = obtener_partidos_nba_hoy()
    en_vivo = obtener_marcadores_nba_vivo()

    # Actualizamos marcadores de los partidos en vivo
    marcadores = {p["id"]: p for p in en_vivo}
    for partido in todos:
        if partido["id"] in marcadores:
            vivo = marcadores[partido["id"]]
            partido["puntos_local"]     = vivo["puntos_local"]
            partido["puntos_visitante"] = vivo["puntos_visitante"]
            partido["estado"]           = vivo["estado"]
            partido["periodo"]          = vivo.get("periodo", 0)
            partido["en_vivo"]          = vivo.get("status_id", 1) == 2
            partido["programado"]       = vivo.get("status_id", 1) == 1

    return {
        "programados": [p for p in todos if p.get("programado")],
        "en_vivo":     [p for p in todos if p.get("en_vivo")],
        "finalizados": [p for p in todos if p.get("finalizado")]
    }