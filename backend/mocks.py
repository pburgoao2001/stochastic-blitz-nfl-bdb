"""Datos de prueba con la forma exacta del contrato de la API (en memoria, sin escrituras)."""
import math

EQUIPOS_NFL = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET",
    "GB", "HOU", "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE",
    "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
]

RESUMEN = {
    "titular": "Cuando el QB lanza antes de que la defensa revele su cobertura, su éxito cambia 8.4 pp",
    "n_jugadas": 12840,
    "id_liga": {"valor": 0.47, "ic90": [0.44, 0.50], "n": 12840},
    "efecto": {"valor_pp": 8.4, "ic90": [6.1, 10.7], "n": 12840, "metodo": "Regresión logística con efectos fijos (datos de prueba)"},
    "contraste": [
        {"estrato": "menos de 2.5 s", "ciega": {"exito": 0.54, "ic90": [0.52, 0.56], "n": 3000}, "leida": {"exito": 0.49, "ic90": [0.47, 0.51], "n": 2500}},
        {"estrato": "2.5 s o más", "ciega": {"exito": 0.47, "ic90": [0.45, 0.49], "n": 2800}, "leida": {"exito": 0.38, "ic90": [0.36, 0.40], "n": 4000}},
        {"estrato": "total", "ciega": {"exito": 0.506, "ic90": [0.49, 0.52], "n": 5800}, "leida": {"exito": 0.422, "ic90": [0.41, 0.435], "n": 6500}},
    ],
    "revelacion": {
        "mediana_s": 2.1,
        "ic90": [1.9, 2.3],
        "prob_disfrazado_2_5s": 0.38,
        "curva": [
            {"t": round(i * 0.25, 2), "s": round(1 / (1 + math.exp((i * 0.25 - 2.1) * 2.2)), 3),
             "lo": round(max(0.0, 1 / (1 + math.exp((i * 0.25 - 2.1) * 2.2)) - 0.05), 3),
             "hi": round(min(1.0, 1 / (1 + math.exp((i * 0.25 - 2.1) * 2.2)) + 0.05), 3)}
            for i in range(0, 21)
        ],
        "lanzamiento": [
            {"t": round(i * 0.25, 2), "acumulado": round(1 / (1 + math.exp(-(i * 0.25 - 2.6) * 2.5)), 3)}
            for i in range(0, 21)
        ],
    },
    "validacion": {
        "exactitud": 0.74, "auc": 0.81, "brier": 0.17, "exactitud_regla": 0.62, "n": 3200,
        "texto": "El modelo supera a la regla simple en exactitud (74% vs 62%) sobre jugadas no vistas (datos de prueba).",
    },
    "estabilidad": {"r": 0.58, "spearman_brown": 0.73},
    "sankey": {
        "nodes": [
            {"name": "Pre-snap"}, {"name": "Cobertura cerrada"}, {"name": "Cobertura abierta"},
            {"name": "Disfrazado"}, {"name": "Leído"}, {"name": "Éxito"}, {"name": "Fracaso"},
        ],
        "links": [
            {"source": 0, "target": 1, "value": 6200}, {"source": 0, "target": 2, "value": 6640},
            {"source": 1, "target": 3, "value": 3100}, {"source": 1, "target": 4, "value": 3100},
            {"source": 2, "target": 3, "value": 2400}, {"source": 2, "target": 4, "value": 4240},
            {"source": 3, "target": 5, "value": 2800}, {"source": 3, "target": 6, "value": 2700},
            {"source": 4, "target": 5, "value": 2900}, {"source": 4, "target": 6, "value": 4440},
        ],
    },
}


def _equipos() -> list:
    filas = []
    n = len(EQUIPOS_NFL)
    for i, eq in enumerate(EQUIPOS_NFL):
        valor = round(0.30 + 0.35 * ((i * 11) % n) / (n - 1), 3)
        filas.append({
            "equipo": eq,
            "id": {"valor": valor, "ic90": [round(valor - 0.06, 3), round(valor + 0.06, 3)], "n": 350 + (i * 7) % 90},
            "revelacion_mediana_s": round(1.6 + 1.0 * ((i * 5) % n) / (n - 1), 2),
        })
    return sorted(filas, key=lambda x: x["id"]["valor"], reverse=True)


EQUIPOS = _equipos()


def _replay(game_id: str, play_id: str, desc: str, desfase: float) -> dict:
    frames = []
    for k in range(20):
        t = round(k * 0.25, 2)
        avance = k * 0.4
        of = [[round(40 + (j % 5) * 0.8 + avance * (1 if j > 6 else 0.2), 2), round(15 + j * 2.3, 2)] for j in range(11)]
        de = [[round(46 + (j % 4) * 1.5 - avance * 0.1 * desfase, 2), round(12 + j * 2.8, 2)] for j in range(11)]
        frames.append({
            "t": t, "def": de, "of": of,
            "balon": [round(40 + avance * 0.3, 2), 26.6],
            "estructura": "Cover 2 (disfrazado)" if t < 2.0 else "Cover 3 (revelado)",
        })
    return {
        "gameId": game_id, "playId": play_id, "descripcion": desc, "frames": frames,
        "eventos": {"snap": 0.0, "revela": 2.0, "lanza": 3.5},
    }


REPLAYS = [
    _replay("2022091108", "1056", "KC vs ARI, 3ª y 5, pase profundo (datos de prueba)", 1.0),
    _replay("2022091109", "2210", "BUF vs LAR, 2ª y 8, pase corto (datos de prueba)", 1.6),
]


def _fila(p_abierto: float, n: int) -> list:
    return [
        {"muestra": "abierto", "juega_un_alto": {"p": round(p_abierto, 2), "ic90": [round(p_abierto - 0.08, 2), round(p_abierto + 0.08, 2)], "n": n}},
        {"muestra": "cerrado", "juega_un_alto": {"p": round(p_abierto - 0.2, 2), "ic90": [round(p_abierto - 0.28, 2), round(p_abierto - 0.12, 2)], "n": n}},
    ]


def _entrada(equipo: str, p: float, n: int) -> dict:
    return {
        "equipo": equipo,
        "filas": _fila(p, n),
        "formaciones": [
            {"formacion": "Shotgun 11", "exito": {"p": round(p - 0.05, 2), "ic90": [round(p - 0.13, 2), round(p + 0.03, 2)], "n": n}},
            {"formacion": "Under center 21", "exito": {"p": round(p - 0.15, 2), "ic90": [round(p - 0.25, 2), round(p - 0.05, 2)], "n": max(n // 2, 1)}},
        ],
        "validacion_tarjeta": {"brier_mezcla": 0.19, "brier_liga": 0.23, "brier_equipo": 0.21},
        "frases": [
            f"{equipo} suele jugar con un safety alto cuando el ataque abre la formación (datos de prueba).",
            f"Con formación cerrada, {equipo} reduce el uso de un safety alto.",
            f"La muestra es limitada: interpreta los intervalos con cautela.",
        ],
    }


# Clave: (equipo, down, distancia). Tres equipos x 4 downs x 3 cubetas de distancia.
RIVAL_TABLE = {}
for _eq, _base in (("KC", 0.62), ("BUF", 0.55), ("SF", 0.48)):
    for _down in (1, 2, 3, 4):
        for _k, _dist in enumerate(("1-3", "4-6", "7+")):
            RIVAL_TABLE[(_eq, _down, _dist)] = _entrada(_eq, _base - 0.03 * _k + 0.01 * _down, 40 + 5 * _down + 3 * _k)


def rival_default(equipo: str) -> dict:
    return _entrada(equipo, 0.5, 30)
