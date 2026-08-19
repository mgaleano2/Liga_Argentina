import os
import sys
from datetime import date
import pandas as pd
from ScraperFC.sofascore import Sofascore
from ScraperFC.utils import botasaurus_browser_get_json, get_module_comps

##############################
# Actualizado: 18-08-2026
##############################


YEAR = "2026"
LEAGUE = "Argentina Liga Profesional"
OUT = "data/top_jugadores_liga.csv"
METADATA = "data/ultima_actualizacion.txt"
DETALLES_CSV = "data/player_details.csv"
MIN_MINUTOS = 180

os.makedirs("data", exist_ok=True)

POS_ESP = {"G": "Portero", "D": "Defensor", "M": "Mediocampista", "F": "Delantero"}

PER90 = [
    "goals", "assists", "goalsAssistsSum", "expectedGoals", "expectedAssists",
    "totalShots", "shotsOnTarget", "keyPasses", "successfulDribbles",
    "tackles", "interceptions", "ballRecovery", "totalDuelsWon",
    "wasFouled", "fouls", "yellowCards", "redCards",
]

CAMPOS = [
    "player", "team",
    "appearances", "minutesPlayed",
    "rating",
    "goals", "assists", "goalsAssistsSum", "penaltyGoals",
    "expectedGoals", "expectedAssists",
    "totalShots", "shotsOnTarget", "shotsOffTarget",
    "bigChancesCreated", "keyPasses",
    "totalPasses", "accuratePassesPercentage",
    "successfulDribbles",
    "tackles", "interceptions", "ballRecovery", "clearances", "blockedShots",
    "totalDuelsWon", "duelLost",
    "wasFouled", "fouls",
    "yellowCards", "redCards", "ownGoals",
]


def edad_desde_ts(ts):
    if pd.isna(ts):
        return None
    from datetime import date
    return (date.today() - date.fromtimestamp(ts)).days // 365


def ultima_actualizacion() -> str:
    if os.path.exists(METADATA):
        with open(METADATA) as f:
            return f.read().strip()
    return "desconocida"


def cargar_cache_edades() -> dict:
    if os.path.exists(DETALLES_CSV):
        det = pd.read_csv(DETALLES_CSV, dtype={"id": str})
        return dict(zip(det["id"], det["edad"]))
    return {}


def guardar_cache_edades(cache: dict) -> None:
    pd.DataFrame({"id": list(cache), "edad": list(cache.values())}).to_csv(
        DETALLES_CSV, index=False
    )


def actualizar() -> None:
    s = Sofascore()
    df = s.scrape_player_league_stats(YEAR, LEAGUE)

    keep = ["player id", "team id"] + [c for c in CAMPOS if c in df.columns]
    df = df[keep]

    df = df[df["minutesPlayed"] >= MIN_MINUTOS]
    df = df.sort_values("rating", ascending=False, na_position="last")

    comps = get_module_comps("SOFASCORE")
    league_id = comps[LEAGUE]["SOFASCORE"]
    season_id = s.get_valid_seasons(LEAGUE)[YEAR]
    players = botasaurus_browser_get_json(
        f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/players"
    )
    pos = {str(x["playerId"]): POS_ESP.get(x["position"]) for x in players["players"]}
    df.insert(4, "posicion", df["player id"].astype(str).map(pos))

    edades = {}
    equipos = df["team id"].unique()
    for i, tid in enumerate(equipos, 1):
        squad = botasaurus_browser_get_json(f"https://api.sofascore.com/api/v1/team/{tid}/players")
        for x in squad["players"]:
            p = x["player"]
            edades[str(p["id"])] = edad_desde_ts(p.get("dateOfBirthTimestamp"))
        print(f"edades: {i}/{len(equipos)}")

    cache = cargar_cache_edades()
    ids = df["player id"].astype(str)
    faltantes = [jid for jid in ids.unique() if jid not in edades or edades[jid] is None]
    total = len(faltantes)
    for n, jid in enumerate(faltantes, 1):
        if jid in cache:
            edades[jid] = cache[jid]
        else:
            try:
                p = botasaurus_browser_get_json(
                    f"https://api.sofascore.com/api/v1/player/{jid}"
                )["player"]
                edad = edad_desde_ts(p.get("dateOfBirthTimestamp"))
            except Exception as e:
                print(f"  (sin edad para id {jid}: {e})")
                edad = None
            edades[jid] = edad
            cache[jid] = edad
        if n % 25 == 0 or n == total:
            print(f"edades faltantes: {n}/{total}")
    guardar_cache_edades(cache)

    df.insert(5, "Edad", pd.to_numeric(
        ids.map(edades), errors="coerce").astype("Int64"))

    for c in PER90:
        if c in df.columns:
            df[f"{c}_per90"] = df[c].mul(90).div(df["minutesPlayed"])

    for col in df.select_dtypes(include="float").columns:
        df[col] = df[col].round(2)

    df.to_csv(OUT, index=False)
    with open(METADATA, "w") as f:
        f.write(date.today().isoformat())
    print(f"-> {OUT} ({len(df)} filas x {df.shape[1]} columnas)")
    print(f"Actualizado: {date.today().isoformat()}")


if __name__ == "__main__":
    forzar = "--actualizar" in sys.argv
    if os.path.exists(OUT) and not forzar:
        print(f"Ya hay datos del {ultima_actualizacion()}.")
        print("Corré 'python liga_arg.py --actualizar' para actualizarlos.")
    else:
        actualizar()
