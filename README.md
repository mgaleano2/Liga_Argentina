# Liga Argentina 2026 · Top 20 por posición

Ranking de los 20 mejores jugadores por posición (**Defensores, Mediocampistas, Delanteros**) de la **Liga Profesional Argentina 2026**, construido con datos de la API de [Sofascore](https://www.sofascore.com/).

## Qué incluye

| Script | Descripción |
|---|---|
| `analisis_arg.py` | Ranking de **temporada completa** por posición (25 columnas de stats). |
| `analisis_arg_sub20.py` | **Top 20 sub-20** (edad ≤ 20) con filtro server-side y detalle por jugador. |
| `analisis_detallado.py` | Versión completa: mismas stats + **Edad, Altura, Pie, País y Valor de mercado** de cada jugador (con caché). |

## Columnas de la tabla

`Jugador, Equipo, PJ, Min, Rating, Goles, Asist., G+A, xG, xA, Tiros, Tiros a puerta, Pases clave, Gr. chances, Dribbles ok, %Pases ok, %Pases largos ok, %Duelos, Duelos/90, Entradas/90, Interc./90, Recup./90, Despejes/90, Aéreos/90, Bloqueos/90` (+ `Edad, Altura, Pie, País, Valor` en la versión detallada).

- Las métricas defensivas se normalizan **por 90 minutos** para que sean comparables entre jugadores con distinto rodaje.
- `Rating` es el promedio Sofascore; se exige **mínimo 10 partidos con rating** (`countRating`) para entrar al ranking.
- Orden: `Rating` desc → `Minutos` desc → top 20.

## Datos

- Torneo Sofascore `155` · Temporada `87913`.
- El scrapeo usa `botasaurus_browser_get_json` (helper de ScraperFC que sortea el bloqueo de Cloudflare) sobre el endpoint público de estadísticas, con paginación `limit=100`.
- Detalles por jugador (edad, altura, pie, país, valor) se piden al endpoint `player/{id}` y se **cachean** en `data/player_details.csv` para no repetir llamadas entre corridas.

## Cómo correrlo

```bash
# Python 3.10+ con pandas y ScraperFC instalados
python -u analisis_arg.py
python -u analisis_arg_sub20.py
python -u analisis_detallado.py
```

## Dependencia

Se usa la librería [ScraperFC](https://github.com/oseymour/ScraperFC) (paquete Python para scraping de datos de fútbol); este proyecto se desarrolló sobre un **fork propio**: [mgaleano2/ScraperFC](https://github.com/mgaleano2/ScraperFC).

Salidas en `data/`:

- `top20_{defensores,mediocampistas,delanteros}.csv`
- `top20_sub20_{defensores,mediocampistas,delanteros}.csv`
- `top20_detallado_{defensores,mediocampistas,delanteros}.csv`
- `player_details.csv` (caché de detalles)

## Notas

- Sofascore puede responder `403 challenge` si se consulta con demasiada frecuencia o desde ciertas redes/VPN. En ese caso conviene esperar unos minutos y reintentar.
- Los datos son de temporada completa; para ventanas chicas (últimos 5 partidos) hace falta scrapear partido a partido.

## Fuente

[Sofascore](https://www.sofascore.com/) · API pública (no oficial).
