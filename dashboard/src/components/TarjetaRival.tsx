import { useEffect, useState } from 'react'
import type { EquipoRow, RivalData } from '../types'

const DISTANCIAS = ['1-3', '4-6', '7+']
const pct = (x: number) => `${(x * 100).toFixed(0)}%`

export default function TarjetaRival({ equipos }: { equipos: EquipoRow[] }) {
  const [equipo, setEquipo] = useState('')
  const [down, setDown] = useState(1)
  const [distancia, setDistancia] = useState('1-3')
  const [rival, setRival] = useState<RivalData | null>(null)
  const [informe, setInforme] = useState<{ texto: string; fuente: string } | null>(null)
  const [error, setError] = useState('')
  const [errorInforme, setErrorInforme] = useState('')
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!equipo && equipos.length) setEquipo(equipos[0].equipo)
  }, [equipos, equipo])

  useEffect(() => {
    if (!equipo) return
    let vivo = true
    const q = new URLSearchParams({ equipo, down: String(down), distancia })
    fetch(`api/rival?${q.toString()}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: RivalData) => { if (vivo) { setRival(d); setError('') } })
      .catch(() => { if (vivo) setError('No se pudo cargar al rival') })
    return () => { vivo = false }
  }, [equipo, down, distancia])

  useEffect(() => { setInforme(null); setErrorInforme('') }, [equipo])

  const generar = () => {
    setCargando(true)
    setErrorInforme('')
    fetch('api/informe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ equipo }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => { setInforme(d) })
      .catch(() => setErrorInforme('No se pudo redactar el informe. Intenta de nuevo.'))
      .finally(() => setCargando(false))
  }

  const sel = 'border rounded px-2 py-1 bg-white'
  return (
    <section className="bg-white rounded-lg shadow p-5">
      <h2 className="text-xl font-bold">Tarjeta del rival</h2>
      <div className="flex flex-wrap gap-3 mt-2 items-center">
        <select className={sel} value={equipo} onChange={(e) => setEquipo(e.target.value)} aria-label="Equipo">
          {equipos.map((e) => <option key={e.equipo} value={e.equipo}>{e.equipo}</option>)}
        </select>
        <select className={sel} value={down} onChange={(e) => setDown(Number(e.target.value))} aria-label="Down">
          {[1, 2, 3, 4].map((d) => <option key={d} value={d}>{d}º down</option>)}
        </select>
        <select className={sel} value={distancia} onChange={(e) => setDistancia(e.target.value)} aria-label="Distancia">
          {DISTANCIAS.map((d) => <option key={d} value={d}>{d} yardas</option>)}
        </select>
        <button
          className="bg-green-700 hover:bg-green-800 text-white rounded px-4 py-1 disabled:opacity-50"
          onClick={generar}
          disabled={!equipo || cargando}
        >
          {cargando ? 'Redactando…' : 'Redactar informe semanal'}
        </button>
      </div>
      {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
      {errorInforme && <p className="text-gray-500 text-sm mt-2">{errorInforme}</p>}
      {rival && (
        <div className="grid md:grid-cols-2 gap-4 mt-4 text-sm">
          <div>
            <h3 className="font-semibold mb-1">Formaciones (éxito, IC 90%)</h3>
            <ul className="space-y-1">
              {rival.formaciones.map((f) => (
                <li key={f.formacion}>
                  {f.formacion}: <b>{pct(f.exito.p)}</b>{' '}
                  <span className="text-gray-500">({pct(f.exito.ic90[0])} a {pct(f.exito.ic90[1])}, n={f.exito.n})</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-1">Frases clave</h3>
            <ul className="list-disc ml-5 space-y-1">
              {rival.frases.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        </div>
      )}
      {informe && (
        <div className="mt-4 border-t pt-3">
          <span className="inline-block text-xs font-semibold bg-gray-200 rounded px-2 py-0.5 mb-2">
            {informe.fuente === 'ia'
              ? 'IA (Amazon Nova) · números verificados contra los datos'
              : 'Plantilla (sin IA)'}
          </span>
          <p className="whitespace-pre-line">{informe.texto}</p>
        </div>
      )}
    </section>
  )
}
