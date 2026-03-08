"""
Initialisation Neo4j — Cognitive Graph RAG
Crée les index, contraintes et nœuds initiaux.
"""
import asyncio
import os
from neo4j import AsyncGraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "cognitive2024")


async def init():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    async with driver.session() as session:
        print("Création des contraintes...")
        await session.run(
            "CREATE CONSTRAINT entity_name IF NOT EXISTS "
            "FOR (e:Entity) REQUIRE e.name IS UNIQUE"
        )

        print("Création de l'index full-text...")
        try:
            await session.run(
                "CALL db.index.fulltext.createNodeIndex("
                "'cognitiveIndex', ['Entity'], ['name', 'description', 'content'])"
            )
        except Exception:
            print("Index full-text déjà existant.")

        print("Création du nœud racine cognitif...")
        await session.run(
            """
            MERGE (root:Entity {name: 'CognitiveSystem'})
            SET root.type = 'system',
                root.description = 'Cerveau numérique persistant multi-RAG',
                root.created_at = datetime()
            """
        )

        print("Neo4j initialisé.")

    await driver.close()


if __name__ == "__main__":
    asyncio.run(init())
