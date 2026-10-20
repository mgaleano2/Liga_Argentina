import os
import random
import sys
import time
from datetime import date, datetime, timezone
import pandas as pd
from ScraperFC.sofascore import Sofascore
from ScraperFC.utils import botasaurus_browser_get_json_via_xhr, get_module_comps

_SOFASCORE_HOME = "https://www.sofascore.com/"
_API = "https://api.sofascore.com/api/v1"

# season_id conocido (evita 1 request a /seasons/, que es la que más bloquean).
# Visto en sofascore_statistics_cache.json: liga 155, temporada 2026 -> 87913.
SEASON_IDS = {"2026": 87913}

# Pausa aleatoria entre requests. Lento a propósito: pocas requests y espaciadas
# es lo que evita que el anti-bot marque la IP.
PAUSA_MIN_SEG, PAUSA_MAX_SEG = 10, 20


class SofascoreBloqueo(RuntimeError):
    pass


def _proxy_args() -> list[str] | None:
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if proxy:
        return [f"--proxy-server={proxy}"]
    return None


_ultimo_request = 0.0


def sofa_get(url: str) -> dict:
    """Una request a Sofascore, respetando la pausa entre requests.

    Sin reintentos: insistir después de un 403 solo alarga el bloqueo.
    Devuelve {} si el recurso no existe (404).
    """
    global _ultimo_request
    if _ultimo_request:
        espera = random.uniform(PAUSA_MIN_SEG, PAUSA_MAX_SEG) - (time.monotonic() - _ultimo_request)
        if espera > 0:
            time.sleep(espera)
    r = botasaurus_browser_get_json_via_xhr(
        url, _SOFASCORE_HOME, add_arguments=_proxy_args()
    )
    _ultimo_request = time.monotonic()

    if not isinstance(r, dict):
        raise SofascoreBloqueo(f"respuesta inválida en {url.split('?')[0]}")
    if "error" in r and len(r) == 1:
        codigo = r["error"].get("code") if isinstance(r["error"], dict) else r["error"]
        if codigo == 404:
            return {}
        raise SofascoreBloqueo(f"error {codigo} en {url.split('?')[0]}")
    return r


##############################
# Actualizado: 20-10-2026
##############################


YEAR = "2026"
LEAGUE = "Argentina Liga Profesional"
OUT = "data/top_jugadores_liga.csv"
METADATA = "data/ultima_actualizacion.txt"
# Caché permanente por jugador: nacimiento y posición casi no cambian, así que
# cada jugador se pide una sola vez. "consultado" = ya se pidió su nacimiento
# (aunque Sofascore no lo tenga), para no volver a pedirlo.
CACHE_JUGADORES = "data/player_details.csv"
MIN_MINUTOS = 300

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


def edad_desde_ts(ts) -> int | None:
    if ts is None or pd.isna(ts):
        return None
    # Sofascore da el nacimiento como medianoche UTC: en hora local (UTC-3)
    # caería el día anterior.
    nac = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
    hoy = date.today()
    return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))


def ultima_actualizacion() -> str:
    if os.path.exists(METADATA):
        with open(METADATA) as f:
            return f.read().strip()
    return "desconocida"


# ============================================================
# CACHÉ DE JUGADORES
# ============================================================
def _nuevo() -> dict:
    return {"nacimiento": None, "edad": None, "posicion": None, "consultado": False}


def cargar_cache() -> dict:
    """{player_id: {"nacimiento", "edad", "posicion", "consultado"}}.

    "edad" solo viene de filas del formato viejo (id, edad), sin nacimiento.
    """
    if not os.path.exists(CACHE_JUGADORES):
        return {}
    det = pd.read_csv(CACHE_JUGADORES, dtype={"id": str})
    if "consultado" not in det.columns:  # formato viejo
        det["consultado"] = det["edad"].notna()
    for col in _nuevo():
        if col not in det.columns:
            det[col] = None
    det = det.astype(object).where(det.notna(), None)
    return {r.pop("id"): r for r in det.to_dict("records")}


def guardar_cache(cache: dict) -> None:
    det = pd.DataFrame.from_dict(cache, orient="index").reindex(columns=list(_nuevo()))
    det.index.name = "id"
    for col in ("nacimiento", "edad"):
        det[col] = pd.to_numeric(det[col]).astype("Int64")
    det["consultado"] = det["consultado"].astype(bool)
    det.sort_index().to_csv(CACHE_JUGADORES)


def edad_jugador(info: dict | None) -> int | None:
    if not info:
        return None
    if info["nacimiento"] is not None:
        return edad_desde_ts(info["nacimiento"])
    return info["edad"]


def _guardar_jugador(cache: dict, jid: str, p: dict) -> None:
    """Guarda nacimiento y posición de un dict "player" de Sofascore
    (los de /team/{id}/players y /player/{id} traen ambos)."""
    info = cache.setdefault(jid, _nuevo())
    if p.get("dateOfBirthTimestamp") is not None:
        info["nacimiento"] = p["dateOfBirthTimestamp"]
    info["consultado"] = True
    if p.get("position") in POS_ESP:
        info["posicion"] = POS_ESP[p["position"]]


# ============================================================
# REQUESTS
# ============================================================
def bajar_estadisticas(s: Sofascore, league_id: int, season_id: int) -> pd.DataFrame:
    """Igual que Sofascore.scrape_player_league_stats, pero con el season_id fijo
    (ahorra la request a /seasons/) y con pausa entre páginas."""
    posiciones = s.get_positions(["Goalkeepers", "Defenders", "Midfielders", "Forwards"])
    resultados, offset = [], 0
    while True:
        r = sofa_get(
            f"{_API}/unique-tournament/{league_id}/season/{season_id}/statistics"
            f"?limit=100&offset={offset}&accumulation=total"
            f"&fields={s.concatenated_stat_names}&filters=position.in.{posiciones}"
        )
        resultados += r["results"]
        print(f"estadísticas: página {r['page']}/{r['pages']}")
        if r["page"] >= r["pages"] or r["pages"] == 0:
            break
        offset += 100

    df = pd.DataFrame(resultados)
    df["player id"] = df["player"].map(lambda p: p["id"])
    df["player"] = df["player"].map(lambda p: p["name"])
    df["team id"] = df["team"].map(lambda t: t["id"])
    df["team"] = df["team"].map(lambda t: t["name"])
    return df


def completar_cache(df: pd.DataFrame, cache: dict) -> None:
    """Pide a Sofascore solo lo que falta en la caché."""
    ids = df["player id"].astype(str)

    pendientes = [not cache.get(jid, {}).get("consultado")
                  or cache[jid].get("posicion") is None for jid in ids]
    sin_datos = df[pendientes]
    if sin_datos.empty:
        return
    print(f"jugadores sin edad o posición en caché: {len(sin_datos)}")

    # Si a un equipo le faltan varios jugadores, una request al plantel trae a
    # todos juntos: más barato que una por jugador.
    por_equipo = sin_datos.groupby("team id").size()
    equipos = por_equipo[por_equipo >= 2].index
    for i, tid in enumerate(equipos, 1):
        squad = sofa_get(f"{_API}/team/{tid}/players")
        for x in squad.get("players", []):
            _guardar_jugador(cache, str(x["player"]["id"]), x["player"])
        print(f"planteles: {i}/{len(equipos)}")

    # Los que quedan: transferidos a mitad de temporada o únicos faltantes de su equipo.
    sueltos = [jid for jid in sin_datos["player id"].astype(str)
               if not cache.get(jid, {}).get("consultado")
               or cache[jid].get("posicion") is None]
    for n, jid in enumerate(sueltos, 1):
        _guardar_jugador(cache, jid, sofa_get(f"{_API}/player/{jid}").get("player", {}))
        print(f"jugadores sueltos: {n}/{len(sueltos)}")


# ============================================================
# ACTUALIZACIÓN
# ============================================================
def actualizar() -> None:
    s = Sofascore()
    league_id = get_module_comps("SOFASCORE")[LEAGUE]["SOFASCORE"]
    season_id = SEASON_IDS[YEAR]

    # Si esto falla no se escribe nada: el CSV anterior queda intacto.
    df = bajar_estadisticas(s, league_id, season_id)

    keep = ["player id", "team id"] + [c for c in CAMPOS if c in df.columns]
    df = df[keep]
    df = df[df["minutesPlayed"] >= MIN_MINUTOS]
    df = df.sort_values("rating", ascending=False, na_position="last")

    # Posición y edad son extras: si Sofascore bloquea a mitad de camino se
    # guarda lo conseguido y el CSV se escribe igual (con huecos).
    cache = cargar_cache()
    bloqueo = None
    try:
        completar_cache(df, cache)
    except SofascoreBloqueo as e:
        bloqueo = e
    finally:
        guardar_cache(cache)

    ids = df["player id"].astype(str)
    df.insert(4, "posicion", ids.map(lambda jid: cache.get(jid, {}).get("posicion")))
    df.insert(5, "Edad", pd.to_numeric(
        ids.map(lambda jid: edad_jugador(cache.get(jid)))).astype("Int64"))

    # Calculo goles/90 >> goles x 90 / minutos jugados
    # ejemplo: Avalos >> 8 x 90 / 1350 = 0.53 goles / 90 minutos
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

    if bloqueo:
        print(
            f"\n⚠️  Sofascore bloqueó a mitad de camino ({bloqueo}).\n"
            f"   Las estadísticas están actualizadas, pero faltan "
            f"{df['Edad'].isna().sum()} edades y {df['posicion'].isna().sum()} posiciones.\n"
            "   Lo conseguido quedó en la caché: corré de nuevo en 24-48 hs y "
            "solo se va a pedir lo que falta."
        )


if __name__ == "__main__":
    forzar = "--actualizar" in sys.argv
    if os.path.exists(OUT) and not forzar:
        print(f"Ya hay datos del {ultima_actualizacion()}.")
        print("Corré 'python liga_arg.py --actualizar' para actualizarlos.")
    else:
        try:
            actualizar()
        except SofascoreBloqueo as e:
            print(
                f"\n❌ Sofascore bloqueó la descarga de estadísticas ({e}).\n"
                "   No se modificó ningún archivo. No reintentes enseguida: "
                "esperá 24-48 hs (insistir alarga el bloqueo)."
            )
            sys.exit(1)
