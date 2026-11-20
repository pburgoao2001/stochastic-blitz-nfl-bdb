"""API de La Carrera Invisible. Ejecuta: .venv/Scripts/uvicorn backend.main:app --reload"""
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel


def cargar_env():
    f = Path(__file__).resolve().parent.parent / ".env"
    if f.exists():
        for linea in f.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


cargar_env()

from backend import mocks  # noqa: E402

RESUMEN = mocks.RESUMEN
EQUIPOS = mocks.EQUIPOS
REPLAYS = mocks.REPLAYS
_rival_real = None

# backend/analisis/ es territorio de otra herramienta; solo se importa, nunca se modifica.
try:
    from backend.analisis.metricas import resumen as _resumen, equipos as _equipos, rival as _rival

    RESUMEN = _resumen()
    EQUIPOS = sorted(_equipos(), key=lambda x: x["id"]["valor"], reverse=True)
    _rival_real = _rival
    DATA_SOURCE = "real"
except Exception as e:  # noqa: BLE001
    print(f"[warn] metricas.py no disponible: {e}", file=sys.stderr)
    DATA_SOURCE = "mock"

# La carga de repeticiones es independiente del resto de las métricas.
try:
    from backend.analisis.metricas import replays as _replays

    REPLAYS = _replays()
except Exception as e:  # noqa: BLE001
    print(f"[warn] replays() no disponible: {e}", file=sys.stderr)

app = FastAPI(title="Hackathon NFL UNAM")


@app.middleware("http")
async def cabecera_fuente(request: Request, call_next):
    response = await call_next(request)
    if DATA_SOURCE == "mock" and request.url.path.startswith("/api/"):
        response.headers["X-Data-Source"] = "mock"
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/resumen")
def api_resumen() -> dict:
    return RESUMEN


@app.get("/api/equipos")
def api_equipos() -> list:
    return EQUIPOS


def _obtener_rival(equipo: str, down: Optional[int] = None, distancia: Optional[str] = None) -> dict:
    if _rival_real is not None:
        try:
            return _rival_real(equipo, down, distancia)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] rival() falló: {e}", file=sys.stderr)
    entrada = mocks.RIVAL_TABLE.get((equipo, down, distancia))
    return entrada if entrada is not None else mocks.rival_default(equipo)


@app.get("/api/rival")
def api_rival(equipo: str, down: Optional[int] = None, distancia: Optional[str] = None) -> dict:
    return _obtener_rival(equipo, down, distancia)


@app.get("/api/replays")
def api_replays() -> list:
    return REPLAYS


class InformeRequest(BaseModel):
    equipo: str


@app.post("/api/informe")
def informe(body: InformeRequest) -> dict:
    try:
        # Importación perezosa; cargar_env() ya corrió al inicio de este módulo.
        from backend.informe import generar_informe

        # Se pasan los mismos datos que usan los demás endpoints (sin importación circular).
        return generar_informe(body.equipo, EQUIPOS, RESUMEN, _obtener_rival)
    except Exception:  # noqa: BLE001
        print("informe: plantilla (error interno)", file=sys.stderr)
        return {"texto": f"No se pudo redactar el informe de {body.equipo}.", "fuente": "plantilla"}
