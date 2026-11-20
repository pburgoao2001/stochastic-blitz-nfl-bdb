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

Uso, desde la raíz del proyecto:
    ./.venv/Scripts/python.exe -m backend.analisis.preparar

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


if __name__ == "__main__":
    main()
