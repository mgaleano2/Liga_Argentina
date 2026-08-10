import os
from datetime import date, datetime, timezone

import pandas as pd
from ScraperFC.sofascore import botasaurus_browser_get_json

SEASON_ID = 87913
TOURNAMENT_ID = 155

MAX_EDAD = 20
MIN_PARTIDOS = 3

CAMPOS = (
    "rating,countRating,minutesPlayed,goals,assists,goalsAssistsSum,expectedGoals,"
    "expectedAssists,totalShots,shotsOnTarget,keyPasses,bigChancesCreated,successfulDribbles,"
    "accuratePassesPercentage,accurateLongBallsPercentage,totalDuelsWon,totalDuelsWonPercentage,"
    "aerialDuelsWon,tackles,interceptions,ballRecovery,clearances,blockedShots"
)

POSICIONES = {"Defenders": "defensores", "Midfielders": "mediocampistas", "Forwards": "delanteros"}
CODIGOS = {"Defenders": "D", "Midfielders": "M", "Forwards": "F"}

OUT_DIR = "data"
DETALLES_CSV = os.path.join(OUT_DIR, "player_details.csv")
os.makedirs(OUT_DIR, exist_ok=True)

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
PER90 = {"totalDuelsWon", "tackles", "interceptions", "ballRecovery", "clearances", "blockedShots", "aerialDuelsWon"}

SIMBOLOS_MONEDA = {"EUR": "€", "USD": "$", "GBP": "£", "ARS": "$", "BRL": "R$"}

COLUMNAS = [
    "Jugador", "Equipo", "Edad", "PJ", "Min", "Rating", "Goles", "Asist.", "G+A", "xG", "xA",
    "Tiros", "Tiros a puerta", "Pases clave", "Gr. chances", "Dribbles ok",
    "%Pases ok", "%Pases largos ok", "%Duelos", "Duelos/90", "Entradas/90", "Interc./90",
    "Recup./90", "Despejes/90", "Aéreos/90", "Bloqueos/90",
    "Altura", "Pie", "País", "Valor",
]


def scrape_stats(codigo_posicion: str) -> pd.DataFrame:
    filtros = [f"position.in.{codigo_posicion}", f"age.lte.{MAX_EDAD}"]
    offset = 0
    resultados = []
    while True:
        url = (
            "https://api.sofascore.com/api/v1/unique-tournament/"
            f"{TOURNAMENT_ID}/season/{SEASON_ID}/statistics"
            f"?limit=100&offset={offset}&accumulation=total&fields={CAMPOS}&filters="
            + ",".join(filtros)
        )
        r = botasaurus_browser_get_json(url)
        resultados += r["results"]
        if r["page"] == r["pages"] or r["pages"] == 0:
            break
        offset += 100
    df = pd.DataFrame.from_dict(resultados)
    df["player id"] = df["player"].apply(lambda p: p["id"])
    df["player"] = df["player"].apply(lambda p: p["name"])
    df["team"] = df["team"].apply(lambda p: p["name"])
    return df


def edad_desde_ts(ts: int | None) -> int | None:
    if not ts:
        return None
    dob = datetime.fromtimestamp(ts, timezone.utc)
    hoy = date.today()
    return hoy.year - dob.year - ((hoy.month, hoy.day) < (dob.month, dob.day))


def cargar_detalles() -> pd.DataFrame:
    if os.path.exists(DETALLES_CSV):
        return pd.read_csv(DETALLES_CSV, dtype={"id": str})
    return pd.DataFrame(columns=["id", "edad", "altura", "pie", "pais", "valor", "moneda"])


def obtener_detalles(jugadores_ids: list) -> pd.DataFrame:
    det = cargar_detalles()
    conocidos = set(det["id"])
    nuevos = [str(i) for i in jugadores_ids if str(i) not in conocidos]
    filas = []
    for jid in nuevos:
        try:
            p = botasaurus_browser_get_json(f"https://api.sofascore.com/api/v1/player/{jid}")["player"]
            filas.append({
                "id": jid,
                "edad": edad_desde_ts(p.get("dateOfBirthTimestamp")),
                "altura": p.get("height"),
                "pie": p.get("preferredFoot"),
                "pais": (p.get("country") or {}).get("name"),
                "valor": (p.get("proposedMarketValueRaw") or {}).get("value"),
                "moneda": (p.get("proposedMarketValueRaw") or {}).get("currency"),
            })
        except Exception as e:
            print(f"  (sin detalle para id {jid}: {e})")
    if filas:
        det = pd.concat([det, pd.DataFrame(filas)], ignore_index=True)
        det.to_csv(DETALLES_CSV, index=False)
    return det


def formatear_valor(valor, moneda):
    if pd.isna(valor) or pd.isna(moneda):
        return None
    simbolo = SIMBOLOS_MONEDA.get(moneda, moneda)
    return f"{valor:,.1f} {simbolo}"


def construir_tabla(pos_en: str) -> pd.DataFrame:
    df = scrape_stats(CODIGOS[pos_en])
    df["pj"] = df["countRating"]
    df = df[df["pj"] >= MIN_PARTIDOS]
    df = df.sort_values(["rating", "minutesPlayed"], ascending=[False, False]).head(20)

    det = obtener_detalles(df["player id"].tolist()).set_index("id")
    ids = df["player id"].astype(str)
    df["Edad"] = ids.map(det["edad"])
    df["Altura"] = ids.map(det["altura"])
    df["Pie"] = ids.map(det["pie"])
    df["País"] = ids.map(det["pais"])
    df["Valor"] = ids.map(
        det.apply(lambda f: formatear_valor(f["valor"], f["moneda"]), axis=1)
    )

    for c in PER90:
        df[c] = (df[c] * 90 / df["minutesPlayed"]).round(1)

    tabla = df[list(RENOMBRES) + ["Edad", "Altura", "Pie", "País", "Valor"]].rename(columns=RENOMBRES)
    return tabla[COLUMNAS].reset_index(drop=True)


def main():
    print(f"Liga Profesional Argentina 2026 · sub-{MAX_EDAD} (edad <= {MAX_EDAD}) · mín. {MIN_PARTIDOS} PJ")
    for pos_en, pos_es in POSICIONES.items():
        tabla = construir_tabla(pos_en)
        print(f"\n=== TOP 20 SUB-{MAX_EDAD} {pos_es.upper()} ===")
        print(tabla.to_string(index=False))
        salida = os.path.join(OUT_DIR, f"top20_sub{MAX_EDAD}_{pos_es}.csv")
        tabla.to_csv(salida, index=False)
        print(f"-> guardado en {salida}")


if __name__ == "__main__":
    main()
