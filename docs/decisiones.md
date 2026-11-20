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

## Pendientes

- Prueba de sensibilidad del efecto principal sin las jugadas con `flag_linea`.
