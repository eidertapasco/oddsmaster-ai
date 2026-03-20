# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RAPIDAPI_KEY   = os.getenv("RAPIDAPI_KEY")

# Hosts correctos para las APIs de REcodeX
BASKETBALL_HOST = "basketapi1.p.rapidapi.com"
BASKETBALL_URL  = f"https://{BASKETBALL_HOST}"

TENNIS_HOST     = "tennisapi1.p.rapidapi.com"
TENNIS_URL      = f"https://{TENNIS_HOST}"

TEMPORADA = "2024-2025"

# Conectamos la API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = "gemini-2.5-flash"

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_API_URL = "https://api.the-odds-api.com/v4"