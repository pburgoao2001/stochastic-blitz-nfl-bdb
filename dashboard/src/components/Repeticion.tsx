import { useCallback, useEffect, useRef, useState } from 'react'
import { segundos } from '../formato'
import { AZUL, NARANJA, SLATE } from '../paleta'
import type { ReplayData } from '../types'

const CAMPO_X_MIN = -10
const CAMPO_X_MAX = 25
const CAMPO_ANCHO = CAMPO_X_MAX - CAMPO_X_MIN
const CAMPO_Y_MAX = 53.3
const LINEAS_REFERENCIA = [-10, -5, 0, 5, 10, 15, 20, 25]
const CLASE_TARJETA = 'rounded-2xl bg-white p-6 shadow-sm sm:p-8'

interface MarcaEventoProps {
  etiqueta: string
  tiempo: number
  porcentaje: number
  color: string
  posicion: 'arriba' | 'abajo'
}

function desplazamientoEtiqueta(porcentaje: number): string {
  if (porcentaje <= 8) return 'translateX(0)'
  if (porcentaje >= 92) return 'translateX(-100%)'
  return 'translateX(-50%)'
}

function MarcaEvento({ etiqueta, tiempo, porcentaje, color, posicion }: MarcaEventoProps) {
  return (
    <div
      className="absolute top-8 h-9 border-l-2"
      style={{ left: `${porcentaje}%`, borderColor: color }}
    >
      <span
        className="absolute -left-1 top-3 h-2 w-2 rounded-full border border-white"
        style={{ backgroundColor: color }}
      />
      <span
        className={`absolute left-0 whitespace-nowrap rounded bg-white/95 px-1.5 py-0.5 text-xs font-semibold text-slate-700 shadow-sm ${
          posicion === 'arriba' ? 'bottom-full mb-1' : 'top-full mt-1'
        }`}
        style={{ transform: desplazamientoEtiqueta(porcentaje) }}
      >
        {etiqueta} · {segundos(tiempo)}
      </span>
    </div>
  )
}

function EncabezadoRepeticion() {
  return (
    <>
      <h2 id="titulo-repeticion" className="text-xl font-semibold text-slate-900">
        4. Repetición
      </h2>
      <p className="mt-1 text-slate-500">Ejemplos reales elegidos por regla, no a mano.</p>
    </>
  )
}

function claseLectura(estructura: string): string {
  const valor = estructura.trim().toLocaleLowerCase('es-MX')
  if (valor === 'cerrado') return 'bg-blue-100 text-blue-800'
  if (valor === 'abierto') return 'bg-orange-100 text-orange-800'
  return 'bg-slate-200 text-slate-700'
}

export default function Repeticion() {
  const [replays, setReplays] = useState<ReplayData[] | null>(null)
  const [indiceJugada, setIndiceJugada] = useState(0)
  const [indiceFrame, setIndiceFrame] = useState(0)
  const [reproduciendo, setReproduciendo] = useState(false)
  const intervaloRef = useRef<number | null>(null)

  const limpiarIntervalo = useCallback(() => {
    if (intervaloRef.current !== null) {
      window.clearInterval(intervaloRef.current)
      intervaloRef.current = null
    }
  }, [])

  useEffect(() => {
    let montado = true

    async function cargarReplays() {
      try {
        const respuesta = await fetch('api/replays')
        if (!respuesta.ok) throw new Error('No se pudieron cargar las repeticiones')
        const datos: unknown = await respuesta.json()
        if (!montado) return
        setReplays(Array.isArray(datos) ? (datos as ReplayData[]) : [])
      } catch {
        if (montado) setReplays([])
      }
    }

    void cargarReplays()
    return () => {
      montado = false
    }
  }, [])

  const jugada = replays?.[indiceJugada]

  useEffect(() => {
    limpiarIntervalo()
    if (!reproduciendo || !jugada || jugada.frames.length < 2) return limpiarIntervalo

    const ultimo = jugada.frames.length - 1
    intervaloRef.current = window.setInterval(() => {
      setIndiceFrame((actual) => {
        const siguiente = Math.min(actual + 1, ultimo)
        if (siguiente >= ultimo) {
          limpiarIntervalo()
          setReproduciendo(false)
        }
        return siguiente
      })
    }, 100)

    return limpiarIntervalo
  }, [jugada, limpiarIntervalo, reproduciendo])

  function pausar() {
    limpiarIntervalo()
    setReproduciendo(false)
  }

  function reproducir() {
    if (!jugada || jugada.frames.length < 2) return
    const ultimo = jugada.frames.length - 1
    if (indiceFrame >= ultimo) setIndiceFrame(0)
    setReproduciendo(true)
  }

  function reiniciar() {
    pausar()
    setIndiceFrame(0)
  }

  function seleccionarJugada(nuevoIndice: number) {
    pausar()
    setIndiceJugada(nuevoIndice)
    setIndiceFrame(0)
  }

  function moverAFrame(nuevoIndice: number) {
    pausar()
    setIndiceFrame(nuevoIndice)
  }

  if (replays === null) {
    return (
      <section className={CLASE_TARJETA} aria-labelledby="titulo-repeticion">
        <EncabezadoRepeticion />
        <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 py-10 text-center text-slate-500">
          Cargando repetición…
        </div>
      </section>
    )
  }

  if (replays.length === 0 || !jugada || jugada.frames.length === 0) {
    return (
      <section className={CLASE_TARJETA} aria-labelledby="titulo-repeticion">
        <EncabezadoRepeticion />
        <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 py-10 text-center text-slate-500">
          Repetición disponible próximamente
        </div>
      </section>
    )
  }

  const ultimoFrame = jugada.frames.length - 1
  const frame = jugada.frames[Math.min(indiceFrame, ultimoFrame)]
  const origenX = jugada.frames[0].balon[0]
  const revelar = jugada.eventos.revela
  const tiemposEventos = [jugada.eventos.snap, jugada.eventos.lanza]
  if (revelar !== null) tiemposEventos.push(revelar)
  const inicioLinea = Math.min(...tiemposEventos)
  const finLinea = Math.max(...tiemposEventos)
  const rangoLinea = finLinea - inicioLinea
  const porcentajeEvento = (tiempo: number) => {
    if (rangoLinea <= 0) return 0
    return Math.max(0, Math.min(100, ((tiempo - inicioLinea) / rangoLinea) * 100))
  }
  const lanzoAntesDeRevelar = revelar === null || jugada.eventos.lanza < revelar

  return (
    <section className={CLASE_TARJETA} aria-labelledby="titulo-repeticion">
      <EncabezadoRepeticion />

      <label htmlFor="selector-replay" className="mt-5 block text-sm font-semibold text-slate-700">
        Jugada
      </label>
      <select
        id="selector-replay"
        value={indiceJugada}
        onChange={(evento) => seleccionarJugada(Number(evento.target.value))}
        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm"
      >
        {replays.map((replay, indice) => (
          <option key={`${replay.gameId}-${replay.playId}`} value={indice}>
            {replay.descripcion}
          </option>
        ))}
      </select>

      <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-slate-700" aria-label="Leyenda">
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-3.5 w-3.5 rounded-full border"
            style={{ backgroundColor: AZUL, borderColor: AZUL }}
          />
          Defensa
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-3.5 w-3.5 border"
            style={{ backgroundColor: NARANJA, borderColor: NARANJA }}
          />
          Ofensiva
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SLATE }} />
          Balón
        </span>
      </div>

      <div className="mx-auto mt-3 max-w-md overflow-hidden rounded-xl border-4 border-emerald-950 bg-emerald-800">
        <svg
          viewBox={`${CAMPO_X_MIN} 0 ${CAMPO_ANCHO} ${CAMPO_Y_MAX}`}
          className="block h-auto w-full"
          role="img"
          aria-label="Vista de la jugada desde diez yardas detrás de la línea de scrimmage hasta veinticinco yardas adelante"
        >
          <title>Repetición animada de la jugada</title>
          <rect x={CAMPO_X_MIN} y={0} width={CAMPO_ANCHO} height={CAMPO_Y_MAX} fill="#166534" />
          {LINEAS_REFERENCIA.map((x) => {
            const esScrimmage = x === 0
            return (
              <g key={x}>
                <line
                  x1={x}
                  y1={0}
                  x2={x}
                  y2={CAMPO_Y_MAX}
                  stroke={esScrimmage ? '#fde047' : '#ffffff'}
                  strokeOpacity={esScrimmage ? 1 : 0.45}
                  strokeWidth={esScrimmage ? 0.35 : 0.14}
                />
                {x !== CAMPO_X_MIN && x !== CAMPO_X_MAX && (
                  <text
                    x={x}
                    y={2.2}
                    fill={esScrimmage ? '#fde047' : '#ffffff'}
                    fontSize={1.25}
                    fontWeight={esScrimmage ? 700 : 500}
                    textAnchor="middle"
                  >
                    {esScrimmage ? 'LOS' : `${x > 0 ? '+' : ''}${x}`}
                  </text>
                )}
              </g>
            )
          })}
          <rect
            x={CAMPO_X_MIN}
            y={0}
            width={CAMPO_ANCHO}
            height={CAMPO_Y_MAX}
            fill="none"
            stroke="#ffffff"
            strokeOpacity={0.8}
            strokeWidth={0.22}
          />

          {frame.def.map(([x, y], indice) => (
            <circle
              key={`def-${indice}`}
              cx={x - origenX}
              cy={y}
              r={0.78}
              fill={AZUL}
              stroke={AZUL}
              strokeWidth={0.18}
            />
          ))}
          {frame.of.map(([x, y], indice) => (
            <rect
              key={`of-${indice}`}
              x={x - origenX - 0.75}
              y={y - 0.75}
              width={1.5}
              height={1.5}
              rx={0.08}
              fill={NARANJA}
              stroke={NARANJA}
              strokeWidth={0.18}
            />
          ))}
          <circle
            cx={frame.balon[0] - origenX}
            cy={frame.balon[1]}
            r={0.42}
            fill={SLATE}
            stroke="#f8fafc"
            strokeWidth={0.14}
          />
        </svg>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={reproducir}
          disabled={reproduciendo}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Play
        </button>
        <button
          type="button"
          onClick={pausar}
          disabled={!reproduciendo}
          className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Pausa
        </button>
        <button
          type="button"
          onClick={reiniciar}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
        >
          Reset
        </button>
        <span className="ml-auto text-sm font-semibold tabular-nums text-slate-700">
          Tiempo: {segundos(frame.t)}
        </span>
      </div>

      <label htmlFor="control-frame" className="mt-4 block text-sm font-medium text-slate-700">
        Cuadro {indiceFrame + 1} de {jugada.frames.length}
      </label>
      <input
        id="control-frame"
        type="range"
        min={0}
        max={ultimoFrame}
        step={1}
        value={indiceFrame}
        onChange={(evento) => moverAFrame(Number(evento.target.value))}
        className="mt-1 w-full accent-blue-600"
      />

      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-700">
        <span>Lectura del modelo</span>
        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${claseLectura(frame.estructura)}`}>
          {frame.estructura}
        </span>
      </div>

      <div className="mt-5" aria-label="Línea de tiempo de eventos">
        <h3 className="text-sm font-semibold text-slate-800">Línea de tiempo</h3>
        <div className="relative mt-2 h-24">
          <div className="absolute left-0 right-0 top-12 h-1 rounded-full bg-slate-200" />
          <div
            className="absolute left-0 top-12 h-1 rounded-full bg-blue-600/60"
            style={{ width: `${porcentajeEvento(frame.t)}%` }}
          />
          <MarcaEvento
            etiqueta="Snap"
            tiempo={jugada.eventos.snap}
            porcentaje={porcentajeEvento(jugada.eventos.snap)}
            color={SLATE}
            posicion="arriba"
          />
          {revelar !== null && (
            <MarcaEvento
              etiqueta="Revelación"
              tiempo={revelar}
              porcentaje={porcentajeEvento(revelar)}
              color={AZUL}
              posicion="abajo"
            />
          )}
          <MarcaEvento
            etiqueta="Lanzamiento"
            tiempo={jugada.eventos.lanza}
            porcentaje={porcentajeEvento(jugada.eventos.lanza)}
            color={NARANJA}
            posicion="arriba"
          />
        </div>
        {revelar === null && (
          <p className="text-sm text-slate-600">
            <strong>Revelación:</strong> no se reveló antes del pase
          </p>
        )}
      </div>

      {lanzoAntesDeRevelar && (
        <p className="mt-3 rounded-xl border border-orange-200 bg-orange-50 px-3 py-2 text-sm font-semibold text-orange-900">
          El QB lanzó antes de que se revelara la cobertura
        </p>
      )}
    </section>
  )
}
