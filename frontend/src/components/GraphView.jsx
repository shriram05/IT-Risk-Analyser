import { useEffect, useRef, useState, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

const NODE_COLORS = {
  Service:  '#6366f1',
  Server:   '#0ea5e9',
  Database: '#f59e0b',
  Team:     '#10b981',
}

const EDGE_COLORS = {
  DEPENDS_ON: '#818cf8',
  RUNS_ON:    '#38bdf8',
  HOSTS:      '#fbbf24',
  OWNED_BY:   '#34d399',
}

function Legend() {
  return (
    <div className="absolute bottom-3 left-3 bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs">
      <p className="text-slate-500 mb-1.5 font-medium">Node Types</p>
      {Object.entries(NODE_COLORS).map(([type, color]) => (
        <div key={type} className="flex items-center gap-1.5 mb-1">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
          <span className="text-slate-400">{type}</span>
        </div>
      ))}
    </div>
  )
}

export default function GraphView({ graphData, affectedNodeLabels }) {
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 400, height: 300 })

  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(([entry]) => {
      setDimensions({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      })
    })
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  const nodes = (graphData?.nodes || []).map((n) => ({
    id: n.id,
    label: n.label || n.id,
    type: n.type || 'Service',
    criticality: n.criticality,
    status: n.status,
    isAffected: affectedNodeLabels.includes(n.label),
  }))

  const links = (graphData?.edges || []).map((e) => ({
    source: e.source,
    target: e.target,
    label: e.label,
  }))

  const paintNode = useCallback((node, ctx, globalScale) => {
    const label = node.label || ''
    const fontSize = Math.max(8, 12 / globalScale)
    const r = node.isAffected ? 7 : 5

    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = node.isAffected
      ? '#ef4444'
      : (NODE_COLORS[node.type] || '#6366f1')
    ctx.fill()

    if (node.isAffected) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI)
      ctx.strokeStyle = 'rgba(239,68,68,0.4)'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    ctx.font = `${fontSize}px Inter, sans-serif`
    ctx.fillStyle = node.isAffected ? '#fca5a5' : '#cbd5e1'
    ctx.textAlign = 'center'
    ctx.fillText(label, node.x, node.y + r + fontSize)
  }, [affectedNodeLabels])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-slate-200">Infrastructure Graph</h2>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>{nodes.length} nodes</span>
          <span>{links.length} edges</span>
          {affectedNodeLabels.length > 0 && (
            <span className="text-red-400">{affectedNodeLabels.length} affected</span>
          )}
        </div>
      </div>

      <div
        ref={containerRef}
        className="flex-1 rounded-lg bg-slate-900 border border-slate-700 relative overflow-hidden"
      >
        {nodes.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-xs text-slate-600">Loading infrastructure graph...</p>
          </div>
        ) : (
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height}
            graphData={{ nodes, links }}
            nodeCanvasObject={paintNode}
            nodeCanvasObjectMode={() => 'replace'}
            linkColor={(link) => EDGE_COLORS[link.label] || '#475569'}
            linkWidth={1.2}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            backgroundColor="#0f172a"
            cooldownTicks={80}
          />
        )}
        <Legend />
      </div>
    </div>
  )
}
