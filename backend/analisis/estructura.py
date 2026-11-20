"""Lector de estructura: ¿la defensa muestra el centro del campo cerrado o abierto en cada cuadro?

Entradas (de preparar.py): data/derivado/frames_def.pkl y data/derivado/jugadas_base.csv.
Salidas:
  data/derivado/estructura_cuadros.pkl  rasgos, P(cerrado), clase del modelo y de la regla por cuadro.
  data/derivado/validacion.json         validación cruzada, coeficientes, validación en semanas 7-8
                                        y distribución de la estructura en el snap.

Uso, desde la raíz del proyecto:
    ./.venv/Scripts/python.exe -m backend.analisis.estructura
    ./.venv/Scripts/python.exe -m backend.analisis.estructura --solo-entrenamiento
La segunda forma ajusta con las semanas 1-6, imprime el ajuste y se detiene sin evaluar
las semanas 7-8 y sin escribir archivos.

Pre-registro (fijado antes de ver las semanas 7-8; después de verlas no se reajusta nada):
  - Rasgos por cuadro con los defensores de profundidad >= 5 (ver rasgos_por_cuadro).
  - Verdad PFF: cerrado = Cover-1, Cover-3; abierto = Cover-2, 2-Man, Quarters, Cover-6;
    Cover-0, Bracket, Goal Line, Red Zone, Prevent y Miscellaneous quedan fuera.
  - Entrenamiento: semanas 1-6, t_pase >= 3.0 s, un cuadro por jugada a 2.0 s del snap.
  - Modelo: logit_irls de P(cerrado); l2 en {0.1, 1, 10} por validación cruzada de
    5 bloques por partido (log-loss).
  - Validación: semanas 7-8 con el mismo criterio. Exactitudes con IC 90% de Wilson y,
    además, con bootstrap por partido; AUC y Brier con bootstrap por partido.
  - Clases por cuadro: P >= 0.65 cerrado; P <= 0.35 abierto; en medio indeterminado.
  - Regla de comparación: cerrado si hay un defensor a >= 10 yd con |y - 26.65| <= 5;
    si no, abierto si hay 2 o más a >= 10 yd; si no, indeterminado.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .modelos import SEMILLA, auc, bootstrap_partidos, brier, intervalo, logit_irls, perdida_log, wilson

RAIZ = Path(__file__).resolve().parents[2]
DERIVADO = RAIZ / "data" / "derivado"

CENTRO = 26.65
RASGOS = ["n10", "n15", "dmid_campo", "dmid_balon", "separacion", "prof1"]
CERRADO = ["Cover-1", "Cover-3"]
ABIERTO = ["Cover-2", "2-Man", "Quarters", "Cover-6"]
SEMANAS_ENTRENAMIENTO = [1, 2, 3, 4, 5, 6]
SEMANAS_VALIDACION = [7, 8]
CUADRO_MUESTRA = 20      # 2.0 s después del snap, a 10 Hz
MIN_CUADROS_PASE = 30    # t_pase >= 3.0 s
L2_REJILLA = [0.1, 1.0, 10.0]
BLOQUES = 5
UMBRAL_CERRADO = 0.65
UMBRAL_ABIERTO = 0.35
B = 2000
JUGADA = ["gameId", "playId"]
CUADRO = JUGADA + ["frameId"]
CLASES = ["cerrado", "abierto", "indeterminado"]
GRUPOS_PFF = ["cerrado", "abierto", "fuera"]
METRICAS = ["modelo_exactitud_umbral_0.5", "modelo_auc", "modelo_brier",
            "modelo_3clases_decididas", "modelo_3clases_exactitud_en_decididas",
            "modelo_3clases_exactitud_en_todas",
            "regla_decididas", "regla_exactitud_en_decididas", "regla_exactitud_en_todas",
            "tasa_cerrado_pff"]


def rasgos_por_cuadro(frames: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Seis rasgos por cuadro con los defensores a profundidad >= 5 yd.

    n10, n15     cuántos están a >= 10 y a >= 15 yd.
    dmid_campo   distancia lateral mínima a y = 26.65 entre los de >= 10 yd (26.65 si no hay).
    dmid_balon   distancia lateral mínima a y_balon_snap entre los de >= 10 yd (26.65 si no hay).
    separacion   distancia lateral entre los dos más profundos (0 si hay menos de 2).
    prof1        profundidad del más profundo (5.0, el umbral del conjunto, si nadie llega a 5 yd).
    """
    r = frames.loc[frames["nflId"].isna(), CUADRO + ["t"]].set_index(CUADRO)  # el balón: 1 fila por cuadro
    d = frames[frames["nflId"].notna() & (frames["profundidad"] >= 5)]
    d10 = d[d["profundidad"] >= 10]
    r["n10"] = d10.groupby(CUADRO).size()
    r["n15"] = d[d["profundidad"] >= 15].groupby(CUADRO).size()
    lateral = d10.assign(dmid_campo=(d10["y"] - CENTRO).abs(),
                         dmid_balon=(d10["y"] - d10["y_balon_snap"]).abs())
    r = r.join(lateral.groupby(CUADRO)[["dmid_campo", "dmid_balon"]].min())
    orden = d.sort_values(CUADRO + ["profundidad", "nflId"], ascending=[True, True, True, False, True])
    rango = orden.groupby(CUADRO).cumcount().to_numpy()
    p1 = orden[rango == 0].set_index(CUADRO)
    p2 = orden[rango == 1].set_index(CUADRO)
    r["prof1"] = p1["profundidad"]
    r["separacion"] = (p1["y"] - p2["y"]).abs()
    respaldo = {"cuadros": int(len(r)),
                "sin_defensor_a_5yd__prof1_5": int(r["prof1"].isna().sum()),
                "menos_de_2_a_5yd__separacion_0": int(r["separacion"].isna().sum()),
                "sin_defensor_a_10yd__dmid_26.65": int(r["dmid_campo"].isna().sum())}
    r = r.fillna({"n10": 0, "n15": 0, "dmid_campo": CENTRO, "dmid_balon": CENTRO,
                  "separacion": 0.0, "prof1": 5.0})
    r = r.astype({c: float for c in RASGOS}).astype({"n10": int, "n15": int})
    return r.reset_index(), respaldo


def regla(r: pd.DataFrame) -> np.ndarray:
    """Regla de comparación: un defensor profundo en el centro = cerrado; dos profundos = abierto."""
    return np.select([r["dmid_campo"] <= 5, r["n10"] >= 2], ["cerrado", "abierto"], default="indeterminado")


def clase(p: np.ndarray) -> np.ndarray:
    """Clase final por cuadro a partir de P(cerrado)."""
    return np.select([p >= UMBRAL_CERRADO, p <= UMBRAL_ABIERTO], ["cerrado", "abierto"],
                     default="indeterminado")


def metricas(df: pd.DataFrame) -> np.ndarray:
    """Métricas de validación en el orden de METRICAS."""
    y = df["verdad"].to_numpy()
    p = df["p_cerrado"].to_numpy()
    real = np.where(y == 1, "cerrado", "abierto")
    m3, rg = df["estructura"].to_numpy(), df["regla"].to_numpy()
    dm, dr = m3 != "indeterminado", rg != "indeterminado"
    return np.array([
        np.mean((p >= 0.5) == (y == 1)), auc(y, p), brier(y, p),
        np.mean(dm), np.mean(m3[dm] == real[dm]) if dm.any() else np.nan, np.mean(m3 == real),
        np.mean(dr), np.mean(rg[dr] == real[dr]) if dr.any() else np.nan, np.mean(rg == real),
        np.mean(y == 1),
    ])


def conteos(df: pd.DataFrame) -> dict:
    """(aciertos, n) de cada métrica que es una proporción, para el intervalo de Wilson."""
    y = df["verdad"].to_numpy()
    real = np.where(y == 1, "cerrado", "abierto")
    m3, rg = df["estructura"].to_numpy(), df["regla"].to_numpy()
    dm, dr = m3 != "indeterminado", rg != "indeterminado"
    n = len(df)
    return {"modelo_exactitud_umbral_0.5": (int(((df["p_cerrado"].to_numpy() >= 0.5) == (y == 1)).sum()), n),
            "modelo_3clases_decididas": (int(dm.sum()), n),
            "modelo_3clases_exactitud_en_decididas": (int((m3[dm] == real[dm]).sum()), int(dm.sum())),
            "modelo_3clases_exactitud_en_todas": (int((m3 == real).sum()), n),
            "regla_decididas": (int(dr.sum()), n),
            "regla_exactitud_en_decididas": (int((rg[dr] == real[dr]).sum()), int(dr.sum())),
            "regla_exactitud_en_todas": (int((rg == real).sum()), n),
            "tasa_cerrado_pff": (int((y == 1).sum()), n)}


def num(v) -> float | None:
    """Número redondeado para JSON (None si no es finito)."""
    v = float(v)
    return round(v, 4) if math.isfinite(v) else None


def matriz(real: np.ndarray, pred: np.ndarray, columnas: list[str]) -> dict:
    t = pd.crosstab(real, pred).reindex(index=["cerrado", "abierto"], columns=columnas, fill_value=0)
    return {f: {c: int(t.loc[f, c]) for c in columnas} for f in t.index}


def main() -> None:
    lector = argparse.ArgumentParser(description="Lector de estructura (centro abierto o cerrado).")
    lector.add_argument("--solo-entrenamiento", action="store_true",
                        help="ajusta con semanas 1-6 y se detiene sin evaluar semanas 7-8")
    solo_entrenamiento = lector.parse_args().solo_entrenamiento

    frames = pd.read_pickle(DERIVADO / "frames_def.pkl")
    jug = pd.read_csv(DERIVADO / "jugadas_base.csv")
    R, respaldo = rasgos_por_cuadro(frames)
    R = R.merge(jug[JUGADA + ["week", "pff_passCoverage", "frame_snap", "frame_pase"]], on=JUGADA, how="left")
    R["rel"] = (R["frameId"] - R["frame_snap"]).astype(int)
    R["verdad"] = np.select([R["pff_passCoverage"].isin(CERRADO), R["pff_passCoverage"].isin(ABIERTO)],
                            [1, 0], default=-1)
    largo = (R["frame_pase"] - R["frame_snap"]) >= MIN_CUADROS_PASE

    jugadas = R.drop_duplicates(JUGADA)

    def embudo(semanas: list[int]) -> dict:
        p = jugadas[jugadas["week"].isin(semanas)]
        lg = (p["frame_pase"] - p["frame_snap"]) >= MIN_CUADROS_PASE
        et = p["verdad"] >= 0
        fuera = p.loc[lg & ~et, "pff_passCoverage"].value_counts()
        return {"jugadas": int(len(p)), "descartadas_t_pase_menor_a_3s": int((~lg).sum()),
                "descartadas_cobertura_fuera_de_la_verdad": {str(k): int(v) for k, v in fuera.items()},
                "incluidas": int((lg & et).sum())}

    # Ajuste: solo semanas 1-6.
    ent = R[(R["rel"] == CUADRO_MUESTRA) & largo & (R["verdad"] >= 0) & R["week"].isin(SEMANAS_ENTRENAMIENTO)]
    X, y = ent[RASGOS].to_numpy(float), ent["verdad"].to_numpy(float)
    juegos = np.random.default_rng(SEMILLA).permutation(np.sort(ent["gameId"].unique()))
    pliegue = ent["gameId"].map(pd.Series(np.arange(len(juegos)) % BLOQUES, index=juegos)).to_numpy()
    cv = {}
    for l2 in L2_REJILLA:
        fuera = np.empty(len(y))
        for k in range(BLOQUES):
            m = logit_irls(X[pliegue != k], y[pliegue != k], l2)
            fuera[pliegue == k] = m.predecir(X[pliegue == k])
        cv[l2] = {"log_loss": perdida_log(y, fuera), "auc": auc(y, fuera)}
    l2 = min(L2_REJILLA, key=lambda v: (cv[v]["log_loss"], -v))
    modelo = logit_irls(X, y, l2)
    p_ent = modelo.predecir(X)

    print(f"entrenamiento: {len(ent)} jugadas, {ent['gameId'].nunique()} partidos, "
          f"tasa cerrado {y.mean():.3f}; embudo {embudo(SEMANAS_ENTRENAMIENTO)}")
    print("rasgos (media) por verdad PFF en el cuadro de 2.0 s:")
    print(ent.groupby("verdad")[RASGOS].mean().rename(index={0: "abierto", 1: "cerrado"}).round(2).to_string())
    print("CV 5 bloques por partido:", {k: {m: round(v, 4) for m, v in d.items()} for k, d in cv.items()},
          "-> l2 =", l2)
    print("coeficientes estandarizados:", dict(zip(RASGOS, np.round(modelo.coef_estandarizados, 3))),
          f"| iteraciones {modelo.iteraciones}")
    print(f"en la muestra de entrenamiento: exactitud {np.mean((p_ent >= 0.5) == (y == 1)):.3f}, "
          f"AUC {auc(y, p_ent):.3f}, Brier {brier(y, p_ent):.3f}")
    print("respaldos de rasgos:", respaldo)
    if solo_entrenamiento:
        print("--solo-entrenamiento: no se evaluaron las semanas 7-8 ni se escribieron archivos.")
        return

    R["p_cerrado"] = modelo.predecir(R[RASGOS].to_numpy(float))
    R["estructura"] = clase(R["p_cerrado"].to_numpy())
    R["regla"] = regla(R)

    # Validación: semanas 7-8, una sola vez.
    val = R[(R["rel"] == CUADRO_MUESTRA) & largo & (R["verdad"] >= 0) & R["week"].isin(SEMANAS_VALIDACION)]
    punto = metricas(val)
    ic = intervalo(bootstrap_partidos(val, metricas, B, SEMILLA))
    cuentas = conteos(val)
    validacion = {}
    for i, nombre in enumerate(METRICAS):
        d = {"valor": num(punto[i]), "ic90_bootstrap_partido": [num(ic[0, i]), num(ic[1, i])]}
        if nombre in cuentas:
            x, n = cuentas[nombre]
            _, lo, hi = wilson(x, n)
            d.update({"aciertos": x, "n": n, "ic90_wilson": [num(lo), num(hi)]})
        else:
            d["n"] = int(len(val))
        validacion[nombre] = d
    real = np.where(val["verdad"] == 1, "cerrado", "abierto")
    confusion = {
        "modelo_umbral_0.5": matriz(real, np.where(val["p_cerrado"] >= 0.5, "cerrado", "abierto"),
                                    ["cerrado", "abierto"]),
        "modelo_3clases": matriz(real, val["estructura"].to_numpy(), CLASES),
        "regla": matriz(real, val["regla"].to_numpy(), CLASES),
    }

    # Estructura en el snap (todas las jugadas del análisis).
    snap = R[R["rel"] == 0].copy()
    snap["g"] = pd.Categorical(np.select([snap["verdad"] == 1, snap["verdad"] == 0], ["cerrado", "abierto"],
                                         default="fuera"), GRUPOS_PFF).codes
    snap["c"] = pd.Categorical(snap["estructura"], CLASES).codes

    def distribucion(df: pd.DataFrame) -> np.ndarray:
        tab = np.bincount(df["g"].to_numpy() * 3 + df["c"].to_numpy(), minlength=9).reshape(3, 3).astype(float)
        with np.errstate(invalid="ignore"):
            return np.concatenate([tab.sum(axis=0) / tab.sum(), (tab / tab.sum(axis=1, keepdims=True)).ravel()])

    d_punto = distribucion(snap)
    d_ic = intervalo(bootstrap_partidos(snap, distribucion, B, SEMILLA))
    tab = np.bincount(snap["g"].to_numpy() * 3 + snap["c"].to_numpy(), minlength=9).reshape(3, 3)
    en_snap = {"n_jugadas": int(len(snap)), "n_partidos": int(snap["gameId"].nunique()),
               "global": {c: {"n": int(tab[:, j].sum()), "pct": num(d_punto[j]),
                              "ic90_bootstrap_partido": [num(d_ic[0, j]), num(d_ic[1, j])]}
                          for j, c in enumerate(CLASES)},
               "por_verdad_pff": {g: {"n": int(tab[i].sum()),
                                      **{c: {"pct": num(d_punto[3 + 3 * i + j]),
                                             "ic90_bootstrap_partido": [num(d_ic[0, 3 + 3 * i + j]),
                                                                        num(d_ic[1, 3 + 3 * i + j])]}
                                         for j, c in enumerate(CLASES)}}
                                  for i, g in enumerate(GRUPOS_PFF)}}

    resultado = {
        "pre_registro": {"rasgos": RASGOS, "cerrado": CERRADO, "abierto": ABIERTO,
                         "semanas_entrenamiento": SEMANAS_ENTRENAMIENTO, "semanas_validacion": SEMANAS_VALIDACION,
                         "cuadro_muestra_s": CUADRO_MUESTRA / 10, "t_pase_minimo_s": MIN_CUADROS_PASE / 10,
                         "l2_rejilla": L2_REJILLA, "bloques_cv": BLOQUES,
                         "umbrales": {"cerrado": UMBRAL_CERRADO, "abierto": UMBRAL_ABIERTO},
                         "bootstrap": {"B": B, "semilla": SEMILLA, "unidad": "gameId"}},
        "respaldos_rasgos": respaldo,
        "entrenamiento": {"embudo": embudo(SEMANAS_ENTRENAMIENTO), "n": int(len(ent)),
                          "partidos": int(ent["gameId"].nunique()), "tasa_cerrado": num(y.mean()),
                          "cv": {str(k): {m: num(v) for m, v in d.items()} for k, d in cv.items()},
                          "l2_elegido": l2,
                          "intercepto": num(modelo.intercepto),
                          "coef": {r: num(c) for r, c in zip(RASGOS, modelo.coef)},
                          "coef_estandarizados": {r: num(c) for r, c in zip(RASGOS, modelo.coef_estandarizados)}},
        "validacion": {"embudo": embudo(SEMANAS_VALIDACION), "n": int(len(val)),
                       "partidos": int(val["gameId"].nunique()), "metricas": validacion,
                       "confusion": confusion},
        "estructura_en_snap": en_snap,
    }
    DERIVADO.mkdir(parents=True, exist_ok=True)
    (DERIVADO / "validacion.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    R[CUADRO + ["t"] + RASGOS + ["p_cerrado", "estructura", "regla"]].astype(
        {"estructura": "category", "regla": "category"}).to_pickle(DERIVADO / "estructura_cuadros.pkl")

    print(f"\nvalidacion semanas 7-8: {len(val)} jugadas, {val['gameId'].nunique()} partidos")
    for nombre, d in validacion.items():
        w = f" wilson {d['ic90_wilson']}" if "ic90_wilson" in d else ""
        print(f"  {nombre}: {d['valor']} (n={d['n']}){w} boot {d['ic90_bootstrap_partido']}")
    for nombre, t in confusion.items():
        print(f"  confusion {nombre}: {t}")
    print(f"\nestructura en el snap: {en_snap['n_jugadas']} jugadas")
    print("  global:", {c: (v["n"], v["pct"], v["ic90_bootstrap_partido"]) for c, v in en_snap["global"].items()})
    for g, v in en_snap["por_verdad_pff"].items():
        print(f"  pff {g} (n={v['n']}):", {c: (v[c]["pct"], v[c]["ic90_bootstrap_partido"]) for c in CLASES})


if __name__ == "__main__":
    main()
