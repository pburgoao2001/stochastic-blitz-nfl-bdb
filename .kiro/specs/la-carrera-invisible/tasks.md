# Implementation Plan: La Carrera Invisible

## Overview

Five sequential tasks follow the implementation order from the spec description. Task 1 (API + mocks) must complete before task 2 (dashboard); task 3 (analytics connector) requires tasks 1 and 2; task 4 (replay animation) requires task 2; task 5 (AI) requires task 1.

## Task Dependency Graph

```json
{
  "waves": [
    {"id": 0, "tasks": ["1.1", "1.2", "1.3"]},
    {"id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10", "5.1", "5.2", "5.3", "5.4"]},
    {"id": 2, "tasks": ["3.1", "3.2", "4.1", "4.2", "4.3", "4.4"]}
  ]
}
```

## Tasks

- [ ] 1. Add mock data module and wire all API endpoints

  Create `backend/mocks.py` with hardcoded Python dicts/lists that satisfy every field of the full API contract. Update `backend/main.py` to import the mocks, detect whether `backend/analisis/metricas.py` exists, set a module-level `DATA_SOURCE` variable, and expose all six endpoints (`/health`, `/api/resumen`, `/api/equipos`, `/api/rival`, `/api/replays`, `POST /api/informe` with template fallback). Every endpoint that reads from mocks adds the response header `X-Data-Source: mock`.

  - [ ] 1.1 Create `backend/mocks.py` with `RESUMEN`, `EQUIPOS` (32 teams sorted by `id.valor` desc), `REPLAYS` (2 plays × 20 frames), and `RIVAL_TABLE` covering at least three teams × three distance buckets.
  - [ ] 1.2 Update `backend/main.py`: add startup import logic (try `metricas`, fall back to mocks, log to stderr on failure); add `GET /api/resumen`, `GET /api/equipos`, `GET /api/rival`, `GET /api/replays`, `POST /api/informe` (template only for now); retain `GET /health` unchanged; attach `X-Data-Source: mock` header where applicable.
  - [ ] 1.3 Verify manually: start Uvicorn (`.venv/Scripts/uvicorn backend.main:app --reload`), hit each endpoint with curl or a browser, confirm shapes and header.

- [ ] 2. Build the single-page dashboard consuming the API

  Replace the placeholder `App.tsx` with a full single-page layout that renders all six sections. Add the Vite proxy. Each section reads from the API responses and renders with Recharts where specified.

  - [ ] 2.1 Update `vite.config.ts`: add `server.proxy` mapping `/api` to `http://localhost:8000`; keep `base: './'`.
  - [ ] 2.2 Create `dashboard/src/components/Banner.tsx`: shows a yellow banner "⚠ datos de prueba" when the `X-Data-Source: mock` header is detected.
  - [ ] 2.3 Create `dashboard/src/components/Titular.tsx`: displays `resumen.titular`, `efecto.valor_pp` (formatted as `+X pp`), and a horizontal `BarChart` with error bars for each `contraste` stratum comparing `ciega.exito` and `leida.exito`.
  - [ ] 2.4 Create `dashboard/src/components/LaCarrera.tsx`: renders a `LineChart` with two series — `revelacion.curva` (disguise rate + IC band as area) and `revelacion.lanzamiento` (cumulative launch probability) — on the same X axis (time in seconds).
  - [ ] 2.5 Create `dashboard/src/components/SankeyChart.tsx`: renders Recharts' `Sankey` component with `sankey.nodes` and `sankey.links`.
  - [ ] 2.6 Create `dashboard/src/components/Ranking.tsx`: renders a horizontal `BarChart` from `GET api/equipos`, one bar per team, with error bars for `id.ic90`.
  - [ ] 2.7 Create `dashboard/src/components/TarjetaRival.tsx`: contains a `<select>` for team (from equipos list), a `<select>` for down (1–4), a `<select>` for distancia (`1-3`, `4-6`, `7+`), and a "Generar informe" button. On selection change, calls `fetch('api/rival?equipo=...&down=...&distancia=...')` and shows formations/frases. On button click, calls `fetch('api/informe', {method:'POST', body: JSON.stringify({equipo})})` and displays the returned text with the matching label.
  - [ ] 2.8 Create `dashboard/src/components/Repeticion.tsx`: shows a static placeholder "Repetición disponible próximamente" (section 4 is wired in task 4).
  - [ ] 2.9 Rewrite `dashboard/src/App.tsx`: fetch `api/resumen` and `api/equipos` on mount, detect mock header, assemble all sections in order: Banner → Titular → LaCarrera → SankeyChart → Repeticion → Ranking → TarjetaRival.
  - [ ] 2.10 Run `npm run build` inside `dashboard/` and confirm zero TypeScript errors and a successful Vite build.

- [ ] 3. Connect to real analytics module when available

  Add the conditional import logic so that when `backend/analisis/metricas.py` exists its data replaces the mocks transparently, and the "datos de prueba" banner disappears.

  - [ ] 3.1 Confirm the try/except import block in `backend/main.py` (from task 1.2) covers `get_resumen`, `get_equipos`, `get_replays`, and sets `DATA_SOURCE = "real"` on success. Adjust if needed.
  - [ ] 3.2 Verify that when `metricas.py` is present and importable, `GET /api/resumen` returns its data, `X-Data-Source` header is absent, and the frontend banner does not render (manual check with a stub `metricas.py`).

- [ ] 4. Implement animated replay viewer

  Replace the Repeticion placeholder with a live animation driven by `/api/replays` data.

  - [ ] 4.1 Update `dashboard/src/components/Repeticion.tsx`: on mount, fetch `api/replays`; if the array is empty or the fetch throws, render "Repetición disponible próximamente" and exit.
  - [ ] 4.2 Render a green `<div>` field (120 × 53.3 yard proportions) with 10-yard line markers. Map tracking coordinates to pixel space using the container's bounding rect.
  - [ ] 4.3 Add Play / Pause / Reset buttons and a scrub bar. Use `setInterval` / `requestAnimationFrame` to advance the frame index; update player `<div>` positions via CSS `transform: translate(x,y)`.
  - [ ] 4.4 Show `eventos.snap`, `eventos.revela`, `eventos.lanza` as color-coded markers on the scrub bar.

- [ ] 5. Add AI-powered informe generation via Amazon Bedrock

  Extend `POST /api/informe` to call Strands Agents + Amazon Bedrock when available, falling back to the template without breaking the app.

  - [ ] 5.1 Add the `cargar_env()` function at the top of `backend/main.py` (before any boto3 import) exactly as specified in the project rules.
  - [ ] 5.2 Implement `llamar_bedrock(equipo: str) -> str` inside `backend/main.py`: create `boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))`, use Strands Agents to invoke the model `os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")`, and return the generated text.
  - [ ] 5.3 Update `POST /api/informe`: call `llamar_bedrock`; on success return `{"texto": ..., "fuente": "ia"}`; on any exception call `plantilla(equipo)` and return `{"texto": ..., "fuente": "plantilla"}`.
  - [ ] 5.4 Confirm that when Bedrock is unavailable the endpoint still returns HTTP 200 with `fuente: "plantilla"` and the rest of the dashboard is unaffected.

## Notes

- Never add new Python or npm dependencies; all required libraries are already in the stack.
- Task 5 (AI) requires a `.env` with Bedrock credentials for local testing; copy `.env.example` and fill in the workshop keys. The file must not be committed.
- `data/` is read-only; `backend/analisis/metricas.py` does not exist yet — that is built by another tool. Task 3 only wires the connector; do not create or modify `metricas.py`.
- Tailwind CSS version 3 is in use; do not use `@import "tailwindcss"` or `@theme` directives.
- Start Uvicorn for backend development with: `.venv/Scripts/uvicorn backend.main:app --reload`
- Start Vite for frontend development with: `cd dashboard && npm run dev`
