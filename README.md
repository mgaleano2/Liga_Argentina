# Liga Argentina 2026 · Top Jugadores

Ranking y análisis de jugadores de la **Liga Profesional Argentina 2026** con datos de la API de [Sofascore](https://www.sofascore.com/), scrapeados con el fork propio de [ScraperFC](https://github.com/mgaleano2/ScraperFC).

## Arquitectura

El proyecto tiene dos partes: un **scraper** que genera los datos y una **app** que los visualiza.

| Archivo | Rol |
|---|---|
| `liga_arg.py` | Scraper: baja stats de Sofascore, las procesa con pandas y escribe `data/top_jugadores_liga.csv`. |
| `streamlit_arg.py` | App: filtros, tabla, gráficos, radar chart y ficha por jugador leyendo el CSV generado. |
Link: https://ligaargentina2026.streamlit.app/

### `liga_arg.py`

- Descarga las estadísticas de la temporada (`Liga Profesional 2026`, torneo Sofascore 155) con `scrape_player_league_stats`.
- Filtra jugadores con **más de 300 minutos** y ordena por **rating** desc.
- Agrega:
  - **Posición** (`posicion`): desde el endpoint `/players` (una sola request, todos los jugadores).
  - **Edad**: desde los planteles por equipo (`/team/{id}/players`, 30 requests) y, para los jugadores que se fueron de su equipo a mitad de temporada, consulta individual con caché en `data/player_details.csv`.
  - Columnas **por 90 minutos** (`*_per90`): `goles, asistencias, xG, xA, tiros, pases clave, regates, entradas, intercepciones, balones recuperados, duelos ganados, faltas recibidas, faltas, amarillas, rojas`, normalizadas cada 90'.
- **Control de actualización**: registra la fecha en `data/ultima_actualizacion.txt`. Si ya hay datos, no vuelve a scrapear salvo que corras con `--actualizar`.

### `streamlit_arg.py`

- **Filtros** (sidebar): Posición, Equipo, **Edad (15–45)**, Minutos mínimos, Rating mínimo.
- **Orden** por cualquier métrica (rating, goles, xG, /90, edad...), ascendente/descendente.
- **Métricas** del conjunto filtrado (jugadores, rating promedio, goles totales, mejor rating).
- Tres pestañas:
  - 📋 **Tabla** con columnas agrupadas (Básicas, Ataque, Tiros, Creación, Pases, Defensa, Disciplina, Por 90) y descarga en CSV.
  - 📊 **Gráficos** (plotly): Goles vs xG /90, Top 10 rating, Goles vs Asistencias, distribución de edad.
  - 👤 **Ficha de jugador**: foto desde Sofascore, métricas clave y radar chart comparando vs promedio de la liga (por 90).

## Datos

`data/top_jugadores_liga.csv` — **617 jugadores × 52 columnas**:

- Identificación: `player id`, `team id`, `player`, `team`, `posicion`, `Edad`.
- Volumen: `appearances` (partidos), `minutesPlayed` (minutos), `rating`.
- Ataque/creación: `goals`, `assists`, `goalsAssistsSum`, `penaltyGoals`, `expectedGoals`, `expectedAssists`, `totalShots`, `shotsOnTarget`, `shotsOffTarget`, `bigChancesCreated`, `keyPasses`.
- Pases: `totalPasses`, `accuratePassesPercentage`.
- Regate: `successfulDribbles`.
- Defensa: `tackles`, `interceptions`, `ballRecovery`, `clearances`, `blockedShots`, `totalDuelsWon`, `duelLost`.
- Disciplina: `wasFouled`, `fouls`, `yellowCards`, `redCards`, `ownGoals`.
- 17 columnas `*_per90` (las anteriores normalizadas por 90 minutos).

Otros archivos:
- `data/player_details.csv` — caché de edades por jugador (evita repetir consultas).
- `data/ultima_actualizacion.txt` — fecha de la última actualización.

## Cómo correrlo

Requiere el venv con pandas, streamlit, plotly y ScraperFC (fork local, install editable):

```bash
# Actualizar los datos (solo la primera vez, o cuando quieras refrescar)
python liga_arg.py --actualizar

# Correr sin volver a scrapear (usa los datos existentes)
python liga_arg.py

# Levantar la app
streamlit run streamlit_arg.py
```

## Estado actual

*Última actualización: 19-08-2026*

- Scrapeo de temporada completa funcionando: **617 jugadores × 52 columnas**.
- Edad resuelta con planteles por equipo + fetch individual con caché para transferidos a mitad de temporada.
- Guard anti-scrapeo: el script no re-descarga si ya hay datos vigentes.
- App con radar chart y foto de jugador en la ficha.

## Fuente

[Sofascore](https://www.sofascore.com/) · API pública (no oficial) · [ScraperFC (fork propio)](https://github.com/mgaleano2/ScraperFC)
