from typing import List
from langchain_core.tools import tool
from app.db.neo4j_client import neo4j_client


@tool
def get_affected_services(keywords: List[str]) -> dict:
    """
    Find services in the infrastructure graph that are potentially affected by this incident.
    Pass a list of keywords extracted from the alert (service names, error types, components).
    Example: keywords=["database", "order-service", "timeout"]
    """
    if not keywords:
        return {"affected_services": [], "total": 0}

    query = """
    MATCH (s:Service)
    WHERE any(kw IN $keywords WHERE
        toLower(s.name) CONTAINS toLower(kw)
        OR toLower(s.description) CONTAINS toLower(kw)
    )
    OPTIONAL MATCH (s)-[:OWNED_BY]->(t:Team)
    RETURN s.name AS service, s.description AS description,
           s.criticality AS criticality, t.name AS team
    """
    results = neo4j_client.query(query, {"keywords": keywords})
    return {"affected_services": results, "total": len(results)}


@tool
def trace_dependencies(service_name: str) -> dict:
    """
    Trace all upstream (what this service depends on) and downstream (what depends on this service)
    dependencies in the graph. Use this to find the blast radius and identify the root cause.
    """
    upstream_query = """
    MATCH path = (s:Service {name: $name})-[:DEPENDS_ON*1..4]->(dep:Service)
    RETURN dep.name AS dependency, dep.criticality AS criticality,
           length(path) AS depth,
           [node IN nodes(path) | node.name] AS chain
    ORDER BY depth
    """
    downstream_query = """
    MATCH path = (dep:Service)-[:DEPENDS_ON*1..4]->(s:Service {name: $name})
    RETURN dep.name AS dependent, dep.criticality AS criticality,
           length(path) AS depth,
           [node IN nodes(path) | node.name] AS chain
    ORDER BY depth
    """
    upstream = neo4j_client.query(upstream_query, {"name": service_name})
    downstream = neo4j_client.query(downstream_query, {"name": service_name})

    return {
        "service": service_name,
        "depends_on": upstream,
        "depended_by": downstream,
    }


@tool
def get_server_info(service_name: str) -> dict:
    """
    Get the physical server/host and database details for a given service.
    Use this to understand the infrastructure layer contributing to the incident.
    """
    query = """
    MATCH (s:Service {name: $name})-[:RUNS_ON]->(srv:Server)
    OPTIONAL MATCH (srv)-[:HOSTS]->(db:Database)
    RETURN s.name AS service, srv.name AS server, srv.ip AS ip,
           srv.status AS server_status,
           collect({name: db.name, type: db.type, status: db.status}) AS databases
    """
    results = neo4j_client.query(query, {"name": service_name})
    return {
        "server_info": results if results else f"No server info found for '{service_name}'"
    }


@tool
def get_team_ownership(service_name: str) -> dict:
    """
    Get the engineering team responsible for a service — for incident escalation.
    Returns team name, Slack channel, and on-call contact email.
    """
    query = """
    MATCH (s:Service {name: $name})-[:OWNED_BY]->(t:Team)
    RETURN s.name AS service, t.name AS team,
           t.slack_channel AS slack_channel, t.oncall AS oncall_contact
    """
    results = neo4j_client.query(query, {"name": service_name})
    return {
        "ownership": results if results else f"No team ownership found for '{service_name}'"
    }
