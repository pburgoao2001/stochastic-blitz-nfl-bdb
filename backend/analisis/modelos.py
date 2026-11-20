"""Funciones estadísticas reutilizables de La Carrera Invisible (solo numpy y la biblioteca estándar).

Todo lo que usa azar recibe una semilla (por omisión SEMILLA), así que dos corridas dan lo mismo.
  wilson               proporción con intervalo de Wilson
  logit_irls           logística con penalización L2 por IRLS, columnas estandarizadas
  auc, brier, perdida_log
  bootstrap_partidos   remuestreo de partidos completos (gameId); intervalo() da el percentil
  kaplan_meier         supervivencia con IC de Greenwood en escala log-log
  betabinom_eb         beta-binomial empírico (mu, kappa) por verosimilitud marginal en rejilla
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

SEMILLA = 2026
Z90 = 1.645


def wilson(x: float, n: float, z: float = Z90) -> tuple[float, float, float]:
    """Proporción x/n con su intervalo de Wilson. Devuelve (p, inferior, superior)."""
    if n <= 0:
        return (math.nan, math.nan, math.nan)
    p = x / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    medio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centro - medio), min(1.0, centro + medio)


def _sigmoide(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))


@dataclass
class Logit:
    """Logística ajustada. coef está en la escala original de X; coef_estandarizados, en desviaciones."""
    intercepto: float
    coef: np.ndarray
    coef_estandarizados: np.ndarray
    l2: float
    iteraciones: int

    def predecir(self, X) -> np.ndarray:
        """P(y = 1 | X)."""
        return _sigmoide(self.intercepto + np.asarray(X, float) @ self.coef)


def logit_irls(X, y, l2: float, max_iter: int = 100, tol: float = 1e-8) -> Logit:
    """Regresión logística con penalización L2, ajustada por IRLS (Newton amortiguado).

    Estandariza cada columna (media 0, desviación 1) y minimiza
    -sum(loglik) + l2/2 * ||b||^2 sobre los coeficientes estandarizados; el intercepto
    no se penaliza. Devuelve los coeficientes en la escala original.
    """
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    media = X.mean(axis=0)
    escala = X.std(axis=0)
    escala = np.where(escala > 0, escala, 1.0)
    Z = np.column_stack([np.ones(len(X)), (X - media) / escala])
    pen = np.full(Z.shape[1], float(l2))
    pen[0] = 0.0

    def objetivo(b: np.ndarray) -> float:
        eta = Z @ b
        return float(np.sum(np.logaddexp(0.0, eta) - y * eta) + 0.5 * np.sum(pen * b * b))

    b = np.zeros(Z.shape[1])
    f = objetivo(b)
    it = 0
    for it in range(1, max_iter + 1):
        p = _sigmoide(Z @ b)
        g = Z.T @ (y - p) - pen * b
        H = (Z * (p * (1 - p))[:, None]).T @ Z + np.diag(pen)
        paso = np.linalg.solve(H, g)
        for _ in range(30):  # parte el paso a la mitad hasta que el objetivo no suba
            nuevo = objetivo(b + paso)
            if nuevo <= f + 1e-12:
                break
            paso = paso / 2
        b = b + paso
        f = nuevo
        if np.max(np.abs(paso)) < tol:
            break
    coef = b[1:] / escala
    return Logit(float(b[0] - np.sum(coef * media)), coef, b[1:].copy(), float(l2), it)


def perdida_log(y, p, eps: float = 1e-12) -> float:
    """Log-loss promedio."""
    y = np.asarray(y, float)
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def _rangos(v) -> np.ndarray:
    """Rangos 1..n, con el promedio en los empates."""
    v = np.asarray(v, float)
    orden = np.argsort(v, kind="mergesort")
    r = np.empty(len(v))
    r[orden] = np.arange(1, len(v) + 1)
    _, inv, cuenta = np.unique(v, return_inverse=True, return_counts=True)
    return (np.bincount(inv, weights=r) / cuenta)[inv]


def auc(y, p) -> float:
    """Área bajo la curva ROC por rangos (Mann-Whitney); los empates cuentan la mitad."""
    y = np.asarray(y).astype(bool)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return math.nan
    r = _rangos(p)
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def brier(y, p) -> float:
    """Error cuadrático medio de la probabilidad."""
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def bootstrap_partidos(df, funcion, B: int = 2000, semilla: int = SEMILLA) -> np.ndarray:
    """Remuestrea partidos completos (gameId) con reemplazo y aplica funcion a cada réplica.

    df: DataFrame con columna gameId. Un partido que sale k veces aporta sus filas k veces,
    así que funcion debe trabajar por filas, no por llaves únicas.
    Devuelve un arreglo (B,) o (B, k) si funcion devuelve k valores.
    """
    rng = np.random.default_rng(semilla)
    _, inv = np.unique(df["gameId"].to_numpy(), return_inverse=True)
    G = int(inv.max()) + 1
    orden = np.argsort(inv, kind="stable")
    grupos = np.split(orden, np.cumsum(np.bincount(inv, minlength=G))[:-1])
    replicas = []
    for _ in range(B):
        idx = np.concatenate([grupos[g] for g in rng.integers(0, G, G)])
        replicas.append(funcion(df.iloc[idx]))
    return np.asarray(replicas, float)


def intervalo(replicas, nivel: float = 0.90) -> np.ndarray:
    """Intervalo percentil de las réplicas, por columna: fila 0 inferior, fila 1 superior."""
    a = (1 - nivel) / 2
    return np.nanquantile(np.asarray(replicas, float), [a, 1 - a], axis=0)


def kaplan_meier(t, evento, z: float = Z90) -> dict:
    """Kaplan-Meier con IC de Greenwood en escala log-log.

    t: tiempo hasta el evento o la censura; evento: 1 si ocurrió, 0 si se censuró.
    Devuelve arreglos con una entrada por tiempo con al menos un evento:
    tiempo, n_riesgo, eventos, S, inferior, superior.
    """
    t = np.asarray(t, float)
    e = np.asarray(evento).astype(bool)
    tiempos = np.unique(t[e])
    n_riesgo = len(t) - np.searchsorted(np.sort(t), tiempos, side="left")
    eventos = np.array([np.count_nonzero(e & (t == u)) for u in tiempos], dtype=float)
    S = np.cumprod(1 - eventos / n_riesgo)
    with np.errstate(divide="ignore", invalid="ignore"):
        V = np.cumsum(eventos / (n_riesgo * (n_riesgo - eventos)))
        sigma = np.sqrt(V) / np.abs(np.log(S))
        inferior = S ** np.exp(z * sigma)
        superior = S ** np.exp(-z * sigma)
    definido = (S > 0) & np.isfinite(sigma)
    return {"tiempo": tiempos, "n_riesgo": n_riesgo, "eventos": eventos, "S": S,
            "inferior": np.where(definido, inferior, np.nan),
            "superior": np.where(definido, superior, np.nan)}


def betabinom_eb(x, n, media: float | None = None, rejilla_mu=None, rejilla_kappa=None) -> dict:
    """Beta-binomial empírico por máxima verosimilitud marginal en una rejilla (con math.lgamma).

    Cada unidad i tiene x_i éxitos de n_i, con p_i ~ Beta(mu*kappa, (1-mu)*kappa).
    Estima (mu, kappa); si recibe media, fija mu = media y solo estima kappa.
    La verosimilitud omite el coeficiente binomial, que no depende de (mu, kappa).
    kappa en el borde de la rejilla avisa que el máximo podría estar fuera de ella
    (en el borde superior: no se detecta sobredispersión).
    """
    xs = [int(v) for v in x]
    ns = [int(v) for v in n]
    mus = [float(media)] if media is not None else list(rejilla_mu or [i / 200 for i in range(1, 200)])
    kappas = list(rejilla_kappa or [10 ** (k / 40) for k in range(0, 161)])  # de 1 a 10^4
    lg = math.lgamma
    mejor = (-math.inf, math.nan, math.nan)
    for mu in mus:
        for kappa in kappas:
            a, b = mu * kappa, (1 - mu) * kappa
            ll = (sum(lg(xi + a) + lg(ni - xi + b) - lg(ni + a + b) for xi, ni in zip(xs, ns))
                  + len(xs) * (lg(a + b) - lg(a) - lg(b)))
            if ll > mejor[0]:
                mejor = (ll, mu, kappa)
    ll, mu, kappa = mejor
    return {"mu": mu, "kappa": kappa, "loglik": ll,
            "kappa_en_borde": bool(kappa in (kappas[0], kappas[-1]))}


def betabinom_posterior(x, n, mu: float, kappa: float) -> np.ndarray:
    """Media posterior de cada p_i: (x + mu*kappa) / (n + kappa)."""
    return (np.asarray(x, float) + mu * kappa) / (np.asarray(n, float) + kappa)
