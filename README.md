# GraphRAG — IT Incident Root Cause Analysis

AI agent that traverses a Neo4j infrastructure graph to identify root causes of IT incidents. Combines graph relationships (service dependencies, server topology, team ownership) with semantic search over past incidents to produce structured RCA reports.

## Architecture

```
React Frontend (Vite)
    → FastAPI Backend
        → LangChain Agent (Gemini 2.0 Flash)
            ├── get_affected_services   → Neo4j (graph query)
            ├── trace_dependencies      → Neo4j (multi-hop traversal)
            ├── get_server_info         → Neo4j
            ├── get_team_ownership      → Neo4j
            └── get_similar_past_incidents → ChromaDB (vector search)
```

**Neo4j Graph Schema:**
```
(Service)-[:DEPENDS_ON]->(Service)
(Service)-[:RUNS_ON]->(Server)
(Server)-[:HOSTS]->(Database)
(Service)-[:OWNED_BY]->(Team)
```

## Project Structure

```
graphrag/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── api/routes/
│   │   │   ├── incidents.py     # POST /api/analyze  (SSE stream)
│   │   │   └── graph.py         # GET  /api/graph
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings
│   │   │   └── agent.py         # LangChain agentic loop
│   │   ├── db/
│   │   │   ├── neo4j_client.py
│   │   │   └── chroma_client.py
│   │   └── tools/
│   │       ├── graph_tools.py   # Neo4j LangChain tools
│   │       └── vector_tools.py  # ChromaDB LangChain tool
│   ├── seed_data.py             # Populate Neo4j + ChromaDB
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── AlertInput.jsx
        │   ├── GraphView.jsx    # react-force-graph-2d
        │   ├── AgentTrace.jsx   # Live SSE tool call display
        │   └── RCAReport.jsx    # Markdown report
        └── services/api.js
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Neo4j AuraDB](https://neo4j.com/cloud/platform/aura-graph-database/) free account
- Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Create `.env` (copy from `.env.example`):
```env
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_auradb_password
GEMINI_API_KEY=your_gemini_api_key
```

Seed the databases (run once):
```bash
python seed_data.py
```

Start the API:
```bash
uvicorn app.main:app --reload
```
API runs at `http://localhost:8000`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```
UI runs at `http://localhost:5173`

## Usage

1. Open `http://localhost:5173`
2. Click **Sample 1** or paste your own alert text
3. Click **Run RCA Analysis**
4. Watch the agent traverse the graph in real time (Agent Trace panel)
5. Affected services light up red in the infrastructure graph
6. Read the full RCA report on the right — download as `.md`

## Sample Alerts

```
CRITICAL: prod-db-01 CPU at 95%, connection pool exhausted.
order-service returning HTTP 503.

ALERT: api-gateway 5xx rate 45% — upstream timeout to
user-service on prod-server-01.

WARNING: payment-service p99 latency 8s (SLA: 500ms).
Redis connection refused in logs.
```

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `POST /api/analyze` | POST | Stream SSE events for RCA analysis |
| `GET /api/graph` | GET | Full infrastructure graph (nodes + edges) |
| `GET /api/graph/highlight?service=X` | GET | Subgraph for a specific service |
| `GET /health` | GET | Health check |

## SSE Event Format

```json
{"type": "tool_start",  "tool": "get_affected_services", "input": {...}}
{"type": "tool_result", "tool": "get_affected_services", "output": {...}}
{"type": "report",      "content": "## Incident Summary\n..."}
{"type": "done"}
```
