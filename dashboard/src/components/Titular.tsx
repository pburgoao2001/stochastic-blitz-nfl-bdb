import { Bar, BarChart, CartesianGrid, ErrorBar, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ResumenData } from '../types'

export default function Titular({ resumen }: { resumen: ResumenData }) {
  const { efecto, contraste } = resumen
  const signo = efecto.valor_pp >= 0 ? '+' : ''
  const data = contraste.map((c) => ({
    estrato: c.estrato,
    ciega: +(c.ciega.exito * 100).toFixed(1),
    errCiega: [(c.ciega.exito - c.ciega.ic90[0]) * 100, (c.ciega.ic90[1] - c.ciega.exito) * 100],
    leida: +(c.leida.exito * 100).toFixed(1),
    errLeida: [(c.leida.exito - c.leida.ic90[0]) * 100, (c.leida.ic90[1] - c.leida.exito) * 100],
  }))
  return (
    <section className="bg-white rounded-lg shadow p-5">
      <p className="text-lg text-gray-700">{resumen.titular}</p>
      <p className="text-5xl font-extrabold text-red-600 mt-1">
        {signo}{efecto.valor_pp.toFixed(1)} pp
        <span className="text-sm font-normal text-gray-500 ml-3">
          IC 90%: {efecto.ic90[0].toFixed(1)} a {efecto.ic90[1].toFixed(1)} · n={efecto.n}
        </span>
      </p>
      <div className="h-64 mt-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 100]} unit="%" />
            <YAxis type="category" dataKey="estrato" width={120} />
            <Tooltip />
            <Legend />
            <Bar dataKey="ciega" name="QB lanzó a ciegas (éxito %)" fill="#2F7D4F">
              <ErrorBar dataKey="errCiega" direction="x" stroke="#1f4f33" />
            </Bar>
            <Bar dataKey="leida" name="QB alcanzó a leer (éxito %)" fill="#dc2626">
              <ErrorBar dataKey="errLeida" direction="x" stroke="#7f1d1d" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
