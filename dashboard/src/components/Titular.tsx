import { Bar, BarChart, CartesianGrid, ErrorBar, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ResumenData } from '../types'
import { conSigno, decimal3, estimacion, NA, porcentaje, pp } from '../formato'

export default function Titular({ resumen }: { resumen: ResumenData }) {
  const { efecto, contraste } = resumen
  const concluyente = !(efecto.ic90[0] <= 0 && efecto.ic90[1] >= 0)
  const data = contraste.map((c) => ({
    estrato: c.estrato,
    ciega: c.ciega.exito,
    errCiega: [c.ciega.exito - c.ciega.ic90[0], c.ciega.ic90[1] - c.ciega.exito],
    txtCiega: estimacion(c.ciega.exito, c.ciega.ic90, c.ciega.n),
    leida: c.leida.exito,
    errLeida: [c.leida.exito - c.leida.ic90[0], c.leida.ic90[1] - c.leida.exito],
    txtLeida: estimacion(c.leida.exito, c.leida.ic90, c.leida.n),
  }))
  const icTxt = `IC90 ${conSigno(efecto.ic90[0])} a ${conSigno(efecto.ic90[1])}`
  const est = resumen.estabilidad
  return (
    <section className="bg-white rounded-lg shadow p-5">
      <p className="text-lg text-gray-700">{resumen.titular}</p>
      {concluyente ? (
        <p className="text-5xl font-extrabold text-red-600 mt-1">
          {pp(efecto.valor_pp)}
          <span className="text-sm font-normal text-gray-500 ml-3">
            ({icTxt}) · n={efecto.n}
          </span>
        </p>
      ) : (
        <p className="text-base text-gray-500 mt-1">
          diferencia no concluyente: {pp(efecto.valor_pp)} ({icTxt}) · n={efecto.n}
        </p>
      )}
      <p className="text-xs text-gray-500 mt-1">
        Estabilidad del ID entre mitades: r = {est?.r != null ? decimal3(est.r) : NA} · Spearman-Brown ={' '}
        {est?.spearman_brown != null ? decimal3(est.spearman_brown) : NA}
      </p>
      <div className="h-64 mt-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => porcentaje(Number(v))} />
            <YAxis type="category" dataKey="estrato" width={120} />
            <Tooltip
              formatter={(v, _n, item) => {
                const p = (item as { payload?: Record<string, string> }).payload
                const k = (item as { dataKey?: string }).dataKey
                const t = k === 'ciega' ? p?.txtCiega : k === 'leida' ? p?.txtLeida : undefined
                return t ?? porcentaje(Number(v))
              }}
            />
            <Legend />
            <Bar dataKey="ciega" name="Lanzó antes de la revelación" fill="#2F7D4F">
              <ErrorBar dataKey="errCiega" direction="x" stroke="#1f4f33" />
            </Bar>
            <Bar dataKey="leida" name="Lanzó después de la revelación" fill="#dc2626">
              <ErrorBar dataKey="errLeida" direction="x" stroke="#7f1d1d" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="text-xs text-gray-500 mt-2 space-y-0.5">
        {data.map((d) => (
          <li key={d.estrato}>
            {d.estrato}: antes {d.txtCiega} · después {d.txtLeida}
          </li>
        ))}
      </ul>
    </section>
  )
}
