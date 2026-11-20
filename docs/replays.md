# Repeticiones: regla de selección

`data/derivado/replays.json` lo sirve `metricas.replays()` con la misma forma que `REPLAYS` en `backend/mocks.py`. Se genera, después de `preparar jugadas`, con:

```sh
./.venv/Scripts/python.exe -m backend.analisis.preparar replays
```

## Regla

Hay tres clases dentro del universo de la carrera (`jugadas.csv`):

- **a)** Disfrazada, y el QB lanzó antes de la revelación (`ciega = 1`).
- **b)** Disfrazada, y el QB lanzó después de la revelación (`disfraz = 1`, `evento_revela = 1`).
- **c)** Honesta (`disfraz = 0`).

En cada clase se elige la jugada con mayor |p_snap − 0.5|, es decir, la lectura más segura del lector en el snap. Solo se consideran jugadas que cumplen dos condiciones:

- 2.5 s ≤ t_pase ≤ 4.0 s.
- Ningún cuadro faltante: cada cuadro del snap al pase tiene 11 defensores, 11 atacantes, el balón y la salida del lector.

Si hay empate, se ordena por gameId y luego por playId.

## Formato

- `frames`: del snap al pase, a 10 Hz. El lector solo tiene salida en ese tramo. `t` son segundos desde el snap.
- Coordenadas normalizadas, con la ofensiva atacando hacia +x:
  - **x es relativa a la línea:** x menos la x del balón en el snap. 0 es la línea de scrimmage y los valores positivos van hacia la defensa.
  - y va de 0 a 53.3 yd.
  - Todo se redondea a 0.1 yd.
- Los jugadores van ordenados por nflId, así que cada índice es el mismo jugador en todos los cuadros.
- `estructura`: salida del lector en cada cuadro (cerrado, abierto o indeterminado).
- `eventos`:
  - `snap` = 0.
  - `lanza` = t_pase.
  - `revela` = revela_t. Es `null` en la clase a, porque no hubo revelación antes del pase (cumple "revela null o > lanza"), y 0 en la honesta.
- `descripcion`: `playDescription` recortada a 140 caracteres, seguida de " · ejemplo ilustrativo elegido por regla".

El archivo pesa 30.8 KB.

## Jugadas elegidas

| Clase | Jugada | Defensa vs. ataque | Muestra → juega (PFF) | p_snap | t_pase | revela | Candidatas |
|---|---|---|---|---|---|---|---|
| a | 2021101700-2536 | MIA vs. JAX | abierto → cerrado (Cover-3) | 0.0006 | 2.5 s | null | 340 |
| b | 2021101005-2746 | MIN vs. DET | abierto → cerrado (Cover-3) | 0.0075 | 3.9 s | 3.6 s | 417 |
| c | 2021103112-4362 | DAL vs. MIN | abierto → abierto (Cover-6) | 0.0039 | 2.8 s | 0.0 s | 1,857 |

## Advertencias

- **Son ejemplos ilustrativos, no representativos.** La regla favorece las lecturas de "abierto" en el snap (p_snap cerca de 0). Por eso las dos jugadas disfrazadas muestran abierto y juegan un alto, que es la dirección minoritaria del disfraz: 266 de 1,279. La dirección mayoritaria, mostrar un alto y jugar con dos, suma 1,013.
- La jugada b tuvo castigo (interferencia de pase defensiva), así que su éxito no entra al análisis.
- En la honesta hay cuadros "indeterminado" a mitad de la jugada. El lector duda, pero la jugada se clasifica por lo que muestra en el snap.
- Como x es relativa a la línea, el dashboard tiene que sumar la posición de la línea si dibuja un campo de 120 yardas.
