# Requirements Document

## Introduction

"La Carrera Invisible" is a weekly NFL preparation tool for offensive coordinators, scouts, and commentators. The core thesis is that on every passing play the defense disguises its coverage and the QB must read it before releasing the ball. The tool surfaces how often defenses stay disguised, when they reveal themselves, and how that shapes play outcomes — all in a single-page dashboard backed by a FastAPI + React stack.

## Requirements

### 1. API endpoints with mock data

**User story:** As a developer, I want all five API endpoints to return structurally correct responses from in-memory mock data so the frontend can be built and tested before real computation is wired in.

#### Acceptance Criteria

- 1.1 `GET /health` returns `{"status": "ok"}` and is never modified.
- 1.2 `GET /api/resumen` returns a JSON object matching the full contract: `titular`, `n_jugadas`, `id_liga` (with `valor`, `ic90[lo,hi]`, `n`), `efecto` (`valor_pp`, `ic90`, `n`, `metodo`), `contraste` (array of strata each with `estrato`, `ciega` and `leida` objects), `revelacion` (`mediana_s`, `ic90`, `prob_disfrazado_2_5s`, `curva` array, `lanzamiento` array), `validacion` (all six fields), `estabilidad` (`r`, `spearman_brown`), and `sankey` (`nodes` and `links` arrays).
- 1.3 `GET /api/equipos` returns a JSON array of team objects each containing `equipo`, `id` (with `valor`, `ic90`, `n`), and `revelacion_mediana_s`, ordered by `id.valor` descending.
- 1.4 `GET /api/rival` accepts query parameters `equipo`, `down`, and `distancia` (values `"1-3"`, `"4-6"`, `"7+"`); returns `equipo`, `filas` array, `formaciones` array, `validacion_tarjeta` object, and `frases` array of three strings.
- 1.5 `GET /api/replays` returns a JSON array where each item has `gameId`, `playId`, `descripcion`, `frames` (array of `{t, def, of, balon, estructura}`), and `eventos` (`snap`, `revela`, `lanza`).
- 1.6 `POST /api/informe` accepts `{"equipo": string}` and returns `{"texto": string, "fuente": "ia" | "plantilla"}`.
- 1.7 All endpoints compute or construct their response at startup and serve from memory; no file writes occur at runtime.
- 1.8 When mock data is active, every endpoint includes a response header `X-Data-Source: mock`.

### 2. Single-page dashboard consuming the API

**User story:** As a scout or coordinator, I want a single-page dashboard that shows disguise rate, reveal timing, formation tendencies, and rankings so I can prepare for the upcoming opponent in one place.

#### Acceptance Criteria

- 2.1 The page renders six named sections: Titular, La Carrera, Sankey, Repetición, Ranking, and Tarjeta del Rival.
- 2.2 The Titular section shows the effect size (`efecto.valor_pp`) with a 90 % confidence band and a horizontal bar chart comparing disguised vs. read coverages per stratum from `contraste`.
- 2.3 "La Carrera" section renders two overlaid time-series lines using Recharts: the disguised-defense curve (`revelacion.curva`) with its IC band, and the cumulative launch-time curve (`revelacion.lanzamiento`), both on the same time axis.
- 2.4 The Sankey section renders the nodes and links from `sankey` using Recharts' `Sankey` component; node labels are the `name` field.
- 2.5 The Ranking section renders a horizontal bar chart of all teams from `/api/equipos`, sorted by `id.valor` descending, with error bars for `ic90`.
- 2.6 The Tarjeta del Rival section contains a team selector (populated from `/api/equipos`), a down selector, a `distancia` selector, and a "Generar informe" button that calls `POST api/informe`.
- 2.7 The informe result is displayed below the button with a label that reads "Generado por IA" when `fuente === "ia"` or "Generado por plantilla" when `fuente === "plantilla"`.
- 2.8 While mock data is active (detected via the `X-Data-Source: mock` header), a persistent banner reads "datos de prueba" and is visible in all sections.
- 2.9 All `fetch` calls use relative paths beginning with `api/` (no leading slash, no `localhost`, no absolute URLs).
- 2.10 The Vite config contains a proxy from `/api` to `http://localhost:8000` and retains `base: './'`.

### 3. Connect to real analytics module

**User story:** As a data scientist, I want the API to switch from mock data to computed results from `backend/analisis/metricas.py` as soon as that module exists, without changing the frontend.

#### Acceptance Criteria

- 3.1 When `backend/analisis/metricas.py` is present and importable, the API loads its output at startup and uses it instead of the built-in mocks.
- 3.2 The shape and field names of the real data match the mock contract exactly; the frontend requires no changes.
- 3.3 When real data is in use, the `X-Data-Source: mock` header is absent and the "datos de prueba" banner does not appear.
- 3.4 If importing `metricas.py` raises any exception, the API falls back to mocks, logs the error to stderr, and continues serving.

### 4. Animated replay viewer

**User story:** As a commentator, I want to watch an animated replay of each tracking play so I can explain the coverage disguise visually.

#### Acceptance Criteria

- 4.1 The Repetición section renders a simplified football field (green rectangle, yard lines every 10 yards, end zones).
- 4.2 For the selected play from `/api/replays`, the animation moves each defensive player (`frames[t].def`), each offensive player (`frames[t].of`), and the ball (`frames[t].balon`) frame by frame.
- 4.3 The section provides Play, Pause, and Reset controls.
- 4.4 `eventos.snap`, `eventos.revela`, and `eventos.lanza` are marked as vertical event lines or annotations on a progress bar.
- 4.5 When `/api/replays` returns an empty array or is unreachable, the section shows a placeholder message "Repetición disponible próximamente" without throwing.

### 5. AI report generation

**User story:** As a coordinator, I want the "Generar informe" button to produce a natural-language scouting note using Amazon Bedrock when available, or a structured template when it is not.

#### Acceptance Criteria

- 5.1 `POST /api/informe` calls Amazon Bedrock via Strands Agents using the model from `os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")` and the region from `os.environ.get("AWS_REGION", "us-east-1")`.
- 5.2 The boto3 client is created with region only: `boto3.client("bedrock-runtime", region_name=region)`; no credentials are passed in code.
- 5.3 If the Bedrock call succeeds, the response includes `"fuente": "ia"`.
- 5.4 If the Bedrock call raises any exception, the endpoint falls back to a template string built from mock or real data for the requested team and returns `"fuente": "plantilla"`.
- 5.5 The dashboard shows its main findings (Titular, La Carrera, Ranking) regardless of whether the AI endpoint succeeds.

### 6. Deployment contract compliance

**User story:** As the AWS deployment system, I need the app to meet the platform contract so it can be hosted without modification.

#### Acceptance Criteria

- 6.1 `backend/main.py` exposes a FastAPI instance named `app`.
- 6.2 `GET /health` returns `{"status": "ok"}`.
- 6.3 `vite build` runs without errors and produces output in `dashboard/dist`.
- 6.4 No new Python or npm dependencies are added beyond those already declared.
- 6.5 `data/` files are read-only and accessed via paths relative to the project root.
- 6.6 No code references `localhost`, `127.0.0.1`, or any absolute URL in dashboard source files (the Vite proxy config is the sole exception).
- 6.7 Python code runs inside `.venv`; no system Python is used.
