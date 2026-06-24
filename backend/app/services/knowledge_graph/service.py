"""
Module 2: Knowledge Graph Generator
Builds and queries Neo4j graph from ingested entities.

Node types : Service, Module, Class, Function, Developer, API,
             Incident, BugPattern, ArchDecision, Team
Relationship types : DEPENDS_ON, PUBLISHES, CONSUMES, CREATED_BY,
                     AFFECTED_BY, DECIDED_BY, REPLACED_BY
"""
from __future__ import annotations
from app.db.neo4j import get_driver
from app.core.logging import logger


class KnowledgeGraphService:

    async def create_node(self, label: str, properties: dict) -> str:
        """Create or merge a node; returns neo4j element id."""
        driver = get_driver()
        async with driver.session() as session:
            result = await session.run(
                f"MERGE (n:{label} {{name: $name}}) SET n += $props RETURN elementId(n) AS id",
                name=properties.get("name", ""),
                props=properties,
            )
            record = await result.single()
            return record["id"] if record else ""

    async def create_relationship(self, from_name: str, from_label: str,
                                   to_name: str, to_label: str,
                                   rel_type: str, props: dict | None = None) -> None:
        driver = get_driver()
        async with driver.session() as session:
            await session.run(
                f"""
                MATCH (a:{from_label} {{name: $from_name}})
                MATCH (b:{to_label} {{name: $to_name}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """,
                from_name=from_name,
                to_name=to_name,
                props=props or {},
            )

    async def get_dependencies(self, service_name: str) -> list[dict]:
        """Return all services that depend_on or are depended-on by a service."""
        driver = get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Service {name: $name})-[r:DEPENDS_ON*1..3]-(dep:Service)
                RETURN dep.name AS name, type(r) AS rel, dep.description AS description
                """,
                name=service_name,
            )
            return [dict(r) async for r in result]

    async def get_impact_analysis(self, component_name: str) -> list[dict]:
        """Which components are affected if this one changes?"""
        driver = get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (c {name: $name})<-[:DEPENDS_ON*1..5]-(affected)
                RETURN labels(affected)[0] AS type, affected.name AS name
                """,
                name=component_name,
            )
            return [dict(r) async for r in result]

    async def get_incident_history(self, service_name: str) -> list[dict]:
        driver = get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Service {name: $name})-[:AFFECTED_BY]->(i:Incident)
                RETURN i.title AS title, i.severity AS severity,
                       i.root_cause AS root_cause, i.resolved_at AS resolved_at
                ORDER BY i.created_at DESC LIMIT 20
                """,
                name=service_name,
            )
            return [dict(r) async for r in result]

    async def build_from_document(self, entities: list[dict], relations: list[dict]) -> None:
        """Bulk-insert entities + relations extracted from a parsed document."""
        for entity in entities:
            await self.create_node(entity["label"], entity["properties"])
        for rel in relations:
            await self.create_relationship(**rel)
        logger.info("kg_build_complete", entities=len(entities), relations=len(relations))
