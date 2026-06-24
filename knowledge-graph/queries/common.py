"""
knowledge-graph/queries/common.py
Reusable parameterised Cypher queries.
"""

FIND_SHORTEST_PATH = """
MATCH path = shortestPath((a {name: $from})-[*..10]-(b {name: $to}))
RETURN [n in nodes(path) | n.name] AS path_nodes,
       [r in relationships(path) | type(r)] AS relationships
"""

GET_ALL_DEPENDENCIES = """
MATCH (s:Service {name: $service})-[:DEPENDS_ON*1..5]->(dep)
RETURN labels(dep)[0] AS type, dep.name AS name, dep.team AS team
ORDER BY type, name
"""

GET_INCIDENT_CLUSTER = """
MATCH (i:Incident)
WHERE i.affected_service = $service
WITH i ORDER BY i.created_at DESC
RETURN i.id AS id, i.title AS title, i.severity AS severity,
       i.root_cause AS root_cause, i.resolved_at AS resolved_at
LIMIT 30
"""

GET_DEVELOPER_CONTRIBUTIONS = """
MATCH (d:Developer {email: $email})-[:CREATED|MODIFIED]->(n)
RETURN labels(n)[0] AS type, n.name AS name, count(*) AS contributions
ORDER BY contributions DESC
"""

GET_TECH_DECISIONS = """
MATCH (ad:ArchDecision)-[:REJECTED_ALTERNATIVE]->(t:Technology)
RETURN ad.title AS decision, t.name AS rejected, ad.status AS status
ORDER BY ad.created_at DESC
"""

FULL_TEXT_SEARCH = """
CALL db.index.fulltext.queryNodes('entity_fulltext', $query)
YIELD node, score
RETURN labels(node)[0] AS type, node.name AS name, score
ORDER BY score DESC LIMIT 20
"""
