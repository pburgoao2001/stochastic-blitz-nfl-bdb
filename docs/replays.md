# Repeticiones: regla de selección

`metricas.replays()` sirve `data/derivado/replays.json` con la misma forma que `REPLAYS` en `backend/mocks.py`. El archivo se genera después de `preparar jugadas`:

```sh
./.venv/Scripts/python.exe -m backend.analisis.preparar replays
```

## Regla

Hay tres clases dentro del universo de la carrera (`jugadas.csv`). En las tres se excluyen las jugadas con castigo (`foulName1` no vacío).

- **a)** Disfrazada en la dirección principal (el lector ve **cerrado** en el snap y PFF dice dos altos), y el QB lanzó antes de la revelación (`ciega = 1`).
- **b)** Disfrazada en la dirección principal (muestra cerrado en el snap), y el QB lanzó después de la revelación (`evento_revela = 1`).
- **c)** Honesta (`disfraz = 0`).

En cada clase se elige la jugada con mayor |p_snap − 0.5|, es decir, la lectura más segura del lector en el snap. Las candidatas deben cumplir dos condiciones:

- 2.5 s ≤ t_pase ≤ 4.0 s.
- Ningún cuadro faltante: cada cuadro del snap al pase tiene 11 defensores, 11 atacantes, el balón y la salida del lector.

Los empates se resuelven por gameId y luego por playId. Si una clase queda vacía, el rango de t_pase se amplía a 2.0–4.5 s. **No hizo falta en ninguna de las tres.**

La dirección principal se eligió porque representa 1,013 de los 1,279 disfraces.

## Formato

- `frames`: del snap al pase, a 10 Hz, porque el lector solo tiene salida en ese tramo. `t` son segundos desde el snap.
- Coordenadas normalizadas, con la ofensiva atacando hacia +x:
  - **x es relativa a la línea**, es decir, x menos la x del balón en el snap. 0 es la línea de scrimmage y los valores positivos van hacia la defensa.
  - y va de 0 a 53.3 yd.
  - Todo se redondea a 0.1 yd.
- Los jugadores van ordenados por nflId: cada índice es el mismo jugador en todos los cuadros.
- `estructura`: salida del lector en cada cuadro (cerrado, abierto o indeterminado).
- `eventos`:
  - `snap` = 0 y `lanza` = t_pase.
  - `revela` = revela_t. Es `null` en la clase a, porque no hubo revelación antes del pase, y 0 en la honesta.
- `descripcion`: `playDescription` recortada a 140 caracteres, seguida de " · ejemplo ilustrativo elegido por regla".

El archivo pesa 27.6 KB.

## Jugadas elegidas

| Clase | Jugada | Defensa vs. ataque | Muestra → juega (PFF) | p_snap | t_pase | revela | Candidatas |
|---|---|---|---|---|---|---|---|
| a | 2021091907-2527 | SF vs. PHI | cerrado → abierto (Quarters) | 0.956 | 2.6 s | null | 214 |
| b | 2021101705-1820 | IND vs. HOU | cerrado → abierto (Quarters) | 0.961 | 2.6 s | 2.5 s | 346 |
| c | 2021103112-4362 | DAL vs. MIN | abierto → abierto (Cover-6) | 0.004 | 2.8 s | 0.0 s | 1,673 |

## Advertencias

- **Son ejemplos ilustrativos, no representativos.** La regla elige la lectura más segura del snap, no una jugada típica.
- En la jugada b, la estructura pasa de cerrado a indeterminado y luego queda en abierto a los 2.5 s. El pase sale a los 2.6 s, solo un cuadro después de la revelación.
- La honesta muestra cuadros "indeterminado" a mitad de la jugada. El lector duda, pero la jugada se clasifica por el snap.
- Como x es relativa a la línea, el dashboard tiene que sumar la posición de la línea si dibuja un campo de 120 yardas.
