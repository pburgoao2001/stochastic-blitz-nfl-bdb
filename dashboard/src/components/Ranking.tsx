import {
  Bar,
  BarChart,
  CartesianGrid,
  ErrorBar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { estimacion, porcentaje } from '../formato'
import { AZUL, SLATE } from '../paleta'
import type { EquipoRow } from '../types'

export default function Ranking({ equipos }: { equipos: EquipoRow[] }) {
  const data = [...equipos]
    .sort((a, b) => b.id.valor - a.id.valor)
    .map((equipo) => ({
      equipo: equipo.equipo,
      id: equipo.id.valor,
      error: [equipo.id.valor - equipo.id.ic90[0], equipo.id.ic90[1] - equipo.id.valor],
      texto: estimacion(equipo.id.valor, equipo.id.ic90, equipo.id.n),
    }))

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm sm:p-8" aria-labelledby="titulo-ranking">
      <h2 id="titulo-ranking" className="text-xl font-semibold text-slate-900">
        5. Ranking por defensa
      </h2>
      <p className="mt-1 text-slate-500">
        Nota: el ID refleja en parte cuánto juega dos altos cada defensa.
      </p>
      <div style={{ height: Math.max(320, data.length * 22) }} className="mt-5 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 28, top: 4, bottom: 4 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, 'auto']}
              tickFormatter={(valor) => porcentaje(Number(valor))}
              tick={{ fill: SLATE, fontSize: 12 }}
              axisLine={{ stroke: '#cbd5e1' }}
              tickLine={{ stroke: '#cbd5e1' }}
            />
            <YAxis
              type="category"
              dataKey="equipo"
              width={48}
              interval={0}
              tick={{ fill: SLATE, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: '#f8fafc' }}
              formatter={(valor, _nombre, elemento) =>
                (elemento as { payload?: { texto?: string } }).payload?.texto ?? porcentaje(Number(valor))
              }
            />
            <Bar dataKey="id" name="ID" fill={AZUL} radius={[0, 4, 4, 0]}>
              <ErrorBar
                dataKey="error"
                direction="x"
                stroke={AZUL}
                strokeOpacity={0.7}
                strokeWidth={2}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
