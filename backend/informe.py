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
    "Termina con una recomendación concreta de preparación."
)

MAX_PALABRAS = 160
NUMEROS_LIBRES = {"1", "2", "3", "4"}  # downs


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _idx(x: float) -> str:
    return f"{x:.2f}"


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
        id_txt = f"{_idx(i['valor'])} (IC90 {_idx(i['ic90'][0])} a {_idx(i['ic90'][1])}, n={int(i['n'])})"
        lineas.append(f"Índice de disfraz (ID) de {equipo}: {id_txt}")
        partes.append(f"{equipo} tiene un índice de disfraz de {id_txt}")
        rev = _seg(fila["revelacion_mediana_s"])
        lineas.append(f"Mediana de revelación de {equipo}: {rev}")
        partes.append(f"revela su cobertura en una mediana de {rev}")

    li = resumen.get("id_liga")
    liga_txt = None
    if li:
        liga_txt = f"{_idx(li['valor'])} (IC90 {_idx(li['ic90'][0])} a {_idx(li['ic90'][1])}, n={int(li['n'])})"
        lineas.append(f"Índice de disfraz (ID) de la liga: {liga_txt}")

    riv = None
    if rival_fn is not None:
        try:
            riv = rival_fn(equipo)
        except Exception:  # noqa: BLE001
            riv = None
    frases: list[str] = []
    filas_txt: list[str] = []
    if riv:
        for f in riv.get("filas", []):
            j = f["juega_un_alto"]
            t = f"{_pct(j['p'])} (IC90 {_pct(j['ic90'][0])} a {_pct(j['ic90'][1])}, n={int(j['n'])})"
            filas_txt.append(f"formación {f['muestra']}: {t}")
            lineas.append(f"Safety alto con formación {f['muestra']}: {t}")
        frases = [str(x) for x in riv.get("frases", [])][:3]
        for k, fr in enumerate(frases, 1):
            lineas.append(f"Frase clave {k}: {fr}")

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
    base += " Recomendación: prepara al QB para decidir con cobertura disfrazada y practica lecturas rápidas antes de la revelación."
    return hechos, base


def verificar(texto: str, hechos: str) -> bool:
    """True si el texto es aceptable: no vacío, longitud razonable y sin números inventados."""
    if not texto or not texto.strip():
        return False
    if len(texto.split()) > MAX_PALABRAS:
        return False
    for num in re.findall(r"\d+(?:[.,]\d+)?", texto):
        if num in NUMEROS_LIBRES:
            continue
        if num not in hechos:
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
