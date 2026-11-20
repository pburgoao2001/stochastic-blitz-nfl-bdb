"""Informe semanal redactado por IA (Amazon Bedrock, Nova) con verificación de números.

No importa main.py: recibe los datos ya resueltos como parámetros (sin importaciones circulares).
Nunca lanza excepciones hacia fuera: si la IA falla, devuelve una plantilla determinista.
"""
import os
import re
import sys
from typing import Callable, Optional

SISTEMA = (
    "Eres analista de un staff de NFL. Escribe en español un informe de preparación semanal "
    "de máximo 120 palabras sobre la defensa indicada, dirigido al coordinador ofensivo. "
    "Usa SOLO los números del bloque HECHOS y cita cada uno con su n. "
    "'Antes de la revelación' describe el momento del lanzamiento, no un error del QB. "
    "No inventes jugadores, jugadas ni números. "
    "Termina con una recomendación concreta de preparación. "
    "La única recomendación permitida es: 'cuando esta defensa muestre un alto en el snap, "
    "prepara la lectura de rotación a dos altos', citando la probabilidad de rotación a dos altos "
    "con su n tal como aparece en HECHOS. No recomiendes lecturas rápidas ni nada que HECHOS no sostenga. "
    "Si HECHOS no trae esa probabilidad, no hagas recomendación."
)

MAX_PALABRAS = 160
NUMEROS_LIBRES = {"1", "2", "3", "4"}  # downs
UMBRAL_N = 15


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _ic(lo: float, hi: float, n: float) -> str:
    """'IC90 48–58%, n=210' (porcentajes sin decimales, igual que el dashboard)."""
    return f"IC90 {lo * 100:.0f}–{hi * 100:.0f}%, n={int(n)}"


def _est(p: float, lo: float, hi: float, n: float) -> str:
    return f"{_pct(p)} ({_ic(lo, hi, n)})"


def _pp(x: float) -> str:
    t = f"{abs(x):.1f}"
    return f"\u2212{t} pp" if x < 0 and float(t) != 0 else f"+{t} pp"


def _seg(x: float) -> str:
    return f"{x:.1f} s"


def construir_hechos(
    equipo: str,
    equipos: list,
    resumen: dict,
    rival_fn: Optional[Callable[[str], Optional[dict]]] = None,
) -> tuple[str, str]:
    """Devuelve (HECHOS, plantilla). Cada número se formatea una sola vez y se reutiliza."""
    lineas: list[str] = [f"Defensa: {equipo}"]
    partes: list[str] = []

    fila = next((e for e in equipos if e.get("equipo") == equipo), None)
    if fila is not None:
        i = fila["id"]
        id_txt = _est(i["valor"], i["ic90"][0], i["ic90"][1], i["n"])
        lineas.append(f"Índice de disfraz (ID) de {equipo}: {id_txt}")
        partes.append(f"{equipo} tiene un índice de disfraz de {id_txt}")
        rev = _seg(fila["revelacion_mediana_s"])
        lineas.append(f"Mediana de revelación de {equipo}: {rev}")
        partes.append(f"revela su cobertura en una mediana de {rev}")

    li = resumen.get("id_liga")
    liga_txt = None
    if li:
        liga_txt = _est(li["valor"], li["ic90"][0], li["ic90"][1], li["n"])
        lineas.append(f"Índice de disfraz (ID) de la liga: {liga_txt}")

    riv = None
    if rival_fn is not None:
        try:
            riv = rival_fn(equipo)
        except Exception:  # noqa: BLE001
            riv = None
    frases: list[str] = []
    filas_txt: list[str] = []
    rec_txt: Optional[str] = None
    if riv:
        for f in riv.get("filas", []):
            j = f["juega_un_alto"]
            t = _est(j["p"], j["ic90"][0], j["ic90"][1], j["n"])
            filas_txt.append(f"formación {f['muestra']}: {t}")
            lineas.append(f"Safety alto con formación {f['muestra']}: {t}")
            if f.get("muestra") == "cerrado" and rec_txt is None:
                lo, hi = 1 - j["ic90"][1], 1 - j["ic90"][0]
                rec_txt = f"rota a dos altos en {_pct(1 - j['p'])} de las jugadas ({_ic(lo, hi, j['n'])})"
                if j["n"] < UMBRAL_N:
                    rec_txt += " (muestra chica)"
        frases = [str(x) for x in riv.get("frases", [])][:3]
        for k, fr in enumerate(frases, 1):
            lineas.append(f"Frase clave {k}: {fr}")
    if rec_txt:
        lineas.append(f"Cuando muestra un alto en el snap, {rec_txt}")

    hechos = "\n".join(lineas)

    # Plantilla determinista con los mismos textos.
    if fila is None:
        base = f"No hay datos específicos para {equipo}."
    else:
        base = f"Informe semanal de {equipo}: " + "; ".join(partes) + "."
    if liga_txt:
        base += f" Referencia de la liga: {liga_txt}."
    if filas_txt:
        base += " Uso de un safety alto: " + "; ".join(filas_txt) + "."
    if frases:
        base += " " + " ".join(frases)
    if rec_txt:
        base += (
            " Recomendación: cuando esta defensa muestre un alto en el snap, prepara la lectura "
            f"de rotación a dos altos ({rec_txt})."
        )
    return hechos, base


def verificar(texto: str, hechos: str) -> bool:
    """True si el texto es aceptable: no vacío, longitud razonable y sin números inventados.

    Compara números completos (tokens), no subcadenas; la coma decimal se normaliza a punto.
    """
    if not texto or not texto.strip():
        return False
    if len(texto.split()) > MAX_PALABRAS:
        return False
    patron = r"\d+(?:[.,]\d+)?"
    permitidos = {t.replace(",", ".") for t in re.findall(patron, hechos)}
    for num in re.findall(patron, texto):
        num = num.replace(",", ".")
        if num in NUMEROS_LIBRES:
            continue
        if num not in permitidos:
            return False
    return True


def _llamar_bedrock(hechos: str) -> str:
    # Importación perezosa: main.py ya ejecutó cargar_env() al arrancar.
    import boto3
    import botocore.config

    client = boto3.client(
        "bedrock-runtime",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        config=botocore.config.Config(connect_timeout=5, read_timeout=20, retries={"max_attempts": 1}),
    )
    resp = client.converse(
        modelId=os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0"),
        system=[{"text": SISTEMA}],
        messages=[{"role": "user", "content": [{"text": hechos}]}],
        inferenceConfig={"maxTokens": 400, "temperature": 0.2},
    )
    return resp["output"]["message"]["content"][0]["text"]


def _log(msg: str) -> None:
    print(f"informe: {msg}", file=sys.stderr)


def generar_informe(
    equipo: str,
    equipos: list,
    resumen: dict,
    rival_fn: Optional[Callable[[str], Optional[dict]]] = None,
) -> dict:
    """Devuelve {texto, fuente}. Garantiza texto no vacío y nunca lanza."""
    try:
        hechos, plantilla = construir_hechos(equipo, equipos, resumen, rival_fn)
    except Exception:  # noqa: BLE001
        _log("plantilla (datos no disponibles)")
        return {"texto": f"No hay datos disponibles para {equipo}.", "fuente": "plantilla"}

    try:
        texto = _llamar_bedrock(hechos).strip()
    except Exception as e:  # noqa: BLE001
        nombre = type(e).__name__
        motivo = "timeout" if "Timeout" in nombre else "sin credenciales/fallo de Bedrock"
        _log(f"plantilla ({motivo})")
        return {"texto": plantilla, "fuente": "plantilla"}

    try:
        ok = verificar(texto, hechos)
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        _log("plantilla (verificación de números)")
        return {"texto": plantilla, "fuente": "plantilla"}
    _log("ia")
    return {"texto": texto, "fuente": "ia"}
