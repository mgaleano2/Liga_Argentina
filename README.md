# Liga Argentina 2026 · Top 20 por posición

Ranking de los 20 mejores jugadores por posición (**Defensores, Mediocampistas, Delanteros**) de la **Liga Profesional Argentina 2026**, construido con datos de la API de [Sofascore](https://www.sofascore.com/).

## Qué incluye

| Script | Descripción |
|---|---|
| `analisis_arg.py` | Ranking de **temporada completa** por posición (25 columnas de stats). |
| `analisis_arg_sub20.py` | **Top 20 sub-20** (edad ≤ 20) detalle por jugador.
| `analisis_detallado.py` | Versión completa: mismas stats + **Edad, Altura, Pie, País y Valor de mercado** de cada jugador (con caché). |

- Utilizacion de OpenCode + Claude Code, para mejoras del codigo.
## Columnas de la tabla

`Jugador, Equipo, PJ, Min, Rating, Goles, Asist., G+A, xG, xA, Tiros, Tiros a puerta, Pases clave, Gr. chances, Dribbles ok, %Pases ok, %Pases largos ok, %Duelos, Duelos/90, Entradas/90, Interc./90, Recup./90, Despejes/90, Aéreos/90, Bloqueos/90` (+ `Edad, Altura, Pie, País, Valor` en la versión detallada).

- `Rating` es el promedio Sofascore; se exige **mínimo 10 partidos con rating** (`countRating`) para entrar al ranking.
- Orden: `Rating` desc → `Minutos` desc → top 20.

## Datos

- Torneo Sofascore `155` · Temporada `87913`.
- Detalles por jugador (edad, altura, pie, país, valor)  y se **cachean** en `data/player_details.csv` para no repetir llamadas entre corridas.

## Cómo correrlo

```bash
# Python 3.10+ con pandas y ScraperFC instalados
python  analisis_arg.py
python  analisis_arg_sub20.py
python  analisis_detallado.py
```

## Dependencia

Se usa la librería [ScraperFC](https://github.com/oseymour/ScraperFC) (paquete Python para scraping de datos de fútbol); este proyecto se desarrolló sobre un **fork propio**: [mgaleano2/ScraperFC](https://github.com/mgaleano2/ScraperFC).
