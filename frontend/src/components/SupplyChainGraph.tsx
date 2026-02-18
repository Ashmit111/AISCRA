import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import cytoscape, { Core } from 'cytoscape'
// @ts-ignore
import dagre from 'cytoscape-dagre'

// Register dagre layout
cytoscape.use(dagre)

export default function SupplyChainGraph() {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)

  const { data: suppliers } = useQuery({
    queryKey: ['suppliers'],
    queryFn: api.getSuppliers,
  })

  const { data: company } = useQuery({
    queryKey: ['company'],
    queryFn: () => api.getDashboardSummary(),
  })

  useEffect(() => {
    if (!containerRef.current || !suppliers) return

    // Build graph elements
    const elements: cytoscape.ElementDefinition[] = []

    // Add company node
    elements.push({
      data: {
        id: 'company',
        label: 'Nayara Energy',
        type: 'company',
        risk: 0
      }
    })

    // Add supplier nodes
    suppliers.forEach((supplier) => {
      elements.push({
        data: {
          id: supplier._id,
          label: supplier.name,
          type: 'supplier',
          risk: supplier.risk_score_current,
          country: supplier.country,
          status: supplier.status,
          tier: supplier.tier
        }
      })

      // Add edge from supplier to company
      elements.push({
        data: {
          id: `edge-${supplier._id}`,
          source: supplier._id,
          target: 'company',
          weight: supplier.supply_volume_pct
        }
      })
    })

    // Initialize Cytoscape
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '12px',
            'width': '60px',
            'height': '60px',
          }
        },
        {
          selector: 'node[type="company"]',
          style: {
            'background-color': '#3b82f6',
            'width': '80px',
            'height': '80px',
            'font-size': '14px',
            'font-weight': 'bold',
            'color': '#000',
          }
        },
        {
          selector: 'node[type="supplier"]',
          style: {
            'background-color': (ele: any) => {
              const risk = ele.data('risk')
              if (risk >= 10) return '#dc2626' // critical
              if (risk >= 6) return '#ea580c' // high
              if (risk >= 3) return '#f59e0b' // medium
              return '#10b981' // low
            },
            'border-width': '2px',
            'border-color': (ele: any) => {
              return ele.data('status') === 'active' ? '#000' : '#999'
            }
          }
        },
        {
          selector: 'edge',
          style: {
            'width': (ele: any) => Math.max(1, ele.data('weight') / 10),
            'line-color': '#cbd5e1',
            'target-arrow-color': '#cbd5e1',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        }
      ],
      layout: {
        name: 'dagre',
        rankDir: 'BT', // Bottom to top
        padding: 50,
        spacingFactor: 1.5,
      } as any,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    })

    // Add click event
    cyRef.current.on('tap', 'node[type="supplier"]', (evt) => {
      const node = evt.target
      const data = node.data()
      
      alert(`${data.label}\nCountry: ${data.country}\nRisk Score: ${data.risk.toFixed(2)}\nStatus: ${data.status}`)
    })

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy()
      }
    }
  }, [suppliers, company])

  return (
    <div className="relative">
      <div ref={containerRef} className="w-full h-[500px] border rounded-lg bg-gray-50" />
      
      <div className="mt-4 flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-red-600"></div>
          <span>Critical (≥10)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-orange-600"></div>
          <span>High (≥6)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
          <span>Medium (≥3)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-green-600"></div>
          <span>Low (&lt;3)</span>
        </div>
      </div>
    </div>
  )
}
