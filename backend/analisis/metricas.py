"""Métricas de La Carrera Invisible con la forma exacta del contrato de la API (.kiro/specs, design.md).

Solo lee archivos versionados de data/derivado/ (jugadas.csv, validacion_jugadas.csv, validacion.json),
así que la API las calcula al arrancar sin escribir en disco.
  resumen()                       GET /api/resumen
  equipos()                       GET /api/equipos
  rival(equipo, down, distancia)  GET /api/rival
Revisión (imprime resumen, top 5, chequeos y sensibilidad), desde la raíz:
    ./.venv/Scripts/python.exe -m backend.analisis.metricas

Definiciones (ver docs/decisiones.md):
  - Universo: jugadas de jugadas.csv (dist_endzone >= 20 y cobertura con etiqueta).
  - Decididas: las del universo en que el lector decide en el snap. ID observado = fracción con disfraz.
  - ID corregido: Rogan-Gladen dentro de cada clase de PFF, con la sensibilidad y especificidad del
    lector de 3 clases cuando decide (validación, semanas 7-8). El bootstrap remuestrea partidos del
    universo y, por separado, partidos de la validación.
  - efecto: efecto marginal promedio de ciega sobre exito, en puntos porcentuales, entre jugadas con disfraz.
    El error del lector depende de t_pase, así que el sesgo del efecto puede ir en cualquier dirección.
  - carrera: fracción de jugadas con disfraz en que el QB lanzó antes de la revelación (ciega).
"""
from __future__ import annotations

import json
import math
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .modelos import SEMILLA, betabinom_eb, bootstrap_partidos, intervalo, kaplan_meier, logit_irls, wilson

RAIZ = Path(__file__).resolve().parents[2]
DERIVADO = RAIZ / "data" / "derivado"
B = 300
L2_EFECTO = 1e-6  # solo estabilidad numérica (una columna puede quedar vacía en una réplica)
REJILLA_T = np.round(np.arange(0, 50 + 1) / 10, 1)  # 0.0 a 5.0 s cada 0.1 s
CORTES_T = [2.0, 2.5, 3.0]
TRAMOS_T = ["<2.0", "2.0-2.5", "2.5-3.0", ">=3.0"]
TRAMOS_DIST = ["1-3", "4-6", "7+"]
MIN_DISFRAZ_EQUIPO = 20
MUESTRA_CHICA = 10  # en rival(): por debajo de esto la frase avisa que la estimación se acerca a la liga
MIN_LIGA = 30       # en rival(): jugadas mínimas de la celda de la liga hacia la que se encoge
SORTEOS = 20000
NODOS_SANKEY = ["Muestra cerrada", "Muestra abierta", "Sin disfraz", "Disfraz leído a tiempo", "A ciegas",
                "Éxito", "Fracaso"]


def _num(v, d: int = 4):
    """Número para JSON: redondeado, o None si falta o no es finito."""
    if v is None:
        return None
    v = float(v)
    return round(v, d) if math.isfinite(v) else None


def _ic(lo, hi, d: int = 4) -> list:
    return [_num(lo, d), _num(hi, d)]


@lru_cache(maxsize=1)
def _datos() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    j = pd.read_csv(DERIVADO / "jugadas.csv")
    j["tramo_t"] = pd.cut(j["t_pase"], [-np.inf] + CORTES_T + [np.inf], right=False, labels=TRAMOS_T).astype(str)
    j["tramo_dist"] = pd.cut(j["yardsToGo"], [0, 3, 6, np.inf], labels=TRAMOS_DIST).astype(str)
    j["zona"] = np.select([j["dist_endzone"] > 50, j["dist_endzone"] > 20], ["propia", "medio"], default="roja")
    v = pd.read_csv(DERIVADO / "validacion_jugadas.csv")
    registro = json.loads((DERIVADO / "validacion.json").read_text(encoding="utf-8"))
    return j, v, registro


def _decididas(j: pd.DataFrame) -> pd.DataFrame:
    return j[j["disfraz"].notna()]


def _con_disfraz(j: pd.DataFrame) -> pd.DataFrame:
    return j[j["disfraz"] == 1]


# --- Índice de disfraz -------------------------------------------------------------------------

def _sens_espec(v: pd.DataFrame) -> np.ndarray:
    """Sensibilidad (cerrado) y especificidad (abierto) del lector de 3 clases cuando decide."""
    d = v[v["estructura"] != "indeterminado"]
    se = (d.loc[d["verdad"] == "cerrado", "estructura"] == "cerrado").mean()
    sp = (d.loc[d["verdad"] == "abierto", "estructura"] == "abierto").mean()
    return np.array([se, sp], float)


def _tasas_por_clase(d: pd.DataFrame) -> np.ndarray:
    """Tasa observada de disfraz dentro de cada clase de PFF y sus tamaños."""
    c, a = d[d["juega"] == "cerrado"], d[d["juega"] == "abierto"]
    return np.array([c["disfraz"].mean(), a["disfraz"].mean(), len(c), len(a)], float)


def _rogan_gladen(tasas: np.ndarray, se: float, sp: float) -> np.ndarray:
    """ID corregido y su valor dentro de cada clase, recortados a [0, 1].

    Juega cerrado: disfraz = leer abierto -> pi = (p + se - 1) / (se + sp - 1).
    Juega abierto: disfraz = leer cerrado -> pi = (p + sp - 1) / (se + sp - 1).
    """
    pc, pa, nc, na = tasas
    den = se + sp - 1
    if not den > 0.05:
        return np.array([np.nan, np.nan, np.nan])
    pi_c = min(max((pc + se - 1) / den, 0.0), 1.0)
    pi_a = min(max((pa + sp - 1) / den, 0.0), 1.0)
    return np.array([(pi_c * nc + pi_a * na) / (nc + na), pi_c, pi_a])


def indice_disfraz() -> dict:
    """ID observado y corregido (Rogan-Gladen), con IC 90% por bootstrap por partido."""
    j, v, _ = _datos()
    d = _decididas(j)
    obs_rep = bootstrap_partidos(d, lambda x: x["disfraz"].mean(), B, SEMILLA)
    tasas = _tasas_por_clase(d)
    se, sp = _sens_espec(v)
    corr = _rogan_gladen(tasas, se, sp)
    t_rep = bootstrap_partidos(d, _tasas_por_clase, B, SEMILLA)
    s_rep = bootstrap_partidos(v, _sens_espec, B, SEMILLA + 1)
    c_rep = np.array([_rogan_gladen(t_rep[b], s_rep[b, 0], s_rep[b, 1]) for b in range(B)])
    return {"n": int(len(d)), "observado": float(d["disfraz"].mean()), "observado_ic90": intervalo(obs_rep),
            "corregido": float(corr[0]), "corregido_ic90": intervalo(c_rep[:, 0]),
            "por_clase": {"juega_cerrado": {"n": int(tasas[2]), "observado": float(tasas[0]),
                                            "observado_ic90": intervalo(t_rep[:, 0]).tolist(),
                                            "corregido": float(corr[1]), "corregido_ic90": intervalo(c_rep[:, 1]).tolist()},
                          "juega_abierto": {"n": int(tasas[3]), "observado": float(tasas[1]),
                                            "observado_ic90": intervalo(t_rep[:, 1]).tolist(),
                                            "corregido": float(corr[2]), "corregido_ic90": intervalo(c_rep[:, 2]).tolist()}},
            "sensibilidad": float(se), "especificidad": float(sp),
            "replicas_invalidas": int(np.isnan(c_rep[:, 0]).sum())}


# --- Efecto de lanzar a ciegas ------------------------------------------------------------------

def _diseno(d: pd.DataFrame, columnas: list[str] | None = None) -> tuple[np.ndarray, list[str]]:
    """Matriz con ciega en la columna 0 y los controles (categorías de referencia: <2.0 s, 1.º down,
    1-3 yardas, zona propia)."""
    X = pd.DataFrame({"ciega": d["ciega"].astype(float)}, index=d.index)
    for k in TRAMOS_T[1:]:
        X[f"t_pase {k}"] = (d["tramo_t"] == k).astype(float)
    for k in (2, 3, 4):
        X[f"down {k}"] = (d["down"] == k).astype(float)
    for k in TRAMOS_DIST[1:]:
        X[f"distancia {k}"] = (d["tramo_dist"] == k).astype(float)
    for k in ("medio", "roja"):
        X[f"zona {k}"] = (d["zona"] == k).astype(float)
    X["n_rushers"] = d["n_rushers"].astype(float)
    X["shotgun"] = (d["offenseFormation"] == "SHOTGUN").astype(float)
    X["play_action"] = d["pff_playAction"].astype(float)
    if columnas is None:  # fuera las columnas constantes en los datos completos (p. ej., zona roja vacía)
        columnas = ["ciega"] + [c for c in X.columns[1:] if X[c].nunique() > 1]
    return X[columnas].to_numpy(float), columnas


def _efecto_logit(d: pd.DataFrame, columnas: list[str]) -> np.ndarray:
    """[efecto marginal promedio de ciega en pp, convergió (1/0)]."""
    X, _ = _diseno(d, columnas)
    m = logit_irls(X, d["exito"].to_numpy(float), L2_EFECTO)
    X1, X0 = X.copy(), X.copy()
    X1[:, 0], X0[:, 0] = 1.0, 0.0
    return np.array([100 * np.mean(m.predecir(X1) - m.predecir(X0)), float(m.convergio)])


def _efecto_mh(d: pd.DataFrame) -> float:
    """Diferencia de riesgos de Mantel-Haenszel (ciega - leída) por tramos de t_pase, en pp."""
    num = den = 0.0
    for _, s in d.groupby("tramo_t"):
        c1, c0 = s[s["ciega"] == 1], s[s["ciega"] == 0]
        n1, n0 = len(c1), len(c0)
        if n1 and n0:
            num += (c1["exito"].sum() * n0 - c0["exito"].sum() * n1) / (n1 + n0)
            den += n1 * n0 / (n1 + n0)
    return 100 * num / den if den else math.nan


def _muestra_efecto(j: pd.DataFrame) -> pd.DataFrame:
    d = _con_disfraz(j)
    return d[d["exito"].notna()]


def efecto_ciega(j: pd.DataFrame | None = None) -> dict:
    """Efecto principal con su método, IC 90% (bootstrap por partido, B=300) y diagnósticos."""
    if j is None:
        j = _datos()[0]
    d = _muestra_efecto(j)
    _, columnas = _diseno(d)
    valor, convergio = _efecto_logit(d, columnas)
    if convergio:
        rep = bootstrap_partidos(d, lambda x: _efecto_logit(x, columnas), B, SEMILLA)
        no_conv = int((rep[:, 1] == 0).sum())
        lo, hi = intervalo(np.where(rep[:, 1] == 1, rep[:, 0], np.nan))
        metodo = ("Regresión logística (IRLS) de éxito sobre ciega con controles de tramo de t_pase, down, "
                  "distancia, zona del campo, n_rushers, shotgun y play action; efecto marginal promedio "
                  f"de ciega; IC 90% por bootstrap por partido (B={B}).")
    else:
        valor, no_conv = _efecto_mh(d), 0
        lo, hi = intervalo(bootstrap_partidos(d, _efecto_mh, B, SEMILLA))
        metodo = ("Diferencia de Mantel-Haenszel (ciega menos leída) por tramos de t_pase; la logística no "
                  f"convergió. IC 90% por bootstrap por partido (B={B}).")
    return {"valor_pp": float(valor), "ic90": [float(lo), float(hi)], "n": int(len(d)), "metodo": metodo,
            "columnas": columnas, "replicas_sin_converger": no_conv,
            "mh_pp": float(_efecto_mh(d))}


def _contraste(j: pd.DataFrame) -> list[dict]:
    d = _muestra_efecto(j)
    estratos = [("menos de 2.5 s", d["t_pase"] < 2.5), ("2.5 s o más", d["t_pase"] >= 2.5),
                ("total", pd.Series(True, index=d.index))]
    salida = []
    for nombre, m in estratos:
        fila = {"estrato": nombre}
        for clave, valor in (("ciega", 1), ("leida", 0)):
            s = d.loc[m & (d["ciega"] == valor), "exito"]
            p, lo, hi = wilson(int(s.sum()), len(s))
            fila[clave] = {"exito": _num(p), "ic90": _ic(lo, hi), "n": int(len(s))}
        salida.append(fila)
    return salida


# --- Revelación ---------------------------------------------------------------------------------

def _s_en(km: dict, t: float) -> tuple[float, float, float]:
    """S(t) del Kaplan-Meier (escalón) con su banda de Greenwood log-log."""
    i = np.searchsorted(km["tiempo"], t + 1e-9, side="right") - 1
    if i < 0:
        return 1.0, 1.0, 1.0
    return float(km["S"][i]), float(km["inferior"][i]), float(km["superior"][i])


def _mediana_km(d: pd.DataFrame) -> float:
    km = kaplan_meier(d["revela_t"], d["evento_revela"])
    bajo = np.flatnonzero(km["S"] <= 0.5)
    return float(km["tiempo"][bajo[0]]) if len(bajo) else math.nan


def _revelacion(j: pd.DataFrame) -> tuple[dict, dict]:
    d = _con_disfraz(j)
    km = kaplan_meier(d["revela_t"], d["evento_revela"])
    rep = bootstrap_partidos(d, _mediana_km, B, SEMILLA)
    lo, hi = intervalo(rep)
    curva = []
    for t in REJILLA_T:
        s, a, b = _s_en(km, t)
        curva.append({"t": float(t), "s": _num(s), "lo": _num(a), "hi": _num(b)})
    # Misma población que la curva de Kaplan-Meier: las jugadas con disfraz.
    lanzamiento = [{"t": float(t), "acumulado": _num((d["t_pase"] <= t + 1e-9).mean())} for t in REJILLA_T]
    salida = {"mediana_s": _num(_mediana_km(d), 2), "ic90": _ic(lo, hi, 2),
              "prob_disfrazado_2_5s": _num(_s_en(km, 2.5)[0]), "curva": curva, "lanzamiento": lanzamiento}
    diag = {"n": int(len(d)), "eventos": int(d["evento_revela"].sum()),
            "replicas_sin_mediana": int(np.isnan(rep).sum())}
    return salida, diag


# --- Sankey, validación, titular ----------------------------------------------------------------

def _sankey(j: pd.DataFrame) -> dict:
    d = _decididas(j)
    d = d[d["exito"].notna()]
    origen = np.where(d["muestra"] == "cerrado", 0, 1)
    destino = np.select([d["disfraz"] == 0, d["ciega"] == 0], [2, 3], default=4)
    final = np.where(d["exito"] == 1, 5, 6)
    links = []
    for a, b in ((origen, destino), (destino, final)):
        cuenta = pd.Series(1, index=pd.MultiIndex.from_arrays([a, b])).groupby(level=[0, 1]).sum()
        links += [{"source": int(s), "target": int(t), "value": int(n)} for (s, t), n in cuenta.items() if n > 0]
    return {"nodes": [{"name": n} for n in NODOS_SANKEY], "links": links}


def _validacion(registro: dict) -> dict:
    m = registro["validacion"]["metricas"]
    exa, regla = m["modelo_exactitud_umbral_0.5"], m["regla_exactitud_en_todas"]
    n = registro["validacion"]["n"]
    # Desde los conteos (478/607 = 78.748%), no desde el valor ya redondeado a 4 decimales (0.7875 -> 78.8%).
    p, lo, hi = wilson(exa["aciertos"], exa["n"])
    p_regla = regla["aciertos"] / regla["n"]
    texto = (f"En {n} jugadas de las semanas 7-8, que el lector no vio al ajustarse, acierta "
             f"{p:.1%} (IC90 {lo:.1%}-{hi:.1%}) contra {p_regla:.1%} de la regla simple; "
             f"AUC {m['modelo_auc']['valor']:.2f}, Brier {m['modelo_brier']['valor']:.3f}.")
    return {"exactitud": round(p, 6), "auc": m["modelo_auc"]["valor"], "brier": m["modelo_brier"]["valor"],
            "exactitud_regla": round(p_regla, 6), "n": n, "texto": texto}


def _con_signo(x: float) -> str:
    return f"{x:+.1f}".replace("-", "−")


def carrera() -> dict:
    """Fracción de disfraces en que el QB lanzó antes de la revelación (ciega), con IC 90% por partido."""
    d = _con_disfraz(_datos()[0])
    lo, hi = intervalo(bootstrap_partidos(d, lambda x: x["ciega"].mean(), B, SEMILLA))
    return {"valor": float(d["ciega"].mean()), "ic90": [float(lo), float(hi)], "n": int(len(d))}


def _titular(car: dict, dos_altos: float, ef: dict) -> str:
    """Titular con los números calculados: quién gana la carrera (fracción de disfraces lanzados antes de
    la revelación), disfraz corregido en coberturas de dos altos y efecto de lanzar a ciegas."""
    p, (lo_c, hi_c) = car["valor"], car["ic90"]
    ic_c = f"IC90 {lo_c * 100:.1f}–{hi_c * 100:.1f}"
    if lo_c <= 0.5 <= hi_c:
        inicio = (f"La carrera es un volado: cuando la defensa disfraza, el QB lanza antes de que se revele la "
                  f"cobertura en la mitad de las jugadas ({p:.1%}, {ic_c}).")
    elif p > 0.5:
        inicio = (f"La defensa gana la carrera: cuando disfraza, el QB lanza antes de que se revele la cobertura "
                  f"en el {p:.1%} de las jugadas ({ic_c}).")
    else:
        inicio = (f"El QB gana la carrera: cuando la defensa disfraza, lanza antes de que se revele la cobertura "
                  f"solo en el {p:.1%} de las jugadas ({ic_c}).")
    v, (lo, hi) = ef["valor_pp"], ef["ic90"]
    if lo > 0:
        relacion = "se asocia con más éxito"
    elif hi < 0:
        relacion = "se asocia con menos éxito"
    else:
        relacion = "no se asocia con una diferencia clara de éxito"
    disfraz = (f"El disfraz casi siempre es mostrar un safety profundo y jugar con dos "
               f"({dos_altos:.0%} de las coberturas de dos altos que el lector decide en el snap).")
    efecto = (f"Lanzar antes de la revelación {relacion}: {_con_signo(v)} pp "
              f"(IC90 {_con_signo(lo)} a {_con_signo(hi)}, n={ef['n']:,}).")
    return f"{inicio} {disfraz} {efecto}"


def _mitades(j: pd.DataFrame) -> pd.DataFrame:
    """Decididas con su mitad: partidos impares (1.º, 3.º, ...) o pares de cada defensa, en orden cronológico."""
    d = _decididas(j)
    orden = d[["defensiveTeam", "gameId"]].drop_duplicates().sort_values(["defensiveTeam", "gameId"])
    orden["mitad"] = orden.groupby("defensiveTeam").cumcount() % 2
    return d.merge(orden, on=["defensiveTeam", "gameId"])


def _split_half(d: pd.DataFrame, **rejillas) -> np.ndarray:
    """[r de Pearson entre mitades del ID por equipo (Bayes empírico en cada mitad), Spearman-Brown, equipos]."""
    medias = []
    for m in (0, 1):
        g = d[d["mitad"] == m].groupby("defensiveTeam")["disfraz"].agg(x="sum", n="size")
        eb = betabinom_eb(g["x"], g["n"], **rejillas)
        a, b = eb["mu"] * eb["kappa"], (1 - eb["mu"]) * eb["kappa"]
        medias.append((g["x"] + a) / (g["n"] + a + b))
    t = pd.concat(medias, axis=1, keys=["impar", "par"]).dropna()
    r = float(np.corrcoef(t["impar"], t["par"])[0, 1]) if len(t) > 2 else math.nan
    return np.array([r, 2 * r / (1 + r), len(t)])


def _estabilidad(j: pd.DataFrame) -> dict:
    r, sb, _ = _split_half(_mitades(j))
    return {"r": _num(r), "spearman_brown": _num(sb)}


@lru_cache(maxsize=1)
def resumen() -> dict:
    """GET /api/resumen."""
    j, _, registro = _datos()
    idd = indice_disfraz()
    ef = efecto_ciega(j)
    revelacion, _ = _revelacion(j)
    return {
        "titular": _titular(carrera(), idd["por_clase"]["juega_abierto"]["corregido"], ef),
        "n_jugadas": int(len(j)),
        "id_liga": {"valor": _num(idd["observado"]), "ic90": _ic(*idd["observado_ic90"]), "n": idd["n"]},
        "efecto": {"valor_pp": _num(ef["valor_pp"], 2), "ic90": _ic(*ef["ic90"], 2), "n": ef["n"],
                   "metodo": ef["metodo"]},
        "contraste": _contraste(j),
        "revelacion": revelacion,
        "validacion": _validacion(registro),
        "estabilidad": _estabilidad(j),
        "sankey": _sankey(j),
    }


# --- Equipos y tarjeta del rival ----------------------------------------------------------------

@lru_cache(maxsize=1)
def _equipos() -> tuple:
    j, _, _ = _datos()
    d = _decididas(j)
    g = d.groupby("defensiveTeam")["disfraz"].agg(x="sum", n="size").sort_index()
    eb = betabinom_eb(g["x"], g["n"])
    a0, b0 = eb["mu"] * eb["kappa"], (1 - eb["mu"]) * eb["kappa"]
    rng = np.random.default_rng(SEMILLA)
    dis = _con_disfraz(j)
    filas = []
    for equipo, fila in g.iterrows():
        a, b = fila["x"] + a0, fila["n"] - fila["x"] + b0
        lo, hi = np.quantile(rng.beta(a, b, SORTEOS), [0.05, 0.95])
        propio = dis[dis["defensiveTeam"] == equipo]
        mediana = _mediana_km(propio) if len(propio) >= MIN_DISFRAZ_EQUIPO else None
        filas.append({"equipo": str(equipo), "id": {"valor": _num(a / (a + b)), "ic90": _ic(lo, hi), "n": int(fila["n"])},
                      "revelacion_mediana_s": _num(mediana, 2)})
    filas.sort(key=lambda e: e["id"]["valor"], reverse=True)
    return tuple(filas), eb


def equipos() -> list[dict]:
    """GET /api/equipos: ID por defensa (beta-binomial empírico) y mediana de revelación."""
    return [dict(e) for e in _equipos()[0]]


def _filtrar(d: pd.DataFrame, down: int | None, distancia: str | None) -> pd.DataFrame:
    if down is not None:
        d = d[d["down"] == int(down)]
    if distancia is not None:
        d = d[d["tramo_dist"] == distancia]
    return d


def _un_alto(liga: pd.DataFrame, x: int, n: int, rng: np.random.Generator) -> dict:
    """P(juega un alto) del equipo (x de n en su celda), encogida hacia la liga con kappa beta-binomial.

    Con n = 0 es la tendencia de la liga con su IC90 (la Beta previa). liga nunca está vacía (ver rival).
    kappa se limita al número de jugadas de la liga: la previa no puede pesar más que los datos que la
    sostienen (en celdas chicas la beta-binomial no detecta sobredispersión y kappa se iría al borde).
    """
    mu = min(max(float((liga["juega"] == "cerrado").mean()), 1e-3), 1 - 1e-3)
    por = liga.assign(u=liga["juega"] == "cerrado").groupby("defensiveTeam")["u"].agg(["sum", "size"])
    kappa = min(betabinom_eb(por["sum"], por["size"], media=mu)["kappa"], float(len(liga)))
    a, b = x + mu * kappa, n - x + (1 - mu) * kappa
    lo, hi = np.quantile(rng.beta(a, b, SORTEOS), [0.05, 0.95])
    return {"p": _num(a / (a + b)), "ic90": _ic(lo, hi), "n": int(n)}


@lru_cache(maxsize=1)
def _validacion_tarjeta() -> dict:
    """Brier de P(juega un alto | equipo, muestra): ajuste en semanas 1-6, evaluación en 7-8."""
    j, _, _ = _datos()
    d = _decididas(j)
    errores = {"brier_mezcla": [], "brier_liga": [], "brier_equipo": []}
    for muestra in ("abierto", "cerrado"):
        e = d[(d["week"] <= 6) & (d["muestra"] == muestra)]
        v = d[(d["week"] >= 7) & (d["muestra"] == muestra)]
        mu = min(max(float((e["juega"] == "cerrado").mean()), 1e-3), 1 - 1e-3)
        por = e.assign(u=e["juega"] == "cerrado").groupby("defensiveTeam")["u"].agg(["sum", "size"])
        kappa = betabinom_eb(por["sum"], por["size"], media=mu)["kappa"]
        x = v["defensiveTeam"].map(por["sum"]).fillna(0).to_numpy(float)
        n = v["defensiveTeam"].map(por["size"]).fillna(0).to_numpy(float)
        y = (v["juega"] == "cerrado").to_numpy(float)
        pred = {"brier_mezcla": (x + mu * kappa) / (n + kappa), "brier_liga": np.full(len(v), mu),
                "brier_equipo": np.where(n > 0, x / np.maximum(n, 1), mu)}
        for k, p in pred.items():
            errores[k].append((p - y) ** 2)
    return {k: _num(np.mean(np.concatenate(v))) for k, v in errores.items()}


def rival(equipo: str, down: int | None = None, distancia: str | None = None) -> dict:
    """GET /api/rival: qué juega la defensa según lo que muestra en el snap, y éxito por formación."""
    j, _, _ = _datos()
    if distancia is not None:  # "7+" sin codificar en la URL llega como "7 "
        distancia = distancia.strip()
        distancia = "7+" if distancia == "7" else distancia
    decididas = _decididas(j)
    d = _filtrar(decididas, down, distancia)
    e = _filtrar(j[(j["defensiveTeam"] == equipo) & j["exito"].notna()], down, distancia)
    rng = np.random.default_rng(SEMILLA)
    filas = []
    for m in ("abierto", "cerrado"):
        propio = d[(d["muestra"] == m) & (d["defensiveTeam"] == equipo)]
        # Celda de la liga para encoger: la de la situación pedida si tiene al menos MIN_LIGA jugadas;
        # si no, sin distancia; luego sin down (esa siempre tiene miles).
        for dn, ds in ((down, distancia), (down, None), (None, None)):
            liga = _filtrar(decididas, dn, ds)
            liga = liga[liga["muestra"] == m]
            if len(liga) >= MIN_LIGA:
                break
        filas.append({"muestra": m, "juega_un_alto": _un_alto(liga, int((propio["juega"] == "cerrado").sum()),
                                                              len(propio), rng)})
    formaciones = []
    for formacion, s in sorted(e.groupby("offenseFormation"), key=lambda g: -len(g[1]))[:4]:
        p, lo, hi = wilson(int(s["exito"].sum()), len(s))
        formaciones.append({"formacion": str(formacion), "exito": {"p": _num(p), "ic90": _ic(lo, hi), "n": int(len(s))}})
    partes = [f"en {down}.º down" if down else "", f"con {distancia} yardas por avanzar" if distancia else ""]
    sit = "".join(f" {p}" for p in partes if p)
    frases = []
    for fila in reversed(filas):  # primero "cerrado"
        u = fila["juega_un_alto"]
        ic = f"IC90 {u['ic90'][0]:.0%}-{u['ic90'][1]:.0%}"
        if u["n"] == 0:
            frases.append(f"Sin jugadas de {equipo} mostrando {fila['muestra']} en el snap{sit}: se muestra la "
                          f"tendencia de la liga, que juega un alto el {u['p']:.0%} de las veces ({ic}).")
        elif u["n"] < MUESTRA_CHICA:
            frases.append(f"Cuando {equipo} muestra {fila['muestra']} en el snap{sit}, termina jugando un alto "
                          f"el {u['p']:.0%} de las veces ({ic}, n={u['n']}); con tan pocas jugadas, la "
                          "estimación se acerca a la tendencia de la liga.")
        else:
            frases.append(f"Cuando {equipo} muestra {fila['muestra']} en el snap{sit}, termina jugando un alto "
                          f"el {u['p']:.0%} de las veces ({ic}, n={u['n']}).")
    if formaciones:
        f = max(formaciones, key=lambda x: x["exito"]["n"])
        frases.append(f"La formación más usada contra {equipo}{sit} es {f['formacion']}: éxito "
                      f"{f['exito']['p']:.0%} (IC90 {f['exito']['ic90'][0]:.0%}-{f['exito']['ic90'][1]:.0%}, "
                      f"n={f['exito']['n']}); con muestras chicas, guíate por los intervalos.")
    else:
        frases.append(f"No hay jugadas suficientes contra {equipo}{sit} para comparar formaciones.")
    return {"equipo": equipo, "filas": filas, "formaciones": formaciones,
            "validacion_tarjeta": _validacion_tarjeta(), "frases": frases}


def replays() -> list[dict]:
    """GET /api/replays: 3 repeticiones elegidas por regla (docs/replays.md), con la forma de REPLAYS."""
    return json.loads((DERIVADO / "replays.json").read_text(encoding="utf-8"))


# --- Revisión -----------------------------------------------------------------------------------

def lanzado_con_disfraz() -> dict:
    """Fracción de jugadas con disfraz ya lanzadas a 2.5 y 3.0 s (la población de la curva de la carrera)."""
    d = _con_disfraz(_datos()[0])

    def fraccion(x: pd.DataFrame) -> np.ndarray:
        return np.array([(x["t_pase"] <= 2.5).mean(), (x["t_pase"] <= 3.0).mean()])

    ic, p = intervalo(bootstrap_partidos(d, fraccion, B, SEMILLA)), fraccion(d)
    return {f"{t} s": {"valor": round(float(p[i]), 4), "ic90": np.round(ic[:, i], 4).tolist(), "n": int(len(d))}
            for i, t in enumerate(("2.5", "3.0"))}


def cifras_extra() -> dict:
    """Cifras de docs/descubrimiento.md que no están en el contrato, con su IC 90% por partido."""
    j, _, _ = _datos()
    d = _muestra_efecto(j)
    mh = bootstrap_partidos(d, _efecto_mh, B, SEMILLA)
    idd = indice_disfraz()
    # Estabilidad split-half: IC por bootstrap por partido con una rejilla gruesa de la beta-binomial.
    gruesa = {"rejilla_mu": [i / 50 for i in range(1, 50)], "rejilla_kappa": [10 ** (k / 10) for k in range(0, 41)]}
    mitades = _mitades(j)
    sh = bootstrap_partidos(mitades, lambda x: _split_half(x, **gruesa), B, SEMILLA)
    # El bootstrap por partido sesga r hacia abajo (duplica jugadas dentro de una mitad); se reporta además
    # Fisher z sobre los equipos y la variación entre 50 divisiones al azar balanceadas por equipo.
    rng = np.random.default_rng(SEMILLA)
    pares = mitades[["defensiveTeam", "gameId"]].drop_duplicates()
    azar = []
    for _ in range(50):
        p = pares.assign(u=rng.random(len(pares))).sort_values(["defensiveTeam", "u"])
        p["mitad"] = p.groupby("defensiveTeam").cumcount() % 2
        azar.append(_split_half(mitades.drop(columns="mitad").merge(p[["defensiveTeam", "gameId", "mitad"]]),
                                **gruesa)[0])
    azar = np.array(azar)
    # ID observado por equipo contra su tasa de dos altos (mezcla de coberturas).
    def mezcla(x: pd.DataFrame) -> float:
        t = _decididas(x).groupby("defensiveTeam").agg(id=("disfraz", "mean"), dos=("juega", lambda s: (s == "abierto").mean()))
        return float(t["id"].corr(t["dos"]))
    mz = bootstrap_partidos(j, mezcla, B, SEMILLA)
    punto_sh = _split_half(mitades)
    z, se = math.atanh(punto_sh[0]), 1 / math.sqrt(punto_sh[2] - 3)
    fz = np.tanh([z - 1.645 * se, z + 1.645 * se])
    return {"estabilidad": {"r": round(float(punto_sh[0]), 4), "spearman_brown": round(float(punto_sh[1]), 4),
                            "equipos": int(punto_sh[2]),
                            "partidos_por_mitad": mitades.groupby("mitad")["gameId"].nunique().to_dict(),
                            "r_ic90_fisher_z_equipos": np.round(fz, 4).tolist(),
                            "spearman_brown_ic90_fisher_z": np.round(2 * fz / (1 + fz), 4).tolist(),
                            "divisiones_al_azar_50": {"media": round(float(azar.mean()), 4),
                                                      "p5": round(float(np.quantile(azar, 0.05)), 4),
                                                      "p95": round(float(np.quantile(azar, 0.95)), 4)},
                            "bootstrap_partido_sesgado": {"ic90": np.round(intervalo(sh[:, 0]), 4).tolist(),
                                                          "mediana": round(float(np.median(sh[:, 0])), 4),
                                                          "fraccion_bajo_el_punto": round(float(np.mean(sh[:, 0] < punto_sh[0])), 3)}},
            "corr_id_vs_dos_altos": {"r": round(mezcla(j), 4), "ic90": np.round(intervalo(mz), 4).tolist(), "equipos": 32},
            "mh_pp": {"valor": round(_efecto_mh(d), 2), "ic90": np.round(intervalo(mh), 2).tolist(), "n": int(len(d))},
            "lanzado_con_disfraz": lanzado_con_disfraz(),
            "id_por_clase": {k: {m: (np.round(x, 4).tolist() if isinstance(x, (list, np.ndarray)) else
                                     (round(x, 4) if isinstance(x, float) else x)) for m, x in v.items()}
                             for k, v in idd["por_clase"].items()}}


def revision() -> None:
    """Imprime el contrato y los chequeos de signo, normalización y censura; y la sensibilidad."""
    t0 = time.perf_counter()
    r = resumen()
    t_res = time.perf_counter() - t0
    eq = equipos()
    t_eq = time.perf_counter() - t0 - t_res
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"\ntiempos: resumen {t_res:.1f} s, equipos {t_eq:.1f} s")
    print("top 5 ID:", json.dumps(eq[:5], ensure_ascii=False))
    print("beta-binomial liga:", _equipos()[1])
    j, v, _ = _datos()
    idd, ef = indice_disfraz(), efecto_ciega(j)
    print("\nID:", {k: (np.round(x, 4).tolist() if isinstance(x, np.ndarray) else x) for k, x in idd.items()})
    print("efecto:", {k: x for k, x in ef.items() if k != "metodo"})
    _, diag = _revelacion(j)
    print("revelacion diag:", diag)

    d = _muestra_efecto(j)
    print("\n[signo] exito por grupo (crudo):", d.groupby("ciega")["exito"].agg(["mean", "size"]).round(3).to_dict())
    print("[signo] exito por down (universo):", j.groupby("down")["exito"].agg(["mean", "size"]).round(3).to_dict())
    print("[signo] ciega por tramo de t_pase:", _con_disfraz(j).groupby("tramo_t")["ciega"].agg(["mean", "size"]).round(3).to_dict())
    dis = _con_disfraz(j)
    print("[censura] revela_t <= t_pase:", bool((dis["revela_t"] <= dis["t_pase"] + 1e-9).all()),
          "| censuradas con revela_t == t_pase:", bool(np.allclose(dis.loc[dis["evento_revela"] == 0, "revela_t"],
                                                                   dis.loc[dis["evento_revela"] == 0, "t_pase"])),
          "| eventos con revela_t < t_pase:", bool((dis.loc[dis["evento_revela"] == 1, "revela_t"]
                                                    < dis.loc[dis["evento_revela"] == 1, "t_pase"] - 1e-9).all()),
          "| eventos con revela_t > 0:", bool((dis.loc[dis["evento_revela"] == 1, "revela_t"] > 0).all()))
    base = pd.read_csv(DERIVADO / "jugadas_base.csv", usecols=["gameId", "playId", "absoluteYardlineNumber"])
    jj = j.merge(base, on=["gameId", "playId"])
    jj["direccion"] = np.where((jj["absoluteYardlineNumber"] - (110 - jj["dist_endzone"])).abs()
                               <= (jj["absoluteYardlineNumber"] - (10 + jj["dist_endzone"])).abs(), "right", "left")
    print("[normalizacion] por direccion inferida:",
          jj.groupby("direccion").agg(n=("muestra", "size"), muestra_cerrado=("muestra", lambda s: (s == "cerrado").mean()),
                                      disfraz=("disfraz", "mean"), ciega=("ciega", "mean")).round(3).to_dict())
    print("\n[extra] " + json.dumps(cifras_extra(), ensure_ascii=False))
    sin_flag = j[~j["flag_linea"]]
    ef2 = efecto_ciega(sin_flag)
    print(f"\n[sensibilidad] sin flag_linea: n={ef2['n']}, efecto {ef2['valor_pp']:.2f} pp, IC90 "
          f"[{ef2['ic90'][0]:.2f}, {ef2['ic90'][1]:.2f}] (completo: {ef['valor_pp']:.2f} [{ef['ic90'][0]:.2f}, {ef['ic90'][1]:.2f}])")
    ejemplo = rival(eq[0]["equipo"], 3, "7+")
    print("\nrival ejemplo:", json.dumps(ejemplo, ensure_ascii=False))
    json.dumps(equipos()); json.dumps(resumen())  # todo serializable
    print(f"total {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    revision()
