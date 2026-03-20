# dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página — debe ser lo primero
st.set_page_config(
    page_title="OddsMaster AI",
    page_icon="🏀",
    layout="wide"  # usa todo el ancho de la pantalla
)

# Importamos nuestros módulos
from api_client import obtener_todos_los_partidos_completo
from motor_estadistico import analizar_partido
from agente_ia import consultar_agente
from odds_client import obtener_cuotas_nba, buscar_cuotas_partido


# ── HEADER ──────────────────────────────────────────────
st.title("🏀🎾 OddsMaster AI")
st.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")

# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")
    bankroll = st.number_input(
        "Bankroll ($)",
        min_value=10,
        max_value=10000,
        value=100,
        step=10,
        help="Tu capital total para calcular el Kelly"
    )
    umbral_edge = st.slider(
        "Edge mínimo para alerta (%)",
        min_value=1,
        max_value=30,
        value=8
    )
    usar_ia = st.toggle("Incluir análisis IA", value=True)
    st.divider()
    if st.button("🔄 Actualizar datos"):
        # Limpiamos la caché de Streamlit para forzar recarga
        st.cache_data.clear()
        st.rerun()


# ── CARGA DE DATOS CON CACHÉ ─────────────────────────────
# @st.cache_data(ttl=300) = Streamlit no vuelve a llamar
# esta función por 300 segundos — igual que nuestra caché manual
@st.cache_data(ttl=300)
def cargar_partidos():
    return obtener_todos_los_partidos_completo()


@st.cache_data(ttl=600)
def cargar_cuotas():
    return obtener_cuotas_nba()


datos    = cargar_partidos()
cuotas   = cargar_cuotas()

basketball_vivo        = datos["basketball_vivo"]
basketball_programados = datos["basketball_programados"]
tenis_vivo             = datos["tenis_vivo"]
tenis_programados      = datos["tenis_programados"]

todos_basketball = basketball_vivo + basketball_programados
todos_tenis      = tenis_vivo + tenis_programados


# ── MÉTRICAS PRINCIPALES ─────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("🏀 NBA en vivo",        len(basketball_vivo))
col2.metric("📅 NBA programados",    len(basketball_programados))
col3.metric("🎾 Tenis en vivo",      len(tenis_vivo))
col4.metric("📅 Tenis programados",  len(tenis_programados))

st.divider()


# ── TABS PRINCIPALES ─────────────────────────────────────
tab_basket, tab_tenis, tab_analizar = st.tabs([
    "🏀 Baloncesto",
    "🎾 Tenis",
    "🔍 Analizar partido"
])


# ── TAB BALONCESTO ───────────────────────────────────────
with tab_basket:
    if not todos_basketball:
        st.info("No hay partidos de baloncesto disponibles ahora")
    else:
        # Construimos tabla con pandas
        filas = []
        for p in todos_basketball:
            estado_icon = "🔴" if p.get("en_vivo", True) else "📅"

            # Buscamos cuotas reales
            c = buscar_cuotas_partido(p["local"], p["visitante"], cuotas)
            cuota_l = c["local"]     if c else "N/A"
            cuota_v = c["visitante"] if c else "N/A"

            filas.append({
                "Estado":     estado_icon,
                "Local":      p["local"],
                "Visitante":  p["visitante"],
                "Marcador":   f"{p.get('puntos_local','-')} - {p.get('puntos_visitante','-')}",
                "Cuota L":    cuota_l,
                "Cuota V":    cuota_v,
                "Liga":       p.get("liga", "NBA")
            })

        df = pd.DataFrame(filas)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Selector de partido para analizar
        st.subheader("Seleccionar partido para analizar")
        opciones = [f"{p['local']} vs {p['visitante']}" for p in todos_basketball]
        seleccion = st.selectbox("Partido", opciones, key="sel_basket")

        idx = opciones.index(seleccion)
        partido_sel = todos_basketball[idx]

        # Cuotas — reales si hay, manuales si no
        cuotas_reales = buscar_cuotas_partido(
            partido_sel["local"],
            partido_sel["visitante"],
            cuotas
        )

        col_a, col_b = st.columns(2)
        with col_a:
            cuota_local_input = st.number_input(
                f"Cuota {partido_sel['local']}",
                min_value=1.01,
                max_value=50.0,
                value=float(cuotas_reales["local"]) if cuotas_reales else 2.0,
                step=0.05,
                key="cuota_l_basket"
            )
        with col_b:
            cuota_vis_input = st.number_input(
                f"Cuota {partido_sel['visitante']}",
                min_value=1.01,
                max_value=50.0,
                value=float(cuotas_reales["visitante"]) if cuotas_reales else 2.0,
                step=0.05,
                key="cuota_v_basket"
            )

        if st.button("🔍 Analizar este partido", key="btn_basket"):
            with st.spinner("Calculando análisis ELO..."):
                analisis = analizar_partido(
                    nombre_local=partido_sel["local"],
                    nombre_visitante=partido_sel["visitante"],
                    cuota_local=cuota_local_input,
                    cuota_visitante=cuota_vis_input,
                    deporte="basketball",
                    bankroll=bankroll
                )

            # Mostramos resultados
            st.subheader("📊 Análisis ELO")
            c1, c2 = st.columns(2)
            c1.metric(
                partido_sel["local"],
                f"{analisis['prob_local']}%",
                f"cuota {analisis['cuota_local']}"
            )
            c2.metric(
                partido_sel["visitante"],
                f"{analisis['prob_visitante']}%",
                f"cuota {analisis['cuota_visitante']}"
            )

            if analisis["hay_valor"]:
                for vb in analisis["value_bets"]:
                    if vb["valor"] * 100 >= umbral_edge:
                        st.success(
                            f"💰 VALUE BET: **{vb['equipo']}** | "
                            f"Edge: **+{round(vb['valor']*100,1)}%** | "
                            f"Kelly: **${vb['kelly']}** de ${bankroll}"
                        )
                    else:
                        st.warning(
                            f"⚠️ Edge débil: {vb['equipo']} "
                            f"+{round(vb['valor']*100,1)}% (bajo umbral)"
                        )
            else:
                st.error("❌ Sin value bet en este partido")

            if usar_ia:
                with st.spinner("Consultando agente IA..."):
                    respuesta_ia = consultar_agente(analisis)
                st.subheader("🤖 Análisis del Agente IA")
                st.text(respuesta_ia["texto"])


# ── TAB TENIS ────────────────────────────────────────────
with tab_tenis:
    if not todos_tenis:
        st.info("No hay partidos de tenis disponibles ahora")
    else:
        filas_t = []
        for p in todos_tenis:
            estado_icon = "🔴" if p.get("en_vivo", True) else "📅"
            filas_t.append({
                "Estado":    estado_icon,
                "Jugador 1": p["local"],
                "Jugador 2": p["visitante"],
                "Torneo":    p.get("liga", ""),
                "Info":      f"{p.get('puntos_local','-')} - {p.get('puntos_visitante','-')}"
            })

        df_t = pd.DataFrame(filas_t)
        st.dataframe(df_t, use_container_width=True, hide_index=True)

        st.subheader("Seleccionar partido para analizar")
        opciones_t = [f"{p['local']} vs {p['visitante']}" for p in todos_tenis]
        seleccion_t = st.selectbox("Partido", opciones_t, key="sel_tenis")

        idx_t = opciones_t.index(seleccion_t)
        partido_t = todos_tenis[idx_t]

        col_c, col_d = st.columns(2)
        with col_c:
            cuota_j1 = st.number_input(
                f"Cuota {partido_t['local']}",
                min_value=1.01, max_value=50.0,
                value=2.0, step=0.05, key="cuota_j1"
            )
        with col_d:
            cuota_j2 = st.number_input(
                f"Cuota {partido_t['visitante']}",
                min_value=1.01, max_value=50.0,
                value=2.0, step=0.05, key="cuota_j2"
            )

        if st.button("🔍 Analizar este partido", key="btn_tenis"):
            with st.spinner("Calculando..."):
                analisis_t = analizar_partido(
                    nombre_local=partido_t["local"],
                    nombre_visitante=partido_t["visitante"],
                    cuota_local=cuota_j1,
                    cuota_visitante=cuota_j2,
                    deporte="tenis",
                    bankroll=bankroll
                )

            c1t, c2t = st.columns(2)
            c1t.metric(partido_t["local"],     f"{analisis_t['prob_local']}%")
            c2t.metric(partido_t["visitante"], f"{analisis_t['prob_visitante']}%")

            if analisis_t["hay_valor"]:
                for vb in analisis_t["value_bets"]:
                    st.success(
                        f"💰 VALUE BET: **{vb['equipo']}** | "
                        f"Edge: **+{round(vb['valor']*100,1)}%** | "
                        f"Kelly: **${vb['kelly']}** de ${bankroll}"
                    )
            else:
                st.error("❌ Sin value bet")

            if usar_ia:
                with st.spinner("Consultando agente IA..."):
                    respuesta_ia_t = consultar_agente(analisis_t)
                st.subheader("🤖 Análisis del Agente IA")
                st.text(respuesta_ia_t["texto"])


# ── TAB ANALIZAR MANUAL ──────────────────────────────────
with tab_analizar:
    st.subheader("Análisis manual de cualquier partido")
    st.caption("Útil para partidos que no aparecen en la lista o de otras ligas")

    col1m, col2m = st.columns(2)
    with col1m:
        equipo_l = st.text_input("Equipo/Jugador local", placeholder="Denver Nuggets")
        cuota_lm = st.number_input("Cuota local", min_value=1.01, value=2.0, step=0.05)
    with col2m:
        equipo_v = st.text_input("Equipo/Jugador visitante", placeholder="Lakers")
        cuota_vm = st.number_input("Cuota visitante", min_value=1.01, value=2.0, step=0.05)

    deporte_sel = st.radio("Deporte", ["basketball", "tenis"], horizontal=True)

    if st.button("🔍 Analizar", key="btn_manual", disabled=not equipo_l or not equipo_v):
        with st.spinner("Analizando..."):
            analisis_m = analizar_partido(
                nombre_local=equipo_l,
                nombre_visitante=equipo_v,
                cuota_local=cuota_lm,
                cuota_visitante=cuota_vm,
                deporte=deporte_sel,
                bankroll=bankroll
            )

        col1r, col2r = st.columns(2)
        col1r.metric(equipo_l, f"{analisis_m['prob_local']}%",  f"ELO {analisis_m['elo_local']:.0f}")
        col2r.metric(equipo_v, f"{analisis_m['prob_visitante']}%", f"ELO {analisis_m['elo_visitante']:.0f}")

        if analisis_m["hay_valor"]:
            for vb in analisis_m["value_bets"]:
                st.success(
                    f"💰 **{vb['equipo']}** | "
                    f"Edge: **+{round(vb['valor']*100,1)}%** | "
                    f"Kelly: **${vb['kelly']}** de ${bankroll}"
                )
        else:
            st.error("❌ Sin value bet con las cuotas ingresadas")

        if usar_ia:
            with st.spinner("Consultando agente IA..."):
                respuesta_m = consultar_agente(analisis_m)
            st.subheader("🤖 Agente IA")
            st.text(respuesta_m["texto"])