from neo4j import GraphDatabase
from app.core.config import settings


class Neo4jClient:
    def __init__(self):
        self._driver = None

    def get_driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        return self._driver

    def query(self, cypher: str, params: dict = None) -> list:
        params = params or {}
        with self.get_driver().session() as session:
            result = session.run(cypher, params)
            return [dict(r) for r in result]

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None


neo4j_client = Neo4jClient()