# Revisión independiente: La Carrera Invisible

Fecha: 2026-11-20. Revisé el árbol de trabajo tal como está en disco: HEAD `90a77c8` más cambios sin commit en `backend/analisis/metricas.py`, `backend/main.py`, `dashboard/src/components/{Titular,TarjetaRival}.tsx` y `backend/informe.py`, que no está versionado. El titular revisado es el de esa versión sin commit. No modifiqué ningún archivo del proyecto. Los recálculos están en `_verif_revision.py`, `_verif_revision2.py` y `_verif_rev3.py`, que el `.gitignore` excluye.

## Lo que se verificó y está bien

| Punto | Resultado | Evidencia |
|---|---|---|
| 1. Fuga en los rasgos | **No hay fuga.** Los seis rasgos de cada cuadro usan solo las posiciones de ese cuadro y la posición del balón en el snap (`x_balon_snap`, `y_balon_snap`). No usan el evento de pase ni PFF. La etiqueta PFF solo entra al ajuste. | `estructura.py:76-97`, `preparar.py:192-195` |
| 1. Pre-registro | `estructura.py` no cambió después de `d2146f5`: `git diff d2146f5 HEAD --stat` no lo lista. l2 se elige por CV con bloques por partido dentro de las semanas 1-6. | `estructura.py:181-193` |
| 2. Dirección | Las 3 jugadas al azar (semilla 7) están bien. En las tres, la ofensiva queda detrás del balón (−2.0, −1.24, −1.82 yd), la defensa queda delante (+10.2, +5.0, +4.3 yd) y los dos defensores más profundos están a +26.9/+25.1, +10.0/+9.5 y +17.5/+5.8 yd. `110 − x` coincide con `dist_endzone` en las tres. Jugadas revisadas: 2021101702-2601 (left), 2021101011-2565 (right) y 2021092300-365 (right). | `_verif_revision2.py` |
| 2. Línea de scrimmage | Contra `yardlineSide`/`yardlineNumber` de `plays.csv` en las 6,380 jugadas, la diferencia mediana es de 0.36 yd. Solo el 1.6% difiere más de 2 yd (máximo 7.7), y eso es consistente con `flag_linea`. | `_verif_revision2.py` |
| 3. Zona de duda | Un cuadro indeterminado cuenta como "no coincide", es decir, como no revelado, porque `"indeterminado" != juega`. Recalculé `revela_t` y `evento_revela` cuadro por cuadro y coinciden en **1,279/1,279** jugadas con disfraz. Ninguna jugada tiene cuadros faltantes. | `preparar.py:333-343` |
| 3. Censura | Las jugadas sin revelación se censuran en `t_pase` y no se descartan: hay 0 descartadas, 636 censuradas, todas con `revela_t == t_pase`, y los 643 eventos tienen `revela_t < t_pase`. | `preparar.py:340-347` |
| 4. Conteos | Mi recálculo desde `jugadas.csv` **coincide con `resumen()`**: n del universo = 6,380 (todas con dist ≥ 20 y cobertura etiquetada), decididas = 4,606, con disfraz = 1,279, muestra del efecto = 1,168. A ciegas: 294/584 = 50.34%. Revelada: 295/584 = 50.51%. Los estratos de `contraste` también coinciden. El `exito` recalculado con la regla 40/60/100 + INT es idéntico fila por fila. | `_verif_revision.py` |
| 4. Tasa de éxito global | Recalculada: **3,033/5,849 = 51.86%**. `resumen()` no la reporta, así que no hay contra qué compararla. No es una diferencia, pero conviene publicarla (ver MENOR). | |
| 5. Bootstrap | Remuestrea **partidos completos** (`gameId`), no jugadas. | `modelos.py:129-145` |
| 5. Controles | Incluye down, distancia (3 tramos), tramo de `t_pase` (4 tramos), zona, n_rushers, shotgun y play action. | `metricas.py:135-152` |
| 6. Rogan-Gladen | Usa la sensibilidad (250/281 = 0.890) y la especificidad (126/163 = 0.773) de validación de las semanas 7-8, calculadas desde `validacion_jugadas.csv`. La confusión coincide con `validacion.json` gracias al assert de `preparar.py:366`. Recorta a [0,1]. | `metricas.py:81-107` |

## BLOQUEANTE

**B1. El titular afirma "La defensa gana la carrera" y los datos dan un empate.**
- Evidencia: el veredicto sale de `lanzado >= 0.5` (`metricas.py:300`), y `lanzado` se calcula sobre **todo el universo** (`metricas.py:340`, 64.0%), mientras que la mediana de 3.0 s es **solo de las jugadas con disfraz**. La estimación directa de la carrera es la fracción de disfraces lanzados a ciegas: **636/1,279 = 49.7%**, con IC90 de Wilson 47.4–52.0% y de bootstrap por partido 47.2–52.4%. El IC contiene el 50%. Entre las disfrazadas, el porcentaje lanzado a los 3.0 s es 58.8%, no 64%. Además, la mediana de Kaplan-Meier supone censura no informativa, y `descubrimiento.md:122` reconoce que no se cumple.
- Arreglo: en `_titular`, cambiar el veredicto por `f"La carrera está empatada: el QB lanzó antes de la revelación en el {p:.0%} de los disfraces (IC90 {lo:.0%}–{hi:.0%}, n={n})"`, con `p = mean(ciega)` entre las jugadas con disfraz y su IC por partido, y calcular `lanzado` sobre `_con_disfraz(j)`.

**B2. La afirmación "error no diferencial → sesgo hacia 0 → estimación conservadora" no se sostiene y va más allá del IC.**
- Evidencia: aparece en `README.md:11`, `docs/decisiones.md:65`, `docs/descubrimiento.md:116` y `metricas.py:17-19`. Que el lector no vea el resultado no vuelve no diferencial el error en "ciega". La clasificación "ciega" depende de que el lector se mantenga estable hasta el pase, y las jugadas más largas tienen más cuadros donde fallar. `descubrimiento.md:123` muestra que 286 de las 636 "ciegas" coincidieron con PFF y luego cambiaron. Ese error depende de `t_pase`, y el éxito también: cae de 61% con < 2 s a 40% con ≥ 4 s. Además, la muestra con disfraz la selecciona el mismo lector, que mezcla disfraces reales con errores en el snap. Con eso no se puede afirmar la dirección del sesgo, y la frase "un efecto real podría estar escondido" interpreta más allá de lo que dice un IC que contiene el 0.
- Arreglo: reemplazar la frase en los cuatro lugares por "El error del lector puede depender de t_pase, así que no podemos garantizar la dirección del sesgo; el IC90 (−6.6 a +2.3 pp) descarta efectos mayores que unos 7 pp en cualquier dirección".

## IMPORTANTE

**I1. Los sacks están fuera del universo, aunque la definición dice "sack = fracaso".**
- Evidencia: `preparar.py:178` y `preparar.py:27-28` excluyen todo lo que no tenga passResult C/I/IN, así que `plays.csv` tiene 543 sacks y ninguno entra al universo. El `passResult.isin(["S", ...])` de `preparar.py:353` es código muerto. Esto condiciona el análisis a "el QB alcanzó a lanzar", y el sack es justo el caso en que la defensa gana la carrera. La exclusión está declarada en `decisiones.md:43`, pero contradice la definición de éxito.
- Arreglo: renombrar el éxito a "éxito condicionado a que hubo pase" en el README, el dashboard y `decisiones.md`, o incluir los sacks con `exito=0` y `t_pase = cuadro del sack` (y censurados ahí) y volver a correr.

**I2. Rogan-Gladen aplica la sensibilidad y especificidad de semanas 7-8 a semanas 1-6, donde el lector está dentro de muestra, y ese cruce produce el "0%" de juega un alto.**
- Evidencia: el disfraz observado en juega cerrado es 8.3% en las semanas 1-6 contra 11.1% en 7-8. Con la sens/esp de validación, RG da **−4.2%** (recortado a 0) en 1-6 y **0.1%** en 7-8. En juega abierto da 58.4% en 1-6 y 61.5% en 7-8. Que el corregido de juega un alto sea 0 (IC 0–2.7%) se debe en buena parte a que el lector se ajustó con esas mismas etiquetas. A eso se suma que la sens/esp se midió a 2.0 s en pases de ≥ 3 s (`estructura.py:181`) y se aplica en el snap (`estructura.py:211`, límite 1 y 5 de `descubrimiento.md`).
- Arreglo: reportar el ID corregido calculado solo con las semanas 7-8 (`_tasas_por_clase(d[d.week >= 7])`) como cifra principal, o como sensibilidad junto a la actual.

**I3. El lector no está validado en el snap, y la asimetría del disfraz podría ser en parte un desplazamiento de distribución.**
- Evidencia: en juega abierto, el número de defensores a ≥ 10 yd es 1.83 en el snap y 2.85 a 2.0 s, y la profundidad del más profundo es 15.0 yd en el snap y 18.7 yd a 2.0 s. El modelo aprendió "pocos profundos = cerrado" a 2.0 s, y en el snap todos están más cerca. Atenuante: la regla geométrica, que no se entrenó, también encuentra la asimetría en el snap: 52.7% en juega abierto (n = 2,349) contra 13.7% en juega cerrado (n = 3,275). Pero el 60% de los "disfrazados" de juega abierto tiene 2 o más defensores a ≥ 10 yd en el snap.
- Arreglo: agregar a `descubrimiento.md` la tabla del ID de la regla en el snap como segundo lector y decir explícitamente que la magnitud (59%) no es identificable sin una etiqueta de estructura en el snap.

**I4. El control de t_pase es grueso, y t_pase puede ser mediador.**
- Evidencia: el último tramo (≥ 3.0 s) abarca éxitos de 53% a 40%, y dentro de él las ciegas duran más que las leídas (3.88 s contra 3.75 s), de modo que queda confusión residual en contra de "ciega". Recalculé el efecto marginal promedio con B=200 y semilla 2026, y el IC90 incluye el 0 en todas las especificaciones (la original da −6.2 a +2.3 con B=200):

  | Control de t_pase | Efecto marginal promedio | IC90 |
  |---|---|---|
  | 4 tramos (original) | −1.88 pp | −6.2 a +2.3 |
  | escalones cada 0.25 s | −1.59 pp | −5.5 a +2.7 |
  | cúbico | −1.46 pp | −5.7 a +2.8 |
  | sin t_pase | −0.89 pp | −5.0 a +3.0 |

  Además, "ciega" es por construcción `revela_t > t_pase`. Condicionado a t_pase, la comparación es "disfraz que se revela lento contra disfraz que se revela rápido al mismo t_pase", y no "el QB leyó o no leyó". Si el QB suelta el balón *porque* vio la revelación, t_pase es mediador, y ajustar por él puede introducir sesgo.
- Arreglo: reportar la tabla de arriba en `descubrimiento.md` y cambiar el método a escalones de 0.25 s o a un spline, más una línea que diga que t_pase puede ser mediador.

**I5. El texto del dashboard y del informe va más allá del resultado.**
- Evidencia: `Titular.tsx:17` muestra el −1.9 pp en `text-5xl text-red-600`, el énfasis visual de un hallazgo negativo, aunque el IC contiene el 0. `informe.py:91` recomienda "practica lecturas rápidas antes de la revelación", y ningún resultado respalda esa recomendación: el estrato crudo < 2.5 s apunta en contra, con −9.2 pp, sin pre-registro. El titular dice "casi siempre" (`metricas.py:296`) y "59%" sin su IC (51–66%); el 79% observado de disfraces que son "muestra un alto y juega dos" pasa a "casi siempre" solo porque RG recorta a 0 (ver I2).
- Arreglo: usar un color neutro cuando el IC contiene el 0 (`efecto.ic90[0] < 0 && efecto.ic90[1] > 0 ? 'text-gray-700' : ...`), quitar la recomendación de `informe.py:91` y escribir en el titular "en el 59% (IC90 51–66%) de las coberturas de dos altos".

## MENOR

- **M1.** `_validacion` (`metricas.py:272-274`) compara la exactitud del modelo con umbral 0.5 (sin indeterminados) contra la regla contando sus indeterminados como error (`regla_exactitud_en_todas`). La comparación no es pareja. Arreglo: comparar contra `regla_exactitud_en_decididas` con su tasa de decisión, o el modelo de 3 clases "en todas" contra la regla "en todas".
- **M2.** B = 300 (`metricas.py:36`) es poco para percentiles al 5/95%: mi corrida con B=200 movió el extremo inferior de −6.6 a −6.2. Arreglo: `B = 2000` para el efecto y el ID, igual que en `estructura.py:55`.
- **M3.** El bootstrap de RG remuestrea el universo y la validación por separado (`metricas.py:118-119`), aunque los partidos de las semanas 7-8 están en los dos. Arreglo: remuestrear los partidos una sola vez y derivar de esa réplica tanto las tasas como la sens/esp.
- **M4.** La "zona roja" (`metricas.py:65`) solo puede contener `dist_endzone == 20` dentro del universo. Hay 1 jugada y la columna se elimina. Arreglo: quitar la categoría o redefinir los cortes (20-35 / 35-50 / > 50).
- **M5.** `resumen()` no publica la tasa de éxito global (51.86%, n = 5,849). Arreglo: añadir `"exito_global": {"valor", "ic90", "n"}` al resumen y al README.
- **M6.** `README.md:9` dice "La mitad de los disfraces sigue oculta a los 3.0 s" sin la salvedad de censura informativa que sí está en `descubrimiento.md:122`. Arreglo: añadir "(Kaplan-Meier, suponiendo que el pase no depende de la revelación)".
- **M7.** El árbol de trabajo tiene cambios sin commit en `metricas.py`, que generan el titular revisado, y `informe.py` no está versionado. Arreglo: hacer commit antes de entregar, para que el número publicado se pueda reproducir desde un hash.

## Calificación de solidez: **3 / 5**

La tubería es reproducible y está bien construida: cuadros, dirección, censura, conteos y bootstrap por partido coinciden exactamente con mi recálculo, y el pre-registro se respetó. Lo que baja la calificación es la interpretación. El titular declara un ganador de una carrera empatada (B1) y defiende el efecto nulo con un argumento de sesgo que no aplica (B2). El ID corregido y la frase "casi siempre" descansan en trasladar la sens/esp de 2.0 s al snap y de fuera de muestra a dentro de muestra (I2, I3). Corregidos B1 y B2, el resultado defendible es este: hay un disfraz frecuente en las coberturas de dos altos, la carrera está empatada y no se detecta diferencia de éxito mayor que unos ±6 pp.

## Las 3 preguntas más difíciles de un jurado de estadística

**1. "Su lector se entrenó a 2.0 s en pases largos. ¿Cómo saben que el 'disfraz' en el snap no es el lector equivocándose fuera de su distribución?"**
No lo podemos saber del todo. En el snap los safeties están más cerca: en juega abierto hay 1.83 defensores a ≥ 10 yd en el snap contra 2.85 a 2.0 s. Pero una regla geométrica que no se entrenó encuentra la misma asimetría en el snap: 52.7% de disfraz en juega abierto contra 13.7% en juega cerrado. Que haya disfraz y que vaya en la dirección "un alto → dos altos" es robusto a cambiar de lector. Su magnitud (59%) no es identificable sin una etiqueta de estructura en el snap.

**2. "'A ciegas' es casi por definición 'lanzó rápido'. ¿El −1.9 pp no es solo el efecto de soltar rápido?"**
Los datos no muestran un efecto que explicar. El crudo es 50.3% contra 50.5% (n = 584 y 584). Con t_pase en 4 tramos da −1.9 pp, con escalones de 0.25 s −1.6 pp (IC90 −5.5 a +2.7), cúbico −1.5 pp (IC90 −5.7 a +2.8) y sin t_pase −0.9 pp (IC90 −5.0 a +3.0). Ninguna especificación excluye el 0. Lo que se puede sostener es que no detectamos una diferencia mayor que unos 6 pp. No se puede sostener que lanzar a ciegas no importe, porque t_pase puede ser mediador y el estrato < 2.5 s (−9.2 pp crudo) no estaba pre-registrado.

**3. "¿Quién gana la carrera?"**
Nadie, con estos datos. En el 49.7% de los disfraces el QB lanzó antes de la revelación (IC90 47.4–52.0%, n = 1,279). La mediana de revelación de 3.0 s (IC90 2.9–3.1) supone que el QB no lanza en respuesta a la revelación, y además el universo excluye los 543 sacks, que es donde la defensa gana con más claridad. Con los sacks, la balanza podría inclinarse hacia la defensa, pero eso no está medido.
