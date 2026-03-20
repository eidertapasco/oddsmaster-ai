# motor_estadistico.py
import math
import json
import os
import logging
from datetime import datetime
from elo_data import ELO_INICIAL_NBA, ELO_INICIAL_TENIS, ELO_DEFAULT

logger = logging.getLogger(__name__)

# Archivo donde guardamos los ELOs actualizados
# Así el sistema "aprende" con cada partido
ELO_FILE = "elo_ratings.json"

# Factor K — qué tanto cambia el ELO por partido
# NBA: 20 es estándar (FiveThirtyEight usaba entre 20-30)
# Tenis: 32 es estándar (como en ajedrez FIDE)
K_NBA   = 20
K_TENIS = 32


# ============================================================
# GESTIÓN DE RATINGS ELO
# ============================================================

def cargar_ratings() -> dict:
    """
    Carga los ratings del archivo JSON.
    Si no existe, usa los valores iniciales.
    
    JSON en Python es trivial — json.load() convierte
    el archivo directamente en un diccionario.
    """
    if os.path.exists(ELO_FILE):
        with open(ELO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Primera vez: combinamos NBA y tenis en un solo dict
    ratings_iniciales = {}
    ratings_iniciales.update(ELO_INICIAL_NBA)
    ratings_iniciales.update(ELO_INICIAL_TENIS)
    return ratings_iniciales


def guardar_ratings(ratings: dict):
    """Persiste los ratings actualizados en disco"""
    with open(ELO_FILE, "w", encoding="utf-8") as f:
        json.dump(ratings, f, indent=2, ensure_ascii=False)


def obtener_elo(ratings: dict, nombre: str) -> float:
    """
    Busca el ELO de un equipo/jugador.
    Búsqueda flexible: prueba el nombre exacto primero,
    luego busca si el nombre está contenido en alguna clave.
    """
    # Búsqueda exacta
    if nombre in ratings:
        return ratings[nombre]
    
    # Búsqueda parcial — útil porque la API a veces
    # devuelve "LA Lakers" en vez de "Los Angeles Lakers"
    nombre_lower = nombre.lower()
    for clave in ratings:
        if nombre_lower in clave.lower() or clave.lower() in nombre_lower:
            return ratings[clave]
    
    logger.warning(f"ELO no encontrado para '{nombre}', usando default {ELO_DEFAULT}")
    return ELO_DEFAULT


# ============================================================
# CÁLCULO DE PROBABILIDADES
# ============================================================

def calcular_probabilidad_elo(elo_a: float, elo_b: float) -> tuple[float, float]:
    """
    Fórmula ELO estándar.
    Retorna (prob_A_gana, prob_B_gana).
    
    tuple[] es como retornar dos valores a la vez.
    En Java necesitarías una clase wrapper o un array.
    En Python simplemente: return valor1, valor2
    """
    # Esta es LA fórmula ELO — memorizala
    prob_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    prob_b = 1 - prob_a  # siempre suman 1.0
    return prob_a, prob_b


def ajuste_local_visitante(prob_local: float, deporte: str) -> tuple[float, float]:
    # Tenis: no hay ventaja de cancha — ambos son visitantes
    # Basketball: ventaja real y medible en NBA (~3.5%)
    if deporte == "tenis":
        return prob_local, 1 - prob_local  # sin ajuste
    
    ventaja = 0.035
    prob_local_ajustada     = min(prob_local + ventaja, 0.99)
    prob_visitante_ajustada = 1 - prob_local_ajustada
    return prob_local_ajustada, prob_visitante_ajustada


# ============================================================
# CÁLCULO DE VALUE BET
# ============================================================

def cuota_a_probabilidad(cuota: float) -> float:
    """
    Convierte cuota decimal en probabilidad implícita.
    Cuota 2.0 → 50%, Cuota 1.5 → 66.7%, Cuota 3.0 → 33.3%
    """
    if cuota <= 1.0:
        return 0.99  # cuota inválida
    return 1 / cuota


def calcular_valor(prob_real: float, cuota: float) -> float:
    """
    Fórmula central del proyecto.
    Valor > 0 = ventaja sobre la casa
    Valor > 0.05 = señal interesante (5% edge)
    Valor > 0.10 = señal fuerte (10% edge)
    """
    return (prob_real * cuota) - 1


def calcular_kelly(prob_real: float, cuota: float, bankroll: float = 100) -> float:
    """
    Criterio de Kelly — cuánto apostar exactamente.
    Kelly dice: apuesta el porcentaje de tu bankroll
    que maximiza el crecimiento a largo plazo.
    
    Fórmula: f = (p*(b+1) - 1) / b
    donde b = cuota - 1, p = probabilidad real
    
    Usamos Kelly fraccional (25%) para ser conservadores.
    """
    b = cuota - 1  # ganancia neta por unidad apostada
    f_kelly = (prob_real * (b + 1) - 1) / b
    
    # Kelly negativo = no apostar
    if f_kelly <= 0:
        return 0
    
    # Kelly fraccional al 25% — más seguro
    f_kelly_fraccional = f_kelly * 0.25
    
    return round(bankroll * f_kelly_fraccional, 2)


# ============================================================
# ANÁLISIS COMPLETO DE UN PARTIDO
# ============================================================

def analizar_partido(
    nombre_local: str,
    nombre_visitante: str,
    cuota_local: float,
    cuota_visitante: float,
    deporte: str = "basketball",
    bankroll: float = 100
) -> dict:
    """
    Función principal — recibe un partido con sus cuotas
    y devuelve el análisis completo.
    
    Retorna un diccionario con todo lo necesario
    para mostrar el resultado en Telegram.
    """
    ratings = cargar_ratings()
    
    # 1. Obtenemos los ELOs
    elo_local     = obtener_elo(ratings, nombre_local)
    elo_visitante = obtener_elo(ratings, nombre_visitante)
    
    # 2. Calculamos probabilidades base con ELO
    prob_local_base, prob_vis_base = calcular_probabilidad_elo(
        elo_local, elo_visitante
    )
    
    # 3. Ajustamos por ventaja local
    prob_local, prob_visitante = ajuste_local_visitante(
        prob_local_base, deporte
    )
    
    # 4. Calculamos el valor de cada apuesta
    valor_local     = calcular_valor(prob_local, cuota_local)
    valor_visitante = calcular_valor(prob_visitante, cuota_visitante)
    
    # 5. Calculamos Kelly para cada opción
    kelly_local     = calcular_kelly(prob_local, cuota_local, bankroll)
    kelly_visitante = calcular_kelly(prob_visitante, cuota_visitante, bankroll)
    
    # 6. Determinamos si hay value bet
    # Umbral mínimo de 3% de edge para considerar interesante
    UMBRAL_VALOR = 0.03
    
    value_bets = []
    if valor_local > UMBRAL_VALOR:
        value_bets.append({
            "equipo":       nombre_local,
            "rol":          "Local",
            "prob_real":    prob_local,
            "cuota":        cuota_local,
            "valor":        valor_local,
            "kelly":        kelly_local,
            "intensidad":   _clasificar_valor(valor_local)
        })
    if valor_visitante > UMBRAL_VALOR:
        value_bets.append({
            "equipo":       nombre_visitante,
            "rol":          "Visitante",
            "prob_real":    prob_visitante,
            "cuota":        cuota_visitante,
            "valor":        valor_visitante,
            "kelly":        kelly_visitante,
            "intensidad":   _clasificar_valor(valor_visitante)
        })
    
    return {
        "local":            nombre_local,
        "visitante":        nombre_visitante,
        "elo_local":        elo_local,
        "elo_visitante":    elo_visitante,
        "prob_local":       round(prob_local * 100, 1),
        "prob_visitante":   round(prob_visitante * 100, 1),
        "cuota_local":      cuota_local,
        "cuota_visitante":  cuota_visitante,
        "valor_local":      round(valor_local, 4),
        "valor_visitante":  round(valor_visitante, 4),
        "value_bets":       value_bets,
        "hay_valor":        len(value_bets) > 0,
        "deporte":          deporte,
        "timestamp":        datetime.now().strftime("%H:%M")
    }


def _clasificar_valor(valor: float) -> str:
    """
    Clasifica la intensidad del value bet.
    El guión bajo al inicio = función privada (como private en Java).
    """
    if valor >= 0.15:
        return "🔥 MUY FUERTE"
    elif valor >= 0.10:
        return "💚 FUERTE"
    elif valor >= 0.05:
        return "✅ MODERADO"
    else:
        return "⚠️ DÉBIL"


def actualizar_elo_post_partido(
    nombre_local: str,
    nombre_visitante: str,
    gano_local: bool,
    deporte: str = "basketball"
):
    """
    Actualiza los ELOs después de un partido terminado.
    El sistema aprende con cada resultado real.
    
    gano_local = True si ganó el equipo local
    """
    ratings = cargar_ratings()
    k = K_NBA if deporte == "basketball" else K_TENIS
    
    elo_l = obtener_elo(ratings, nombre_local)
    elo_v = obtener_elo(ratings, nombre_visitante)
    
    prob_l, _ = calcular_probabilidad_elo(elo_l, elo_v)
    
    # Resultado real: 1 si ganó local, 0 si ganó visitante
    resultado_l = 1 if gano_local else 0
    resultado_v = 1 - resultado_l
    
    # Fórmula de actualización ELO
    nuevo_elo_l = elo_l + k * (resultado_l - prob_l)
    nuevo_elo_v = elo_v + k * (resultado_v - (1 - prob_l))
    
    ratings[nombre_local]    = round(nuevo_elo_l, 1)
    ratings[nombre_visitante] = round(nuevo_elo_v, 1)
    
    guardar_ratings(ratings)
    logger.info(f"ELO actualizado: {nombre_local} {elo_l}→{nuevo_elo_l:.1f} | "
                f"{nombre_visitante} {elo_v}→{nuevo_elo_v:.1f}")