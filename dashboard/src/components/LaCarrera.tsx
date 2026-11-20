import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { porcentaje, segundos } from '../formato'
import { AZUL, NARANJA, SLATE } from '../paleta'
import type { Revelacion } from '../types'

interface PuntoCarrera {
  t: number
  s?: number
  banda?: [number, number]
  lanzamiento?: number
}

export default function LaCarrera({ revelacion }: { revelacion: Revelacion }) {
  const porTiempo = new Map<number, PuntoCarrera>()

  revelacion.curva.forEach((punto) => {
    porTiempo.set(punto.t, {
      ...porTiempo.get(punto.t),
      t: punto.t,
      s: punto.s,
      banda: [punto.lo, punto.hi],
    })
  })
  revelacion.lanzamiento.forEach((punto) => {
    porTiempo.set(punto.t, {
      ...porTiempo.get(punto.t),
      t: punto.t,
      lanzamiento: punto.acumulado,
    })
  })

  const data = Array.from(porTiempo.values()).sort((a, b) => a.t - b.t)

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm sm:p-8" aria-labelledby="titulo-carrera">
      <h2 id="titulo-carrera" className="text-xl font-semibold text-slate-900">
        1. La carrera
      </h2>
      <p className="mt-1 text-slate-500">
        Azul: disfraces que siguen activos. Naranja: QBs que ya lanzaron.
      </p>
      <div className="mt-5 h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ left: 0, right: 20, top: 8, bottom: 8 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              type="number"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(valor) => segundos(Number(valor))}
              tick={{ fill: SLATE, fontSize: 12 }}
              axisLine={{ stroke: '#cbd5e1' }}
              tickLine={{ stroke: '#cbd5e1' }}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(valor) => porcentaje(Number(valor))}
              tick={{ fill: SLATE, fontSize: 12 }}
              axisLine={{ stroke: '#cbd5e1' }}
              tickLine={{ stroke: '#cbd5e1' }}
              width={44}
            />
            <Tooltip
              labelFormatter={(valor) => segundos(Number(valor))}
              formatter={(valor) =>
                Array.isArray(valor)
                  ? `${porcentaje(Number(valor[0]))}–${porcentaje(Number(valor[1]))}`
                  : porcentaje(Number(valor))
              }
            />
            <Legend wrapperStyle={{ color: SLATE, fontSize: 13 }} />
            <Area
              dataKey="banda"
              name="IC90 del disfraz"
              stroke="none"
              fill={AZUL}
              fillOpacity={0.16}
              legendType="none"
              connectNulls
            />
            <Line
              dataKey="s"
              name="Disfraz sigue activo"
              stroke={AZUL}
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
            <Line
              dataKey="lanzamiento"
              name="QB ya lanzó"
              stroke={NARANJA}
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
