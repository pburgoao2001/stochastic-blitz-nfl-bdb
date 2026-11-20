import {
  Bar,
  BarChart,
  CartesianGrid,
  ErrorBar,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { estimacion, porcentaje } from '../formato'
import { AZUL, NARANJA, SLATE } from '../paleta'
import type { Contraste as ContrasteData } from '../types'

export default function Contraste({ contraste }: { contraste: ContrasteData[] }) {
  const data = contraste.map((fila) => ({
    estrato: fila.estrato,
    antes: fila.ciega.exito,
    errorAntes: [
      fila.ciega.exito - fila.ciega.ic90[0],
      fila.ciega.ic90[1] - fila.ciega.exito,
    ],
    textoAntes: estimacion(fila.ciega.exito, fila.ciega.ic90, fila.ciega.n),
    despues: fila.leida.exito,
    errorDespues: [
      fila.leida.exito - fila.leida.ic90[0],
      fila.leida.ic90[1] - fila.leida.exito,
    ],
    textoDespues: estimacion(fila.leida.exito, fila.leida.ic90, fila.leida.n),
  }))

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm sm:p-8" aria-labelledby="titulo-contraste">
      <h2 id="titulo-contraste" className="text-xl font-semibold text-slate-900">
        2. ¿Cuesta lanzar antes?
      </h2>
      <p className="mt-1 text-slate-500">
        Éxito con IC90; si los intervalos se traslapan, no hay diferencia clara.
      </p>

      {data.length > 0 ? (
        <>
          <div className="mt-5 h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{ left: 8, right: 28, top: 8, bottom: 8 }}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  domain={[0, 1]}
                  tickFormatter={(valor) => porcentaje(Number(valor))}
                  tick={{ fill: SLATE, fontSize: 12 }}
                  axisLine={{ stroke: '#cbd5e1' }}
                  tickLine={{ stroke: '#cbd5e1' }}
                />
                <YAxis
                  type="category"
                  dataKey="estrato"
                  width={118}
                  tick={{ fill: SLATE, fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: '#f8fafc' }}
                  formatter={(valor, _nombre, elemento) => {
                    const payload = (elemento as { payload?: Record<string, string> }).payload
                    const dataKey = (elemento as { dataKey?: string }).dataKey
                    if (dataKey === 'antes') return payload?.textoAntes ?? porcentaje(Number(valor))
                    if (dataKey === 'despues') return payload?.textoDespues ?? porcentaje(Number(valor))
                    return porcentaje(Number(valor))
                  }}
                />
                <Legend wrapperStyle={{ color: SLATE, fontSize: 13 }} />
                <Bar dataKey="antes" name="Lanzó antes de la revelación" fill={AZUL} radius={[0, 4, 4, 0]}>
                  <ErrorBar
                    dataKey="errorAntes"
                    direction="x"
                    stroke={AZUL}
                    strokeOpacity={0.65}
                    strokeWidth={2}
                  />
                </Bar>
                <Bar dataKey="despues" name="Lanzó después de la revelación" fill={NARANJA} radius={[0, 4, 4, 0]}>
                  <ErrorBar
                    dataKey="errorDespues"
                    direction="x"
                    stroke={NARANJA}
                    strokeOpacity={0.65}
                    strokeWidth={2}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-3 space-y-1 text-xs text-slate-500">
            {data.map((fila) => (
              <li key={fila.estrato}>
                {fila.estrato}: antes {fila.textoAntes} · después {fila.textoDespues}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-5 rounded-xl bg-slate-50 px-4 py-8 text-center text-slate-500">
          No hay datos de contraste disponibles.
        </p>
      )}
    </section>
  )
}
