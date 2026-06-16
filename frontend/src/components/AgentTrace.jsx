const TOOL_META = {
  get_affected_services:    { color: 'text-indigo-400', icon: '🔍', label: 'Find Affected Services' },
  trace_dependencies:       { color: 'text-violet-400', icon: '🕸️', label: 'Trace Dependencies' },
  get_server_info:          { color: 'text-cyan-400',   icon: '🖥️', label: 'Get Server Info' },
  get_team_ownership:       { color: 'text-orange-400', icon: '👥', label: 'Get Team Ownership' },
  get_similar_past_incidents:{ color: 'text-emerald-400', icon: '📚', label: 'Search Past Incidents' },
}

function ToolEvent({ event }) {
  const meta = TOOL_META[event.tool] || { color: 'text-slate-400', icon: '🔧', label: event.tool }

  if (event.type === 'tool_start') {
    return (
      <div className="flex items-start gap-2 py-1.5 border-b border-slate-800">
        <span className="text-sm mt-0.5">{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <span className={`text-xs font-semibold ${meta.color}`}>{meta.label}</span>
          <pre className="text-xs text-slate-500 mt-0.5 truncate">
            {JSON.stringify(event.input)}
          </pre>
        </div>
      </div>
    )
  }

  if (event.type === 'tool_result') {
    const hasError = event.output?.error
    const resultStr = JSON.stringify(event.output, null, 0)
    const preview = resultStr.length > 120 ? resultStr.slice(0, 120) + '…' : resultStr
    return (
      <div className="flex items-start gap-2 py-1.5 border-b border-slate-800 pl-6">
        <span className="text-xs mt-0.5">{hasError ? '❌' : '✅'}</span>
        <pre className={`text-xs flex-1 truncate ${hasError ? 'text-red-400' : 'text-slate-400'}`}>
          {preview}
        </pre>
      </div>
    )
  }

  return null
}

export default function AgentTrace({ trace, isAnalyzing }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-slate-200">Agent Trace</h2>
        {isAnalyzing && (
          <span className="text-xs text-indigo-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            Running
          </span>
        )}
        {!isAnalyzing && trace.length > 0 && (
          <span className="text-xs text-slate-500">
            {trace.filter(e => e.type === 'tool_start').length} tools called
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto rounded-lg bg-slate-900 border border-slate-700 p-2">
        {trace.length === 0 && (
          <p className="text-xs text-slate-600 text-center mt-8">
            Tool calls will appear here in real time
          </p>
        )}
        {trace.map((event, i) => (
          <ToolEvent key={i} event={event} />
        ))}
        {isAnalyzing && (
          <div className="flex items-center gap-2 py-2 text-xs text-slate-500">
            <span className="w-3 h-3 border border-slate-500 border-t-indigo-400 rounded-full animate-spin" />
            Thinking...
          </div>
        )}
      </div>
    </div>
  )
}
