# GraphRAG — IT Incident Root Cause Analysis

AI agent that traverses a Neo4j infrastructure graph to identify root causes of IT incidents. Combines graph relationship traversal (service dependencies, server topology, team ownership) with semantic search over past incidents to produce structured RCA reports in real time.

## Architecture

```
React Frontend (Vite + Tailwind)
    → FastAPI Backend
        → LangChain Agent (Gemini 2.0 Flash)
            ├── get_affected_services      → Neo4j (keyword match on Service nodes)
            ├── trace_dependencies         → Neo4j (multi-hop traversal *1..4)
            ├── get_server_info            → Neo4j (RUNS_ON + HOSTS traversal)
            ├── get_team_ownership         → Neo4j (OWNED_BY traversal)
            └── get_similar_past_incidents → ChromaDB (vector similarity search)
```

**Neo4j Graph Schema — 15 nodes, 24 relationships:**
```
(Service)-[:DEPENDS_ON]->(Service)   # service calls service
(Service)-[:RUNS_ON]->(Server)       # service deployed on server
(Server)-[:HOSTS]->(Database)        # server has database
(Service)-[:OWNED_BY]->(Team)        # team responsible for service
```

**Infrastructure seeded:**
- 7 Services: api-gateway, user-service, order-service, payment-service, notification-service, inventory-service, catalog-service
- 2 Servers: prod-server-01, prod-server-02
- 3 Databases: prod-db-01 (PostgreSQL), prod-db-02 (MongoDB), redis-cluster
- 3 Teams: platform-team, backend-team, payments-team

## Project Structure

```
Graphrag/
├── .gitignore
├── README.md
├── CYPHER_QUERIES.md          # All Cypher queries explained in detail
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── seed_data.py           # Populate Neo4j + ChromaDB (run once)
│   └── app/
│       ├── main.py            # FastAPI app + CORS
│       ├── api/routes/
│       │   ├── incidents.py   # POST /api/analyze (SSE stream)
│       │   └── graph.py       # GET /api/graph
│       ├── core/
│       │   ├── config.py      # Pydantic settings (.env loader)
│       │   └── agent.py       # LangChain agentic loop + SSE generator
│       ├── db/
│       │   ├── neo4j_client.py
│       │   └── chroma_client.py
│       └── tools/
│           ├── graph_tools.py # 4 Neo4j LangChain tools
│           └── vector_tools.py# ChromaDB semantic search tool
└── frontend/
    ├── package.json
    ├── vite.config.js         # Vite proxy → FastAPI on :8000
    ├── tailwind.config.js
    └── src/
        ├── App.jsx            # Layout + SSE stream handler + state
        ├── index.css          # Tailwind + markdown styles
        ├── services/
        │   └── api.js         # fetch() SSE stream + axios graph call
        └── components/
            ├── Header.jsx         # Top bar with stack indicators
            ├── AlertInput.jsx     # Alert textarea + sample buttons
            ├── AgentTrace.jsx     # Live tool call trace panel
            ├── GraphView.jsx      # react-force-graph-2d visualization
            └── RCAReport.jsx      # Markdown RCA report + download
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

Seed Neo4j + ChromaDB (run once):
```bash
python seed_data.py
```
Expected output:
```
✅ Neo4j seeded — 15 nodes created
✅ ChromaDB seeded — 5 past incidents indexed
```

Start the API:
```bash
uvicorn app.main:app --reload
```
Verify: `http://localhost:8000/health` → `{"status":"ok"}`

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
4. Watch the Agent Trace panel fill with live tool calls
5. Affected services highlight red in the infrastructure graph
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

| Endpoint | Description |
|---|---|
| `POST /api/analyze` | Stream SSE events for RCA analysis |
| `GET /api/graph` | Full infrastructure graph (nodes + edges) |
| `GET /api/graph/highlight?service=X` | Subgraph for a specific service |
| `GET /health` | Health check |

## SSE Event Format

```json
{"type": "tool_start",  "tool": "get_affected_services", "input": {...}}
{"type": "tool_result", "tool": "get_affected_services", "output": {...}}
{"type": "report",      "content": "## Incident Summary\n..."}
{"type": "done"}
```

## Why GraphRAG over regular RAG

Regular RAG (vector search) can find semantically similar past incidents but cannot answer:
- *"What services will break if prod-db-01 goes down?"*
- *"Which team owns the root cause service?"*
- *"How many hops away is the failing database from the user-facing API?"*

Neo4j graph traversal answers these in a single Cypher query with `*1..4` multi-hop syntax. See [CYPHER_QUERIES.md](CYPHER_QUERIES.md) for all queries explained in detail.
