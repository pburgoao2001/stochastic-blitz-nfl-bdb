# Decisiones de análisis: La Carrera Invisible

Registro en orden. Cada número sale de los scripts de `backend/analisis/` y queda en `data/derivado/*.json`.

## Datos (`preparar.py`)

- Los organizadores recortaron el tracking: va de 5 cuadros antes del primer evento de snap a 5 cuadros después del primer evento de pase. Por eso la revelación se mide entre el snap y el pase; antes del snap solo hay 0.5 s.
- Snap: primer cuadro con `ball_snap`; si no hay, `autoevent_ballsnap`. Lo confirma la velocidad del balón: mediana de 0.03 yd/s en el cuadro del snap y 4.0 yd/s en el siguiente.
- Pase: primer cuadro con `pass_forward`; si no hay, `autoevent_passforward`.
- Coordenadas normalizadas para que la ofensiva ataque hacia +x: si `playDirection == "left"`, x = 120 − x, y = 53.3 − y.
- **Solo pases (passResult C, I, IN): 7,541 jugadas.** Las 42 sacks o scrambles que tienen evento de pase quedan fuera y aparecen en `exclusiones_preparar.csv`.
- **Profundidad** = x − x del balón en el snap. **Zona del campo**: `dist_endzone` = 110 − x normalizada del balón en el snap. No se usa `absoluteYardlineNumber`, porque está en x cruda (sin normalizar).
- **`flag_linea`**: |absoluteYardlineNumber − x cruda del balón en el snap| > 2 yd, en 121 jugadas del análisis. Se quedan, y al final se corre el efecto principal sin ellas como prueba de sensibilidad.

## Lector de estructura (`estructura.py`)

Pre-registrado en el commit `d2146f5`, antes de mirar las semanas 7-8. Después de validar no se reajusta nada.

- Rasgos por cuadro con los defensores a profundidad ≥ 5 yd: `n10`, `n15`, `dmid_campo`, `dmid_balon`, `separacion` y `prof1`. Cuando nadie llega a 5 yd, `prof1` = 5.0, el umbral del conjunto. Ese respaldo lo elegí yo, porque la especificación no lo fijaba, y aplica a 1,988 de 229,439 cuadros.
- Verdad PFF: **cerrado** = Cover-1 y Cover-3; **abierto** = Cover-2, 2-Man, Quarters y Cover-6. El resto queda fuera.
- Entrenamiento: semanas 1-6, t_pase ≥ 3.0 s, un cuadro por jugada a 2.0 s del snap. `logit_irls` elige l2 ∈ {0.1, 1, 10} por validación cruzada de 5 bloques por partido (log-loss). Eligió l2 = 10, prácticamente empatado: 0.4985 contra 0.4987.
- Validación: semanas 7-8 con el mismo criterio, corrida una sola vez. Las exactitudes llevan IC 90% de Wilson, como se pidió, y además bootstrap por partido. AUC y Brier llevan bootstrap por partido.
- Clase final por cuadro: P(cerrado) ≥ 0.65 es cerrado, ≤ 0.35 es abierto y lo de en medio es indeterminado.

## La carrera (`preparar.py jugadas` y `metricas.py`)

Decisiones tomadas antes de calcular el efecto:

1. **Universo:** `dist_endzone` ≥ 20 y cobertura con etiqueta (un alto o dos altos). Quedan 6,380 jugadas.
2. **Muestra:** solo cuenta si el lector decide en el snap (P ≥ 0.65 o ≤ 0.35). Las indeterminadas en el snap (1,774) quedan fuera del análisis de disfraz.
3. **Disfraz** = muestra decidida distinta de juega. Se reportan el ID observado y el ID corregido con Rogan-Gladen, calculado dentro de cada clase de PFF con la sensibilidad y la especificidad del lector de 3 clases cuando decide (semanas 7-8). El bootstrap remuestrea por partido el universo y, por separado, la validación. **El titular usa el corregido.** En la API, `id_liga` y `equipos` están en escala observada, que es la comparable entre sí.
4. **revela_t:** primer cuadro desde el cual el lector decide la clase de PFF y ya no cambia hasta el pase. Si eso no pasa antes del cuadro del pase, se censura en `t_pase` (Kaplan-Meier).
5. El error del lector depende de t_pase, así que el sesgo del efecto puede ir en cualquier dirección. Queda escrito en `descubrimiento.md` y en el `README`. Corregido tras la revisión (B2).
6. **Sensibilidad:** efecto principal sin `flag_linea`, -1.4 pp (IC90 -6.2 a +2.7, n = 1,146), contra -1.9 pp (IC90 -6.6 a +2.3, n = 1,168) completo. **Hecha.**

Definiciones:
- **Éxito:** queda vacío si hubo castigo (`foulName1`). En 1.er down, `prePenaltyPlayResult` ≥ 0.4·yardsToGo; en 2.º, ≥ 0.6·yardsToGo; en 3.º y 4.º, ≥ yardsToGo. Las intercepciones cuentan como fracaso.
- **Efecto:** logística por IRLS de éxito sobre ciega, entre jugadas con disfraz. Controles: tramos de t_pase (<2.0, 2.0-2.5, 2.5-3.0, ≥3.0), down, distancia (1-3, 4-6, 7+), zona (propia > 50, medio 20-50, roja ≤ 20; la roja tiene 1 jugada), n_rushers, shotgun y play action. Se usa l2 = 1e-6 solo por estabilidad numérica. Se reporta el efecto marginal promedio en pp. Convergieron las 300 réplicas; si no, se usaría Mantel-Haenszel.
- **equipos():** beta-binomial empírico sobre disfraz/decididas por defensa (mu = 0.275, kappa = 35.5). El IC sale de 20,000 sorteos de la posterior. La mediana de revelación queda vacía si el equipo tiene menos de 20 jugadas con disfraz.
- **rival():** P(juega un alto | lo que muestra en el snap), encogida hacia la liga con kappa beta-binomial.
  - La celda de la liga es la de la situación pedida si tiene al menos 30 jugadas. Si no, se quita la distancia, y si aún no alcanza, también el down.
  - kappa no puede ser mayor que el número de jugadas de esa celda.
  - Con n = 0 se muestra la tendencia de la liga con su IC90. `p` e `ic90` nunca son `null`.
- **Curva de lanzamiento** (`revelacion.lanzamiento`): se calcula sobre las 1,279 jugadas con disfraz, la misma población que la curva de Kaplan-Meier, y ya no sobre todo el universo. La `validacion_tarjeta` es el Brier en semanas 7-8 usando las semanas 1-6: mezcla 0.197, liga 0.203, equipo 0.199. El éxito por formación lleva IC de Wilson.
## P6b: titular final y estabilidad

- **Titular:** se genera con una plantilla a partir de los números calculados: mediana de revelación y su IC, % de pases lanzados a esa mediana, disfraz corregido en coberturas de dos altos y efecto de lanzar a ciegas. Comprobé que es idéntico, carácter por carácter, al texto pedido.
- **Estabilidad (`resumen()["estabilidad"]`):** split-half del ID por defensa. Se comparan los partidos impares (1.º, 3.º, …) contra los pares de cada defensa, en orden cronológico, con Bayes empírico (beta-binomial) en cada mitad. Se reportan la r de Pearson entre las medias posteriores de las dos mitades y Spearman-Brown, 2r/(1 + r).
- **Titular, corregido tras la revisión (B1):** el veredicto sale de la fracción de disfraces lanzados antes de la revelación, 636/1,279 = 49.7%, con IC90 por bootstrap por partido de 47.3 a 52.3 (B = 300, semilla 2026). Como el IC contiene el 50%, el titular dice "la carrera es un volado". El IC de Wilson (47.4-52.0) no se usa porque es por jugada. El 64% salió del titular: se calculaba sobre todos los pases y no solo sobre los disfrazados.
- **Intervalo de la estabilidad:** el bootstrap por partido queda sesgado hacia abajo, porque remuestrear partidos con reemplazo duplica jugadas dentro de una mitad y mete ruido. Por eso se reporta el IC Fisher z sobre los 32 equipos y, además, la variación de r entre 50 divisiones al azar balanceadas por equipo (`cifras_extra()`).
