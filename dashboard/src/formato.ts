import type { IC90 } from './types'

// Helpers de formato. Los valores de la API vienen como proporciones 0–1.
const MENOS = '\u2212'
const FORMATO_ENTERO = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 })

export const NA = '—'

const esNumero = (x: number | null | undefined): x is number =>
  typeof x === 'number' && Number.isFinite(x)

const esIntervalo = (ic: IC90 | null | undefined): ic is IC90 =>
  Array.isArray(ic) && ic.length === 2 && esNumero(ic[0]) && esNumero(ic[1])

/** Formatea enteros con separadores de miles. */
export const enteroLegible = (x: number | null | undefined): string =>
  esNumero(x) ? FORMATO_ENTERO.format(x) : NA

/** Formatea una proporción como porcentaje sin decimales. */
export const porcentaje = (x: number | null | undefined): string =>
  esNumero(x) ? `${(x * 100).toFixed(0)}%` : NA

/** Formatea un valor con un decimal, signo y menos tipográfico. */
export const conSigno = (x: number | null | undefined): string => {
  if (!esNumero(x)) return NA
  const texto = Math.abs(x).toFixed(1)
  return x < 0 && Number(texto) !== 0 ? `${MENOS}${texto}` : `+${texto}`
}

/** Formatea puntos porcentuales con un decimal y signo. */
export const pp = (x: number | null | undefined): string =>
  esNumero(x) ? `${conSigno(x)} pp` : NA

/** Formatea segundos con un decimal. */
export const segundos = (x: number | null | undefined): string =>
  esNumero(x) ? `${x.toFixed(1)} s` : NA

/** 1 decimal sin signo */
export const decimal1 = (x: number | null | undefined): string =>
  esNumero(x) ? x.toFixed(1) : NA

/** 3 decimales (Brier, r) */
export const decimal3 = (x: number | null | undefined): string =>
  esNumero(x) ? x.toFixed(3) : NA

/** Formatea una estimación porcentual completa; devuelve raya si faltan datos. */
export const estimacion = (
  p: number | null | undefined,
  ic: IC90 | null | undefined,
  n: number | null | undefined,
): string => {
  if (!esNumero(p) || !esIntervalo(ic) || !esNumero(n)) return NA
  return `${porcentaje(p)} (IC90 ${porcentaje(ic[0])}–${porcentaje(ic[1])}, n=${enteroLegible(n)})`
}

/** Formatea un intervalo porcentual y su tamaño de muestra. */
export const icN = (ic: IC90 | null | undefined, n: number | null | undefined): string => {
  if (!esIntervalo(ic)) return `IC90 ${NA}, n=${enteroLegible(n)}`
  return `IC90 ${porcentaje(ic[0])}–${porcentaje(ic[1])}, n=${enteroLegible(n)}`
}

/** Formatea un intervalo en segundos y su tamaño de muestra. */
export const detalleIcSegundos = (ic: IC90 | null | undefined, n: number | null | undefined): string => {
  if (!esIntervalo(ic)) return `IC90 ${NA} · n=${enteroLegible(n)}`
  return `IC90 ${decimal1(ic[0])}–${segundos(ic[1])} · n=${enteroLegible(n)}`
}

/** Formatea un intervalo en puntos porcentuales y su tamaño de muestra. */
export const detalleIcPp = (ic: IC90 | null | undefined, n: number | null | undefined): string => {
  if (!esIntervalo(ic)) return `IC90 ${NA} · n=${enteroLegible(n)}`
  return `IC90 ${conSigno(ic[0])} a ${pp(ic[1])} · n=${enteroLegible(n)}`
}

/** Explicita la ausencia de intervalo y conserva el tamaño de muestra. */
export const detalleSinIc = (n: number | null | undefined): string =>
  `IC90 ${NA} · n=${enteroLegible(n)}`

/** Muestra chica: n < 15 */
export const UMBRAL_N = 15
export const muestraChica = (n: number): boolean => n < UMBRAL_N
