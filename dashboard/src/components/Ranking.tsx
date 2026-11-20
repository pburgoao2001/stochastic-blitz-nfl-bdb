import { Bar, BarChart, CartesianGrid, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { EquipoRow } from '../types'

export default function Ranking({ equipos }: { equipos: EquipoRow[] }) {
  const data = equipos.map((e) => ({
    equipo: e.equipo,
    id: +e.id.valor.toFixed(3),
    err: [e.id.valor - e.id.ic90[0], e.id.ic90[1] - e.id.valor],
  }))
  return (
    <section className="bg-white rounded-lg shadow p-5">
      <h2 className="text-xl font-bold">Ranking del ID por equipo</h2>
      <div style={{ height: Math.max(300, data.length * 20) }} className="mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 'auto']} />
            <YAxis type="category" dataKey="equipo" width={45} interval={0} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="id" name="ID" fill="#2F7D4F">
              <ErrorBar dataKey="err" direction="x" stroke="#1f4f33" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
