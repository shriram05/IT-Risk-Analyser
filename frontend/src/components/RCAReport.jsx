import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function RCAReport({ report, isAnalyzing }) {
  if (isAnalyzing && !report) {
    return (
      <div className="flex flex-col h-full">
        <h2 className="text-sm font-semibold text-slate-200 mb-2">RCA Report</h2>
        <div className="flex-1 rounded-lg bg-slate-900 border border-slate-700 p-4 flex items-center justify-center">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-xs text-slate-500">Generating root cause analysis...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="flex flex-col h-full">
        <h2 className="text-sm font-semibold text-slate-200 mb-2">RCA Report</h2>
        <div className="flex-1 rounded-lg bg-slate-900 border border-slate-700 p-4 flex items-center justify-center">
          <p className="text-xs text-slate-600 text-center">
            Submit an alert to generate<br />a root cause analysis report
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-slate-200">RCA Report</h2>
        <button
          onClick={() => {
            const blob = new Blob([report], { type: 'text/markdown' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `rca-${new Date().toISOString().slice(0, 10)}.md`
            a.click()
          }}
          className="text-xs px-2.5 py-1 rounded border border-slate-600 text-slate-400
                     hover:border-indigo-500 hover:text-slate-200 transition-colors"
        >
          Download .md
        </button>
      </div>

      <div className="flex-1 overflow-y-auto rounded-lg bg-slate-900 border border-slate-700 p-4">
        <div className="rca-markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
