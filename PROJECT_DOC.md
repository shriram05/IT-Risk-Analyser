# GraphRAG RCA — Complete Technical Documentation

---

## 1. Problem Statement

When a production system fails at 2 AM, an on-call engineer receives an alert like:
```
CRITICAL: prod-db-01 CPU at 95%, connection pool exhausted.
order-service returning HTTP 503.
```

The engineer then manually spends 30–60 minutes answering:
- Which services are affected?
- What is the root cause?
- What else will break as a consequence?
- Has this happened before? How was it fixed?
- Who do I escalate to?

**This project automates that entire investigation using an AI agent backed by a graph database and a vector database.**

---

## 2. Why GraphRAG — Not Regular RAG

### Regular RAG
```
User query → embed → vector similarity search → top K chunks → LLM answers
```
Good for: "What is the refund policy?" — finding relevant text.

**Fails for:** "What services will break if prod-db-01 goes down three hops away?"
Vector search finds similar text. It cannot traverse relationships.

### GraphRAG (what we built)
```
User query → LLM extracts entities → graph traversal → relationship data → LLM answers
```

**The key difference:**

| Question | Vector Search | Graph Traversal |
|---|---|---|
| Find similar past incidents | ✅ | ❌ |
| What does order-service depend on? | ❌ | ✅ |
| Which team owns the root cause service? | ❌ | ✅ |
| What breaks 3 hops from a failed DB? | ❌ | ✅ |
| Trace blast radius of an outage | ❌ | ✅ |

**We use both** — Neo4j for relationship traversal, ChromaDB for semantic incident search.

---

## 3. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React 18 + Vite | Fast dev server, component-based UI |
| Styling | Tailwind CSS | Utility-first, no custom CSS needed |
| Graph Visualization | react-force-graph-2d | Force-directed graph, canvas-based, handles dynamic data |
| HTTP Client | Axios + Fetch API | Axios for simple GET, Fetch for SSE streaming |
| Backend | FastAPI | Async Python, native SSE support, fast |
| AI Agent | LangChain + Gemini 2.0 Flash | Tool binding, agentic loop, autonomous reasoning |
| LLM API | Gemini via OpenAI-compatible endpoint | Reuse OpenAI SDK pattern, corporate proxy friendly |
| Graph Database | Neo4j AuraDB | Native graph storage, multi-hop Cypher traversal |
| Vector Database | ChromaDB (local) | Persistent local vector store, no external service needed |
| Config | Pydantic Settings | Type-safe .env loading |

---

## 4. Graph Database Design

### Why a graph database for IT infrastructure?

IT infrastructure is naturally a graph:
- Services call other services
- Services run on servers
- Servers host databases
- Teams own services

Modelling this in a relational database requires multiple tables and complex JOINs. In Neo4j, relationships are first-class citizens stored as direct pointers — traversal is O(relationship count), not O(table size).

### Node Types

| Label | Properties | Count |
|---|---|---|
| `Service` | name, description, criticality | 7 |
| `Server` | name, ip, status | 2 |
| `Database` | name, type, status | 3 |
| `Team` | name, slack_channel, oncall | 3 |

**Total: 15 nodes**

### Relationship Types

| Type | Direction | Meaning | Count |
|---|---|---|---|
| `DEPENDS_ON` | Service → Service | Service A calls Service B | 6 |
| `RUNS_ON` | Service → Server | Service deployed on server | 7 |
| `HOSTS` | Server → Database | Server has a database | 4 |
| `OWNED_BY` | Service → Team | Team responsible for service | 7 |

**Total: 24 relationships**

### Full Graph

```
                        [platform-team]
                              ↑ OWNED_BY
                        api-gateway
                       /           \
              DEPENDS_ON           DEPENDS_ON
                     /                 \
             user-service          order-service ──RUNS_ON──► prod-server-02
                  |                /    |    \                      |
             DEPENDS_ON        pay    inv   notif              prod-db-01 (degraded)
                  ↓              ↑     ↑     ↑                 prod-db-02
            catalog-service   payments backend backend
```

### Why prod-db-01 is marked degraded

Intentional design choice for demo. When Sample 1 alert is analyzed:
- Agent finds order-service affected
- Traces to prod-server-02
- Finds prod-db-01 on that server with status: degraded
- This becomes the root cause in the RCA report

---

## 5. Vector Database Design

### ChromaDB — Past Incidents Knowledge Base

5 past incident reports stored as vector embeddings:

| ID | Incident | Services |
|---|---|---|
| INC-001 | prod-db-01 connection pool exhausted | order-service, payment-service |
| INC-002 | api-gateway 5xx, user-service OOMKilled | api-gateway, user-service |
| INC-003 | payment-service Redis timeout | payment-service |
| INC-004 | inventory-service high CPU, MongoDB slow query | inventory-service, order-service |
| INC-005 | notification-service queue buildup | notification-service |

Each document contains: incident description, root cause, resolution steps, prevention measures.

### How semantic search works

```
Alert text → ChromaDB default embedding model → 384-dimensional vector
Each stored incident → also a 384-dimensional vector

Cosine similarity calculated between alert vector and all 5 incident vectors
Top 3 closest returned with similarity scores (0 to 1)
```

High similarity (>0.8) → Gemini uses the resolution as a recommendation
Low similarity (<0.3) → Gemini notes them as not relevant

### Why ChromaDB alongside Neo4j

Neo4j knows the **current state** of infrastructure.
ChromaDB knows the **history** of what went wrong and how it was fixed.

Together: root cause identified from graph + proven solution found from history.

---

## 6. LangChain Agent — The Core Logic

### What is an agent

A regular LLM call: input → LLM → output. One shot.

An agent: input → LLM → tool call → result → LLM → tool call → result → ... → LLM → final answer.

The LLM decides what tools to call, in what order, with what arguments. We only give it the tools and the goal.

### Tool Definitions

```python
TOOLS = [
    get_affected_services,      # Neo4j — find services matching keywords
    trace_dependencies,         # Neo4j — multi-hop traversal
    get_server_info,            # Neo4j — server + database details
    get_team_ownership,         # Neo4j — team + escalation contact
    get_similar_past_incidents, # ChromaDB — semantic search
]
```

Each tool is decorated with `@tool` from LangChain. The docstring becomes the tool description that Gemini reads to understand when to use it.

### Tool Binding

```python
llm_with_tools = llm.bind_tools(TOOLS)
```

This tells Gemini: "You have these 5 functions available. Their schemas are X. Decide when to call them."

Gemini receives the tool schemas in JSON format:
```json
{
    "name": "get_affected_services",
    "description": "Find services in the infrastructure graph...",
    "parameters": {
        "keywords": {"type": "array", "items": {"type": "string"}}
    }
}
```

### The Agentic Loop

```python
for _ in range(MAX_ITERATIONS):

    # LLM call — Gemini decides: call a tool OR write final answer
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    # No tool calls = Gemini wrote the final RCA report
    if not response.tool_calls:
        yield report event
        return

    # Execute each tool Gemini requested
    for tool_call in response.tool_calls:
        result = tool_map[tool_call["name"]].invoke(tool_call["args"])

        # Stream result to frontend
        yield tool_result event

        # Add result back to message history
        messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

    # Loop — Gemini sees results, decides next action
```

### Message History

Every LLM call receives the full conversation history:

```
Iteration 1:
  messages = [SystemMessage, HumanMessage("analyze this alert")]
  → Gemini calls get_affected_services

Iteration 2:
  messages = [SystemMessage, HumanMessage, AIMessage(tool_call), ToolMessage(result)]
  → Gemini sees result, calls trace_dependencies

Iteration 3:
  messages = [..., AIMessage(tool_call), ToolMessage(result)]
  → Gemini calls get_server_info

...and so on until Gemini stops calling tools and writes the report
```

This is how Gemini "remembers" what it already found — the message history carries all context forward.

### Entity Extraction — How Gemini Picks Keywords

We never wrote keyword extraction code. Gemini reads the alert text and decides:

```
Alert: "prod-db-01 CPU 95%, order-service returning 503"

Gemini thinks:
- "prod-db-01" is a database name → keyword
- "order-service" is a service name → keyword
- "503" means HTTP error → add "database", "connection" as related keywords
- Calls: get_affected_services(keywords=["prod-db-01", "order-service", "database", "503"])
```

This is more intelligent than traditional NER (Named Entity Recognition) because Gemini understands context — it adds "database" even though it's not in the alert, because 503 + connection pool = database issue.

---

## 7. FastAPI Backend

### Why FastAPI

- Native async support — needed for SSE streaming
- Pydantic models — automatic request validation
- Fast — built on Starlette + uvicorn

### SSE Streaming

SSE (Server-Sent Events) allows the server to push data to the client over a single HTTP connection.

```python
@router.post("/api/analyze")
async def analyze_incident(request: AlertRequest):
    return StreamingResponse(
        run_agent_sse(request.alert_text),   # async generator
        media_type="text/event-stream",
    )
```

`run_agent_sse` is an async generator — it `yield`s SSE events as the agent runs:
```python
yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'get_affected_services'})}\n\n"
```

SSE format: every event is `data: {json}\n\n` (double newline = end of event).

### Why asyncio.to_thread

LangChain's `invoke()` is synchronous (blocking). FastAPI is async. Mixing them directly blocks the event loop.

```python
# Wrong — blocks FastAPI's event loop
result = tool_fn.invoke(tool_args)

# Correct — runs blocking code in a thread pool
result = await asyncio.to_thread(tool_fn.invoke, tool_args)
```

`asyncio.to_thread` offloads the blocking call to a thread, freeing the event loop to handle other requests.

---

## 8. React Frontend

### 3-Panel Layout

```
┌──────────────┬──────────────────────────┬────────────────┐
│  LEFT        │  CENTER                  │  RIGHT         │
│  300px       │  flex-1 (fills space)    │  380px         │
│              │                          │                │
│  AlertInput  │  GraphView               │  RCAReport     │
│  textarea    │  react-force-graph-2d    │  react-markdown│
│  Sample btns │  15 nodes + 24 edges     │  download btn  │
│  Run button  │  affected = red          │                │
│              │                          │                │
│  AgentTrace  │                          │                │
│  live tools  │                          │                │
└──────────────┴──────────────────────────┴────────────────┘
```

### SSE Stream Handling in React

Cannot use `EventSource` for POST requests (EventSource only supports GET).
Uses `fetch()` with `ReadableStream` instead:

```javascript
const response = await fetch('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ alert_text: alertText })
})

const reader = response.body.getReader()
const decoder = new TextDecoder()
let buffer = ''

while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()   // keep incomplete line for next chunk

    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const event = JSON.parse(line.slice(6))
            onEvent(event)
        }
    }
}
```

Buffer is needed because one network chunk may contain partial SSE events.

### Graph Highlighting Logic

```
SSE event: tool_result from get_affected_services
    ↓
App.jsx extracts service names from output
    ↓
setAffectedNodes(["order-service", "payment-service"])
    ↓
React re-renders GraphView with new affectedNodeLabels prop
    ↓
GraphView.jsx: isAffected = affectedNodeLabels.includes(node.label)
    ↓
paintNode: fillStyle = isAffected ? '#ef4444' : NODE_COLORS[node.type]
    ↓
react-force-graph-2d repaints canvas
    ↓
Affected nodes appear RED
```

Highlighting happens during analysis — as soon as tool 1 returns, not after the report is done.

### Vite Proxy

React runs on `:5173`. FastAPI runs on `:8000`. Browser blocks cross-origin requests.

```javascript
// vite.config.js
proxy: {
    '/api': { target: 'http://localhost:8000' }
}
```

React thinks it's calling `/api/analyze` on its own server. Vite forwards it to FastAPI transparently. No CORS issues in development.

---

## 9. Data Flow — Complete End to End

```
1. Page loads
   → React calls GET /api/graph
   → FastAPI queries Neo4j: MATCH (n), MATCH (a)-[r]->(b)
   → Returns 15 nodes + 24 edges as JSON
   → react-force-graph-2d renders the force graph

2. User types alert + clicks Run RCA Analysis
   → React calls POST /api/analyze with alert_text
   → FastAPI creates StreamingResponse
   → run_agent_sse() async generator starts

3. Agentic loop — Iteration 1
   → LLM call: Gemini reads alert, decides to call get_affected_services
   → SSE event: tool_start → React AgentTrace shows "Find Affected Services"
   → Tool runs Cypher against Neo4j
   → SSE event: tool_result → React AgentTrace shows result
   → React extracts service names → setAffectedNodes
   → GraphView highlights affected nodes RED

4. Agentic loop — Iterations 2-5
   → Gemini calls trace_dependencies, get_server_info, get_team_ownership
   → Each tool runs Cypher → result → SSE event → AgentTrace updates
   → Gemini calls get_similar_past_incidents
   → ChromaDB vector search → top 3 similar incidents returned

5. Agentic loop — Final iteration
   → Gemini has all data, no more tool calls
   → Gemini writes markdown RCA report
   → SSE event: report → React setRcaReport
   → RCAReport panel renders markdown
   → SSE event: done → isAnalyzing = false → button re-enables

6. User downloads report
   → Click Download .md
   → Blob created from report string
   → Browser downloads rca-2025-01-10.md
```

---

## 10. Cypher Queries — Key Concepts

### Multi-hop traversal — the most important query

```cypher
MATCH path = (s:Service {name: $name})-[:DEPENDS_ON*1..4]->(dep:Service)
RETURN dep.name, length(path) AS depth
```

`*1..4` means follow DEPENDS_ON arrows between 1 and 4 hops.
This is impossible to express cleanly in SQL — requires 4 recursive JOINs.
In Neo4j — one line.

### Parameterized queries — security

```python
neo4j_client.query(query, {"name": service_name})
```

Parameters are passed separately from the query string.
Neo4j driver handles escaping. No Cypher injection possible.

### OPTIONAL MATCH — like LEFT JOIN

```cypher
OPTIONAL MATCH (s)-[:OWNED_BY]->(t:Team)
```

If no team found, row is still returned with `t = null`.
Without OPTIONAL, rows with no team would be dropped entirely.

For full Cypher query explanations see [CYPHER_QUERIES.md](CYPHER_QUERIES.md).

---

## 11. Scalability — How the System Grows

### Adding more infrastructure to Neo4j

```cypher
-- Add a new service
CREATE (s:Service {name: 'search-service', criticality: 'high'})
CREATE (s)-[:DEPENDS_ON]->(catalog)
CREATE (s)-[:OWNED_BY]->(t2)
```

Agent automatically uses new nodes in the next analysis. No code change needed.

### Adding more past incidents to ChromaDB

```python
collection.add(
    ids=["INC-006"],
    documents=["Incident: search-service timeout...Resolution: increased memory limit"],
    metadatas=[{"date": "2025-06-01", "severity": "P2"}]
)
```

ChromaDB re-indexes automatically. Agent finds new incidents in semantic search.

### Production ingestion pipeline

```
ServiceNow / Jira (incident tickets)
    ↓ webhook on ticket close
FastAPI ingestion endpoint
    ↓
Post-mortem text → ChromaDB
New services deployed → Neo4j
    ↓
Agent gets richer with every incident — self-improving knowledge base
```

---

## 12. Main Points

### What is GraphRAG

> "GraphRAG combines a knowledge graph with vector search. Instead of only finding semantically similar text, it traverses relationships between entities. In our project, Neo4j stores the infrastructure graph and ChromaDB stores past incidents. The agent queries both — graph traversal finds the root cause through dependency chains, vector search finds how similar incidents were resolved."

### Why Neo4j over PostgreSQL

> "Neo4j stores relationships as direct pointers between nodes. Traversing 4 levels of service dependencies is a single Cypher query with `*1..4`. In PostgreSQL this requires 4 recursive JOINs — complex to write, slow to execute on large graphs, and hard to maintain as the schema evolves."

### What is an agentic loop

> "The LLM doesn't just answer once. It decides which tools to call, calls them, sees the results, and decides what to do next — in a loop. In our project, Gemini autonomously decides to call get_affected_services first, then trace_dependencies with the service it found, then get_server_info, and so on. We only gave it the tools and the goal. The reasoning and sequencing is Gemini's job."

### What is SSE

> "Server-Sent Events is a protocol where the server pushes data to the client over a single HTTP connection as it becomes available. We use it to stream each tool call and result to the React frontend in real time, so the user sees the agent working live instead of waiting for the full report."

### How entity extraction works

> "We don't use a traditional NER library. Gemini reads the alert text and extracts relevant keywords itself when calling get_affected_services. This is more powerful than NER because Gemini understands context — for a 503 error alert, it adds 'database' and 'connection' as keywords even if they're not in the alert text, because it understands that HTTP 503 in a microservices context usually points to a database or upstream service failure."
