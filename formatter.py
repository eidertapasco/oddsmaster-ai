# formatter.py — archivo completo final
from datetime import date


def formatear_partido(partido: dict) -> str:
    deporte   = partido.get("deporte", "🏆")
    local     = partido["local"]
    visitante = partido["visitante"]
    estado    = partido["estado"]
    liga      = partido.get("liga", "")
    pts_l     = partido.get("puntos_local", "-")
    pts_v     = partido.get("puntos_visitante", "-")
    periodo   = partido.get("periodo", 0)

    en_vivo = any(palabra in estado.lower() for palabra in
                  ["progress", "live", "vivo", "1st", "2nd", "3rd", "4th", "set"])

    if en_vivo:
        info_periodo = f"P{periodo}" if deporte == "🏀" else "En curso"
        return (
            f"{deporte} *{local}* vs *{visitante}*\n"
            f"   🔴 EN VIVO — {info_periodo} | `{pts_l} - {pts_v}`\n"
            f"   🏆 {liga}\n"
        )
    elif any(p in estado.lower() for p in ["ended", "finished", "over", "final"]):
        return (
            f"{deporte} *{local}* vs *{visitante}*\n"
            f"   ✅ Finalizado | `{pts_l} - {pts_v}`\n"
            f"   🏆 {liga}\n"
        )
    else:
        return (
            f"{deporte} *{local}* vs *{visitante}*\n"
            f"   🕐 {estado}\n"
            f"   🏆 {liga}\n"
        )


def formatear_lista_partidos(todos: dict) -> str:
    hoy = date.today().strftime("%d/%m/%Y")
    mensaje = f"📅 *Partidos del {hoy}*\n\n"

    basketball = todos.get("basketball", [])
    if basketball:
        mensaje += "🏀 *NBA — EN VIVO*\n─────────────────\n"
        for p in basketball:
            mensaje += formatear_partido(p)
        mensaje += "\n"
    else:
        mensaje += "🏀 *NBA*\nNo hay partidos NBA en vivo ahora\n\n"

    tenis = todos.get("tenis", [])
    if tenis:
        mensaje += "🎾 *TENIS — EN VIVO*\n─────────────────\n"
        for p in tenis[:8]:
            mensaje += formatear_partido(p)
    else:
        mensaje += "🎾 *TENIS*\nNo hay partidos en vivo ahora\n"

    mensaje += "\n_Solo muestra partidos en vivo · OddsMaster AI_"
    return mensaje


def formatear_solo_basketball(partidos: list) -> str:
    if not partidos:
        return "🏀 *NBA*\nNo hay partidos en vivo ahora"
    mensaje = "🏀 *NBA — EN VIVO*\n─────────────────\n"
    for p in partidos:
        mensaje += formatear_partido(p)
    return mensaje


def formatear_solo_tenis(partidos: list) -> str:
    if not partidos:
        return "🎾 *TENIS*\nNo hay partidos en vivo ahora"
    mensaje = "🎾 *TENIS — EN VIVO*\n─────────────────\n"
    for p in partidos[:8]:
        mensaje += formatear_partido(p)
    return mensaje


def formatear_solo_elo(analisis: dict) -> str:
    """Mensaje 1 — solo estadísticas ELO, Markdown limpio"""
    local     = analisis["local"]
    visitante = analisis["visitante"]
    deporte   = "🏀" if analisis["deporte"] == "basketball" else "🎾"

    mensaje = (
        f"{deporte} Análisis: {local} vs {visitante}\n"
        f"{analisis['timestamp']}\n\n"
        f"📊 Probabilidades calculadas:\n"
        f"   {local}: {analisis['prob_local']}%\n"
        f"   {visitante}: {analisis['prob_visitante']}%\n\n"
        f"🎯 Cuotas ingresadas:\n"
        f"   {local}: {analisis['cuota_local']}  "
        f"→ implica {round(100/analisis['cuota_local'], 1)}%\n"
        f"   {visitante}: {analisis['cuota_visitante']}  "
        f"→ implica {round(100/analisis['cuota_visitante'], 1)}%\n\n"
    )

    if analisis["hay_valor"]:
        mensaje += "💰 VALUE BETS DETECTADAS:\n"
        mensaje += "─────────────────\n"
        for vb in analisis["value_bets"]:
            mensaje += (
                f"{vb['intensidad']}\n"
                f"   Equipo: {vb['equipo']} ({vb['rol']})\n"
                f"   Prob. real: {round(vb['prob_real']*100,1)}%"
                f" vs implícita: {round(100/vb['cuota'],1)}%\n"
                f"   Edge: +{round(vb['valor']*100,1)}%\n"
                f"   Kelly 25%: apostar ${vb['kelly']} de $100\n\n"
            )
    else:
        mensaje += "❌ Sin value bet\n"
        mensaje += "Las cuotas no ofrecen ventaja matemática.\n\n"

    mensaje += "⚠️ Solo análisis estadístico. Apuesta responsablemente."
    return mensaje


def formatear_solo_ia(texto_ia: str, exito: bool) -> str:
    """Mensaje 2 — solo respuesta del agente, texto plano"""
    if not exito:
        return f"🤖 Agente IA:\n{texto_ia}"
    return f"🤖 Análisis del Agente IA:\n\n{texto_ia}"


def formatear_analisis_completo(analisis: dict) -> str:
    """Mantenemos esta función por compatibilidad pero ya no la usamos"""
    return formatear_solo_elo(analisis)