import { ResponsiveContainer, Sankey, Tooltip } from 'recharts'
import type { ResumenData } from '../types'

export default function SankeyChart({ sankey }: { sankey: ResumenData['sankey'] }) {
  return (
    <section className="bg-white rounded-lg shadow p-5">
      <h2 className="text-xl font-bold">Flujo de jugadas</h2>
      <div className="h-80 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <Sankey
            data={{ nodes: sankey.nodes, links: sankey.links }}
            nodePadding={24}
            margin={{ left: 10, right: 90, top: 10, bottom: 10 }}
            link={{ stroke: '#2F7D4F', strokeOpacity: 0.25 }}
            node={{ fill: '#1f4f33' }}
          >
            <Tooltip />
          </Sankey>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
