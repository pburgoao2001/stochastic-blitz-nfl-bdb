import { useEffect, useState } from 'react'
import Banner from './components/Banner'
import Contraste from './components/Contraste'
import LaCarrera from './components/LaCarrera'
import Ranking from './components/Ranking'
import Repeticion from './components/Repeticion'
import SankeyChart from './components/SankeyChart'
import TarjetaRival from './components/TarjetaRival'
import Titular from './components/Titular'
import {
  decimal1,
  detalleIcPp,
  enteroLegible,
  porcentaje,
  pp,
  segundos,
} from './formato'
import type { EquipoRow, ResumenData } from './types'

interface KpiProps {
  valor: string
  etiqueta: string
  detalle?: string
  noConcluyente?: boolean
}

function Kpi({ valor, etiqueta, detalle, noConcluyente = false }: KpiProps) {
  return (
    <article className="rounded-2xl bg-white p-5 shadow-sm">
      <p className={`text-3xl font-bold tabular-nums ${noConcluyente ? 'text-slate-500' : 'text-blue-700'}`}>
        {valor}
      </p>
      <p className="mt-2 text-sm font-semibold leading-5 text-slate-800">{etiqueta}</p>
      {noConcluyente && <p className="mt-1 text-sm font-medium text-slate-500">no concluyente</p>}
      {detalle && <p className="mt-2 text-xs leading-5 text-slate-500">{detalle}</p>}
    </article>
  )
}

function FilaKpi({ resumen }: { resumen: ResumenData }) {
  const noConcluyente = resumen.efecto.ic90[0] <= 0 && resumen.efecto.ic90[1] >= 0

  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Indicadores principales">
      <Kpi
        valor={segundos(resumen.revelacion.mediana_s)}
        etiqueta="Mediana de revelación"
        detalle={`IC90 ${decimal1(resumen.revelacion.ic90[0])}–${segundos(resumen.revelacion.ic90[1])}`}
      />
      <Kpi
        valor={porcentaje(resumen.revelacion.prob_disfrazado_2_5s)}
        etiqueta="Disfraces aún activos a 2.5 s"
      />
      <Kpi
        valor={pp(resumen.efecto.valor_pp)}
        etiqueta="Efecto de lanzar antes"
        detalle={detalleIcPp(resumen.efecto.ic90, resumen.efecto.n)}
        noConcluyente={noConcluyente}
      />
      <Kpi
        valor={porcentaje(resumen.validacion.exactitud)}
        etiqueta="Exactitud del lector fuera de muestra"
        detalle={`n=${enteroLegible(resumen.validacion.n)}`}
      />
    </section>
  )
}

export default function App() {
  const [resumen, setResumen] = useState<ResumenData | null>(null)
  const [equipos, setEquipos] = useState<EquipoRow[]>([])
  const [mock, setMock] = useState(false)
  const [errorResumen, setErrorResumen] = useState('')
  const [errorEquipos, setErrorEquipos] = useState('')

  useEffect(() => {
    fetch('api/resumen')
      .then((respuesta) => {
        if (!respuesta.ok) throw new Error(String(respuesta.status))
        if (respuesta.headers.get('X-Data-Source') === 'mock') setMock(true)
        return respuesta.json()
      })
      .then((datos: ResumenData) => setResumen(datos))
      .catch(() => setErrorResumen('No se pudo cargar el resumen'))

    fetch('api/equipos')
      .then((respuesta) => {
        if (!respuesta.ok) throw new Error(String(respuesta.status))
        if (respuesta.headers.get('X-Data-Source') === 'mock') setMock(true)
        return respuesta.json()
      })
      .then((datos: EquipoRow[]) => setEquipos(datos))
      .catch(() => setErrorEquipos('No se pudieron cargar los equipos'))
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Banner mock={mock} />
      <header className="w-full bg-slate-900 text-white">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">La Carrera Invisible</h1>
          <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-300 sm:text-base">
            ¿Quién llega primero: el disfraz de la defensa o el lanzamiento del QB? · NFL 2021, semanas 1–8
            {resumen ? ` · ${enteroLegible(resumen.n_jugadas)} jugadas` : ''}
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6 sm:py-8 lg:space-y-8 lg:px-8">
        {errorResumen && (
          <p className="rounded-2xl border border-orange-200 bg-orange-50 p-4 text-sm text-slate-700" role="alert">
            {errorResumen}
          </p>
        )}
        {!resumen && !errorResumen && (
          <p className="rounded-2xl bg-white p-6 text-slate-500 shadow-sm">Cargando resumen…</p>
        )}

        {resumen && (
          <>
            <Titular resumen={resumen} />
            <FilaKpi resumen={resumen} />
            <LaCarrera revelacion={resumen.revelacion} />
            <Contraste contraste={resumen.contraste} />
            <SankeyChart sankey={resumen.sankey} />
          </>
        )}

        <Repeticion />

        {errorEquipos && (
          <p className="rounded-2xl border border-orange-200 bg-orange-50 p-4 text-sm text-slate-700" role="alert">
            {errorEquipos}
          </p>
        )}
        {equipos.length === 0 && !errorEquipos && (
          <p className="rounded-2xl bg-white p-6 text-slate-500 shadow-sm">Cargando defensas…</p>
        )}
        {equipos.length > 0 && (
          <>
            <Ranking equipos={equipos} />
            <TarjetaRival equipos={equipos} />
          </>
        )}
      </main>
    </div>
  )
}
