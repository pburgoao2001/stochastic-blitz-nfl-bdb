"""Prepara los insumos de La Carrera Invisible a partir de data/ (solo lectura).

Lee cada archivo de data/ una sola vez y escribe en data/derivado/:
  frames_def.pkl            Defensores y balón, del snap al pase (inclusive), con la
                            ofensiva atacando hacia +x. Columnas: gameId, playId, nflId
                            (NA en el balón), frameId, t, x, y, profundidad, y_balon_snap.
  jugadas_base.csv          Una fila por jugada de plays.csv con su contexto, n_rushers,
                            frame_snap, frame_pase, t_pase, dist_endzone (110 - x normalizada
                            del balón en el snap) y flag_linea (|absoluteYardlineNumber - x cruda
                            del balón en el snap| > 2 yd; absoluteYardlineNumber está en x cruda).
  exclusiones_preparar.csv  Jugadas que no entran a frames_def y su motivo.
  preparar_resumen.json     Conteos y verificaciones de convenciones de la corrida.

Tubería completa, desde la raíz del proyecto:
    1. ./.venv/Scripts/python.exe -m backend.analisis.preparar            (cuadros: lo de arriba)
    2. ./.venv/Scripts/python.exe -m backend.analisis.estructura          (lector de estructura)
    3. ./.venv/Scripts/python.exe -m backend.analisis.preparar jugadas    (jugadas.csv; ver preparar_jugadas)
    4. ./.venv/Scripts/python.exe -m backend.analisis.preparar replays    (replays.json; ver preparar_replays)
    5. ./.venv/Scripts/python.exe -m backend.analisis.metricas            (revisión de la API)

Convenciones (cada corrida las verifica con los datos y las reporta):
  - 10 cuadros por segundo: t = (frameId - frame_snap) / 10.
  - Snap: primer cuadro con event == "ball_snap"; si no hay, "autoevent_ballsnap".
  - Pase: primer cuadro con event == "pass_forward"; si no hay, "autoevent_passforward".
  - Si playDirection == "left": x = 120 - x, y = 53.3 - y (la ofensiva ataca hacia +x).
  - Defensores: team == defensiveTeam de plays.csv. Balón: team == "football".
  - profundidad = x - x del balón en el cuadro del snap.
  - El análisis usa solo pases (passResult C, I, IN): sacks y scrambles con evento de
    pase quedan fuera y se reportan en exclusiones_preparar.csv.
No hay pasos aleatorios: dos corridas dan exactamente las mismas salidas.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data"
DERIVADO = DATOS / "derivado"

HZ = 10
LARGO = 120.0
ANCHO = 53.3
SNAP = ["ball_snap", "autoevent_ballsnap"]
PASE = ["pass_forward", "autoevent_passforward"]
ROLES_DEFENSA_PFF = ["Coverage", "Pass Rush"]
PASES_ANALISIS = ["C", "I", "IN"]
LINEA_GOL = 110.0
TOLERANCIA_LINEA = 2.0
DIST_MIN_UNIVERSO = 20.0
COLS_JUGADAS = ["gameId", "playId", "week", "defensiveTeam", "possessionTeam", "down", "yardsToGo",
                "dist_endzone", "offenseFormation", "pff_playAction", "passResult", "prePenaltyPlayResult",
                "foulName1", "pff_passCoverage", "n_rushers", "t_pase", "flag_linea", "p_snap",
                "muestra", "juega", "disfraz", "revela_t", "evento_revela", "ciega", "exito"]
CLAVE = ["gameId", "playId"]
COLS_TRACKING = ["gameId", "playId", "nflId", "frameId", "time", "team",
                 "playDirection", "x", "y", "s", "event"]
COLS_BASE = ["gameId", "playId", "week", "quarter", "defensiveTeam", "possessionTeam", "down",
             "yardsToGo", "absoluteYardlineNumber", "offenseFormation", "pff_playAction",
             "dropBackType", "passResult", "prePenaltyPlayResult", "foulName1",
             "pff_passCoverage", "n_rushers", "frame_snap", "frame_pase", "t_pase",
             "dist_endzone", "flag_linea"]
COLS_FRAMES = ["gameId", "playId", "nflId", "frameId", "t", "x", "y", "profundidad", "y_balon_snap"]


def procesar_partido(ruta: Path, equipos: pd.DataFrame) -> dict:
    """Lee un archivo de tracking una vez y devuelve sus piezas por jugada."""
    t = pd.read_csv(ruta, usecols=COLS_TRACKING)

    # Primer cuadro de cada evento de snap y de pase (nombre exacto).
    marcas = (t.loc[t["event"].isin(SNAP + PASE), CLAVE + ["frameId", "event"]]
              .groupby(CLAVE + ["event"])["frameId"].min()
              .unstack()
              .reindex(columns=SNAP + PASE))
    info = t.groupby(CLAVE).agg(frame_min=("frameId", "min"),
                                frame_max=("frameId", "max"),
                                n_direcciones=("playDirection", "nunique"))
    info = info.join(marcas)
    info["frame_snap"] = info["ball_snap"].fillna(info["autoevent_ballsnap"])
    info["frame_pase"] = info["pass_forward"].fillna(info["autoevent_passforward"])

    t = t.join(info[["frame_snap", "frame_pase"]].join(equipos), on=CLAVE)

    # Normaliza para que la ofensiva ataque hacia +x.
    izq = t["playDirection"].eq("left").to_numpy()
    t["x"] = np.where(izq, LARGO - t["x"], t["x"])
    t["y"] = np.where(izq, ANCHO - t["y"], t["y"])

    es_balon = t["team"].eq("football")
    es_def = t["team"].eq(t["defensiveTeam"])
    es_of = t["team"].eq(t["possessionTeam"])
    en_snap = t["frameId"].eq(t["frame_snap"])

    # Balón en todos los cuadros: sirve para verificar 10 Hz y el snap con su velocidad.
    balon = t.loc[es_balon, CLAVE + ["frameId", "time", "s"]]
    cuenta = balon.groupby(CLAVE + ["time"]).size().rename("n").reset_index()
    orden = cuenta.groupby(CLAVE).cumcount()
    total = cuenta.groupby(CLAVE)["n"].transform("size")
    interior = cuenta.loc[(orden > 0) & (orden < total - 1), "n"]

    # Diagnóstico en el cuadro del snap.
    bs = (t.loc[es_balon & en_snap, CLAVE + ["x", "y", "playDirection"]]
          .drop_duplicates(CLAVE).set_index(CLAVE))
    diag = pd.DataFrame({
        "x_balon_snap": bs["x"],
        "y_balon_snap": bs["y"],
        "x_crudo_balon_snap": np.where(bs["playDirection"].eq("left"), LARGO - bs["x"], bs["x"]),
    }, index=bs.index)
    sd, so = t.loc[es_def & en_snap], t.loc[es_of & en_snap]
    diag = diag.join(pd.DataFrame({
        "n_def_snap": sd.groupby(CLAVE)["nflId"].nunique(),
        "n_of_snap": so.groupby(CLAVE)["nflId"].nunique(),
        "x_med_def_snap": sd.groupby(CLAVE)["x"].median(),
    }), how="outer")

    ventana = t["frameId"].ge(t["frame_snap"]) & t["frameId"].le(t["frame_pase"])
    return {
        "info": info,
        "diag": diag,
        "balon": balon[CLAVE + ["frameId", "s"]],
        "def_snap": sd[CLAVE + ["nflId"]],
        "of_snap": so[CLAVE + ["nflId", "x"]],
        "frames": t.loc[ventana & (es_def | es_balon), CLAVE + ["nflId", "frameId", "x", "y"]],
        "n_filas": len(t),
        "n_sin_equipo": int((~(es_balon | es_def | es_of)).sum()),
        "direcciones": set(t["playDirection"].dropna().unique()),
        "cuadros_por_segundo": interior.value_counts(),
    }


def cuenta(s: pd.Series) -> dict:
    """value_counts como dict serializable a JSON."""
    return {str(k): int(v) for k, v in s.value_counts(dropna=False).sort_index().items()}


def rango(s: pd.Series) -> dict:
    """n y percentiles 0/5/50/95/100 de una serie (descriptivo, no es un intervalo de confianza)."""
    s = s.dropna()
    return {"n": int(s.size), **{f"p{int(q * 100)}": round(float(s.quantile(q)), 2)
                                 for q in (0, 0.05, 0.5, 0.95, 1)}}


def perfil_velocidad(balon: pd.DataFrame, ancla: pd.Series) -> dict:
    """Mediana de la velocidad del balón por cuadro relativo (-3..+3) a un cuadro ancla."""
    b = balon.join(ancla.dropna().rename("ancla"), on=CLAVE, how="inner")
    b = b.assign(rel=b["frameId"] - b["ancla"])
    b = b[b["rel"].between(-3, 3)]
    return {"n": int(b[CLAVE].drop_duplicates().shape[0]),
            **{str(int(k)): round(float(v), 2) for k, v in b.groupby("rel")["s"].median().items()}}


def main() -> None:
    t0 = time.perf_counter()
    games = pd.read_csv(DATOS / "games.csv", usecols=["gameId", "week"])
    plays = pd.read_csv(DATOS / "plays.csv")
    pff = pd.read_csv(DATOS / "pffScoutingData.csv", usecols=CLAVE + ["nflId", "pff_role"])
    equipos = plays.set_index(CLAVE)[["defensiveTeam", "possessionTeam"]]

    archivos = sorted((DATOS / "tracking").glob("tracking_*.csv"))
    partes = [procesar_partido(r, equipos) for r in archivos]
    t_lectura = time.perf_counter() - t0

    def juntar(k: str) -> pd.DataFrame:
        return pd.concat([p[k] for p in partes])

    info, diag, balon = juntar("info"), juntar("diag"), juntar("balon")
    def_snap, of_snap, frames = juntar("def_snap"), juntar("of_snap"), juntar("frames")

    # Una fila por jugada de plays.csv, con el motivo de exclusión (el primero que aplique).
    base = plays.merge(games, on="gameId", how="left").join(info, on=CLAVE).join(diag, on=CLAVE)
    reglas = [
        ("sin tracking", base["frame_min"].isna()),
        ("sin evento de snap", base["frame_snap"].isna()),
        ("sin evento de pase", base["frame_pase"].isna()),
        ("sack o scramble con evento de pase", ~base["passResult"].isin(PASES_ANALISIS)),
        ("pase no posterior al snap", ~(base["frame_pase"] > base["frame_snap"])),
        ("sin balon en el snap", base["x_balon_snap"].isna()),
        ("sin defensores en el snap", ~(base["n_def_snap"] > 0)),
    ]
    base["motivo"] = np.select([c.to_numpy() for _, c in reglas], [m for m, _ in reglas], default="")
    base["t_pase"] = (base["frame_pase"] - base["frame_snap"]) / HZ
    base["dist_endzone"] = LINEA_GOL - base["x_balon_snap"]
    base["flag_linea"] = (base["absoluteYardlineNumber"] - base["x_crudo_balon_snap"]).abs() > TOLERANCIA_LINEA
    rushers = pff[pff["pff_role"].eq("Pass Rush")].groupby(CLAVE).size().rename("n_rushers")
    base = base.join(rushers, on=CLAVE)
    base["n_rushers"] = base["n_rushers"].fillna(0).astype(int)

    ok = base[base["motivo"].eq("")].copy()
    validas = ok.set_index(CLAVE)[["frame_snap", "x_balon_snap", "y_balon_snap"]]
    frames = frames.join(validas, on=CLAVE, how="inner")
    frames["t"] = (frames["frameId"] - frames["frame_snap"]) / HZ
    frames["profundidad"] = frames["x"] - frames["x_balon_snap"]
    frames = (frames[COLS_FRAMES]
              .sort_values(CLAVE + ["frameId", "nflId"], na_position="last")
              .reset_index(drop=True)
              .astype({"nflId": "Int64", "frameId": "int32", "x": "float32", "y": "float32",
                       "profundidad": "float32", "y_balon_snap": "float32"}))

    # Verificaciones de convenciones.
    por_jugada = frames.groupby(CLAVE).agg(filas=("frameId", "size"), cuadros=("frameId", "nunique"))
    esperados = (ok.set_index(CLAVE)["frame_pase"] - ok.set_index(CLAVE)["frame_snap"] + 1)
    trk = def_snap.merge(ok[CLAVE], on=CLAVE).astype({"nflId": "int64"})
    pffd = pff.loc[pff["pff_role"].isin(ROLES_DEFENSA_PFF), CLAVE + ["nflId"]].merge(ok[CLAVE], on=CLAVE)
    cruce = trk.merge(pffd, on=CLAVE + ["nflId"], how="outer", indicator=True)
    n_pff_distinto = cruce.loc[cruce["_merge"] != "both", CLAVE].drop_duplicates().shape[0]
    bx = base.set_index(CLAVE)
    dif_snap = bx["ball_snap"] - bx["autoevent_ballsnap"]
    disputa = dif_snap.abs() > 2
    qb = pff.loc[pff["pff_role"].eq("Pass"), CLAVE + ["nflId"]]
    qbx = (of_snap.astype({"nflId": "int64"}).merge(qb, on=CLAVE + ["nflId"])
           .merge(ok[CLAVE + ["x_balon_snap"]], on=CLAVE))
    def_atras = ok.loc[~(ok["x_med_def_snap"] > ok["x_balon_snap"]), CLAVE]
    dif_los = (ok["absoluteYardlineNumber"] - ok["x_crudo_balon_snap"]).abs()
    segundos = pd.concat([p["cuadros_por_segundo"] for p in partes]).groupby(level=0).sum().sort_index()
    ver = {
        "diez_hz": {"segundos_completos_por_numero_de_cuadros":
                    {str(int(k)): int(v) for k, v in segundos.items()}},
        "direccion": {"valores": sorted(set().union(*(p["direcciones"] for p in partes))),
                      "jugadas_con_mas_de_una": int((base["n_direcciones"] > 1).sum())},
        "normalizacion_en_snap": {
            "n": len(ok),
            "mediana_defensa_delante_del_balon": len(ok) - len(def_atras),
            "jugadas_defensa_no_delante": def_atras.to_numpy().tolist()[:10],
            "qb_pff_encontrado": len(qbx),
            "qb_detras_del_balon": int((qbx["x"] < qbx["x_balon_snap"]).sum())},
        "equipos": {"filas_sin_equipo_reconocido": sum(p["n_sin_equipo"] for p in partes),
                    "defensores_en_snap": cuenta(ok["n_def_snap"].astype(int)),
                    "ofensivos_en_snap": cuenta(ok["n_of_snap"].astype(int)),
                    "jugadas_mismos_defensores_que_pff": len(ok) - n_pff_distinto},
        "frames_def": {"filas_por_cuadro": cuenta(por_jugada["filas"] / por_jugada["cuadros"]),
                       "jugadas_con_cuadros_faltantes": int((por_jugada["cuadros"] != esperados.reindex(por_jugada.index)).sum())},
        "snap": {"fuente": cuenta(pd.Series(np.where(ok["ball_snap"].notna(), "ball_snap", "autoevent_ballsnap"))),
                 "jugadas_con_ambos_eventos": int(dif_snap.notna().sum()),
                 "ball_snap_menos_autoevent": rango(dif_snap),
                 "ambos_con_diferencia_mayor_a_2_cuadros": int(disputa.sum()),
                 "vel_balon_mediana_rel_snap_elegido": perfil_velocidad(balon, ok.set_index(CLAVE)["frame_snap"]),
                 "diferencia_mayor_2_vel_rel_ball_snap": perfil_velocidad(balon, bx.loc[disputa, "ball_snap"]),
                 "diferencia_mayor_2_vel_rel_autoevent": perfil_velocidad(balon, bx.loc[disputa, "autoevent_ballsnap"])},
        "pase": {"fuente": cuenta(pd.Series(np.where(ok["pass_forward"].notna(), "pass_forward", "autoevent_passforward"))),
                 "passResult_incluidas": cuenta(ok["passResult"]),
                 "t_pase_segundos": rango(ok["t_pase"])},
        "absoluteYardlineNumber": {
            "abs_dif_vs_x_crudo_balon_snap": rango(dif_los),
            "jugadas_dif_mayor_2_yardas": int((dif_los > 2).sum()),
            "abs_dif_vs_x_normalizado_balon_snap": rango((ok["absoluteYardlineNumber"] - ok["x_balon_snap"]).abs())},
        "n_rushers": cuenta(base["n_rushers"]),
    }

    excl = base.loc[base["motivo"].ne(""), CLAVE + ["passResult", "motivo"]]
    exclusiones = {m: {"n": int((excl["motivo"] == m).sum()),
                       "passResult": cuenta(excl.loc[excl["motivo"] == m, "passResult"])}
                   for m, _ in reglas if (excl["motivo"] == m).any()}

    DERIVADO.mkdir(parents=True, exist_ok=True)
    frames.to_pickle(DERIVADO / "frames_def.pkl")
    salida = base[COLS_BASE].astype({"frame_snap": "Int64", "frame_pase": "Int64"})
    salida.to_csv(DERIVADO / "jugadas_base.csv", index=False)
    excl.to_csv(DERIVADO / "exclusiones_preparar.csv", index=False)
    resumen = {
        "entradas": {"archivos_tracking": len(archivos),
                     "filas_tracking": sum(p["n_filas"] for p in partes),
                     "jugadas_plays": len(plays)},
        "salidas": {"frames_def_filas": len(frames), "frames_def_jugadas": len(ok),
                    "jugadas_base_filas": len(salida), "jugadas_descartadas": len(excl)},
        "exclusiones": exclusiones,
        "verificaciones": ver,
    }
    (DERIVADO / "preparar_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    t_total = time.perf_counter() - t0
    print(f"tracking: {len(archivos)} archivos, {resumen['entradas']['filas_tracking']:,} filas leidas una vez")
    print(f"frames_def.pkl: {len(frames):,} filas, {len(ok):,} jugadas")
    print(f"jugadas_base.csv: {len(salida):,} filas | descartadas de frames_def: {len(excl):,} | "
          f"flag_linea en jugadas del analisis: {int(ok['flag_linea'].sum())}")
    for m, d in exclusiones.items():
        print(f"  - {m}: {d['n']} {d['passResult']}")
    print(json.dumps(ver, ensure_ascii=False))
    print(f"tiempo: lectura {t_lectura:.1f} s, total {t_total:.1f} s")


def preparar_jugadas() -> None:
    """Etapa 3, después de estructura.py: data/derivado/jugadas.csv, una fila por jugada del universo.

    Universo de la carrera: jugadas del análisis con dist_endzone >= 20 y cobertura con etiqueta
    (cerrado: Cover-1/Cover-3; abierto: Cover-2/2-Man/Quarters/Cover-6).
      muestra       clase del lector en el snap (cerrado, abierto o indeterminado); p_snap = P(cerrado).
      juega         clase según PFF.
      disfraz       1 si muestra != juega; vacío si el lector no decide en el snap.
      revela_t      con disfraz: primer instante desde el cual la clase del lector coincide con juega y
                    ya no cambia hasta el pase. evento_revela = 1 si ese instante es anterior al cuadro
                    del pase; si no, revela_t = t_pase y evento_revela = 0 (censurada).
                    Sin disfraz: revela_t = 0 y evento_revela = 1.
      ciega         1 si hay disfraz y evento_revela = 0.
      exito         vacío si hubo castigo (foulName1). 1.º down: prePenaltyPlayResult >= 0.4*yardsToGo;
                    2.º: >= 0.6*yardsToGo; 3.º y 4.º: >= yardsToGo. Intercepción (o sack) = 0.
    También escribe validacion_jugadas.csv (las jugadas de validación del lector, para Rogan-Gladen)
    y jugadas_resumen.json (embudo y conteos).
    """
    from . import estructura as E

    t0 = time.perf_counter()
    base = pd.read_csv(DERIVADO / "jugadas_base.csv")
    cuadros = pd.read_pickle(DERIVADO / "estructura_cuadros.pkl")
    cuadros = cuadros.merge(base[CLAVE + ["frame_snap", "frame_pase", "week", "pff_passCoverage"]], on=CLAVE)
    cuadros["rel"] = (cuadros["frameId"] - cuadros["frame_snap"]).astype(int)

    def clase_pff(cobertura: pd.Series) -> np.ndarray:
        return np.select([cobertura.isin(E.CERRADO), cobertura.isin(E.ABIERTO)], ["cerrado", "abierto"], default="")

    # Universo de la carrera.
    j = base.merge(cuadros[CLAVE].drop_duplicates(), on=CLAVE)
    j["juega"] = clase_pff(j["pff_passCoverage"])
    reglas = [(f"dist_endzone < {DIST_MIN_UNIVERSO:g}", j["dist_endzone"] < DIST_MIN_UNIVERSO),
              ("cobertura sin etiqueta", j["juega"].eq(""))]
    j["motivo"] = np.select([c.to_numpy() for _, c in reglas], [m for m, _ in reglas], default="")
    fuera = j[j["motivo"].ne("")]
    u = j[j["motivo"].eq("")].drop(columns="motivo").reset_index(drop=True)

    # Muestra en el snap y disfraz (solo si el lector decide).
    snap = cuadros.loc[cuadros["rel"] == 0, CLAVE + ["p_cerrado", "estructura"]].rename(
        columns={"p_cerrado": "p_snap", "estructura": "muestra"})
    u = u.merge(snap, on=CLAVE, how="left")
    u["muestra"] = u["muestra"].astype(str)
    decide = u["muestra"].ne("indeterminado")
    u["disfraz"] = u["muestra"].ne(u["juega"]).astype("Int64").where(decide)

    # Revelación: último cuadro (snap..pase) en que la clase del lector no coincide con juega.
    c = cuadros.merge(u[CLAVE + ["juega"]], on=CLAVE)
    ultimo = (c.loc[c["estructura"].astype(str).ne(c["juega"])].groupby(CLAVE)["frameId"].max()
              .rename("ultimo_no_coincide"))
    u = u.join(ultimo, on=CLAVE)
    primero_estable = u["ultimo_no_coincide"] + 1
    dis = u["disfraz"].eq(1).fillna(False).to_numpy(bool)
    sin = u["disfraz"].eq(0).fillna(False).to_numpy(bool)
    assert u.loc[dis, "ultimo_no_coincide"].notna().all(), "una jugada con disfraz debe no coincidir en el snap"
    antes = (primero_estable < u["frame_pase"]).to_numpy(bool)
    revela_t = np.full(len(u), np.nan)
    revela_t[dis & antes] = ((primero_estable - u["frame_snap"]) / HZ).to_numpy()[dis & antes]
    revela_t[dis & ~antes] = u["t_pase"].to_numpy()[dis & ~antes]
    revela_t[sin] = 0.0
    u["revela_t"] = np.round(revela_t, 1)
    u["evento_revela"] = pd.array(np.where(dis, antes, sin).astype(int), dtype="Int64")
    u["ciega"] = pd.array((dis & ~antes).astype(int), dtype="Int64")
    u.loc[~(dis | sin), ["evento_revela", "ciega"]] = pd.NA

    # Éxito (vacío si hubo castigo).
    umbral = np.select([u["down"].eq(1), u["down"].eq(2)], [0.4 * u["yardsToGo"], 0.6 * u["yardsToGo"]],
                       default=u["yardsToGo"])
    logro = (u["prePenaltyPlayResult"] >= umbral) & ~u["passResult"].isin(["S", "IN"])
    u["exito"] = logro.astype("Int64").where(u["foulName1"].isna())

    # Jugadas de validación del lector (mismo criterio pre-registrado), para sensibilidad/especificidad.
    v = cuadros[(cuadros["rel"] == E.CUADRO_MUESTRA)
                & ((cuadros["frame_pase"] - cuadros["frame_snap"]) >= E.MIN_CUADROS_PASE)
                & cuadros["week"].isin(E.SEMANAS_VALIDACION)].copy()
    v["verdad"] = clase_pff(v["pff_passCoverage"])
    v = v.loc[v["verdad"].ne(""), CLAVE + ["verdad", "estructura", "p_cerrado"]]
    registro = json.loads((DERIVADO / "validacion.json").read_text(encoding="utf-8"))
    conf = registro["validacion"]["confusion"]["modelo_3clases"]
    propia = pd.crosstab(v["verdad"], v["estructura"].astype(str))
    assert len(v) == registro["validacion"]["n"], "validacion_jugadas no coincide con validacion.json"
    assert all(int(propia.loc[f, k]) == conf[f][k] for f in conf for k in conf[f]), "confusión distinta"

    DERIVADO.mkdir(parents=True, exist_ok=True)
    u[COLS_JUGADAS].to_csv(DERIVADO / "jugadas.csv", index=False)
    v.to_csv(DERIVADO / "validacion_jugadas.csv", index=False)
    resumen = {
        "universo": {"jugadas_analisis": int(len(j)),
                     "excluidas": {m: int((fuera["motivo"] == m).sum()) for m, _ in reglas},
                     "cobertura_sin_etiqueta_por_tipo": {str(k): int(n) for k, n in
                                                         fuera.loc[fuera["motivo"] == "cobertura sin etiqueta",
                                                                   "pff_passCoverage"].value_counts().items()},
                     "incluidas": int(len(u))},
        "muestra_en_snap": {str(k): int(n) for k, n in u["muestra"].value_counts().items()},
        "decididas": int(decide.sum()), "con_disfraz": int(dis.sum()), "sin_disfraz": int(sin.sum()),
        "disfraz_revelado_antes_del_pase": int((dis & antes).sum()), "ciegas": int((dis & ~antes).sum()),
        "exito": {"con_valor": int(u["exito"].notna().sum()), "excluidas_por_castigo": int(u["exito"].isna().sum())},
        "validacion_jugadas": int(len(v)),
    }
    (DERIVADO / "jugadas_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2),
                                                   encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False))
    print(f"tiempo: {time.perf_counter() - t0:.1f} s")


CLASES_REPLAY = ["a: disfrazada (muestra cerrado), lanzó antes de la revelación",
                 "b: disfrazada (muestra cerrado), lanzó después de la revelación", "c: honesta"]
RANGOS_T_REPLAY = [(2.5, 4.0), (2.0, 4.5)]  # el segundo solo si una clase queda vacía con el primero
SUFIJO_REPLAY = " · ejemplo ilustrativo elegido por regla"


def _cuadros_replay(fila: pd.Series, estructura: dict) -> list[dict] | None:
    """Cuadros del snap al pase (10 Hz) de una jugada, o None si falta algún cuadro o jugador.

    Coordenadas normalizadas (ofensiva hacia +x), x relativa a la línea (x - x del balón en el snap),
    redondeo a 0.1 yd; jugadores ordenados por nflId para que cada índice sea el mismo jugador.
    """
    gid, pid, snap, pase = int(fila["gameId"]), int(fila["playId"]), int(fila["frame_snap"]), int(fila["frame_pase"])
    t = pd.read_csv(DATOS / "tracking" / f"tracking_{gid}.csv",
                    usecols=["playId", "nflId", "frameId", "team", "playDirection", "x", "y"])
    t = t[(t["playId"] == pid) & t["frameId"].between(snap, pase)].copy()
    izq = t["playDirection"].eq("left").to_numpy()
    t["x"] = np.where(izq, LARGO - t["x"], t["x"])
    t["y"] = np.where(izq, ANCHO - t["y"], t["y"])
    bal = t[t["team"] == "football"].set_index("frameId")
    if snap not in bal.index:
        return None
    x0 = float(bal.loc[snap, "x"])
    lado = {"def": fila["defensiveTeam"], "of": fila["possessionTeam"]}
    salida = []
    for f in range(snap, pase + 1):
        c = t[t["frameId"] == f].sort_values("nflId")
        grupos = {k: c[c["team"] == v] for k, v in lado.items()}
        if f not in bal.index or len(c) != 23 or any(len(g) != 11 for g in grupos.values()) or f not in estructura:
            return None
        par = lambda x, y: [round(float(x) - x0, 1) + 0.0, round(float(y), 1) + 0.0]
        salida.append({"t": round((f - snap) / HZ, 1),
                       "def": [par(x, y) for x, y in zip(grupos["def"]["x"], grupos["def"]["y"])],
                       "of": [par(x, y) for x, y in zip(grupos["of"]["x"], grupos["of"]["y"])],
                       "balon": par(bal.loc[f, "x"], bal.loc[f, "y"]),
                       "estructura": estructura[f]})
    return salida


def preparar_replays() -> None:
    """Etapa 4: data/derivado/replays.json con 3 jugadas elegidas por regla (docs/replays.md).

    Clases: a) disfraz con muestra cerrado y lanzó antes de la revelación (ciega); b) disfraz con muestra
    cerrado y lanzó después de revelarse; c) honesta (sin disfraz). En las tres se excluyen las jugadas con
    castigo (foulName1). En cada clase, la de mayor |p_snap - 0.5| con 2.5 <= t_pase <= 4.0 s y sin cuadros
    faltantes; si la clase queda vacía, 2.0 <= t_pase <= 4.5 s. Desempate por gameId y playId.
    La forma es la de REPLAYS en backend/mocks.py.
    """
    j = pd.read_csv(DERIVADO / "jugadas.csv").merge(
        pd.read_csv(DERIVADO / "jugadas_base.csv", usecols=CLAVE + ["frame_snap", "frame_pase"]), on=CLAVE)
    descripciones = pd.read_csv(DATOS / "plays.csv", usecols=CLAVE + ["playDescription"]).set_index(CLAVE)
    cuadros = pd.read_pickle(DERIVADO / "estructura_cuadros.pkl")[CLAVE + ["frameId", "estructura"]]
    sin_castigo = j["foulName1"].isna()
    cerrado = j["muestra"] == "cerrado"
    mascaras = [(j["disfraz"] == 1) & (j["ciega"] == 1) & cerrado & sin_castigo,
                (j["disfraz"] == 1) & (j["evento_revela"] == 1) & cerrado & sin_castigo,
                (j["disfraz"] == 0) & sin_castigo]
    replays, elegidas = [], []
    for clase, m in zip(CLASES_REPLAY, mascaras):
        hallada = None
        for lo, hi in RANGOS_T_REPLAY:
            cand = (j[m & j["t_pase"].between(lo, hi)].assign(margen=lambda d: (d["p_snap"] - 0.5).abs())
                    .sort_values(["margen", "gameId", "playId"], ascending=[False, True, True]))
            for _, fila in cand.iterrows():
                est = cuadros[(cuadros["gameId"] == fila["gameId"]) & (cuadros["playId"] == fila["playId"])]
                frames = _cuadros_replay(fila, dict(zip(est["frameId"].astype(int), est["estructura"].astype(str))))
                if frames is not None:
                    hallada = (fila, frames, cand, (lo, hi))
                    break
            if hallada is not None:
                break
        assert hallada is not None, f"clase vacía incluso con t_pase 2.0-4.5 s: {clase}"
        fila, frames, cand, rango = hallada
        revela = None if clase.startswith("a") else float(fila["revela_t"])
        texto = str(descripciones.loc[(int(fila["gameId"]), int(fila["playId"])), "playDescription"])[:140]
        altos = "un alto" if fila["juega"] == "cerrado" else "dos altos"
        lectura = f" · muestra {fila['muestra']} → juega {fila['pff_passCoverage']} ({altos}, PFF)"
        replays.append({"gameId": str(int(fila["gameId"])), "playId": str(int(fila["playId"])),
                        "descripcion": texto + SUFIJO_REPLAY + lectura, "frames": frames,
                        "eventos": {"snap": 0.0, "revela": revela, "lanza": float(fila["t_pase"])}})
        elegidas.append({"clase": clase, "gameId": int(fila["gameId"]), "playId": int(fila["playId"]),
                         "defensa": fila["defensiveTeam"], "ataque": fila["possessionTeam"],
                         "p_snap": round(float(fila["p_snap"]), 4), "muestra": fila["muestra"],
                         "juega": fila["juega"], "cobertura": fila["pff_passCoverage"],
                         "t_pase": float(fila["t_pase"]), "revela": revela, "cuadros": len(frames),
                         "candidatas": int(len(cand)), "rango_t_pase": list(rango),
                         "rango_ampliado": rango != RANGOS_T_REPLAY[0]})
    a, b = replays[0]["eventos"], replays[1]["eventos"]
    assert a["revela"] is None or a["revela"] > a["lanza"], "clase a: revela debe ser null o > lanza"
    assert b["revela"] is not None and b["revela"] < b["lanza"], "clase b: revela debe ser < lanza"
    texto = json.dumps(replays, ensure_ascii=False, separators=(",", ":"))
    (DERIVADO / "replays.json").write_text(texto, encoding="utf-8")
    print(json.dumps(elegidas, ensure_ascii=False, indent=1))
    print(f"replays.json: {len(replays)} jugadas, {len(texto.encode('utf-8')) / 1024:.1f} KB")


if __name__ == "__main__":
    import argparse

    lector = argparse.ArgumentParser(description="Prepara los insumos de La Carrera Invisible.")
    lector.add_argument("etapa", nargs="?", default="cuadros", choices=["cuadros", "jugadas", "replays"],
                        help="cuadros (por omisión), jugadas (después de estructura.py) o replays (al final)")
    etapa = lector.parse_args().etapa
    {"cuadros": main, "jugadas": preparar_jugadas, "replays": preparar_replays}[etapa]()
