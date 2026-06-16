"""
Run this once to populate Neo4j + ChromaDB with sample infrastructure data.
Usage: python seed_data.py
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import chromadb

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def seed_neo4j():
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

        session.run("""
        CREATE
          (api:Service    {name: 'api-gateway',          description: 'Main API gateway entry point',       criticality: 'critical'}),
          (user:Service   {name: 'user-service',          description: 'User authentication and profiles',   criticality: 'high'}),
          (order:Service  {name: 'order-service',         description: 'Order management and fulfillment',   criticality: 'high'}),
          (pay:Service    {name: 'payment-service',       description: 'Payment processing and billing',     criticality: 'critical'}),
          (notif:Service  {name: 'notification-service',  description: 'Email and SMS notifications',        criticality: 'medium'}),
          (inv:Service    {name: 'inventory-service',     description: 'Product inventory management',       criticality: 'high'}),
          (cat:Service    {name: 'catalog-service',       description: 'Product catalog and search',         criticality: 'medium'}),

          (srv1:Server {name: 'prod-server-01', ip: '10.0.1.10', status: 'running'}),
          (srv2:Server {name: 'prod-server-02', ip: '10.0.1.11', status: 'running'}),

          (db1:Database  {name: 'prod-db-01',     type: 'PostgreSQL', status: 'degraded'}),
          (db2:Database  {name: 'prod-db-02',     type: 'MongoDB',    status: 'running'}),
          (cache:Database{name: 'redis-cluster',  type: 'Redis',      status: 'running'}),

          (t1:Team {name: 'platform-team',  slack_channel: '#platform',  oncall: 'alice@company.com'}),
          (t2:Team {name: 'backend-team',   slack_channel: '#backend',   oncall: 'bob@company.com'}),
          (t3:Team {name: 'payments-team',  slack_channel: '#payments',  oncall: 'carol@company.com'}),

          (api)-[:DEPENDS_ON]->(user),
          (api)-[:DEPENDS_ON]->(order),
          (order)-[:DEPENDS_ON]->(pay),
          (order)-[:DEPENDS_ON]->(inv),
          (order)-[:DEPENDS_ON]->(notif),
          (user)-[:DEPENDS_ON]->(cat),

          (api)-[:RUNS_ON]->(srv1),
          (user)-[:RUNS_ON]->(srv1),
          (notif)-[:RUNS_ON]->(srv1),
          (cat)-[:RUNS_ON]->(srv1),
          (order)-[:RUNS_ON]->(srv2),
          (pay)-[:RUNS_ON]->(srv2),
          (inv)-[:RUNS_ON]->(srv2),

          (srv1)-[:HOSTS]->(db1),
          (srv1)-[:HOSTS]->(cache),
          (srv2)-[:HOSTS]->(db1),
          (srv2)-[:HOSTS]->(db2),

          (api)-[:OWNED_BY]->(t1),
          (user)-[:OWNED_BY]->(t2),
          (order)-[:OWNED_BY]->(t2),
          (pay)-[:OWNED_BY]->(t3),
          (notif)-[:OWNED_BY]->(t2),
          (inv)-[:OWNED_BY]->(t2),
          (cat)-[:OWNED_BY]->(t2)
        """)

        count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        print(f"✅ Neo4j seeded — {count} nodes created")


PAST_INCIDENTS = [
    {
        "id": "INC-001",
        "doc": """Incident: Database connection timeout on prod-db-01
Alert: order-service returning HTTP 503. DB connection pool exhausted.
Root Cause: Long-running batch job in order-service acquired all 50 PostgreSQL connections and never released them.
Impact: order-service, payment-service degraded for 45 minutes. ~1,200 failed orders.
Resolution: Killed long-running queries via pg_cancel_backend(). Increased connection pool from 50→100. Added query timeout of 30 seconds.
Prevention: Added alert at 80% pool utilization. Implemented connection pool monitoring dashboard.""",
        "meta": {"date": "2024-01-15", "severity": "P1", "resolved_in": "45min", "services": "order-service,payment-service"},
    },
    {
        "id": "INC-002",
        "doc": """Incident: API Gateway 5xx spike — 45% error rate on all endpoints
Alert: api-gateway 5xx rate crossed threshold. user-service unreachable.
Root Cause: user-service pod OOMKilled due to memory leak in JWT session cache. api-gateway could not authenticate requests without user-service.
Impact: All authenticated API traffic failed for 12 minutes.
Resolution: Restarted user-service pod. Applied memory limit patch (512Mi→1Gi). Cleared Redis session cache.
Prevention: Added memory usage alert at 85%. Implemented proper LRU session cache eviction policy.""",
        "meta": {"date": "2024-02-03", "severity": "P1", "resolved_in": "12min", "services": "api-gateway,user-service"},
    },
    {
        "id": "INC-003",
        "doc": """Incident: Payment service timeout — checkout failures across all regions
Alert: payment-service p99 latency >8s. Redis connection refused errors in logs.
Root Cause: Redis cluster failover triggered by network partition between primary and replica. payment-service lost session state and could not process transactions.
Impact: Payment processing degraded for 8 minutes. ~200 failed transactions totaling $24,000.
Resolution: Redis Sentinel promoted replica to primary. payment-service reconnected automatically after circuit breaker reset.
Prevention: Implemented circuit breaker pattern in payment-service. Added Redis Sentinel health monitoring.""",
        "meta": {"date": "2024-02-20", "severity": "P2", "resolved_in": "8min", "services": "payment-service"},
    },
    {
        "id": "INC-004",
        "doc": """Incident: Inventory service CPU at 95% — order timeouts cascading
Alert: inventory-service CPU 95%. order-service timeout waiting for inventory check.
Root Cause: Unoptimized MongoDB aggregation query in inventory-service triggered by catalog-service sync job running every 60 seconds. Query doing full collection scan due to missing index.
Impact: inventory-service response time >10s. order-service cascading timeouts. ~500 orders delayed.
Resolution: Added compound index on (productId, warehouseId). Changed sync frequency to every 15 minutes. Query time dropped from 8s to 0.3s.
Prevention: Added slow query monitoring alert (>2s). Implemented mandatory query timeout of 5 seconds.""",
        "meta": {"date": "2024-03-10", "severity": "P2", "resolved_in": "25min", "services": "inventory-service,order-service"},
    },
    {
        "id": "INC-005",
        "doc": """Incident: Notification service queue buildup — 50,000+ pending notifications
Alert: notification-service message queue depth >1000. Email delivery delayed 2+ hours.
Root Cause: SMTP relay rate limit hit (500 emails/hour). notification-service retrying failed emails with aggressive exponential backoff, causing queue starvation.
Impact: Email notifications delayed by 2+ hours for all users. SMS unaffected.
Resolution: Implemented exponential backoff with jitter. Added secondary SMTP relay (SendGrid) as fallback. Cleared dead-letter queue.
Prevention: Added queue depth alert at 1,000 messages. Implemented dead letter queue with manual review.""",
        "meta": {"date": "2024-03-25", "severity": "P3", "resolved_in": "2hr", "services": "notification-service"},
    },
]


def seed_chromadb():
    client = chromadb.PersistentClient(path="./chroma_db")
    try:
        client.delete_collection("past_incidents")
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name="past_incidents",
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=[inc["id"] for inc in PAST_INCIDENTS],
        documents=[inc["doc"] for inc in PAST_INCIDENTS],
        metadatas=[inc["meta"] for inc in PAST_INCIDENTS],
    )
    print(f"✅ ChromaDB seeded — {len(PAST_INCIDENTS)} past incidents indexed")


if __name__ == "__main__":
    print("Seeding Neo4j...")
    seed_neo4j()
    print("Seeding ChromaDB...")
    seed_chromadb()
    driver.close()
    print("\n✅ All done! Run the backend: uvicorn app.main:app --reload")