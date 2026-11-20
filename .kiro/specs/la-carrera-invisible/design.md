# Design Document

## Overview

La Carrera Invisible is a single-page NFL preparation dashboard. The backend is a FastAPI application (`backend/main.py`) that exposes five read-only endpoints and one POST endpoint, all under `/api`. Data is loaded once at startup into module-level variables. The frontend is a React 18 + TypeScript + Tailwind CSS application rendered entirely in `dashboard/src/App.tsx` and its child components, consuming the API with relative `fetch('api/...')` calls.

## Architecture

```
dashboard/src/
  App.tsx                    ← root; fetches /api/resumen, /api/equipos on mount
  components/
    Banner.tsx               ← "datos de prueba" banner (shows when X-Data-Source: mock)
    Titular.tsx              ← effect headline + contrast bar chart
    LaCarrera.tsx            ← disguise/launch dual time-series with IC band
    SankeyChart.tsx          ← Sankey flow diagram
    Repeticion.tsx           ← animated field (placeholder until replays endpoint ready)
    Ranking.tsx              ← team ID ranking with error bars
    TarjetaRival.tsx         ← rival selector + situation + report button + result

backend/
  main.py                    ← FastAPI app; loads data at startup; all endpoints here
  mocks.py                   ← pure-Python dicts/lists that satisfy the full contract
```

No new dependencies. Recharts' `Sankey`, `LineChart`, `BarChart`, `ResponsiveContainer`, `ErrorBar`, `ReferenceLine` are used. The animated field in Repeticion uses plain HTML5 `<canvas>` or CSS transforms on `<div>` elements.

## Components and Interfaces

### Backend startup logic

```python
# backend/main.py (startup sequence)
from backend.mocks import RESUMEN, EQUIPOS, REPLAYS

# backend/analisis/ es territorio de la otra herramienta; nunca crear ni modificar
try:
    from backend.analisis.metricas import resumen, equipos, rival
    RESUMEN = resumen()
    EQUIPOS = sorted(equipos(), key=lambda x: x["id"]["valor"], reverse=True)
    # rival(equipo, down, distancia) se llama por request en GET /api/rival
    DATA_SOURCE = "real"
except Exception as e:
    import sys; print(f"[warn] metricas.py no disponible: {e}", file=sys.stderr)
    DATA_SOURCE = "mock"
```

Every response handler adds `response.headers["X-Data-Source"] = DATA_SOURCE` when `DATA_SOURCE == "mock"`.

### GET /api/resumen

Returns the module-level `RESUMEN` dict. No query parameters.

Response shape:
```
{
  titular: string,
  n_jugadas: number,
  id_liga: { valor: number, ic90: [lo, hi], n: number },
  efecto: { valor_pp: number, ic90: [lo, hi], n: number, metodo: string },
  contraste: [{ estrato: string, ciega: { exito: number, ic90: [lo, hi], n: number }, leida: { exito: number, ic90: [lo, hi], n: number } }],
  revelacion: {
    mediana_s: number, ic90: [lo, hi], prob_disfrazado_2_5s: number,
    curva: [{ t: number, s: number, lo: number, hi: number }],
    lanzamiento: [{ t: number, acumulado: number }]
  },
  validacion: { exactitud: number, auc: number, brier: number, exactitud_regla: number, n: number, texto: string },
  estabilidad: { r: number, spearman_brown: number },
  sankey: { nodes: [{ name: string }], links: [{ source: number, target: number, value: number }] }
}
```

### GET /api/equipos

Returns the module-level `EQUIPOS` list sorted by `id.valor` descending at startup.

Response shape:
```
[{ equipo: string, id: { valor: number, ic90: [lo, hi], n: number }, revelacion_mediana_s: number }]
```

### GET /api/rival

Accepts `equipo: string`, `down: int | None`, `distancia: "1-3" | "4-6" | "7+" | None`. Filters `RIVAL_TABLE` by those keys. If no matching entry exists, returns a default entry for the requested team.

Response shape:
```
{
  equipo: string,
  filas: [{ muestra: "abierto" | "cerrado", juega_un_alto: { p: number, ic90: [lo, hi], n: number } }],
  formaciones: [{ formacion: string, exito: { p: number, ic90: [lo, hi], n: number } }],
  validacion_tarjeta: { brier_mezcla: number, brier_liga: number, brier_equipo: number },
  frases: [string, string, string]
}
```

### GET /api/replays

Returns the module-level `REPLAYS` list.

Response shape:
```
[{
  gameId: string, playId: string, descripcion: string,
  frames: [{ t: number, def: [[x, y]], of: [[x, y]], balon: [x, y], estructura: string }],
  eventos: { snap: number, revela: number, lanza: number }
}]
```

### POST /api/informe

Accepts `{ equipo: string }`. Returns `{ texto: string, fuente: "ia" | "plantilla" }`.

```python
@app.post("/api/informe")
def informe(body: InformeRequest):
    try:
        texto = llamar_bedrock(body.equipo)
        return {"texto": texto, "fuente": "ia"}
    except Exception:
        return {"texto": plantilla(body.equipo), "fuente": "plantilla"}
```

`llamar_bedrock` creates `boto3.client("bedrock-runtime", region_name=region)` and calls the Strands agent. `plantilla` builds a string from `RESUMEN` and the matching `EQUIPOS` row.

### Frontend data flow

```
App.tsx
  useEffect → fetch('api/resumen') → setResumen(data), setMock(res.headers.get('X-Data-Source') === 'mock')
  useEffect → fetch('api/equipos') → setEquipos(data)
  renders → Banner (if mock)
           → Titular (resumen.efecto, resumen.contraste)
           → LaCarrera (resumen.revelacion)
           → SankeyChart (resumen.sankey)
           → Repeticion (lazy: fetches 'api/replays' on mount)
           → Ranking (equipos)
           → TarjetaRival (equipos list for selector; calls 'api/rival' on change; 'api/informe' on button click)
```

### Vite proxy (development)

```typescript
// vite.config.ts
server: {
  proxy: { '/api': 'http://localhost:8000' }
}
```

`base: './'` is retained.

### Mock data shape (mocks.py)

`RESUMEN` is a hardcoded dict with realistic-looking numeric values covering all contract fields. `EQUIPOS` is a list of 32 teams. `REPLAYS` is a list of two plays, each with 20 frames. `RIVAL_TABLE` is keyed by `(equipo, down, distancia)` with fallback defaults.

### Animation (Repeticion.tsx)

Uses `requestAnimationFrame` with a frame index driven by `setInterval`. Each frame updates player `<div>` positions via CSS `transform: translate(x,y)` mapped from tracking coordinates (0–120 yards × 0–53.3 yards) to pixel space. Events (`snap`, `revela`, `lanza`) are shown as color-coded dots on a scrub bar. When `replays` is empty or the fetch fails, shows the placeholder string without error.

## Data Models

```typescript
type IC90 = [number, number]  // [lo, hi]
interface ConIC { valor: number; ic90: IC90; n: number }
interface ResumenData {
  titular: string; n_jugadas: number;
  id_liga: ConIC;
  efecto: { valor_pp: number; ic90: IC90; n: number; metodo: string };
  contraste: Array<{ estrato: string; ciega: { exito: number; ic90: IC90; n: number }; leida: { exito: number; ic90: IC90; n: number } }>;
  revelacion: { mediana_s: number; ic90: IC90; prob_disfrazado_2_5s: number; curva: Array<{t:number;s:number;lo:number;hi:number}>; lanzamiento: Array<{t:number;acumulado:number}> };
  validacion: { exactitud: number; auc: number; brier: number; exactitud_regla: number; n: number; texto: string };
  estabilidad: { r: number; spearman_brown: number };
  sankey: { nodes: Array<{name:string}>; links: Array<{source:number;target:number;value:number}> };
}
interface EquipoRow { equipo: string; id: ConIC; revelacion_mediana_s: number }
```

## Error Handling

- If `metricas.py` import raises at startup, the app logs to stderr and falls back to mocks; no endpoint fails.
- If the Bedrock call raises, `POST /api/informe` catches the exception and returns `{"texto": <plantilla>, "fuente": "plantilla"}` with HTTP 200.
- If `/api/replays` returns an empty array or the fetch fails, `Repeticion.tsx` renders the placeholder text without throwing.
- Unexpected query parameter values in `/api/rival` (e.g., unknown `distancia`) return the default fallback entry rather than a 422 or 500.

## Testing Strategy

- Run `GET /health`, `GET /api/resumen`, `GET /api/equipos`, and `GET /api/replays` with httpx to verify shape and status 200.
- Run `GET /api/rival?equipo=KC&down=1&distancia=1-3` and verify required fields are present.
- Run `POST /api/informe` with `{"equipo":"KC"}` and verify the response contains `texto` and a valid `fuente`.
- Verify that when mocks are active the `X-Data-Source: mock` header is present on all API responses.
- Run `vite build` (TypeScript strict mode) to confirm no type errors in the frontend.

## Correctness Properties

### Property 1: Mock header on all API responses
For every request to any `/api/...` endpoint while `DATA_SOURCE == "mock"`, the response includes the header `X-Data-Source: mock`.

**Validates: Requirements 1.8, 2.8**

### Property 2: Informe always returns 200
`POST /api/informe` always returns HTTP 200 with a JSON body containing `texto` (non-empty string) and `fuente` in `{"ia", "plantilla"}`, regardless of Bedrock availability.

**Validates: Requirements 5.3, 5.4**

### Property 3: Equipos sorted at startup
The module-level `EQUIPOS` list is sorted by `id.valor` descending at startup, and `GET /api/equipos` returns that list without re-sorting on each request.

**Validates: Requirements 1.3, 2.5**

### Property 4: No runtime file writes
No path in `backend/main.py` or any imported module writes to the filesystem at request time; all data is in-memory.

**Validates: Requirements 1.7, 6.5**