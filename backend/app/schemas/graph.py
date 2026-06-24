from pydantic import BaseModel


class NodeCreate(BaseModel):
    label: str
    properties: dict


class RelationshipCreate(BaseModel):
    from_name: str
    from_label: str
    to_name: str
    to_label: str
    rel_type: str
    props: dict = {}


class GraphVisualizationResponse(BaseModel):
    nodes: list[dict]
    edges: list[dict]


class DependencyNode(BaseModel):
    name: str
    rel: str
    description: str | None = None


class ImpactNode(BaseModel):
    type: str
    name: str
