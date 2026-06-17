# Cypher Queries — GraphRAG RCA Project

Cypher is the query language for Neo4j, like SQL is for relational databases.
All queries are in `backend/app/tools/graph_tools.py`.

---

## 1. Seed Query — Create the entire graph

**File:** `backend/seed_data.py`

```cypher
CREATE
  (api:Service    {name: 'api-gateway',         criticality: 'critical'}),
  (user:Service   {name: 'user-service',         criticality: 'high'}),
  (order:Service  {name: 'order-service',        criticality: 'high'}),
  (pay:Service    {name: 'payment-service',      criticality: 'critical'}),
  (notif:Service  {name: 'notification-service', criticality: 'medium'}),
  (inv:Service    {name: 'inventory-service',    criticality: 'high'}),
  (cat:Service    {name: 'catalog-service',      criticality: 'medium'}),

  (srv1:Server {name: 'prod-server-01', ip: '10.0.1.10', status: 'running'}),
  (srv2:Server {name: 'prod-server-02', ip: '10.0.1.11', status: 'running'}),

  (db1:Database  {name: 'prod-db-01',    type: 'PostgreSQL', status: 'degraded'}),
  (db2:Database  {name: 'prod-db-02',    type: 'MongoDB',    status: 'running'}),
  (cache:Database{name: 'redis-cluster', type: 'Redis',      status: 'running'}),

  (t1:Team {name: 'platform-team', oncall: 'alice@company.com'}),
  (t2:Team {name: 'backend-team',  oncall: 'bob@company.com'}),
  (t3:Team {name: 'payments-team', oncall: 'carol@company.com'}),

  (api)-[:DEPENDS_ON]->(user),
  (api)-[:DEPENDS_ON]->(order),
  (order)-[:DEPENDS_ON]->(pay),
  (order)-[:DEPENDS_ON]->(inv),
  (order)-[:DEPENDS_ON]->(notif),
  (user)-[:DEPENDS_ON]->(cat),

  (api)-[:RUNS_ON]->(srv1),
  (order)-[:RUNS_ON]->(srv2),
  ...
```

**What this does:**
- `CREATE` makes new nodes and relationships in one shot
- `(variable:Label {property: value})` — creates a node
- `(a)-[:RELATIONSHIP]->(b)` — creates a directed relationship from a to b
- Run once via `python seed_data.py`

---

## 2. Delete all nodes — Clean slate

**Used in:** `seed_data.py` before re-seeding

```cypher
MATCH (n) DETACH DELETE n
```

| Part | Meaning |
|---|---|
| `MATCH (n)` | Find every node in the graph (no filter = all nodes) |
| `DETACH` | Also delete all relationships connected to those nodes |
| `DELETE n` | Delete the nodes themselves |

> Without `DETACH`, Neo4j throws an error if you try to delete a node that still has relationships.

---

## 3. get_affected_services — Find services matching alert keywords

**File:** `graph_tools.py` → Tool 1

```cypher
MATCH (s:Service)
WHERE any(kw IN $keywords WHERE
    toLower(s.name) CONTAINS toLower(kw)
    OR toLower(s.description) CONTAINS toLower(kw)
)
OPTIONAL MATCH (s)-[:OWNED_BY]->(t:Team)
RETURN s.name AS service, s.description AS description,
       s.criticality AS criticality, t.name AS team
```

**Step by step:**

```cypher
MATCH (s:Service)
```
Find all nodes with label `Service`. The variable `s` holds each one.

```cypher
WHERE any(kw IN $keywords WHERE ...)
```
`$keywords` is the parameter passed by Gemini — e.g. `["order-service", "database", "503"]`
`any(...)` means: return true if AT LEAST ONE keyword matches.

```cypher
toLower(s.name) CONTAINS toLower(kw)
```
Case-insensitive substring check.
`"Order-Service"` and `"order-service"` both match `"order"`.

```cypher
OPTIONAL MATCH (s)-[:OWNED_BY]->(t:Team)
```
Try to follow the `OWNED_BY` arrow to get the team.
`OPTIONAL` means: if no team found, don't drop the row — just return null for team.

```cypher
RETURN s.name AS service, s.criticality AS criticality, t.name AS team
```
Return these columns. `AS` renames them for cleaner output.

**Example input/output:**
```
Input:  keywords = ["order-service", "database"]
Output: [{service: "order-service", criticality: "high", team: "backend-team"}]
```

---

## 4. trace_dependencies — Multi-hop upstream traversal

**File:** `graph_tools.py` → Tool 2 (part 1)

```cypher
MATCH path = (s:Service {name: $name})-[:DEPENDS_ON*1..4]->(dep:Service)
RETURN dep.name AS dependency, dep.criticality AS criticality,
       length(path) AS depth,
       [node IN nodes(path) | node.name] AS chain
ORDER BY depth
```

**Step by step:**

```cypher
MATCH path = (s:Service {name: $name})
```
Find the starting service node. `path =` stores the entire path object, not just the endpoint.

```cypher
-[:DEPENDS_ON*1..4]->
```
This is the **key GraphRAG part** — multi-hop traversal.
- `*1..4` means: follow `DEPENDS_ON` arrows between 1 and 4 hops
- `->` means follow arrows in the forward direction (what this service depends ON)
- Without the `*`, it would only go 1 hop

```
order-service →(1 hop)→ payment-service                     depth=1
order-service →(1 hop)→ inventory-service                    depth=1
order-service →(2 hops)→ prod-db (via inventory)             depth=2
```

```cypher
length(path) AS depth
```
How many hops from the starting node to this dependency.

```cypher
[node IN nodes(path) | node.name] AS chain
```
List comprehension — extracts the name of every node in the path.
Result: `["order-service", "payment-service"]`

```cypher
ORDER BY depth
```
Show direct dependencies (depth=1) first, then deeper ones.

**Example output:**
```
[
  {dependency: "payment-service",  depth: 1, chain: ["order-service", "payment-service"]},
  {dependency: "inventory-service",depth: 1, chain: ["order-service", "inventory-service"]},
  {dependency: "notification-service", depth: 1, chain: ["order-service", "notification-service"]}
]
```

---

## 5. trace_dependencies — Multi-hop downstream traversal

**File:** `graph_tools.py` → Tool 2 (part 2)

```cypher
MATCH path = (dep:Service)-[:DEPENDS_ON*1..4]->(s:Service {name: $name})
RETURN dep.name AS dependent, dep.criticality AS criticality,
       length(path) AS depth,
       [node IN nodes(path) | node.name] AS chain
ORDER BY depth
```

**Same as above but arrow is reversed:**

```cypher
(dep:Service)-[:DEPENDS_ON*1..4]->(s:Service {name: $name})
```
Now we start from unknown nodes `dep` and find ones that point TO our service.
This answers: **"who will break if order-service goes down?"**

```
api-gateway →(1 hop)→ order-service    ← api-gateway depends on order-service
```

**Example output:**
```
[{dependent: "api-gateway", depth: 1, chain: ["api-gateway", "order-service"]}]
```

---

## 6. get_server_info — Infrastructure layer

**File:** `graph_tools.py` → Tool 3

```cypher
MATCH (s:Service {name: $name})-[:RUNS_ON]->(srv:Server)
OPTIONAL MATCH (srv)-[:HOSTS]->(db:Database)
RETURN s.name AS service, srv.name AS server, srv.ip AS ip,
       srv.status AS server_status,
       collect({name: db.name, type: db.type, status: db.status}) AS databases
```

**Step by step:**

```cypher
MATCH (s:Service {name: $name})-[:RUNS_ON]->(srv:Server)
```
Follow the `RUNS_ON` arrow from service to its server.

```cypher
OPTIONAL MATCH (srv)-[:HOSTS]->(db:Database)
```
From that server, follow `HOSTS` to find all databases on it.
`OPTIONAL` because not every server has a database node.

```cypher
collect({name: db.name, type: db.type, status: db.status}) AS databases
```
`collect()` is an aggregation function — groups multiple database rows into a single list.
Without `collect`, you'd get one row per database (like SQL JOIN explosion).

**Example output:**
```
[{
  service: "order-service",
  server: "prod-server-02",
  ip: "10.0.1.11",
  server_status: "running",
  databases: [
    {name: "prod-db-01", type: "PostgreSQL", status: "degraded"},
    {name: "prod-db-02", type: "MongoDB",    status: "running"}
  ]
}]
```

---

## 7. get_team_ownership — Escalation info

**File:** `graph_tools.py` → Tool 4

```cypher
MATCH (s:Service {name: $name})-[:OWNED_BY]->(t:Team)
RETURN s.name AS service, t.name AS team,
       t.slack_channel AS slack_channel, t.oncall AS oncall_contact
```

Simplest query — just follow one `OWNED_BY` arrow and return team details.

**Example output:**
```
[{
  service: "order-service",
  team: "backend-team",
  slack_channel: "#backend",
  oncall_contact: "bob@company.com"
}]
```

---

## 8. get_graph — Full graph for UI visualization

**File:** `api/routes/graph.py` — used by React frontend

```cypher
-- Nodes query
MATCH (n)
RETURN elementId(n) AS id, labels(n)[0] AS type,
       n.name AS label, n.criticality AS criticality,
       n.status AS status

-- Edges query
MATCH (a)-[r]->(b)
RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS label
```

```cypher
MATCH (n)
```
Every node, no filter.

```cypher
elementId(n) AS id
```
Neo4j's internal unique ID for each node — used by react-force-graph-2d to identify nodes.

```cypher
labels(n)[0] AS type
```
Gets the label of the node (`Service`, `Server`, `Database`, `Team`).
`[0]` because a node can have multiple labels — we take the first one.

```cypher
MATCH (a)-[r]->(b)
```
Every relationship in the graph.

```cypher
type(r) AS label
```
Gets the relationship type string (`DEPENDS_ON`, `RUNS_ON`, `HOSTS`, `OWNED_BY`).

---

## Summary — All queries at a glance

| Query | Pattern | Purpose |
|---|---|---|
| Seed | `CREATE (n:Label {...})` | Create nodes + relationships |
| Delete | `MATCH (n) DETACH DELETE n` | Wipe entire graph |
| Find services | `MATCH (s:Service) WHERE any(kw IN $keywords ...)` | Keyword match on nodes |
| Upstream deps | `(s)-[:DEPENDS_ON*1..4]->(dep)` | Multi-hop forward traversal |
| Downstream deps | `(dep)-[:DEPENDS_ON*1..4]->(s)` | Multi-hop reverse traversal |
| Server info | `(s)-[:RUNS_ON]->(srv)-[:HOSTS]->(db)` | Two-hop path traversal |
| Team ownership | `(s)-[:OWNED_BY]->(t)` | Single-hop traversal |
| Full graph | `MATCH (n)` + `MATCH (a)-[r]->(b)` | All nodes + all edges for UI |

---

## Key Cypher concepts used

| Concept | Syntax | Meaning |
|---|---|---|
| Node pattern | `(n:Label {prop: val})` | Match a node with label and property |
| Relationship | `-[:TYPE]->` | Follow a directed relationship |
| Multi-hop | `*1..4` | Follow 1 to 4 hops of same relationship |
| Optional | `OPTIONAL MATCH` | Don't drop row if no match (like LEFT JOIN) |
| Aggregation | `collect(...)` | Group multiple rows into a list |
| List comprehension | `[x IN list | x.prop]` | Transform a list inline |
| Parameters | `$name`, `$keywords` | Safe parameterized inputs (no injection) |
| Functions | `toLower()`, `length()`, `type()`, `labels()`, `elementId()` | Built-in helpers |
