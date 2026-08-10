import os
import pandas as pd
from ScraperFC.sofascore import Sofascore

s = Sofascore()

POSICIONES = {
    "Defenders": "defensores",
    "Midfielders": "mediocampistas",
    "Forwards": "delanteros",
}

MIN_PARTIDOS = 10
OUT_DIR = "data"
os.makedirs(OUT_DIR, exist_ok=True)

PER90 = {"totalDuelsWon", "tackles", "interceptions", "ballRecovery", "clearances", "blockedShots", "aerialDuelsWon"}

RENOMBRES = {
    "player": "Jugador", "team": "Equipo", "pj": "PJ", "minutesPlayed": "Min",
    "rating": "Rating", "goals": "Goles", "assists": "Asist.", "goalsAssistsSum": "G+A",
    "expectedGoals": "xG", "expectedAssists": "xA", "totalShots": "Tiros",
    "shotsOnTarget": "Tiros a puerta", "keyPasses": "Pases clave",
    "bigChancesCreated": "Gr. chances", "successfulDribbles": "Dribbles ok",
    "accuratePassesPercentage": "%Pases ok", "accurateLongBallsPercentage": "%Pases largos ok",
    "totalDuelsWonPercentage": "%Duelos", "totalDuelsWon": "Duelos/90",
    "tackles": "Entradas/90", "interceptions": "Interc./90", "ballRecovery": "Recup./90",
    "clearances": "Despejes/90", "blockedShots": "Bloqueos/90", "aerialDuelsWon": "Aéreos/90",
}

for pos_en, pos_es in POSICIONES.items():
    df = s.scrape_player_league_stats(
        "2026",
        "Argentina Liga Profesional",
        accumulation="total",
        selected_positions=[pos_en],
    )

    df["pj"] = df["countRating"]
    df = df[df["pj"] > MIN_PARTIDOS]
    df = df.sort_values(
        ["rating", "minutesPlayed"],
        ascending=[False, False],
    ).head(20)

    minutos = df["minutesPlayed"].replace(0, pd.NA)
    for c in PER90:
        df[c] = (df[c] * 90 / minutos).round(1)

    tabla = df[list(RENOMBRES)].rename(columns=RENOMBRES).reset_index(drop=True)

    print(f"\n=== TOP 20 {pos_es.upper()} ===")
    print(tabla.to_string(index=False))

    tabla.to_csv(os.path.join(OUT_DIR, f"top20_{pos_es}.csv"), index=False)
