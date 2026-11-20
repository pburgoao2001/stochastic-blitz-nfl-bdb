import { useEffect, useState } from 'react'
import { decimal3, icN, muestraChica, NA, porcentaje } from '../formato'
import type { EquipoRow, IC90, InformeData, RivalData } from '../types'

const DISTANCIAS = ['1-3', '4-6', '7+']
const DOWNS = ['1', '2', '3', '4']

interface EstimacionProps {
  etiqueta: string
  p?: number | null
  ic?: IC90 | null
  n: number
}

function Estimacion({ etiqueta, p, ic, n }: EstimacionProps) {
  if (p == null || ic == null) {
    return (
      <li>
        {etiqueta}: <strong>{NA}</strong>
      </li>
    )
  }

  const chica = muestraChica(n)
  return (
    <li className={chica ? 'text-slate-400' : 'text-slate-700'}>
      {etiqueta}: <strong>{porcentaje(p)}</strong>{' '}
      <span className="text-slate-500">({icN(ic, n)})</span>
      {chica && (
        <span className="ml-1 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
          muestra chica
        </span>
      )}
    </li>
  )
}

export default function TarjetaRival({ equipos }: { equipos: EquipoRow[] }) {
  const [equipo, setEquipo] = useState('')
  const [down, setDown] = useState('')
  const [distancia, setDistancia] = useState('')
  const [rival, setRival] = useState<RivalData | null>(null)
  const [informe, setInforme] = useState<InformeData | null>(null)
  const [error, setError] = useState('')
  const [errorInforme, setErrorInforme] = useState('')
  const [cargandoRival, setCargandoRival] = useState(false)
  const [cargandoInforme, setCargandoInforme] = useState(false)

  useEffect(() => {
    if (!equipo && equipos.length) setEquipo(equipos[0].equipo)
  }, [equipos, equipo])

  useEffect(() => {
    if (!equipo) return

    let vivo = true
    const parametros = new URLSearchParams({ equipo })
    if (down) parametros.set('down', down)
    if (distancia) parametros.set('distancia', distancia)

    setCargandoRival(true)
    setError('')
    fetch(`api/rival?${parametros.toString()}`)
      .then((respuesta) =>
        respuesta.ok ? respuesta.json() : Promise.reject(new Error(String(respuesta.status))),
      )
      .then((datos: RivalData) => {
        if (vivo) setRival(datos)
      })
      .catch(() => {
        if (vivo) setError('No se pudo cargar al rival')
      })
      .finally(() => {
        if (vivo) setCargandoRival(false)
      })

    return () => {
      vivo = false
    }
  }, [equipo, down, distancia])

  useEffect(() => {
    setInforme(null)
    setErrorInforme('')
  }, [equipo])

  const generar = () => {
    setCargandoInforme(true)
    setErrorInforme('')
    fetch('api/informe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ equipo }),
    })
      .then((respuesta) =>
        respuesta.ok ? respuesta.json() : Promise.reject(new Error(String(respuesta.status))),
      )
      .then((datos: InformeData) => setInforme(datos))
      .catch(() => setErrorInforme('No se pudo redactar el informe. Intenta de nuevo.'))
      .finally(() => setCargandoInforme(false))
  }

  const claseSelector =
    'min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm'

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm sm:p-8" aria-labelledby="titulo-rival">
      <h2 id="titulo-rival" className="text-xl font-semibold text-slate-900">
        6. Tarjeta del rival
      </h2>
      <p className="mt-1 text-slate-500">
        Filtra la situación y genera el informe semanal del equipo seleccionado.
      </p>

      <div className="mt-5 flex flex-wrap items-end gap-3">
        <label className="flex min-w-[8rem] flex-1 flex-col gap-1 text-sm font-medium text-slate-700">
          Equipo
          <select
            className={claseSelector}
            value={equipo}
            onChange={(evento) => setEquipo(evento.target.value)}
            aria-label="Equipo"
          >
            {equipos.map((fila) => (
              <option key={fila.equipo} value={fila.equipo}>
                {fila.equipo}
              </option>
            ))}
          </select>
        </label>

        <label className="flex min-w-[10rem] flex-1 flex-col gap-1 text-sm font-medium text-slate-700">
          Down
          <select
            className={claseSelector}
            value={down}
            onChange={(evento) => setDown(evento.target.value)}
            aria-label="Down"
          >
            <option value="">Todos los downs</option>
            {DOWNS.map((valor) => (
              <option key={valor} value={valor}>
                {valor}º down
              </option>
            ))}
          </select>
        </label>

        <label className="flex min-w-[11rem] flex-1 flex-col gap-1 text-sm font-medium text-slate-700">
          Distancia
          <select
            className={claseSelector}
            value={distancia}
            onChange={(evento) => setDistancia(evento.target.value)}
            aria-label="Distancia"
          >
            <option value="">Todas las distancias</option>
            {DISTANCIAS.map((valor) => (
              <option key={valor} value={valor}>
                {valor} yardas
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={generar}
          disabled={!equipo || cargandoInforme}
        >
          {cargandoInforme ? 'Redactando…' : 'Redactar informe semanal'}
        </button>
      </div>

      {cargandoRival && <p className="mt-3 text-sm text-slate-500">Actualizando tarjeta…</p>}
      {error && <p className="mt-3 text-sm text-orange-700">{error}</p>}
      {errorInforme && <p className="mt-3 text-sm text-slate-500">{errorInforme}</p>}

      {rival && (
        <div className="mt-6 grid gap-6 text-sm md:grid-cols-2">
          <div>
            <h3 className="mb-2 font-semibold text-slate-900">Juega un alto (por muestra)</h3>
            <ul className="mb-5 space-y-2">
              {rival.filas.map((fila) => (
                <Estimacion
                  key={fila.muestra}
                  etiqueta={fila.muestra}
                  p={fila.juega_un_alto.p}
                  ic={fila.juega_un_alto.ic90}
                  n={fila.juega_un_alto.n}
                />
              ))}
            </ul>

            <h3 className="mb-2 font-semibold text-slate-900">Formaciones (éxito)</h3>
            <ul className="space-y-2">
              {rival.formaciones.map((fila) => (
                <Estimacion
                  key={fila.formacion}
                  etiqueta={fila.formacion}
                  p={fila.exito.p}
                  ic={fila.exito.ic90}
                  n={fila.exito.n}
                />
              ))}
            </ul>

            <p className="mt-4 text-xs leading-5 text-slate-500">
              Brier: mezcla {decimal3(rival.validacion_tarjeta?.brier_mezcla)} · solo liga{' '}
              {decimal3(rival.validacion_tarjeta?.brier_liga)} · solo equipo{' '}
              {decimal3(rival.validacion_tarjeta?.brier_equipo)} (menor es mejor)
            </p>
          </div>

          <div>
            <h3 className="mb-2 font-semibold text-slate-900">Frases clave</h3>
            <ul className="ml-5 list-disc space-y-2 text-slate-700">
              {rival.frases.map((frase, indice) => (
                <li key={indice}>{frase}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {informe && (
        <div className="mt-6 border-t border-slate-200 pt-5">
          <span
            className={`mb-3 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
              informe.fuente === 'ia'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-slate-200 text-slate-700'
            }`}
          >
            {informe.fuente === 'ia'
              ? 'IA (Amazon Nova) · números verificados contra los datos'
              : 'Plantilla (sin IA)'}
          </span>
          <p className="whitespace-pre-line leading-7 text-slate-700">{informe.texto}</p>
        </div>
      )}
    </section>
  )
}
