from neo4j import GraphDatabase

from .config import settings


def normalize_name(name: str) -> str:
    return name.strip().lower()


def normalize_relation(relation: str) -> str:
    return relation.strip().upper()


class GraphStore:
    """Neo4j wrapper. Entities dedup via MERGE on (user_id, normalized name) —
    a deliberately simple v1 linking policy; semantic entity resolution
    (synonyms, pronouns) is a known limitation, not attempted here."""

    def __init__(self) -> None:
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def close(self) -> None:
        self._driver.close()

    def upsert_entity(self, user_id: str, name: str, entity_type: str) -> str:
        query = """
        MERGE (e:Entity {user_id: $user_id, key: $key})
        ON CREATE SET e.name = $name, e.type = $type
        RETURN e.key AS key
        """
        with self._driver.session() as session:
            record = session.run(
                query, user_id=user_id, key=normalize_name(name), name=name, type=entity_type
            ).single()
            return record["key"]

    def upsert_relationship(
        self, user_id: str, source_key: str, target_key: str, relation: str, memory_id: str
    ) -> None:
        """(Re)asserts a fact as current. Always clears superseded_at — this is the
        only path that marks an edge active, so a fact restated after being
        superseded (e.g. reverting a preference) becomes current again correctly."""
        query = """
        MATCH (a:Entity {user_id: $user_id, key: $source_key})
        MATCH (b:Entity {user_id: $user_id, key: $target_key})
        MERGE (a)-[r:RELATES {relation: $relation}]->(b)
        SET r.memory_id = $memory_id, r.updated_at = timestamp(), r.superseded_at = NULL
        """
        with self._driver.session() as session:
            session.run(
                query,
                user_id=user_id,
                source_key=source_key,
                target_key=target_key,
                relation=normalize_relation(relation),
                memory_id=memory_id,
            )

    def supersede_relationship(self, user_id: str, source_key: str, target_key: str, relation: str) -> None:
        query = """
        MATCH (a:Entity {user_id: $user_id, key: $source_key})
              -[r:RELATES {relation: $relation}]->
              (b:Entity {user_id: $user_id, key: $target_key})
        SET r.superseded_at = timestamp()
        """
        with self._driver.session() as session:
            session.run(
                query,
                user_id=user_id,
                source_key=source_key,
                target_key=target_key,
                relation=normalize_relation(relation),
            )

    def find_entity_by_mention(self, user_id: str, text: str) -> str | None:
        """Longest matching known entity name mentioned in free text (rule-based, no NLP)."""
        query = "MATCH (e:Entity {user_id: $user_id}) RETURN e.name AS name"
        with self._driver.session() as session:
            names = [r["name"] for r in session.run(query, user_id=user_id)]
        text_lower = text.lower()
        for name in sorted(names, key=len, reverse=True):
            if name.lower() in text_lower:
                return name
        return None

    def neighbors(self, user_id: str, name: str, hops: int = 1, limit: int = 10) -> list[dict]:
        # Relationship-length ranges can't be parameterized in Cypher; hops is
        # an internal int (never user input), so this is safe string formatting.
        query = f"""
        MATCH p = (e:Entity {{user_id: $user_id, key: $key}})-[:RELATES*1..{int(hops)}]-(n:Entity)
        WHERE ALL(rel IN relationships(p) WHERE rel.superseded_at IS NULL)
        RETURN DISTINCT n.name AS name, n.type AS type
        LIMIT $limit
        """
        with self._driver.session() as session:
            return [
                dict(r) for r in session.run(query, user_id=user_id, key=normalize_name(name), limit=limit)
            ]


graph_store = GraphStore()
