import type { ResumenData } from '../types'

export default function Titular({ resumen }: { resumen: ResumenData }) {
  const separador = resumen.titular.indexOf(':')
  const tieneDetalle = separador >= 0
  const frase = (tieneDetalle ? resumen.titular.slice(0, separador) : resumen.titular).trim()
  const detalle = tieneDetalle ? resumen.titular.slice(separador + 1).trim() : ''

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm sm:p-8" aria-labelledby="titular-principal">
      <h2 id="titular-principal" className="text-3xl font-bold leading-tight text-slate-900">
        {frase || resumen.titular}
      </h2>
      {detalle && <p className="mt-3 max-w-4xl text-lg leading-8 text-slate-600">{detalle}</p>}
    </section>
  )
}
