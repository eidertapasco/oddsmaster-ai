# 🏀🎾 OddsMaster AI

Sistema de análisis estadístico para apuestas deportivas de Baloncesto y Tenis. Combina un modelo ELO de probabilidades con un agente de IA (Gemini 2.5 Flash) para detectar **Value Bets** — oportunidades donde la probabilidad real supera la implícita en las cuotas.

> ⚠️ **Aviso:** Este proyecto es de uso educativo y analítico. No constituye asesoramiento financiero. Apuesta siempre de forma responsable.

---

## ✨ Características

- 🔴 **Partidos en tiempo real** — NBA y tenis vía APIs de REcodeX (RapidAPI)
- 📊 **Motor ELO** — Calcula probabilidades reales usando el sistema ELO estándar
- 🤖 **Agente IA** — Gemini 2.5 Flash analiza lesiones, forma reciente y contexto deportivo
- 💰 **Value Bet detector** — Compara probabilidad real vs implícita en las cuotas
- 📐 **Criterio de Kelly** — Calcula el tamaño óptimo de apuesta
- 🚨 **Alertas automáticas** — El bot escanea partidos cada 15 minutos y te notifica en Telegram
- 💻 **Dashboard web** — Interfaz visual con Streamlit para analizar partidos con un clic
- 📅 **Partidos programados** — No solo en vivo; también los que aún no empezaron

---

## 🏗️ Arquitectura

```
oddsmaster_ai/
├── bot.py                 # Bot de Telegram — interfaz principal
├── dashboard.py           # Dashboard web con Streamlit
├── api_client.py          # Conexión a APIs deportivas (REcodeX)
├── odds_client.py         # Conexión a The Odds API (cuotas reales)
├── motor_estadistico.py   # Modelo ELO + cálculo de Value Bets
├── agente_ia.py           # Agente Gemini 2.5 Flash
├── scanner.py             # Scanner automático de oportunidades
├── formatter.py           # Formateador de mensajes para Telegram
├── cache.py               # Sistema de caché en memoria (TTL)
├── elo_data.py            # Ratings ELO iniciales NBA + ATP
├── config.py              # Configuración centralizada
├── requirements.txt
├── runtime.txt
└── Procfile               # Para despliegue en Railway
```

---

## 🛠️ Stack tecnológico

| Capa | Tecnología | Costo |
|------|-----------|-------|
| Backend | Python 3.11 | Gratis |
| Interfaz principal | Telegram Bot API | Gratis |
| Interfaz web | Streamlit | Gratis |
| APIs deportivas | RapidAPI — REcodeX | Gratis (100 req/día) |
| Cuotas reales | The Odds API | Gratis (500 req/mes) |
| Agente IA | Google Gemini 2.5 Flash | Gratis |
| Despliegue | Railway | Gratis ($5 crédito/mes) |

---

## 🚀 Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/oddsmaster-ai.git
cd oddsmaster-ai
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
TELEGRAM_TOKEN=tu_telegram_bot_token
RAPIDAPI_KEY=tu_rapidapi_key
GEMINI_API_KEY=tu_gemini_api_key
ODDS_API_KEY=tu_odds_api_key
```

### 5. Correr la aplicación

Necesitas dos terminales:

```bash
# Terminal 1 — Bot de Telegram
python bot.py

# Terminal 2 — Dashboard web
streamlit run dashboard.py
```

El dashboard estará disponible en `http://localhost:8501`

---

## 🤖 Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/start` | Bienvenida y registro para alertas |
| `/partidos` | Todos los partidos en vivo |
| `/nba` | Solo partidos NBA en vivo |
| `/tenis` | Solo partidos de tenis en vivo |
| `/analizar [local] [visitante] [cuota_l] [cuota_v]` | Análisis completo ELO + IA |
| `/contexto [equipo]` | Contexto reciente de un equipo o jugador |
| `/resultado [local] [visitante] [local\|visitante]` | Registra resultado y actualiza ELOs |
| `/alertas` | Activa las alertas automáticas |
| `/estado` | Estado del sistema y caché |
| `/ayuda` | Lista de comandos |

### Ejemplo de uso

```
/partidos
→ Lakers vs Nuggets 🔴 EN VIVO P3 | 87 - 91

/analizar Los-Angeles-Lakers Denver-Nuggets 2.10 1.75
→ Probabilidades ELO + análisis Gemini + detección de value bet

/resultado Los-Angeles-Lakers Denver-Nuggets visitante
→ ELO actualizado: Lakers 1521→1511 ↓ | Nuggets 1648→1658 ↑
```

---

## 📐 Cómo funciona el modelo

### 1. Sistema ELO

Cada equipo/jugador tiene un rating numérico. La diferencia entre ratings predice probabilidades:

```
Prob_A = 1 / (1 + 10^((ELO_B - ELO_A) / 400))
```

Los ratings se actualizan automáticamente después de cada partido registrado con `/resultado`.

### 2. Detección de Value Bet

```
Valor = (Probabilidad_real × Cuota) - 1

Valor > 0    → ventaja matemática sobre la casa
Valor > 0.05 → señal interesante (5% de edge)
Valor > 0.10 → señal fuerte (10% de edge)
```

### 3. Criterio de Kelly fraccional

Determina el tamaño óptimo de apuesta:

```
Kelly = ((prob × (cuota - 1) - (1 - prob)) / (cuota - 1)) × 0.25
```

El factor 0.25 aplica Kelly fraccional al 25% para mayor seguridad.

### 4. Agente IA

Gemini 2.5 Flash recibe el análisis ELO y busca contexto real: lesiones, forma reciente, historial H2H. Su veredicto puede **confirmar o contradecir** el modelo estadístico.

---

## ☁️ Despliegue en Railway

### 1. Subir a GitHub

```bash
git add .
git commit -m "deploy inicial"
git push origin main
```

### 2. Configurar en Railway

1. Ve a [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Selecciona tu repositorio
3. En **Variables**, agrega las mismas claves del `.env`
4. Crea dos servicios del mismo repo:
   - **Bot:** Start command → `python bot.py`
   - **Dashboard:** Start command → `streamlit run dashboard.py --server.port=$PORT --server.address=0.0.0.0`

### 3. Actualizar el deploy

```bash
git add .
git commit -m "descripción del cambio"
git push
# Railway redespliega automáticamente en ~2 minutos
```

---

## 🔑 Obtener las API Keys

| Servicio | URL | Plan gratuito |
|----------|-----|---------------|
| Telegram Bot | [@BotFather](https://t.me/BotFather) en Telegram | Ilimitado |
| RapidAPI | [rapidapi.com](https://rapidapi.com) | 100 req/día |
| Google Gemini | [aistudio.google.com](https://aistudio.google.com) | 1500 req/día |
| The Odds API | [the-odds-api.com](https://the-odds-api.com) | 500 req/mes |
| Railway | [railway.app](https://railway.app) | $5 crédito/mes |

---

## 🗺️ Roadmap

- [ ] Base de datos PostgreSQL para persistir ELOs en Railway
- [ ] Histórico de resultados y backtest del modelo
- [ ] Más ligas de baloncesto (Euroliga, ACB)
- [ ] Más torneos de tenis (Grand Slams, Masters 1000)
- [ ] Modelo de superficie para tenis (arcilla, hierba, dura)
- [ ] Notificaciones push vía web
- [ ] Sistema de tracking de resultados de apuestas

---

## 👨‍💻 Sobre el proyecto

Construido como proyecto de aprendizaje siguiendo la filosofía **AI-Native Developer** — usando IA como herramienta de crecimiento exponencial para construir sistemas que piensan, no solo herramientas que ejecutan.

**Stack de aprendizaje:** Java (base) → Python → APIs → Modelos ELO → Agentes IA → Despliegue en nube

---

## 📄 Licencia

MIT License — libre para usar, modificar y distribuir con atribución.