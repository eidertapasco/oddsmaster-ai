# diagnostico.py v3
import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
KEY = os.getenv("RAPIDAPI_KEY")

TENNIS_HOST = "tennisapi1.p.rapidapi.com"

rutas_tenis = [
    "/api/tennis/matches/live",
    "/api/tennis/matches/scheduled",
    "/api/tennis/matches/scheduled/2026-03-14",
    "/api/tennis/events/live",
    "/api/tennis/events/scheduled",
    "/api/tennis/livescore",
    "/api/tennis/scores/live",
    "/api/tennis/tournament/live",
    "/api/tennis/match/live",
]

print("TENIS — segunda búsqueda")
for ruta in rutas_tenis:
    url = f"https://{TENNIS_HOST}{ruta}"
    r = requests.get(url, headers={"X-RapidAPI-Key": KEY, "X-RapidAPI-Host": TENNIS_HOST}, timeout=8)
    simbolo = "✅" if r.status_code == 200 else "❌"
    print(f"{simbolo} {r.status_code} — {ruta}")
    if r.status_code == 200:
        print(f"   Preview: {r.text[:300]}\n")