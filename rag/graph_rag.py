"""
Graph RAG — Neo4j
Raisonnement sur les relations entre entités.
Permet de naviguer les connexions : A → B → C
"""
from __future__ import annotations

import logging
import os
from typing import Any

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)


class GraphRAG:
    """Recherche et raisonnement relationnel dans Neo4j."""

    def __init__(self) -> None:
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "cognitive2024")
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def search(self, query: str, depth: int = 2) -> list[dict[str, Any]]:
        """
        Cherche des entités et relations pertinentes à la requête.
        Stratégie : full-text search sur les nœuds, puis expansion des relations.
        """
        try:
            async with self._driver.session() as session:
                # Full-text index search sur les nœuds
                cypher = """
                CALL db.index.fulltext.queryNodes('cognitiveIndex', $query)
                YIELD node, score
                CALL apoc.path.subgraphAll(node, {maxLevel: $depth, limit: 20})
                YIELD nodes, relationships
                RETURN
                    node.name AS entity,
                    score,
                    [r IN relationships | type(r) + ': ' + startNode(r).name + ' → ' + endNode(r).name] AS relations
                ORDER BY score DESC
                LIMIT 10
                """
                result = await session.run(cypher, query=query, depth=depth)
                records = await result.data()

                return [
                    {
                        "entity": r.get("entity", ""),
                        "score": r.get("score", 0.0),
                        "relation": "; ".join(r.get("relations", [])),
                    }
                    for r in records
                ]
        except Exception as e:
            logger.warning(f"[GraphRAG] Erreur recherche : {e}")
            return []

    async def store_entity(self, name: str, entity_type: str, properties: dict[str, Any]) -> None:
        """Crée ou met à jour un nœud entité."""
        async with self._driver.session() as session:
            cypher = """
            MERGE (e:Entity {name: $name})
            SET e.type = $entity_type, e += $properties
            RETURN e
            """
            await session.run(cypher, name=name, entity_type=entity_type, properties=properties)
            logger.info(f"[GraphRAG] Entité stockée : {name}")

    async def store_relation(
        self, source: str, relation_type: str, target: str, properties: dict[str, Any] | None = None
    ) -> None:
        """Crée une relation typée entre deux entités."""
        async with self._driver.session() as session:
            cypher = f"""
            MERGE (a:Entity {{name: $source}})
            MERGE (b:Entity {{name: $target}})
            MERGE (a)-[r:{relation_type}]->(b)
            SET r += $properties
            RETURN r
            """
            await session.run(
                cypher,
                source=source,
                target=target,
                properties=properties or {},
            )
            logger.info(f"[GraphRAG] Relation : {source} -{relation_type}→ {target}")

    async def init_fulltext_index(self) -> None:
        """Crée l'index full-text pour la recherche rapide."""
        async with self._driver.session() as session:
            try:
                await session.run(
                    "CALL db.index.fulltext.createNodeIndex("
                    "'cognitiveIndex', ['Entity'], ['name', 'description'])"
                )
                logger.info("[GraphRAG] Index full-text créé")
            except Exception:
                pass  # L'index existe déjà

    async def close(self) -> None:
        await self._driver.close()
