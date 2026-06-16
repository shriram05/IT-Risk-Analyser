import { useState, useEffect } from 'react'
import Header from './components/Header'
import AlertInput from './components/AlertInput'
import GraphView from './components/GraphView'
import AgentTrace from './components/AgentTrace'
import RCAReport from './components/RCAReport'
import { fetchGraph, streamAnalysis } from './services/api'

export default function App() {
  const [alertText, setAlertText] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [trace, setTrace] = useState([])
  const [rcaReport, setRcaReport] = useState('')
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [affectedNodes, setAffectedNodes] = useState([])

  useEffect(() => {
    fetchGraph().then(setGraphData).catch(() => {})
  }, [])

  async function handleAnalyze() {
    if (!alertText.trim() || isAnalyzing) return
    setIsAnalyzing(true)
    setTrace([])
    setRcaReport('')
    setAffectedNodes([])

    try {
      await streamAnalysis(alertText, (event) => {
        if (event.type === 'tool_start') {
          setTrace((prev) => [...prev, event])
        } else if (event.type === 'tool_result') {
          setTrace((prev) => [...prev, event])
          if (event.tool === 'get_affected_services' && event.output?.affected_services) {
            const names = event.output.affected_services.map((s) => s.service).filter(Boolean)
            setAffectedNodes((prev) => [...new Set([...prev, ...names])])
          }
          if (event.tool === 'trace_dependencies' && event.output?.service) {
            setAffectedNodes((prev) => [...new Set([...prev, event.output.service])])
          }
        } else if (event.type === 'report') {
          setRcaReport(event.content)
        } else if (event.type === 'done') {
          setIsAnalyzing(false)
          fetchGraph().then(setGraphData).catch(() => {})
        }
      })
    } catch (err) {
      setTrace((prev) => [...prev, { type: 'tool_result', tool: 'error', output: { error: err.message } }])
      setIsAnalyzing(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#0f172a', overflow: 'hidden' }}>
      <Header />

      <div style={{ flex: 1, display: 'flex', gap: '12px', padding: '12px', overflow: 'hidden', minHeight: 0 }}>

        {/* Left panel */}
        <div style={{ width: '300px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Alert Input */}
          <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '16px', flexShrink: 0 }}>
            <AlertInput
              value={alertText}
              onChange={setAlertText}
              onAnalyze={handleAnalyze}
              isAnalyzing={isAnalyzing}
            />
          </div>
          {/* Agent Trace */}
          <div style={{ flex: 1, background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '16px', overflow: 'hidden', minHeight: 0 }}>
            <AgentTrace trace={trace} isAnalyzing={isAnalyzing} />
          </div>
        </div>

        {/* Center — Graph */}
        <div style={{ flex: 1, background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '16px', overflow: 'hidden', minHeight: 0 }}>
          <GraphView graphData={graphData} affectedNodeLabels={affectedNodes} />
        </div>

        {/* Right — RCA Report */}
        <div style={{ width: '380px', flexShrink: 0, background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '16px', overflow: 'hidden', minHeight: 0 }}>
          <RCAReport report={rcaReport} isAnalyzing={isAnalyzing} />
        </div>

      </div>
    </div>
  )
}