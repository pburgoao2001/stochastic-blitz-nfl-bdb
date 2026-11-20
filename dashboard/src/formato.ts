import type { IC90 } from './types'

// Helpers de formato. Los valores de la API vienen como proporciones 0–1.
const MENOS = '\u2212'
const FORMATO_ENTERO = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 })

export const NA = '—'

const esNumero = (x: number | null | undefined): x is number =>
  typeof x === 'number' && Number.isFinite(x)

const esIntervalo = (ic: IC90 | null | undefined): ic is IC90 =>
  Array.isArray(ic) && ic.length === 2 && esNumero(ic[0]) && esNumero(ic[1])

/** 1234 -> "1,234" */
export const enteroLegible = (x: number | null | undefined): string =>
  esNumero(x) ? FORMATO_ENTERO.format(x) : NA

/** 0.534 -> "53%" */
export const porcentaje = (x: number | null | undefined): string =>
  esNumero(x) ? `${(x * 100).toFixed(0)}%` : NA

/** 1 decimal con signo (menos tipográfico): "−1.9", "+2.3" */
export const conSigno = (x: number | null | undefined): string => {
  if (!esNumero(x)) return NA
  const texto = Math.abs(x).toFixed(1)
  return x < 0 && Number(texto) !== 0 ? `${MENOS}${texto}` : `+${texto}`
}

/** "−1.9 pp", "+2.3 pp" */
export const pp = (x: number | null | undefined): string =>
  esNumero(x) ? `${conSigno(x)} pp` : NA

/** "2.1 s" */
export const segundos = (x: number | null | undefined): string =>
  esNumero(x) ? `${x.toFixed(1)} s` : NA

/** 1 decimal sin signo */
export const decimal1 = (x: number | null | undefined): string =>
  esNumero(x) ? x.toFixed(1) : NA

/** 3 decimales (Brier, r) */
export const decimal3 = (x: number | null | undefined): string =>
  esNumero(x) ? x.toFixed(3) : NA

/** "53% (IC90 48%–58%, n=210)"; "—" si falta p o el intervalo. */
export const estimacion = (
  p: number | null | undefined,
  ic: IC90 | null | undefined,
  n: number | null | undefined,
): string => {
  if (!esNumero(p) || !esIntervalo(ic) || !esNumero(n)) return NA
  return `${porcentaje(p)} (IC90 ${porcentaje(ic[0])}–${porcentaje(ic[1])}, n=${enteroLegible(n)})`
}

/** "IC90 48%–58%, n=210" */
export const icN = (ic: IC90 | null | undefined, n: number | null | undefined): string => {
  if (!esIntervalo(ic)) return `IC90 ${NA}, n=${enteroLegible(n)}`
  return `IC90 ${porcentaje(ic[0])}–${porcentaje(ic[1])}, n=${enteroLegible(n)}`
}

/** "IC90 1.8–2.3 s · n=210" */
export const detalleIcSegundos = (ic: IC90 | null | undefined, n: number | null | undefined): string => {
  if (!esIntervalo(ic)) return `IC90 ${NA} · n=${enteroLegible(n)}`
  return `IC90 ${decimal1(ic[0])}–${segundos(ic[1])} · n=${enteroLegible(n)}`
}

/** "IC90 −2.0 a +1.4 pp · n=210" */
export const detalleIcPp = (ic: IC90 | null | undefined, n: number | null | undefined): string => {
  if (!esIntervalo(ic)) return `IC90 ${NA} · n=${enteroLegible(n)}`
  return `IC90 ${conSigno(ic[0])} a ${pp(ic[1])} · n=${enteroLegible(n)}`
}

/** "IC90 — · n=210" para métricas cuyo contrato no expone intervalo. */
export const detalleSinIc = (n: number | null | undefined): string =>
  `IC90 ${NA} · n=${enteroLegible(n)}`

/** Muestra chica: n < 15 */
export const UMBRAL_N = 15
export const muestraChica = (n: number): boolean => n < UMBRAL_N
