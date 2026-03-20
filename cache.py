# cache.py
import time
import logging

logger = logging.getLogger(__name__)

# Diccionario en memoria — se borra al reiniciar el bot
# En el Bloque 7 lo persistiremos si hace falta
_cache = {}


def guardar(clave: str, datos, ttl_segundos: int = 300):
    """
    Guarda datos en caché con tiempo de expiración.
    ttl = Time To Live = cuántos segundos viven los datos
    
    En Java sería un Map<String, CacheEntry> con timestamp.
    En Python lo hacemos con un dict simple.
    """
    _cache[clave] = {
        "datos":   datos,
        "expira":  time.time() + ttl_segundos  # tiempo actual + TTL
    }
    logger.debug(f"Caché guardada: '{clave}' (TTL {ttl_segundos}s)")


def obtener(clave: str):
    """
    Obtiene datos del caché si no han expirado.
    Retorna None si no existe o expiró.
    """
    if clave not in _cache:
        return None

    entrada = _cache[clave]

    # time.time() devuelve segundos desde epoch (como System.currentTimeMillis()/1000)
    if time.time() > entrada["expira"]:
        del _cache[clave]  # limpiamos la entrada expirada
        logger.debug(f"Caché expirada: '{clave}'")
        return None

    logger.debug(f"Caché hit: '{clave}'")
    return entrada["datos"]


def invalidar(clave: str):
    """Fuerza la expiración de una clave — útil para testing"""
    if clave in _cache:
        del _cache[clave]


def estado() -> dict:
    """Retorna cuántas claves hay en caché — útil para /estado"""
    ahora = time.time()
    activas = {k: v for k, v in _cache.items() if ahora < v["expira"]}
    return {"claves_activas": len(activas), "claves": list(activas.keys())}