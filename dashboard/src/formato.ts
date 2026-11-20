// Helpers de formato. Los valores de la API vienen como proporciones 0–1.
const MENOS = '\u2212'

export const NA = '—'

const num = (x: number | null | undefined): x is number => typeof x === 'number' && Number.isFinite(x)

/** 0.534 -> "53%" */
export const porcentaje = (x: number | null | undefined): string => (num(x) ? `${(x * 100).toFixed(0)}%` : NA)

/** 1 decimal con signo (menos tipográfico): "−1.9", "+2.3" */
export const conSigno = (x: number | null | undefined): string => {
  if (!num(x)) return NA
  const t = Math.abs(x).toFixed(1)
  return x < 0 && Number(t) !== 0 ? `${MENOS}${t}` : `+${t}`
}

/** "−1.9 pp", "+2.3 pp" */
export const pp = (x: number | null | undefined): string => (num(x) ? `${conSigno(x)} pp` : NA)

/** "2.1 s" */
export const segundos = (x: number | null | undefined): string => (num(x) ? `${x.toFixed(1)} s` : NA)

/** 1 decimal sin signo */
export const decimal1 = (x: number | null | undefined): string => (num(x) ? x.toFixed(1) : NA)

/** 3 decimales (Brier, r) */
export const decimal3 = (x: number | null | undefined): string => (num(x) ? x.toFixed(3) : NA)

/** "53% (IC90 48–58%, n=210)" */
export const estimacion = (p: number, ic: [number, number], n: number): string =>
  `${porcentaje(p)} (IC90 ${(ic[0] * 100).toFixed(0)}–${porcentaje(ic[1])}, n=${n})`

/** "IC90 48–58%, n=210" */
export const icN = (ic: [number, number], n: number): string =>
  `IC90 ${(ic[0] * 100).toFixed(0)}–${porcentaje(ic[1])}, n=${n}`

/** Muestra chica: n < 15 */
export const UMBRAL_N = 15
export const muestraChica = (n: number): boolean => n < UMBRAL_N
