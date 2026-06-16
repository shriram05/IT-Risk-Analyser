const SAMPLE_ALERTS = [
  'CRITICAL: prod-db-01 CPU at 95%, connection pool exhausted. order-service returning HTTP 503.',
  'ALERT: api-gateway 5xx rate 45% — upstream timeout to user-service on prod-server-01.',
]

export default function AlertInput({ value, onChange, onAnalyze, isAnalyzing }) {
  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Incident Alert</h2>
        <span className="text-xs text-slate-500">Paste any alert text</span>
      </div>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter alert text here..."
        disabled={isAnalyzing}
        rows={5}
        className="w-full rounded-lg bg-slate-900 border border-slate-600 text-slate-200
                   text-xs p-2.5 resize-none focus:outline-none focus:border-indigo-500
                   placeholder:text-slate-600 disabled:opacity-60 font-mono leading-relaxed"
      />

      <div className="flex gap-2">
        {SAMPLE_ALERTS.map((alert, i) => (
          <button
            key={i}
            onClick={() => onChange(alert)}
            disabled={isAnalyzing}
            className="flex-1 text-xs px-2 py-1.5 rounded border border-slate-600 text-slate-400
                       hover:border-indigo-500 hover:text-slate-200 transition-colors disabled:opacity-40"
          >
            Sample {i + 1}
          </button>
        ))}
      </div>

      <button
        onClick={onAnalyze}
        disabled={isAnalyzing || !value.trim()}
        className="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white
                   font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                   flex items-center justify-center gap-2"
      >
        {isAnalyzing ? (
          <>
            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Analyzing...
          </>
        ) : (
          'Run RCA Analysis'
        )}
      </button>
    </div>
  )
}