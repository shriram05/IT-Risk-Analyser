export default function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-slate-700 bg-navy-800">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">
          G
        </div>
        <div>
          <h1 className="text-base font-semibold text-white leading-tight">GraphRAG RCA</h1>
          <p className="text-xs text-slate-400">IT Incident Root Cause Analysis</p>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
          Neo4j Graph
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          ChromaDB
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          Gemini 2.0 Flash
        </span>
      </div>
    </header>
  )
}
