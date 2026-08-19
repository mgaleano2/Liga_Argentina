import datetime as dt
import glob
import json
import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
try:
    from ScraperFC.sofascore import Sofascore
except ImportError:
    Sofascore = None
st.set_page_config(
    page_title="Dingnan United · Análisis (China League 1)",
    layout="wide",
    initial_sidebar_state="expanded",
)
DATA_DIR = "data"
LIGA_CSV = f"{DATA_DIR}/top_jugadores_liga.csv"
TEAM_DINGNAN = "Jiangxi Dingnan United"
YEAR = "2026"
POS_CORTO = {"G": "POR", "D": "DEF", "M": "MED", "F": "DEL"}
# ======================
# LIGA UNO (tablero existente)
# ======================
RENOMBRES = {
    "player": "Jugador", "team": "Equipo", "posicion": "Posición",
    "appearances": "Partidos", "minutesPlayed": "Minutos", "rating": "Rating",
    "goals": "Goles", "assists": "Asistencias", "goalsAssistsSum": "G+A",
    "penaltyGoals": "Goles penalti", "expectedGoals": "xG", "expectedAssists": "xA",
    "totalShots": "Tiros", "shotsOnTarget": "Tiros al arco", "shotsOffTarget": "Tiros fuera",
    "bigChancesCreated": "GC grandes", "keyPasses": "Pases clave",
    "totalPasses": "Pases", "accuratePassesPercentage": "% pases ok",
    "successfulDribbles": "Regates ok", "tackles": "Entradas",
    "interceptions": "Intercepciones", "ballRecovery": "Balones rec.",
    "clearances": "Despejes", "blockedShots": "Tiros bloqueados",
    "totalDuelsWon": "Duelos ganados", "duelLost": "Duelos perdidos",
    "wasFouled": "Faltas recibidas", "fouls": "Faltas",
    "yellowCards": "Amarillas", "redCards": "Rojas", "ownGoals": "Autogoles",
    "Edad": "Edad", "Altura": "Altura", "Pie": "Pie", "País": "País", "Valor": "Valor",
}
PER90 = ["goals", "assists", "goalsAssistsSum", "expectedGoals", "expectedAssists",
         "totalShots", "shotsOnTarget", "keyPasses", "successfulDribbles",
         "tackles", "interceptions", "ballRecovery", "totalDuelsWon",
         "wasFouled", "fouls", "yellowCards", "redCards"]
for c in PER90:
    RENOMBRES[f"{c}_per90"] = f"{RENOMBRES[c]} /90"
COLUMNAS_GRUPOS = {
    "Básicas": ["player", "team", "posicion", "Edad", "rating", "minutesPlayed", "appearances"],
    "Ataque": ["goals", "assists", "goalsAssistsSum", "expectedGoals", "expectedAssists", "penaltyGoals"],
    "Tiros": ["totalShots", "shotsOnTarget", "shotsOffTarget"],
    "Creación": ["bigChancesCreated", "keyPasses", "successfulDribbles"],
    "Pases": ["totalPasses", "accuratePassesPercentage"],
    "Defensa": ["tackles", "interceptions", "ballRecovery", "clearances", "blockedShots", "totalDuelsWon", "duelLost"],
    "Disciplina": ["yellowCards", "redCards", "fouls", "wasFouled", "ownGoals"],
    "Detalles": ["Altura", "Pie", "País", "Valor"],
    "Por 90": [f"{c}_per90" for c in PER90],
}
ORDENES = ["rating", "goals", "goals_per90", "expectedGoals", "expectedGoals_per90",
           "assists", "keyPasses", "minutesPlayed", "appearances", "totalShots",
           "successfulDribbles", "tackles", "ballRecovery", "Edad"]
# ======================
# PARTIDO (mapeos nuevos)
# ======================
MATCH_RENOMBRES = {
    "name": "Jugador", "position": "Pos", "shirtNumber": "Nº", "jerseyNumber": "Nº",
    "substitute": "Sup", "minutesPlayed": "Min", "rating": "Rating",
    "captain": "Cap", "teamName": "Equipo",
    # ataque
    "goals": "Goles", "goalAssist": "Asistencias",
    "expectedGoals": "xG", "expectedAssists": "xA",
    "totalShots": "Tiros", "onTargetScoringAttempt": "Tiros al arco",
    "shotOffTarget": "Tiros fuera", "blockedScoringAttempt": "Tiros bloqueados",
    "bigChanceCreated": "GC grandes", "bigChanceMissed": "GC falladas",
    "penaltyWon": "Penalti ganado", "totalOffside": "Fuera de juego",
    # pases
    "totalPass": "Pases", "accuratePass": "Pases ok",
    "totalLongBalls": "Balones largos", "accurateLongBalls": "Balones largos ok",
    "keyPass": "Pases clave", "totalCross": "Centros", "accurateCross": "Centros ok",
    "totalOwnHalfPasses": "Pases (propia mitad)", "accurateOwnHalfPasses": "Pases ok (propia mitad)",
    # defensa / duelos
    "wonTackle": "Entradas ganadas", "totalTackle": "Entradas",
    "interceptionWon": "Intercepciones", "totalClearance": "Despejes",
    "ballRecovery": "Balones rec.", "aerialWon": "Duelos aéreos g.",
    "aerialLost": "Duelos aéreos p.", "duelWon": "Duelos ganados",
    "duelLost": "Duelos perdidos", "wonContest": "Enfrentamientos g.",
    "challengeLost": "Desafíos perd.", "outfielderBlock": "Bloqueos",
    # posesión
    "touches": "Toques", "possessionLostCtrl": "Pérdidas",
    "dispossessed": "Desposesiones", "unsuccessfulTouch": "Malos controles",
    # disciplina
    "fouls": "Faltas", "wasFouled": "Faltas recibidas",
    # portero
    "saves": "Atajadas", "punches": "Puñetazos",
    "goalsPrevented": "Goles evitados", "goodHighClaim": "Balones aéreos",
    "savedShotsFromInsideTheBox": "Atajadas en el área", "penaltyFaced": "Penaltis afrontados",
    "penaltyConceded": "Penalti concedido", "errorLeadToAGoal": "Error → gol",
    # pases en campo rival
    "accurateOppositionHalfPasses": "Pases ok (campo rival)",
    "totalOppositionHalfPasses": "Pases (campo rival)",
    # progresión / conducción
    "totalBallCarriesDistance": "Dist. conducción", "ballCarriesCount": "Conducciones",
    "totalProgression": "Progresión total", "progressiveBallCarriesCount": "Conducciones progresivas",
    "bestBallCarryProgression": "Mejor progresión",
    "totalProgressiveBallCarriesDistance": "Dist. conducción progresiva",
    # xG
    "expectedGoalsOnTarget": "xG al arco",
    # duelos
    "totalContest": "Duelos totales",
}
MATCH_ORDEN = [
    "name", "position", "shirtNumber", "jerseyNumber", "substitute",
    "minutesPlayed", "rating", "captain", "teamName",
    "goals", "goalAssist", "expectedGoals", "expectedAssists",
    "totalShots", "onTargetScoringAttempt", "shotOffTarget",
    "blockedScoringAttempt", "expectedGoalsOnTarget",
    "bigChanceCreated", "bigChanceMissed", "penaltyWon", "totalOffside",
    "keyPass", "totalPass", "accuratePass", "totalCross", "accurateCross",
    "totalLongBalls", "accurateLongBalls",
    "totalOwnHalfPasses", "accurateOwnHalfPasses",
    "totalOppositionHalfPasses", "accurateOppositionHalfPasses",
    "touches", "ballCarriesCount", "totalBallCarriesDistance",
    "totalProgression", "progressiveBallCarriesCount",
    "totalProgressiveBallCarriesDistance", "bestBallCarryProgression",
    "possessionLostCtrl", "dispossessed", "unsuccessfulTouch",
    "wonTackle", "totalTackle", "interceptionWon", "totalClearance",
    "ballRecovery", "aerialWon", "aerialLost", "duelWon", "duelLost",
    "wonContest", "totalContest", "challengeLost", "outfielderBlock",
    "fouls", "wasFouled",
    "saves", "punches", "goalsPrevented", "goodHighClaim",
    "savedShotsFromInsideTheBox", "penaltyFaced", "penaltyConceded",
    "errorLeadToAGoal",
]
COLUMNAS_JUNK = {
    "firstName", "lastName", "slug", "shortName", "userCount", "gender",
    "sofascoreId", "country", "id", "marketValueCurrency", "fieldTranslations",
    "height", "dateOfBirthTimestamp", "proposedMarketValueRaw", "teamId",
    "jerseyNumber.1", "position.1", "ratingVersions", "statisticsType",
    "passValueNormalized", "defensiveValueNormalized", "dribbleValueNormalized",
    "shotValueNormalized", "keeperSaveValue", "goalkeeperValueNormalized", "match_id",
}
# ======================
# HELPERS
# ======================
def normalizar_partido(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, ~df.columns.duplicated()].copy()
    for extra in ("position.1", "jerseyNumber.1"):
        if extra in df.columns:
            df = df.drop(columns=[extra])
    if {"shirtNumber", "jerseyNumber"} <= set(df.columns):
        df = df.drop(columns=["jerseyNumber"])
    if "position" in df.columns:
        df["position"] = df["position"].map(POS_CORTO).fillna(df["position"])
    for col in ("substitute", "captain"):
        if col in df.columns:
            df[col] = df[col].astype(str).replace({"True": "Sí", "False": "No", "nan": ""})
    return df
def ruta_partido_csv(mid: int) -> str | None:
    for p in (f"{DATA_DIR}/partidos/match_{mid}.csv", f"{DATA_DIR}/stats_{mid}.csv"):
        if os.path.exists(p):
            return p
    return None
def parsear_match_id(texto: str) -> int:
    texto = texto.strip()
    if texto.isdigit():
        return int(texto)
    m = re.search(r"#id:(\d+)", texto)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{7,})", texto)
    if m:
        return int(m.group(1))
    raise ValueError("No se pudo extraer el ID del partido del texto ingresado.")
@st.cache_data(show_spinner=False)
def cargar_partido_csv(mid: int):
    p = ruta_partido_csv(mid)
    if not p:
        return None
    return normalizar_partido(pd.read_csv(p))
def cargar_meta() -> dict:
    pm = f"{DATA_DIR}/.partidos_meta.json"
    if os.path.exists(pm):
        try:
            with open(pm) as f:
                return json.load(f)
        except Exception:
            pass
    return {}
def partidos_guardados() -> list[dict]:
    meta = cargar_meta()
    res: dict[int, str] = {}
    archivos = sorted(glob.glob(f"{DATA_DIR}/stats_*.csv")) + sorted(glob.glob(f"{DATA_DIR}/partidos/match_*.csv"))
    for p in archivos:
        m = re.search(r"(\d+)", os.path.basename(p))
        if not m:
            continue
        mid = int(m.group(1))
        if mid in res:
            continue
        try:
            df = pd.read_csv(p, nrows=200)
        except Exception:
            continue
        dm = meta.get(str(mid), {})
        if TEAM_DINGNAN in (dm.get("home"), dm.get("away")):
            rival = dm.get("away") if dm.get("home") == TEAM_DINGNAN else dm.get("home")
            texto = f"{TEAM_DINGNAN} vs {rival}" if rival else TEAM_DINGNAN
        elif dm.get("home") and dm.get("away"):
            texto = f"{dm['home']} vs {dm['away']}"
        elif "teamName" in df.columns:
            equipos = sorted(df["teamName"].dropna().unique())
            if TEAM_DINGNAN in equipos:
                texto = TEAM_DINGNAN
            elif len(equipos) >= 2:
                texto = f"{equipos[0]} vs {equipos[1]}"
            elif len(equipos) == 1:
                texto = equipos[0]
            else:
                texto = f"Partido {mid}"
        else:
            texto = f"Partido {mid}"
        jornada = dm.get("round")
        if jornada is None and "round" in df.columns and df["round"].notna().any():
            jornada = df["round"].dropna().iloc[0]
        if jornada is not None:
            try:
                texto += f" · Jornada {float(jornada):.0f}"
            except (TypeError, ValueError):
                texto += f" · Jornada {jornada}"
        res[mid] = f"{texto} (id {mid})"
    return [{"mid": mid, "label": label} for mid, label in sorted(res.items(), key=lambda x: -x[0])]
def guardar_meta(mid: int, md: dict | None):
    if not md:
        return
    pm = f"{DATA_DIR}/.partidos_meta.json"
    try:
        cache = json.load(open(pm)) if os.path.exists(pm) else {}
    except Exception:
        cache = {}
    cache[str(mid)] = {
        "home": md.get("homeTeam", {}).get("name"),
        "away": md.get("awayTeam", {}).get("name"),
        "round": (md.get("roundInfo") or {}).get("round"),
        "homeScore": (md.get("homeScore") or {}).get("current"),
        "awayScore": (md.get("awayScore") or {}).get("current"),
    }
    try:
        with open(pm, "w") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass
@st.cache_data(show_spinner=False, ttl=3600)
def info_partido_live(mid: int):
    if Sofascore is None:
        return None
    try:
        return Sofascore().get_match_dict(mid)
    except Exception:
        return None
@st.cache_data(show_spinner=False, ttl=3600)
def partido_live(mid: int) -> pd.DataFrame:
    if Sofascore is None:
        raise RuntimeError("El scraping en vivo requiere ScraperFC (solo disponible localmente)")
    df = Sofascore().scrape_player_match_stats(mid)
    return normalizar_partido(df)
@st.cache_data(ttl=3600, show_spinner=False)
def cargar_liga() -> pd.DataFrame:
    df = pd.read_csv(LIGA_CSV)
    df["player id"] = df["player id"].astype(str)
    df["team id"] = df["team id"].astype(str)
    return df
@st.cache_data(ttl=86400, show_spinner=False)
def foto_jugador(player_id: int) -> bytes | None:
    """Foto del jugador desde la API pública de Sofascore. Cacheada 24hs para
    no golpear la API en cada rerender de Streamlit. Devuelve None si falla
    o si el jugador no tiene foto cargada."""
    try:
        r = requests.get(f"https://api.sofascore.com/api/v1/player/{player_id}/image", timeout=5)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None
def config_columnas(vista: pd.DataFrame) -> dict:
    config = {}
    for c in vista.columns:
        if pd.api.types.is_numeric_dtype(vista[c]):
            v = vista[c].dropna()
            if v.empty:
                continue
            enteros = (v % 1 == 0).all()
            config[c] = st.column_config.NumberColumn(format="%d" if enteros else "%.2f")
    return config
# ======================
# RENDER PARTIDO
# ======================
def render_header(mid: int, md: dict | None, df: pd.DataFrame):
    home = away = hs = as_ = None
    if md:
        home = md.get("homeTeam", {}).get("name")
        away = md.get("awayTeam", {}).get("name")
        hs = (md.get("homeScore") or {}).get("current")
        as_ = (md.get("awayScore") or {}).get("current")
        jornada = md.get("roundInfo", {}).get("round")
        torneo = md.get("tournament", {}).get("name")
        try:
            fecha = dt.datetime.fromtimestamp(md.get("startTimestamp", 0)).strftime("%d/%m/%Y %H:%M")
        except Exception:
            fecha = None
        estado = md.get("status", {}).get("description")
    else:
        dm = cargar_meta().get(str(mid), {})
        home, away = dm.get("home"), dm.get("away")
        hs, as_ = dm.get("homeScore"), dm.get("awayScore")
        jornada = dm.get("round")
        if not (home and away):
            equipos = sorted(df["teamName"].dropna().unique()) if "teamName" in df.columns else []
            if equipos:
                home, away = equipos[0], equipos[-1] if len(equipos) > 1 else equipos[0]
        if jornada is None and "round" in df.columns:
            jornada = df["round"].iloc[0]
        torneo = fecha = estado = None
    c1, cs, c2 = st.columns([1, 0.4, 1], vertical_alignment="center")
    c1.markdown(f"### {home or '—'}")
    marcador = f"{hs} - {as_}" if hs is not None else "vs"
    cs.markdown(
        f"<div style='text-align:center;font-size:42px;font-weight:800'>{marcador}</div>",
        unsafe_allow_html=True,
    )
    c2.markdown(f"### {away or '—'}")
    partes = []
    if jornada:
        partes.append(f"Jornada {jornada}")
    if torneo:
        partes.append(torneo)
    if fecha:
        partes.append(fecha)
    if estado:
        partes.append(estado)
    if partes:
        st.caption("  ·  ".join(partes))
def render_partido():
    st.markdown("## ⚽ Análisis por partido")
    st.caption(
        "Elegí un partido guardado en `data/` o cargá otro por **ID** / **URL de Sofascore**. "
        "Se muestra la información general y el reporte individual por equipo."
    )
    guardados = partidos_guardados()
    OTRO = "✍️ Otro partido (por ID/URL)"
    if guardados:
        labels = [p["label"] for p in guardados]
        mids = [p["mid"] for p in guardados]
        sel = st.selectbox("📂 Partidos guardados en data/", ["— Elegí un partido —"] + labels + [OTRO])
        if sel not in ("— Elegí un partido —", OTRO):
            st.session_state["mid"] = mids[labels.index(sel)]
        elif sel == OTRO:
            with st.form("form_partido"):
                raw = st.text_input(
                    "ID o URL del partido",
                    placeholder="15657854  |  https://www.sofascore.com/.../match#id:15657854",
                )
                enviado = st.form_submit_button("Cargar partido", type="primary")
            if enviado and raw.strip():
                try:
                    st.session_state["mid"] = parsear_match_id(raw)
                except ValueError as e:
                    st.error(str(e))
    else:
        with st.form("form_partido"):
            raw = st.text_input(
                "ID o URL del partido",
                placeholder="15657854  |  https://www.sofascore.com/.../match#id:15657854",
            )
            enviado = st.form_submit_button("Cargar partido", type="primary")
        if enviado and raw.strip():
            try:
                st.session_state["mid"] = parsear_match_id(raw)
            except ValueError as e:
                st.error(str(e))
    mid = st.session_state.get("mid")
    if not mid:
        st.info("Elegí un partido guardado arriba o escribí un ID de partido.")
        return
    df = cargar_partido_csv(mid)
    md = None
    if df is None:
        col1, col2 = st.columns([3, 1])
        col1.warning(
            "No hay datos guardados para este partido en `data/`. "
            "Podés correr `python analisis.py` o `scrape_liga.py` con este ID para guardarlos, "
            "o scrapearlos ahora desde acá."
        )
        if col2.button("Scrapear ahora", type="primary"):
            with st.spinner("Scrapeando el partido desde Sofascore..."):
                try:
                    md = info_partido_live(mid)
                    df = partido_live(mid)
                except Exception as e:
                    st.error(f"No se pudo scrapear el partido: {e}")
            if df is not None and not df.empty:
                if st.button("💾 Guardar en data/"):
                    df.to_csv(f"{DATA_DIR}/stats_{mid}.csv", index=False)
                    st.success(f"Guardado en `data/stats_{mid}.csv`")
    else:
        with st.spinner("Buscando información general del partido..."):
            md = info_partido_live(mid)
    if df is None or df.empty:
        st.stop()
    guardar_meta(mid, md)
    render_header(mid, md, df)
    st.divider()
    # ---- reporte individual por equipo ----
    if "teamName" in df.columns:
        equipos = sorted(df["teamName"].dropna().unique())
    else:
        equipos = []
    default = TEAM_DINGNAN if TEAM_DINGNAN in equipos else (equipos[0] if equipos else None)
    opciones = ["Todos"] + equipos
    seleccion = st.radio("Equipo", opciones, index=opciones.index(default) if default in opciones else 0,
                         horizontal=True)
    sub = df if seleccion == "Todos" else df[df["teamName"] == seleccion]
    orden_col = "minutesPlayed" if "minutesPlayed" in sub.columns else "rating"
    sub = sub.sort_values([orden_col, "rating"], ascending=[False, False], na_position="last")
    cols = [c for c in MATCH_ORDEN if c in sub.columns]
    cols += [c for c in sub.columns if c not in MATCH_ORDEN and c not in COLUMNAS_JUNK]
    vista = sub[cols].rename(columns=MATCH_RENOMBRES)
    st.markdown(f"**{len(sub)}** jugadores" + (f" · {seleccion}" if seleccion != "Todos" else ""))
    config = config_columnas(vista)
    st.dataframe(vista, width="stretch", height=460, column_config=config)
    st.download_button(
        "⬇️ Descargar CSV del partido",
        data=vista.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"partido_{mid}.csv",
        mime="text/csv",
    )
# ======================
# RENDER LIGA UNO
# ======================
def render_liga(posiciones, equipos, paises, pie, rango_edad, rango_min,
                rating_min, orden_col, ascendente, grupos_sel):
    df = cargar_liga()
    filtro = (
        df["posicion"].isin(posiciones)
        & df["team"].isin(equipos)
        & (df["Edad"] >= rango_edad[0]) & (df["Edad"] <= rango_edad[1])
        & (df["minutesPlayed"] >= rango_min)
        & (df["rating"] >= rating_min)
    )
    if paises:
        filtro &= df["País"].isin(paises)
    if pie:
        filtro &= df["Pie"].isin(pie)
    filtrado = df[filtro].copy()
    if filtrado.empty:
        st.warning("No hay jugadores que cumplan los filtros.")
        st.stop()
    filtrado = filtrado.sort_values(orden_col, ascending=ascendente, na_position="last")
    st.markdown("## 🏆 Liga Uno · Top jugadores")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jugadores", f"{len(filtrado):,}")
    c2.metric("Rating promedio", f"{filtrado['rating'].mean():.2f}")
    c3.metric("Goles totales", f"{filtrado['goals'].sum():,.0f}")
    mejor = filtrado.loc[filtrado["rating"].idxmax()]
    c4.metric("Mejor rating", f"{mejor['rating']:.2f}", f"{mejor['player']}")
    tab_tabla, tab_graficos, tab_ficha = st.tabs(["📋 Tabla", "📊 Gráficos", "👤 Ficha de jugador"])
    with tab_tabla:
        cols = []
        for g in grupos_sel:
            cols += [c for c in COLUMNAS_GRUPOS[g] if c in filtrado.columns]
        cols = list(dict.fromkeys(cols))
        vista = filtrado[cols].rename(columns=RENOMBRES)
        config = config_columnas(vista)
        st.dataframe(vista, width="stretch", height=520, column_config=config)
        csv = vista.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Descargar CSV", data=csv, file_name="top_jugadores_filtrado.csv",
                           mime="text/csv")
    with tab_graficos:
        g1, g2 = st.columns(2)
        with g1:
            fig = px.scatter(filtrado, x="goals_per90", y="expectedGoals_per90",
                             color="posicion", size="minutesPlayed",
                             hover_name="player", hover_data=["team", "rating"],
                             labels={"goals_per90": "Goles /90", "expectedGoals_per90": "xG /90"},
                             title="Goles vs xG por 90")
            st.plotly_chart(fig, width="stretch")
        with g2:
            top = filtrado.nlargest(10, "rating")
            fig = px.bar(top.sort_values("rating"), x="rating", y="player", orientation="h",
                         color="posicion", hover_data=["team", "minutesPlayed"],
                         labels={"rating": "Rating", "player": ""}, title="Top 10 rating")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, width="stretch")
        g3, g4 = st.columns(2)
        with g3:
            fig = px.scatter(filtrado, x="goals", y="assists", color="posicion",
                             size="minutesPlayed", hover_name="player", hover_data=["team", "rating"],
                             labels={"goals": "Goles", "assists": "Asistencias"},
                             title="Goles vs Asistencias")
            st.plotly_chart(fig, width="stretch")
        with g4:
            fig = px.histogram(filtrado, x="Edad", nbins=20, color_discrete_sequence=["#0ea5e9"],
                               labels={"Edad": "Edad"}, title="Distribución de edad")
            st.plotly_chart(fig, width="stretch")
    with tab_ficha:
        jugador = st.selectbox("Seleccionar jugador", filtrado["player"].unique())
        p = filtrado[filtrado["player"] == jugador].iloc[0]

        # ---- header: foto + datos básicos ----
        col_foto, col_info = st.columns([1, 3])
        with col_foto:
            img = foto_jugador(int(p["player id"]))
            if img:
                st.image(img, width=110)
            else:
                st.markdown(
                    f"<div style='width:96px;height:96px;border-radius:50%;background:#e6f1fb;"
                    f"display:flex;align-items:center;justify-content:center;font-size:28px;"
                    f"font-weight:500;color:#0c447c'>{jugador[0]}</div>",
                    unsafe_allow_html=True,
                )
        with col_info:
            st.markdown(f"### {p['player']}")
            st.caption(
                f"{p['team']} · {p['posicion']} · "
                f"{p['Edad']:.0f} años · {p['Altura']:.0f} cm · "
                f"{p['Pie'] if pd.notna(p['Pie']) else '—'}"
            )

        f1, f2, f3, f4, f5, f6 = st.columns(6)
        f1.metric("Rating", f"{p['rating']:.2f}")
        f2.metric("Goles", f"{p['goals']:.0f}")
        f3.metric("Goles /90", f"{p['goals_per90']:.2f}")
        f4.metric("Asistencias", f"{p['assists']:.0f}")
        f5.metric("Minutos", f"{p['minutesPlayed']:.0f}")
        f6.metric("Valor", p["Valor"] if pd.notna(p["Valor"]) else "—")

        st.divider()

        # ---- radar: jugador vs promedio de liga ----
        ficha_metricas = ["expectedGoals_per90", "expectedAssists_per90", "keyPasses_per90",
                          "successfulDribbles_per90", "tackles_per90", "interceptions_per90",
                          "ballRecovery_per90"]
        valores_jugador = [p[c] for c in ficha_metricas]
        valores_liga = [df[c].mean() for c in ficha_metricas]
        etiquetas = [RENOMBRES[c] for c in ficha_metricas]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=valores_jugador, theta=etiquetas, fill="toself",
            name=p["player"], line_color="#2a78d6",
        ))
        fig.add_trace(go.Scatterpolar(
            r=valores_liga, theta=etiquetas, fill="toself",
            name="Promedio liga", line_color="#898781", line_dash="dot",
            opacity=0.6,
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, showticklabels=False)),
            showlegend=True,
            title="Jugador vs promedio de la liga (por 90)",
            height=420,
        )
        st.plotly_chart(fig, width="stretch")
# ======================
# APP
# ======================
with st.sidebar:
    st.markdown("## Dingnan United")
    st.caption(f"China League 1 · Temporada {YEAR} · Sofascore")
    seccion = st.radio("Sección", ["⚽ Análisis por partido", "🏆 Liga Uno"])
    st.divider()
    if seccion == "🏆 Liga Uno":
        df_liga = cargar_liga()
        posiciones = st.multiselect("Posición", sorted(df_liga["posicion"].dropna().unique()),
                                    default=sorted(df_liga["posicion"].dropna().unique()))
        equipos = st.multiselect("Equipo", sorted(df_liga["team"].unique()),
                                 default=sorted(df_liga["team"].unique()))
        paises = st.multiselect("País", sorted(df_liga["País"].dropna().unique()), default=[])
        pie = st.multiselect("Pie", sorted(df_liga["Pie"].dropna().unique()), default=[])
        edad_min, edad_max = int(df_liga["Edad"].min()), int(df_liga["Edad"].max())
        rango_edad = st.slider("Edad", edad_min, edad_max, (edad_min, edad_max))
        rango_min = st.slider("Minutos mínimos", 0, int(df_liga["minutesPlayed"].max()), 300)
        rating_min = st.slider("Rating mínimo", 0.0, 10.0, 0.0, 0.1)
        st.divider()
        orden_col = st.selectbox("Ordenar por", ORDENES, format_func=lambda c: RENOMBRES[c])
        ascendente = st.checkbox("Ascendente", value=False)
        grupos_sel = st.multiselect("Columnas a mostrar", list(COLUMNAS_GRUPOS),
                                    default=["Básicas", "Ataque", "Tiros", "Creación", "Por 90"])
    else:
        st.caption("Pegá el ID del partido en el área principal.")
if seccion == "⚽ Análisis por partido":
    render_partido()
else:
    render_liga(posiciones, equipos, paises, pie, rango_edad, rango_min,
                rating_min, orden_col, ascendente, grupos_sel)

