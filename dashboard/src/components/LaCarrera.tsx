import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Revelacion } from '../types'

export default function LaCarrera({ revelacion }: { revelacion: Revelacion }) {
  const lanz = new Map(revelacion.lanzamiento.map((p) => [p.t, p.acumulado]))
  const data = revelacion.curva.map((p) => ({
    t: p.t,
    s: p.s,
    banda: [p.lo, p.hi] as [number, number],
    lanzamiento: lanz.get(p.t),
  }))
  return (
    <section className="bg-white rounded-lg shadow p-5">
      <h2 className="text-xl font-bold">La carrera: disfraz vs. lanzamiento</h2>
      <p className="text-sm text-gray-600">
        Mediana de revelación: {revelacion.mediana_s.toFixed(1)} s (IC 90%: {revelacion.ic90[0].toFixed(1)} a {revelacion.ic90[1].toFixed(1)}).
        Prob. de seguir disfrazado a 2.5 s: {(revelacion.prob_disfrazado_2_5s * 100).toFixed(0)}%.
      </p>
      <div className="h-72 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ left: 0, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="t" type="number" domain={[0, 'dataMax']} unit=" s" />
            <YAxis domain={[0, 1]} />
            <Tooltip />
            <Legend />
            <Area dataKey="banda" name="IC 90% disfraz" stroke="none" fill="#2F7D4F" fillOpacity={0.2} />
            <Line dataKey="s" name="Disfraz sigue activo" stroke="#2F7D4F" strokeWidth={2} dot={false} />
            <Line dataKey="lanzamiento" name="Lanzamiento acumulado" stroke="#dc2626" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
