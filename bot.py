# Importamos las herramientas necesarias

import logging      # Para ver que hace el bot en consola
import os           # Para leer variables del sistema (mi token)
import asyncio
from dotenv import load_dotenv  # Para leer el archivo .env
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

# Importamos nuestros módulos nuevos
from api_client import (
    obtener_todos_los_partidos_hoy,
    obtener_partidos_basketball_hoy,
    obtener_partidos_tenis_hoy
)

from formatter import (
    formatear_lista_partidos,
    formatear_solo_basketball,
    formatear_solo_tenis,
    formatear_solo_elo,
    formatear_solo_ia
)

from motor_estadistico import analizar_partido
from agente_ia import consultar_agente
from scanner import escanear_value_bets, formatear_alerta  # 1. IMPORT al inicio de bot.py



# 2. VARIABLE GLOBAL — guardamos el chat_id del usuario
# En el Bloque 7 esto irá a una base de datos
CHAT_IDS_ACTIVOS = set()  # set = lista sin duplicados

# --- CONFIGURACIÓN ---
load_dotenv()   # Carga las variables del archivo .env
TOKEN = os.getenv("TELEGRAM_TOKEN")   # lee el token

# Logging: equivale a System.out.println() pero con niveles
# Nos muestra qué hace el bot en tiempo real
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# --- FUNCIONES DEL BOT ---
# En Python, async def = función asíncrona
# Es como un método en Java, pero puede "pausar" y esperar
# sin bloquear todo el programa (importante para bots)

# 3. ACTUALIZA la función start() para guardar el chat_id
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user.first_name
    chat_id = update.effective_chat.id

    # Guardamos el chat_id para las alertas automáticas
    CHAT_IDS_ACTIVOS.add(chat_id)
    logger.info(f"Chat ID registrado: {chat_id}")

    await update.message.reply_text(
        f"👋 ¡Hola, {user}!\n\n"
        f"🏀🎾 Bienvenido a OddsMaster AI\n\n"
        f"Comandos disponibles:\n"
        f"/start     — Este mensaje\n"
        f"/partidos  — Partidos en vivo\n"
        f"/nba       — Solo NBA\n"
        f"/tenis     — Solo tenis\n"
        f"/analizar  — Análisis ELO + IA\n"
        f"/contexto  — Info sobre equipos o jugadores\n"
        f"/alertas   — Activar/desactivar alertas\n"
        f"/estado    — Estado del sistema\n"
        f"/ayuda     — Ayuda"
    )

# 4. NUEVO COMANDO — activar/desactivar alertas manualmente
async def alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    CHAT_IDS_ACTIVOS.add(chat_id)
    await update.message.reply_text(
        "🔔 Alertas activadas\n\n"
        f"El scanner revisará partidos cada 15 minutos.\n"
        f"Te avisaré cuando encuentre una value bet con edge > 8%.\n\n"
        f"Chat ID registrado: {chat_id}"
    )
    
# 5. LA FUNCIÓN QUE EJECUTA EL JOB — esta la llama JobQueue automáticamente
async def job_scanner(context):
    """
    Esta función la ejecuta JobQueue cada X minutos.
    'context' aquí es diferente — es el contexto del Job, no del usuario.
    context.bot nos permite enviar mensajes proactivamente.
    """
    if not CHAT_IDS_ACTIVOS:
        logger.info("Scanner: no hay usuarios registrados")
        return

    logger.info("JobQueue: ejecutando scanner...")

    try:
        alertas_encontradas = escanear_value_bets()

        for alerta in alertas_encontradas:
            mensaje = formatear_alerta(alerta)
            # Enviamos a todos los usuarios registrados
            for chat_id in CHAT_IDS_ACTIVOS:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=mensaje
                )
                logger.info(f"Alerta enviada a {chat_id}: {alerta['partido']}")

    except Exception as e:
        logger.error(f"Error en job_scanner: {e}")
    
# Mostrar todos los partidos 
async def partidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Consultando partidos en tiempo real...")
    logger.info(f"/partidos solicitado por {update.effective_user.first_name}")
    todos = obtener_todos_los_partidos_hoy()
    mensaje = formatear_lista_partidos(todos)
    await update.message.reply_text(mensaje, parse_mode="Markdown")
    
# NBA
async def nba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Consultando NBA...")
    logger.info(f"/nba solicitado por {update.effective_user.first_name}")
    partidos_nba = obtener_partidos_basketball_hoy()
    mensaje = formatear_solo_basketball(partidos_nba)
    await update.message.reply_text(mensaje, parse_mode="Markdown")
    
# Tennis
async def tenis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Consultando tenis...")
    logger.info(f"/tenis solicitado por {update.effective_user.first_name}")
    partidos_tenis = obtener_partidos_tenis_hoy()
    mensaje = formatear_solo_tenis(partidos_tenis)
    await update.message.reply_text(mensaje, parse_mode="Markdown")
    
# Analizar partidos
async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 4:
        await update.message.reply_text(
            "⚠️ Uso correcto:\n"
            "/analizar [local] [visitante] [cuota_local] [cuota_visitante]\n\n"
            "Ejemplo:\n"
            "/analizar Lakers Nuggets 2.10 1.80"
        )
        return

    try:
        local     = args[0].replace("-", " ")
        visitante = args[1].replace("-", " ")
        cuota_l   = float(args[2])
        cuota_v   = float(args[3])

        if cuota_l < 1.01 or cuota_v < 1.01:
            await update.message.reply_text("❌ Las cuotas deben ser mayores a 1.01")
            return

        await update.message.reply_text("🔄 Calculando análisis ELO...")

        deportes_tenis = ["sinner", "alcaraz", "djokovic", "nadal",
                         "federer", "medvedev", "zverev", "swiatek"]
        deporte = "tenis" if any(
            t in local.lower() or t in visitante.lower()
            for t in deportes_tenis
        ) else "basketball"


        # Paso 1: ELO
        analisis_elo = analizar_partido(
            nombre_local=local,
            nombre_visitante=visitante,
            cuota_local=cuota_l,
            cuota_visitante=cuota_v,
            deporte=deporte
        )

        # Enviamos ELO inmediatamente — sin esperar a Gemini
        await update.message.reply_text(formatear_solo_elo(analisis_elo))

        # Paso 2: Gemini
        await update.message.reply_text("🤖 Consultando agente IA...")

        try:
            respuesta_ia = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, consultar_agente, analisis_elo
                ),
                timeout=20.0
            )
        except asyncio.TimeoutError:
            respuesta_ia = {
                "exito": False,
                "texto": "⚠️ Agente IA tardó demasiado."
            }

        # Enviamos IA en mensajes separados si es largo
        texto_ia = formatear_solo_ia(respuesta_ia["texto"], respuesta_ia["exito"])
        for i in range(0, len(texto_ia), 3800):
            await update.message.reply_text(texto_ia[i:i+3800])

    except ValueError:
        await update.message.reply_text(
            "❌ Las cuotas deben ser números decimales. Ejemplo: 2.10"
        )
    except Exception as e:
        logger.error(f"Error en /analizar: {e}")
        await update.message.reply_text(f"❌ Error inesperado: {type(e).__name__}")
        
# Resultado
async def resultado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Registra el resultado de un partido y actualiza los ELOs.
    Uso: /resultado Lakers Nuggets local
         /resultado Lakers Nuggets visitante
    """
    args = context.args
    if len(args) != 3:
        await update.message.reply_text(
            "⚠️ Uso: /resultado [local] [visitante] [ganador]\n"
            "Ganador: 'local' o 'visitante'\n\n"
            "Ejemplo:\n"
            "/resultado Lakers Nuggets local"
        )
        return

    local     = args[0].replace("-", " ")
    visitante = args[1].replace("-", " ")
    ganador   = args[2].lower()

    if ganador not in ["local", "visitante"]:
        await update.message.reply_text("❌ Ganador debe ser 'local' o 'visitante'")
        return

    from motor_estadistico import actualizar_elo_post_partido, cargar_ratings

    gano_local = ganador == "local"
    ratings_antes = cargar_ratings()
    elo_l_antes   = ratings_antes.get(local, 1500)
    elo_v_antes   = ratings_antes.get(visitante, 1500)

    actualizar_elo_post_partido(local, visitante, gano_local)

    ratings_despues = cargar_ratings()
    elo_l_despues   = ratings_despues.get(local, 1500)
    elo_v_despues   = ratings_despues.get(visitante, 1500)

    ganador_nombre = local if gano_local else visitante
    await update.message.reply_text(
        f"✅ Resultado registrado\n\n"
        f"Ganador: {ganador_nombre}\n\n"
        f"ELO actualizado:\n"
        f"  {local}: {elo_l_antes:.0f} → {elo_l_despues:.0f} "
        f"({'↑' if elo_l_despues > elo_l_antes else '↓'})\n"
        f"  {visitante}: {elo_v_antes:.0f} → {elo_v_despues:.0f} "
        f"({'↑' if elo_v_despues > elo_v_antes else '↓'})"
    )
        
# Contexto
async def contexto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Uso: `/contexto [equipo]`\nEjemplo: `/contexto Lakers`",
            parse_mode="Markdown"
        )
        return

    equipo = " ".join(args)  # une todos los args por si tiene espacios
    await update.message.reply_text(f"🔍 Consultando contexto de *{equipo}*...", parse_mode="Markdown")


    # Creamos un analisis_elo mínimo solo para reutilizar consultar_agente
    analisis_falso = {
        "local":           equipo,
        "visitante":       "Análisis individual",
        "prob_local":      50.0,
        "prob_visitante":  50.0,
        "cuota_local":     2.0,
        "cuota_visitante": 2.0,
        "valor_local":     0.0,
        "valor_visitante": 0.0,
        "hay_valor":       False,
        "value_bets":      [],
        "deporte":         "basketball"
    }

    try:
        respuesta_ia = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, consultar_agente, analisis_falso
            ),
            timeout=20.0
        )
        await update.message.reply_text(
            f"📋 *Contexto: {equipo}*\n\n{respuesta_ia['texto']}",
            parse_mode="Markdown"
        )
    except asyncio.TimeoutError:
        await update.message.reply_text("⚠️ Timeout consultando el agente.")
        


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from cache import estado as cache_estado
    info_cache = cache_estado()

    await update.message.reply_text(
        f"📊 Estado del sistema\n\n"
        f"✅ Bot: Activo\n"
        f"✅ APIs deportivas: Conectadas\n"
        f"✅ Motor ELO: Activo\n"
        f"✅ Agente IA (Gemini): Activo\n"
        f"✅ Scanner automático: cada 15 min\n"
        f"✅ Alertas: {len(CHAT_IDS_ACTIVOS)} usuario(s) registrado(s)\n\n"
        f"💾 Caché activa: {info_cache['claves_activas']} clave(s)\n"
        f"{'─' * 22}\n"
        f"Escribe /alertas para activar notificaciones"
    )
    
async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *OddsMaster AI — Comandos*\n\n"
        "/partidos — Todos los deportes en vivo\n"
        "/nba      — Solo baloncesto NBA\n"
        "/tenis    — Solo tenis\n"
        "/estado   — Estado del sistema\n"
        "/ayuda    — Esta ayuda",
        parse_mode="Markdown"
    )
    

async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "No entiendo ese mensaje. Usa /ayuda para ver qué sé hacer."
    )


# --- FUNCIÓN PRINCIPAL ---
def main():
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("partidos", partidos))
    app.add_handler(CommandHandler("nba",      nba))
    app.add_handler(CommandHandler("tenis",    tenis))
    app.add_handler(CommandHandler("analizar", analizar))
    app.add_handler(CommandHandler("resultado", resultado))
    app.add_handler(CommandHandler("contexto", contexto))
    app.add_handler(CommandHandler("alertas", alertas))
    app.add_handler(CommandHandler("estado",   estado))
    app.add_handler(CommandHandler("ayuda",    ayuda))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, mensaje_desconocido
    ))
    
    # JobQueue — scanner automático cada 15 minutos
    # first=30 → primera ejecución a los 30 segundos de iniciar
    app.job_queue.run_repeating(
        callback=job_scanner,
        interval=900,   # 900 segundos = 15 minutos
        first=30
    )
    
    print("🚀 OddsMaster AI v3 — Scanner automático activo")
    print(f"   Scanner: cada 15 minutos")
    print(f"   Umbral de alerta: edge > 8%")
    app.run_polling()
    
    
# Equivale al public static void main(String[] args) de Java
# Pero en Python es una convención, no una obligación del lenguaje
if __name__ == "__main__":
    main()