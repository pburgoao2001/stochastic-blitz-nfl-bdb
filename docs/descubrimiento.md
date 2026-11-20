# Descubrimiento: La Carrera Invisible

La defensa esconde su cobertura y el QB intenta leerla antes de soltar el balón. Con el tracking medimos cuándo la defensa revela su estructura (centro del campo **cerrado**: un safety alto; **abierto**: dos altos) y lo comparamos con la cobertura real de PFF. Los datos son de la temporada 2021, semanas 1-8, solo pases.

Todas las cifras salen de `backend/analisis/` (`python -m backend.analisis.metricas`). Llevan n e intervalo de 90%: bootstrap por partido, salvo donde se indica Wilson o Greenwood.

## Universo

- **6,380 pases** con `dist_endzone` ≥ 20 y cobertura con etiqueta, de los 7,541 del análisis. Se excluyen 966 por estar a menos de 20 yardas de la end zone y 195 por tener cobertura sin etiqueta: Cover-0 138, Prevent 29, Bracket 25, Miscellaneous 3.
- El lector decide en el snap en **4,606** de esos pases. Los 1,774 que quedan indeterminados en el snap salen del análisis de disfraz.

## Resultados

| Medida | Valor | IC 90% | n |
|---|---|---|---|
| Índice de disfraz observado | 27.8% | 26.1-29.4 | 4,606 |
| **Índice de disfraz corregido** (Rogan-Gladen) | **21.0%** | 18.4-23.9 | 4,606 |
| … cuando juega dos altos (observado / corregido) | 61.8% / 59.1% | 58.3-65.3 / 51.5-66.0 | 1,638 |
| … cuando juega un alto (observado / corregido) | 9.0% / 0% | 7.9-10.2 / 0-2.7 | 2,968 |
| Mediana del tiempo hasta revelar (Kaplan-Meier) | 3.0 s | 2.9-3.1 | 1,279 (643 revelaciones) |
| Probabilidad de seguir disfrazado a 2.5 s | 0.60 | 0.57-0.62 (Greenwood) | 1,279 |
| **Disfraces lanzados antes de la revelación** (a ciegas) | **49.7%** | 47.3-52.3 | 1,279 |
| Jugadas con disfraz ya lanzadas a 2.5 s / a 3.0 s | 35.1% / 58.8% | 32.1-37.7 / 56.0-61.4 | 1,279 |
| **Efecto de lanzar a ciegas** (efecto marginal promedio) | **-1.9 pp** | -6.6 a +2.3 | 1,168 |
| … Mantel-Haenszel por tramos de t_pase | -1.1 pp | -5.7 a +3.0 | 1,168 |
| … sin las jugadas con `flag_linea` (sensibilidad) | -1.4 pp | -6.2 a +2.7 | 1,146 |

Éxito crudo entre jugadas con disfraz, con IC de Wilson:

| Tramo de t_pase | A ciegas | Leída |
|---|---|---|
| menos de 2.5 s | 50.9% (45.3-56.5), n = 212 | 60.1% (53.4-66.5), n = 148 |
| 2.5 s o más | 50.0% (45.8-54.3), n = 372 | 47.3% (43.3-51.2), n = 436 |
| total | 50.3% (47.0-53.7), n = 584 | 50.5% (47.1-53.9), n = 584 |

**Las dos curvas de la carrera comparan la misma población.** En el dashboard, la curva de lanzamiento (`revelacion.lanzamiento`) se calcula sobre las 1,279 jugadas con disfraz, que son las mismas de la curva de Kaplan-Meier. Antes usaba las 6,380 jugadas del universo, y con eso a los 2.5 s y a los 3.0 s ya se había lanzado el 38.8% y el 64.0% de los pases. Esa comparación mezclaba poblaciones distintas.

**Lectura.** El disfraz casi siempre va en una dirección: la defensa **muestra un alto en el snap y termina jugando dos altos**. Ocurre en el 59% de las coberturas de dos altos ya corregido el error del lector; lo contrario prácticamente no aparece. **La carrera es un volado:** cuando la defensa disfraza, el QB lanza antes de la revelación en el 49.7% de las jugadas (IC90 47.3-52.3). La mediana de revelación de 3.0 s supone que el momento del pase no depende de la revelación (ver límite 2). Lanzar antes de que se revele no se asocia con una diferencia clara de éxito. La tabla cruda sugiere que lanzar a ciegas va peor en los pases rápidos (< 2.5 s), pero los intervalos se traslapan y no hay una prueba pre-registrada de esa interacción.

## Ranking por defensa

El ID por defensa usa Bayes empírico: una beta-binomial con mu = 0.275 y kappa = 35.5, e IC 90% de la posterior. Las cinco defensas más altas son TB 46.4% (40.8-52.2, n = 175), ATL 40.2% (34.2-46.4, n = 138), NYG 37.8% (32.3-43.5, n = 165), KC 34.1% (28.2-40.4, n = 125) y DET 33.7% (27.6-40.1, n = 121).

- **El ranking refleja en parte la mezcla de coberturas, no solo cuánto disfraza cada defensa.** Casi todo el disfraz consiste en mostrar un alto y jugar dos altos, así que una defensa que juega más coberturas de dos altos tiene más ocasiones de disfrazar. El ID observado por equipo tiene **r = 0.53** con su tasa de dos altos (IC90 0.34-0.72; 32 equipos, bootstrap por partido). ATL (60% de dos altos) y TB (53%) encabezan las dos listas, mientras que HOU juega 50% de dos altos y su ID observado es de solo 8%. Para comparar cuánto esconde cada defensa conviene mirar el disfraz dentro de cada clase de cobertura.
- **Estabilidad (split-half):** con partidos impares contra pares de cada defensa y Bayes empírico en cada mitad, **r = 0.68 y Spearman-Brown = 0.81** (32 equipos; IC90 de r 0.48-0.81 por Fisher z sobre los equipos).
  - Con 50 divisiones al azar balanceadas por equipo, r promedia 0.53 (p5-p95 0.40-0.66), así que la división pre-especificada salió en el extremo alto.
  - El bootstrap por partido no sirve para esta medida: al duplicar jugadas dentro de una mitad sesga r hacia abajo (mediana 0.44, con el 98% de las réplicas por debajo del valor puntual).
  - r supera 0.3 en todas las versiones. El ranking separa bien los extremos, pero no a defensas vecinas con intervalos traslapados.

## Cómo interpretar el efecto

- **Dirección del sesgo:** el error del lector depende de t_pase, así que el sesgo del efecto puede ir en cualquier dirección. Por ejemplo, las jugadas largas tienen más cuadros en los que el lector puede cambiar antes del pase (límite 3), y el éxito también depende de t_pase.
- Es una asociación ajustada por tramo de t_pase, down, distancia, zona, n_rushers, shotgun y play action. **No es un efecto causal.**

## Límites

1. **Rogan-Gladen** supone que el lector se equivoca en el snap igual que a 2.0 s, que es donde se validó (sensibilidad 0.890, especificidad 0.773). En la clase "juega un alto", la tasa observada (9.0%) queda por debajo del error esperado (11.0%), y el valor corregido se recorta a 0.
2. **Censura informativa.** El pase censura la revelación, y el QB puede lanzar justo cuando lee. Si es así, Kaplan-Meier no es del todo válido y la mediana de 3.0 s puede estar sesgada.
3. **Revelar exige estabilidad hasta el pase.** 286 de las 636 jugadas "a ciegas" coincidieron con la cobertura de PFF en algún cuadro y luego cambiaron. El ruido cuadro a cuadro del lector cuenta como "no revelado", y también explica en parte que el 31% de los disfraces siga sin revelarse a los 5 s.
4. **El ranking por equipo refleja en parte la mezcla de coberturas:** el ID observado de cada equipo tiene r = 0.53 con su proporción de dos altos. Ver "Ranking por defensa".
5. El lector se entrenó y validó solo con pases de t_pase ≥ 3 s, y aquí se aplica a todos los cuadros.
6. La zona roja quedó casi vacía por el universo (`dist_endzone` ≥ 20): tiene 1 jugada.
7. **Sacks fuera del universo.** Los 543 sacks de `plays.csv` no entran, porque sin pase no hay t_pase. El análisis está condicionado a que el QB alcanzó a lanzar, y el sack es justo el caso en que la defensa gana la carrera.
8. **El lector no está validado en el snap:** se validó a 2.0 s en pases de ≥ 3 s y aquí se aplica en el snap. Aun así, una regla geométrica que no se entrenó encuentra la misma asimetría en el snap: 52.7% de disfraz en coberturas de dos altos (n = 2,349) contra 13.7% en las de un alto (n = 3,275). La dirección del disfraz no depende del lector, pero su magnitud (59%) no se puede identificar sin una etiqueta de estructura en el snap. Cifras de la revisión independiente (`docs/revision.md`); no las recalculé aquí.
9. **t_pase podría ser mediador:** si el QB lanza porque vio la revelación, ajustar por t_pase puede introducir sesgo. El efecto cambia poco con la especificación: −1.6 pp con escalones de 0.25 s, −1.5 pp cúbico y −0.9 pp sin t_pase. Ningún IC excluye 0. Son cifras de la revisión (B = 200), no recalculadas aquí.

**Solidez del titular: 3 de 5.** La validación del lector, la simetría de la normalización y la robustez a `flag_linea` y al método son sólidas. Lo que la limita es la corrección por error (supone que el error se transfiere al snap) y la definición de revelación (censura informativa y ruido).
