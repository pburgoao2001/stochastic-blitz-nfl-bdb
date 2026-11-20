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


@app.get("/api/rival")
def api_rival(equipo: str, down: Optional[int] = None, distancia: Optional[str] = None) -> dict:
    if _rival_real is not None:
        try:
            return _rival_real(equipo, down, distancia)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] rival() falló: {e}", file=sys.stderr)
    entrada = mocks.RIVAL_TABLE.get((equipo, down, distancia))
    return entrada if entrada is not None else mocks.rival_default(equipo)


@app.get("/api/replays")
def api_replays() -> list:
    return REPLAYS


class InformeRequest(BaseModel):
    equipo: str


def plantilla(equipo: str) -> str:
    fila = next((e for e in EQUIPOS if e["equipo"] == equipo), None)
    texto = RESUMEN["titular"]
    if fila is None:
        return f"{texto} No hay datos específicos para {equipo}."
    return (
        f"{texto} {equipo} tiene un índice de disfraz de {fila['id']['valor']:.2f} "
        f"(IC90 {fila['id']['ic90'][0]:.2f}–{fila['id']['ic90'][1]:.2f}, n={fila['id']['n']}) "
        f"y revela su cobertura en una mediana de {fila['revelacion_mediana_s']:.1f} s."
    )


@app.post("/api/informe")
def informe(body: InformeRequest) -> dict:
    return {"texto": plantilla(body.equipo), "fuente": "plantilla"}
