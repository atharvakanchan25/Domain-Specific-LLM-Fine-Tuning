from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.services.knowledge_graph.service import KnowledgeGraphService
from app.schemas.graph import GraphVisualizationResponse

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])

_kg = KnowledgeGraphService()


@router.get("/dependencies/{service_name}")
async def get_dependencies(service_name: str, user=Depends(get_current_user)):
    return await _kg.get_dependencies(service_name)


@router.get("/impact/{component_name}")
async def get_impact(component_name: str, user=Depends(get_current_user)):
    return await _kg.get_impact_analysis(component_name)


@router.get("/incidents/{service_name}")
async def get_incidents(service_name: str, user=Depends(get_current_user)):
    return await _kg.get_incident_history(service_name)


@router.get("/visualize", response_model=GraphVisualizationResponse)
async def visualize(limit: int = 100, user=Depends(get_current_user)):
    from app.db.neo4j import get_driver
    driver = get_driver()
    async with driver.session() as s:
        result = await s.run(
            "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT $limit", limit=limit
        )
        nodes, edges, seen = [], [], set()
        async for record in result:
            for node in [record["n"], record["m"]]:
                nid = node.element_id
                if nid not in seen:
                    seen.add(nid)
                    nodes.append({"id": nid, "label": list(node.labels)[0],
                                  "name": node.get("name", "")})
            edges.append({"source": record["n"].element_id,
                          "target": record["m"].element_id,
                          "type": record["r"].type})
    return GraphVisualizationResponse(nodes=nodes, edges=edges)
