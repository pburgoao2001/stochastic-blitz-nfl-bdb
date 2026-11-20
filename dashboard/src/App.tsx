import { useEffect, useState } from 'react'
import Banner from './components/Banner'
import Titular from './components/Titular'
import LaCarrera from './components/LaCarrera'
import SankeyChart from './components/SankeyChart'
import Repeticion from './components/Repeticion'
import Ranking from './components/Ranking'
import TarjetaRival from './components/TarjetaRival'
import type { EquipoRow, ResumenData } from './types'

export default function App() {
  const [resumen, setResumen] = useState<ResumenData | null>(null)
  const [equipos, setEquipos] = useState<EquipoRow[]>([])
  const [mock, setMock] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('api/resumen')
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status))
        setMock(r.headers.get('X-Data-Source') === 'mock')
        return r.json()
      })
      .then((d: ResumenData) => setResumen(d))
      .catch(() => setError('No se pudo cargar el resumen'))
    fetch('api/equipos')
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status))
        if (r.headers.get('X-Data-Source') === 'mock') setMock(true)
        return r.json()
      })
      .then((d: EquipoRow[]) => setEquipos(d))
      .catch(() => setError('No se pudieron cargar los equipos'))
  }, [])

  return (
    <div className="min-h-screen bg-gray-100">
      <Banner mock={mock} />
      <main className="max-w-5xl mx-auto p-4 space-y-4">
        <h1 className="text-2xl font-bold">La Carrera Invisible</h1>
        {error && <p className="text-red-600">{error}</p>}
        {!resumen && !error && <p className="text-gray-500">Cargando…</p>}
        {resumen && (
          <>
            <Titular resumen={resumen} />
            <LaCarrera revelacion={resumen.revelacion} />
            <SankeyChart sankey={resumen.sankey} />
          </>
        )}
        <Repeticion />
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
