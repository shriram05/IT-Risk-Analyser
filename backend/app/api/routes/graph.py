from fastapi import APIRouter, HTTPException
from app.db.neo4j_client import neo4j_client

router = APIRouter()


@router.get("/graph")
async def get_graph_data():
    """Return the full infrastructure graph for frontend visualization."""
    try:
        nodes_query = """
        MATCH (n)
        RETURN elementId(n) AS id, labels(n)[0] AS type,
               n.name AS label, n.criticality AS criticality,
               n.status AS status, n.description AS description
        """
        edges_query = """
        MATCH (a)-[r]->(b)
        RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS label
        """
        nodes = neo4j_client.query(nodes_query)
        edges = neo4j_client.query(edges_query)
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/highlight")
async def get_highlighted_subgraph(service: str):
    """Return the subgraph for a specific service with its dependencies highlighted."""
    try:
        query = """
        MATCH path = (s:Service {name: $name})-[:DEPENDS_ON*0..3]-(related)
        UNWIND nodes(path) AS n
        WITH collect(DISTINCT n) AS ns
        UNWIND ns AS node
        RETURN elementId(node) AS id, labels(node)[0] AS type,
               node.name AS label, node.criticality AS criticality
        """
        nodes = neo4j_client.query(query, {"name": service})
        return {"highlighted_nodes": [n["id"] for n in nodes]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
