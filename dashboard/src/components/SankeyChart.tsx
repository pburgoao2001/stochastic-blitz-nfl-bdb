import { ResponsiveContainer, Sankey, Tooltip } from 'recharts'
import { enteroLegible } from '../formato'
import { AZUL, NARANJA, SLATE } from '../paleta'
import type { ResumenData } from '../types'

interface EnlaceSankeySeguro {
  source: number
  target: number
  value: number
}

interface NodoPersonalizadoProps {
  x?: number
  y?: number
  width?: number
  height?: number
  index?: number
  payload?: unknown
  nombres: string[]
  totales: number[]
  colores: string[]
}

const esNumero = (valor: unknown): valor is number =>
  typeof valor === 'number' && Number.isFinite(valor)

function esEnlaceSeguro(enlace: unknown, cantidadNodos: number): enlace is EnlaceSankeySeguro {
  if (typeof enlace !== 'object' || enlace === null) return false
  const candidato = enlace as Partial<EnlaceSankeySeguro>
  return (
    Number.isInteger(candidato.source) &&
    Number(candidato.source) >= 0 &&
    Number(candidato.source) < cantidadNodos &&
    Number.isInteger(candidato.target) &&
    Number(candidato.target) >= 0 &&
    Number(candidato.target) < cantidadNodos &&
    esNumero(candidato.value) &&
    candidato.value >= 0
  )
}

function nombreDelPayload(payload: unknown): string | undefined {
  if (typeof payload !== 'object' || payload === null || !('name' in payload)) return undefined
  const nombre = (payload as { name?: unknown }).name
  return typeof nombre === 'string' && nombre.trim() ? nombre : undefined
}

function NodoPersonalizado({
  x,
  y,
  width,
  height,
  index,
  payload,
  nombres,
  totales,
  colores,
}: NodoPersonalizadoProps) {
  if (!esNumero(x) || !esNumero(y) || !esNumero(width) || !esNumero(height)) return null

  const indiceSeguro = Number.isInteger(index) && Number(index) >= 0 ? Number(index) : -1
  const nombre = nombres[indiceSeguro] ?? nombreDelPayload(payload) ?? 'Sin nombre'
  const total = indiceSeguro >= 0 && esNumero(totales[indiceSeguro]) ? totales[indiceSeguro] : undefined
  const color = colores[indiceSeguro] ?? AZUL

  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx={3} fill={color} fillOpacity={0.9} />
      <text
        x={x + width + 8}
        y={y + height / 2}
        dominantBaseline="middle"
        fill={SLATE}
        fontSize={12}
      >
        <tspan fontWeight={600}>{nombre}</tspan>
        <tspan>{` · ${total === undefined ? '—' : `${enteroLegible(total)} jugadas`}`}</tspan>
      </text>
    </g>
  )
}

export default function SankeyChart({
  sankey,
}: {
  sankey?: ResumenData['sankey'] | null
}) {
  const nodos = Array.isArray(sankey?.nodes) ? sankey.nodes : []
  const linksOriginales: unknown[] = Array.isArray(sankey?.links) ? sankey.links : []
  const links = linksOriginales.filter((link): link is EnlaceSankeySeguro =>
    esEnlaceSeguro(link, nodos.length),
  )

  const entradas = nodos.map(() => 0)
  const salidas = nodos.map(() => 0)
  links.forEach((link) => {
    salidas[link.source] += link.value
    entradas[link.target] += link.value
  })

  const totales = nodos.map((_nodo, indice) => Math.max(entradas[indice], salidas[indice]))
  const colores = salidas.map((salida) => (salida > 0 ? AZUL : NARANJA))
  const nombres = nodos.map((nodo) =>
    typeof nodo?.name === 'string' && nodo.name.trim() ? nodo.name : 'Sin nombre',
  )

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm sm:p-8" aria-labelledby="titulo-sankey">
      <h2 id="titulo-sankey" className="text-xl font-semibold text-slate-900">
        3. Flujo de jugadas
      </h2>
      <p className="mt-1 text-slate-500">
        De lo que muestra la defensa en el snap al resultado.
      </p>

      {nodos.length > 0 && links.length > 0 ? (
        <div className="mt-5 w-full overflow-x-auto pb-2">
          <div className="h-96 min-w-[640px]">
            <ResponsiveContainer width="100%" height="100%">
              <Sankey
                data={{ nodes: nodos, links }}
                nodePadding={24}
                nodeWidth={12}
                margin={{ left: 8, right: 190, top: 12, bottom: 12 }}
                link={{ stroke: AZUL, strokeOpacity: 0.24 }}
                node={(props) => (
                  <NodoPersonalizado
                    {...props}
                    nombres={nombres}
                    totales={totales}
                    colores={colores}
                  />
                )}
              >
                <Tooltip />
              </Sankey>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <p className="mt-5 rounded-xl bg-slate-50 px-4 py-8 text-center text-slate-500">
          No hay datos de flujo disponibles.
        </p>
      )}
    </section>
  )
}
