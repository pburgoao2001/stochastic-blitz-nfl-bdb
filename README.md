# La Carrera Invisible

La defensa esconde su cobertura y el QB intenta leerla antes de soltar el balón. Con el tracking de la NFL (Big Data Bowl, temporada 2021, semanas 1-8) medimos **cuándo la defensa revela su estructura** (centro del campo cerrado o abierto) y lo comparamos con la cobertura real de PFF.

## Hallazgo

- Corrigiendo el error del lector, la defensa disfraza su estructura en el **21%** (IC90 18-24%) de los pases que se pueden leer en el snap, n = 4,606. El valor observado es 27.8%.
- Casi siempre el disfraz consiste en **mostrar un alto y jugar dos altos**.
- La mitad de los disfraces sigue oculta a los **3.0 s** (IC90 2.9-3.1). Para entonces el QB ya lanzó el 64% de los pases.
- Lanzar antes de que se revele **no se asocia con una diferencia clara de éxito**: -1.9 pp (IC90 -6.6 a +2.3, n = 1,168). El resultado se mantiene con Mantel-Haenszel y sin las jugadas con `flag_linea`.
- El ranking por defensa es moderadamente estable: split-half r = 0.68 y Spearman-Brown 0.81; con divisiones al azar, r ≈ 0.53. Además refleja en parte la mezcla de coberturas: r = 0.53 con la tasa de dos altos.
- **Nota de interpretación:** el error del lector es no diferencial (nunca ve el resultado de la jugada), así que el efecto de jugar "a ciegas" está sesgado hacia 0. Es una estimación conservadora. Como el IC incluye el 0, tampoco permite afirmar su signo. Es una asociación, no un efecto causal.

Detalle, tablas y límites en [docs/descubrimiento.md](docs/descubrimiento.md); las decisiones de método, en [docs/decisiones.md](docs/decisiones.md).

## Cómo se calcula

El stack es fijo: Python 3.12 con pandas, numpy y la biblioteca estándar. En WSL se usa `./.venv/Scripts/python.exe`. Desde la raíz:

```sh
./.venv/Scripts/python.exe -m backend.analisis.preparar           # cuadros: data/derivado/frames_def.pkl, jugadas_base.csv
./.venv/Scripts/python.exe -m backend.analisis.estructura         # lector de estructura y validación (semanas 7-8)
./.venv/Scripts/python.exe -m backend.analisis.preparar jugadas   # data/derivado/jugadas.csv
./.venv/Scripts/python.exe -m backend.analisis.metricas           # revisión del contrato de la API
```

- `backend/analisis/modelos.py`: Wilson, logística con IRLS, AUC, Brier, bootstrap por partido, Kaplan-Meier con Greenwood y beta-binomial empírico. Todo con semilla fija.
- `backend/analisis/metricas.py`: `resumen()`, `equipos()` y `rival()`, con la forma exacta del contrato de la API (`.kiro/specs/la-carrera-invisible/design.md`). Solo leen los CSV/JSON versionados de `data/derivado/`, así que la API los calcula al arrancar sin escribir en disco.
- Los intervalos son de 90% con bootstrap por partido (`gameId`), salvo donde se indica Wilson o Greenwood. El lector se pre-registró (commit `d2146f5`) antes de mirar la validación y no se reajustó después.

## Datos

`data/` es de solo lectura y no se versiona; solo se versionan los derivados `data/derivado/*.csv|json`. El tracking viene recortado: va de 0.5 s antes del snap a 0.5 s después del pase.
