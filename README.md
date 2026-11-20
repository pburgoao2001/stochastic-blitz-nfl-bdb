# La Carrera Invisible

La defensa esconde su cobertura y el QB intenta leerla antes de soltar el balón. Con el tracking de la NFL (Big Data Bowl, temporada 2021, semanas 1-8) medimos **cuándo la defensa revela su estructura** (centro del campo cerrado o abierto) y lo comparamos con la cobertura real de PFF.

## Hallazgo

- Corrigiendo el error del lector, la defensa disfraza su estructura en el **21%** (IC90 18-24%) de los pases que se pueden leer en el snap, n = 4,606. El valor observado es 27.8%.
- Casi siempre el disfraz consiste en **mostrar un alto y jugar dos altos**.
- **La carrera es un volado:** cuando la defensa disfraza, el QB lanza antes de la revelación en el 49.7% de las jugadas (IC90 47.3-52.3, n = 1,279). La mediana de revelación de Kaplan-Meier es 3.0 s (IC90 2.9-3.1), suponiendo que el momento del pase no depende de la revelación.
- Lanzar antes de que se revele **no se asocia con una diferencia clara de éxito**: -1.9 pp (IC90 -6.6 a +2.3, n = 1,168). El resultado se mantiene con Mantel-Haenszel y sin las jugadas con `flag_linea`.
- El ranking por defensa es moderadamente estable: split-half r = 0.68 y Spearman-Brown 0.81; con divisiones al azar, r ≈ 0.53. Además refleja en parte la mezcla de coberturas: r = 0.53 con la tasa de dos altos.
- **Nota de interpretación:** el error del lector depende de t_pase, así que el sesgo del efecto puede ir en cualquier dirección. Es una asociación, no un efecto causal.

## Límites principales

- **Sacks fuera del universo:** los 543 sacks no entran, porque sin pase no hay t_pase. El análisis está condicionado a que el QB alcanzó a lanzar.
- **El lector no está validado en el snap:** se validó a 2.0 s en pases de ≥ 3 s. Aun así, una regla geométrica que no se entrenó encuentra la misma asimetría en el snap (revisión independiente, `docs/revision.md`).
- **t_pase podría ser mediador:** según cómo se controle t_pase, el efecto da −1.6, −1.5 o −0.9 pp, y ningún IC excluye 0 (revisión independiente).

Detalle, tablas y límites en [docs/descubrimiento.md](docs/descubrimiento.md); las decisiones de método, en [docs/decisiones.md](docs/decisiones.md).

## Cómo se calcula

El stack es fijo: Python 3.12 con pandas, numpy y la biblioteca estándar. En WSL se usa `./.venv/Scripts/python.exe`. Desde la raíz:

```sh
./.venv/Scripts/python.exe -m backend.analisis.preparar           # cuadros: data/derivado/frames_def.pkl, jugadas_base.csv
./.venv/Scripts/python.exe -m backend.analisis.estructura         # lector de estructura y validación (semanas 7-8)
./.venv/Scripts/python.exe -m backend.analisis.preparar jugadas   # data/derivado/jugadas.csv
./.venv/Scripts/python.exe -m backend.analisis.preparar replays   # data/derivado/replays.json (3 repeticiones por regla, docs/replays.md)
./.venv/Scripts/python.exe -m backend.analisis.metricas           # revisión del contrato de la API
```

- `backend/analisis/modelos.py`: Wilson, logística con IRLS, AUC, Brier, bootstrap por partido, Kaplan-Meier con Greenwood y beta-binomial empírico. Todo con semilla fija.
- `backend/analisis/metricas.py`: `resumen()`, `equipos()` y `rival()`, con la forma exacta del contrato de la API (`.kiro/specs/la-carrera-invisible/design.md`). Solo leen los CSV/JSON versionados de `data/derivado/`, así que la API los calcula al arrancar sin escribir en disco.
- Los intervalos son de 90% con bootstrap por partido (`gameId`), salvo donde se indica Wilson o Greenwood. El lector se pre-registró (commit `d2146f5`) antes de mirar la validación y no se reajustó después.

## Datos

`data/` es de solo lectura y no se versiona; solo se versionan los derivados `data/derivado/*.csv|json`. El tracking viene recortado: va de 0.5 s antes del snap a 0.5 s después del pase.
