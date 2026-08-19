import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Liga Profesional · Scouting", layout="wide",
                    initial_sidebar_state="expanded", page_icon="⚽")

# ============================================================
# CONSTANTES / RENOMBRES
# ============================================================
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
    "Edad": "Edad",
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
    "Por 90": [f"{c}_per90" for c in PER90],
}

ORDENES = ["rating", "goals", "goals_per90", "expectedGoals", "expectedGoals_per90",
           "assists", "keyPasses", "minutesPlayed", "appearances", "totalShots",
           "successfulDribbles", "tackles", "ballRecovery", "Edad"]

# Atributos del radar (percentil dentro de la liga, 0-100)
RADAR_STATS = {
    "Ataque": "goals_per90",
    "Creación": "keyPasses_per90",
    "Regate": "successfulDribbles_per90",
    "Duelos": "totalDuelsWon_per90",
    "Defensa": "tackles_per90",
    "Pases": "accuratePassesPercentage",
}

# Set más amplio de percentiles, usado para detectar fortalezas / a mejorar
PERFIL_STATS = {
    "Goles /90": "goals_per90",
    "xG /90": "expectedGoals_per90",
    "Asistencias /90": "assists_per90",
    "Pases clave /90": "keyPasses_per90",
    "Regates ok /90": "successfulDribbles_per90",
    "% pases": "accuratePassesPercentage",
    "Entradas /90": "tackles_per90",
    "Intercepciones /90": "interceptions_per90",
    "Recuperaciones /90": "ballRecovery_per90",
    "Duelos ganados /90": "totalDuelsWon_per90",
}

# ============================================================
# ESTILOS — reporte de scouting profesional (no "carta de FIFA")
# ============================================================
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }

[data-testid="stMetricValue"] { font-weight: 700; }
[data-testid="stMetricLabel"] { opacity: 0.75; }

/* ---- encabezado de ficha ---- */
.player-header {
    background: #171b23;
    border-left: 6px solid var(--accent, #4fa8f0);
    border-radius: 10px;
    padding: 16px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 4px;
}
.player-id .player-name { font-size: 25px; font-weight: 800; letter-spacing: -0.3px; color: #f3f5f8; }
.player-id .player-meta { font-size: 13.5px; color: #9aa4b5; margin-top: 3px; }
.player-id .player-meta b { color: #d6dae2; }
.rating-badge {
    width: 58px; height: 58px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 19px; font-weight: 800; color: #f3f5f8;
    background: #11141a; border: 3px solid var(--accent, #4fa8f0);
    flex-shrink: 0;
}

/* ---- tablas de stats por sección ---- */
.stat-block { background: #14171e; border-radius: 10px; padding: 14px 16px 8px 16px; height: 100%; }
.stat-block-title {
    font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
    color: #7c8698; font-weight: 700; margin-bottom: 8px;
}
.stat-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.stat-table td { padding: 6px 2px; border-bottom: 1px solid #22262f; color: #c9cfd8; }
.stat-table td.val { text-align: right; font-weight: 700; color: #f0f2f5; white-space: nowrap; }
.stat-table tr:last-child td { border-bottom: none; }

/* ---- fortalezas / a mejorar ---- */
.tag-pill {
    display: inline-block; padding: 4px 11px; border-radius: 20px;
    font-size: 12.5px; font-weight: 600; margin: 3px 6px 3px 0;
}
.tag-fuerte { background: rgba(62,207,110,0.15); color: #4fdc84; border: 1px solid rgba(62,207,110,0.4); }
.tag-debil  { background: rgba(224,82,77,0.15); color: #f0776f; border: 1px solid rgba(224,82,77,0.4); }

.section-label {
    font-size: 11px; text-transform: uppercase; letter-spacing: 1.2px;
    color: #7c8698; margin: 14px 0 4px 2px; font-weight: 700;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATOS
# ============================================================
@st.cache_data
def cargar():
    df = pd.read_csv("data/top_jugadores_liga.csv")
    df["player id"] = df["player id"].astype(str)
    df["team id"] = df["team id"].astype(str)
    df["Edad"] = pd.to_numeric(df["Edad"], errors="coerce").astype("Int64")
    return df


@st.cache_data
def ultima_actualizacion() -> str:
    try:
        with open("data/ultima_actualizacion.txt") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "desconocida"


@st.cache_data
def calcular_percentiles(df: pd.DataFrame, stats: dict) -> pd.DataFrame:
    """Percentil (0-100) de cada jugador dentro de TODA la liga, para un set de columnas dado."""
    pct = pd.DataFrame(index=df.index)
    for label, col in stats.items():
        pct[label] = (df[col].rank(pct=True) * 100).round(0)
    return pct


def tier_color(rating: float) -> str:
    if pd.isna(rating):
        return "#8b929c"
    if rating >= 7.3:
        return "#d4af37"
    if rating >= 6.9:
        return "#4fa8f0"
    if rating >= 6.5:
        return "#8b929c"
    return "#b06a3d"


def fmt(v, dec=1):
    return "—" if pd.isna(v) else f"{v:.{dec}f}"


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def stat_row(label, value):
    return f"<tr><td>{label}</td><td class='val'>{value}</td></tr>"


def stat_cnt(row, col, dec=0):
    """Formatea un valor; si la columna no tiene datos en TODA la liga, avisa en vez de mostrar 'nan'."""
    if col not in row or pd.isna(row[col]):
        return "N/D" if columnas_sin_datos.get(col) else "—"
    return f"{row[col]:.{dec}f}"


df = cargar()

# Columnas que Sofascore no trackea para esta liga (100% NaN) — se detecta
# dinámicamente para no ocultar el dato el día que la fuente lo empiece a dar.
columnas_sin_datos = {c: df[c].isna().all() for c in df.columns if df[c].dtype != "object"}

RADAR_STATS = {k: v for k, v in RADAR_STATS.items() if not columnas_sin_datos.get(v)}
PERFIL_STATS = {k: v for k, v in PERFIL_STATS.items() if not columnas_sin_datos.get(v)}

percentiles_radar = calcular_percentiles(df, RADAR_STATS)
percentiles_perfil = calcular_percentiles(df, PERFIL_STATS)

# ============================================================
# SIDEBAR — FILTROS primero, FICHA vinculada a esos filtros
# ============================================================
with st.sidebar:
    st.markdown("## ⚽ Liga Profesional")
    st.caption(f"Temporada 2026 · Sofascore · Datos: {ultima_actualizacion()}")
    st.divider()

    with st.expander("🔎 Filtros", expanded=True):
        posiciones = st.multiselect("Posición", sorted(df["posicion"].dropna().unique()),
                                    default=sorted(df["posicion"].dropna().unique()))
        equipos = st.multiselect("Equipo", sorted(df["team"].unique()), default=sorted(df["team"].unique()))
        rango_edad = st.slider("Edad", 15, 45, (15, 45))
        rango_min = st.slider("Minutos mínimos", 0, int(df["minutesPlayed"].max()), 300)
        rating_min = st.slider("Rating mínimo", 0.0, 10.0, 0.0, 0.1)

    filtro = (
        df["posicion"].isin(posiciones)
        & df["team"].isin(equipos)
        & ((df["Edad"].isna()) | (df["Edad"] >= rango_edad[0]) & (df["Edad"] <= rango_edad[1]))
        & (df["minutesPlayed"] >= rango_min)
        & (df["rating"] >= rating_min)
    )
    filtrado = df[filtro].copy()

    with st.expander("⚙️ Tabla y orden", expanded=False):
        orden_col = st.selectbox("Ordenar por", ORDENES, format_func=lambda c: RENOMBRES[c])
        ascendente = st.checkbox("Ascendente", value=False)
        grupos_sel = st.multiselect("Columnas a mostrar", list(COLUMNAS_GRUPOS),
                                    default=["Básicas", "Ataque", "Tiros", "Creación", "Por 90"])

    # Se ordena ACÁ (antes de armar la lista de la ficha) para que el
    # selector de jugador respete el mismo orden que la tabla / el filtro.
    filtrado = filtrado.sort_values(orden_col, ascending=ascendente, na_position="last")

    st.divider()
    st.markdown("### 🃏 Ficha de jugador")
    if filtrado.empty:
        st.info("Ningún jugador cumple los filtros.")
        jugador = None
    else:
        jugador = st.selectbox(
            "Elegir jugador (según filtros y orden de la tabla)",
            pd.unique(filtrado["player"]),  # respeta el orden de filtrado, no alfabético
            key="ficha_jugador",
        )
        st.caption(f"{len(filtrado)} jugadores disponibles con los filtros actuales.")

if filtrado.empty:
    st.warning("No hay jugadores que cumplan los filtros.")
    st.stop()

# ============================================================
# BARRA DE RESUMEN
# ============================================================
st.caption(
    f"📋 **{len(filtrado):,}** jugadores filtrados · "
    f"Rating promedio **{filtrado['rating'].mean():.2f}** · "
    f"Mejor rating: **{filtrado.loc[filtrado['rating'].idxmax(), 'player']}** "
    f"({filtrado['rating'].max():.2f})"
)

# ============================================================
# FICHA DE JUGADOR — reporte de scouting
# ============================================================
p = df[df["player"] == jugador].iloc[0]
accent = tier_color(p["rating"])
edad_txt = f"{p['Edad']:.0f} años" if pd.notna(p["Edad"]) else "Edad ND"

# --- valores consolidados ---
tiros_tot, tiros_arco = p["totalShots"], p["shotsOnTarget"]
pct_tiros_arco = (tiros_arco / tiros_tot * 100) if tiros_tot else 0
duelos_tot = p["totalDuelsWon"] + p["duelLost"]
pct_duelos = (p["totalDuelsWon"] / duelos_tot * 100) if duelos_tot else 0

st.markdown(f"""
<div class="player-header" style="--accent:{accent};">
    <div class="player-id">
        <div class="player-name">{p['player']}</div>
        <div class="player-meta">
            {p['team']} · <b>{p['posicion']}</b> · {edad_txt} ·
            {p['appearances']:.0f} partidos · {p['minutesPlayed']:.0f}' jugados
        </div>
    </div>
    <div class="rating-badge" style="--accent:{accent};">{p['rating']:.2f}</div>
</div>
""", unsafe_allow_html=True)

col_ofensiva, col_creacion, col_defensa, col_disciplina = st.columns(4)

with col_ofensiva:
    st.markdown(f"""
    <div class="stat-block">
      <div class="stat-block-title">Ofensiva</div>
      <table class="stat-table">
        {stat_row("Goles (xG)", f"{p['goals']:.0f} ({stat_cnt(p, 'expectedGoals', 1)})")}
        {stat_row("Asistencias (xA)", f"{p['assists']:.0f} ({stat_cnt(p, 'expectedAssists', 1)})")}
        {stat_row("G+A", f"{p['goalsAssistsSum']:.0f}")}
        {stat_row("Tiros (al arco)", f"{tiros_tot:.0f} ({tiros_arco:.0f} · {pct_tiros_arco:.0f}%)")}
        {stat_row("De penal", f"{p['penaltyGoals']:.0f}")}
      </table>
    </div>
    """, unsafe_allow_html=True)

with col_creacion:
    st.markdown(f"""
    <div class="stat-block">
      <div class="stat-block-title">Creación</div>
      <table class="stat-table">
        {stat_row("Pases clave", f"{p['keyPasses']:.0f}")}
        {stat_row("Ocasiones creadas", stat_cnt(p, "bigChancesCreated"))}
        {stat_row("Regates ok", f"{p['successfulDribbles']:.0f}")}
        {stat_row("Pases (precisión)", f"{p['totalPasses']:.0f} ({p['accuratePassesPercentage']:.0f}%)")}
      </table>
    </div>
    """, unsafe_allow_html=True)

with col_defensa:
    st.markdown(f"""
    <div class="stat-block">
      <div class="stat-block-title">Defensa</div>
      <table class="stat-table">
        {stat_row("Entradas", stat_cnt(p, "tackles"))}
        {stat_row("Intercepciones", stat_cnt(p, "interceptions"))}
        {stat_row("Recuperaciones", f"{p['ballRecovery']:.0f}")}
        {stat_row("Despejes", f"{p['clearances']:.0f}")}
        {stat_row("Duelos ganados", f"{p['totalDuelsWon']:.0f}/{duelos_tot:.0f} ({pct_duelos:.0f}%)")}
      </table>
    </div>
    """, unsafe_allow_html=True)

with col_disciplina:
    st.markdown(f"""
    <div class="stat-block">
      <div class="stat-block-title">Disciplina</div>
      <table class="stat-table">
        {stat_row("Amarillas / Rojas", f"{p['yellowCards']:.0f} / {p['redCards']:.0f}")}
        {stat_row("Faltas cometidas", f"{p['fouls']:.0f}")}
        {stat_row("Faltas recibidas", f"{p['wasFouled']:.0f}")}
        {stat_row("Tiros bloqueados", f"{p['blockedShots']:.0f}")}
        {stat_row("Autogoles", f"{p['ownGoals']:.0f}")}
      </table>
    </div>
    """, unsafe_allow_html=True)

_faltantes = [RENOMBRES.get(c, c) for c in
              ["expectedGoals", "expectedAssists", "tackles", "interceptions", "bigChancesCreated"]
              if columnas_sin_datos.get(c)]
if _faltantes:
    st.caption(
        f"⚠️ Sin datos en la fuente para esta liga: {', '.join(_faltantes)} "
        "(Sofascore no publica estas métricas para la Liga Profesional; no depende de la app)."
    )

st.write("")
col_radar, col_perfil = st.columns([1, 1.6])

with col_radar:
    st.markdown('<div class="section-label">Perfil de juego (percentil vs. liga)</div>', unsafe_allow_html=True)
    pj = percentiles_radar.loc[p.name]
    radar_vals = list(pj.values) + [list(pj.values)[0]]
    radar_labels = list(pj.index) + [list(pj.index)[0]]
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=radar_vals, theta=radar_labels, fill="toself",
        fillcolor=hex_to_rgba(accent, 0.35), line=dict(color=accent, width=2),
    ))
    fig_radar.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="#2a2f3a"),
            angularaxis=dict(gridcolor="#2a2f3a"),
        ),
        showlegend=False, height=280,
        margin=dict(l=30, r=30, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_radar, width="stretch", config={"displayModeBar": False})

with col_perfil:
    st.markdown('<div class="section-label">Fortalezas y aspectos a mejorar</div>', unsafe_allow_html=True)
    pj_perfil = percentiles_perfil.loc[p.name].dropna().sort_values(ascending=False)

    if pj_perfil.empty:
        st.caption("No hay minutos suficientes para calcular percentiles de este jugador.")
    else:
        fuertes = pj_perfil.head(3)
        debiles = pj_perfil.tail(3)

        pills_fuertes = "".join(
            f'<span class="tag-pill tag-fuerte">▲ {label} · P{int(val)}</span>'
            for label, val in fuertes.items()
        )
        pills_debiles = "".join(
            f'<span class="tag-pill tag-debil">▼ {label} · P{int(val)}</span>'
            for label, val in debiles.items()
        )
        st.markdown(pills_fuertes, unsafe_allow_html=True)
        st.markdown(pills_debiles, unsafe_allow_html=True)
        st.caption(
            "Percentil (P) = posición del jugador dentro de toda la liga (300+ min), "
            "100 = el mejor de la liga en esa métrica, 0 = el último."
        )

st.divider()

# ============================================================
# TABLA (siempre visible, debajo de la ficha, sigue los filtros)
# ============================================================
st.markdown('<div class="section-label">📋 Jugadores filtrados</div>', unsafe_allow_html=True)

cols = []
for g in grupos_sel:
    cols += [c for c in COLUMNAS_GRUPOS[g] if c in filtrado.columns]
cols = list(dict.fromkeys(cols))

vista = filtrado[cols].rename(columns=RENOMBRES)

config = {}
for c in vista.columns:
    if pd.api.types.is_numeric_dtype(vista[c]):
        if pd.api.types.is_integer_dtype(vista[c]):
            config[c] = st.column_config.NumberColumn(format="%d")
        else:
            config[c] = st.column_config.NumberColumn(format="%.2f")

st.dataframe(vista, width="stretch", height=520, column_config=config)

csv = vista.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ Descargar CSV", data=csv, file_name="top_jugadores_filtrado.csv",
                   mime="text/csv")

# ============================================================
# GRÁFICOS (en un expander, para no saturar la pantalla)
# ============================================================
with st.expander("📊 Ver gráficos", expanded=False):
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
        fig = px.histogram(filtrado.dropna(subset=["Edad"]), x="Edad", nbins=20,
                           color_discrete_sequence=["#0ea5e9"],
                           labels={"Edad": "Edad"}, title="Distribución de edad")
        st.plotly_chart(fig, width="stretch")
