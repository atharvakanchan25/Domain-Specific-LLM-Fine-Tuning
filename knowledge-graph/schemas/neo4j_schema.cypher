// ── Constraints (uniqueness) ────────────────────────────────────────
CREATE CONSTRAINT service_name IF NOT EXISTS
  FOR (s:Service) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT module_name IF NOT EXISTS
  FOR (m:Module) REQUIRE m.name IS UNIQUE;

CREATE CONSTRAINT developer_email IF NOT EXISTS
  FOR (d:Developer) REQUIRE d.email IS UNIQUE;

CREATE CONSTRAINT api_name IF NOT EXISTS
  FOR (a:API) REQUIRE a.name IS UNIQUE;

CREATE CONSTRAINT incident_id IF NOT EXISTS
  FOR (i:Incident) REQUIRE i.id IS UNIQUE;

CREATE CONSTRAINT arch_decision_id IF NOT EXISTS
  FOR (ad:ArchDecision) REQUIRE ad.id IS UNIQUE;

// ── Indexes ─────────────────────────────────────────────────────────
CREATE INDEX service_team IF NOT EXISTS FOR (s:Service) ON (s.team);
CREATE INDEX incident_severity IF NOT EXISTS FOR (i:Incident) ON (i.severity);
CREATE INDEX incident_service IF NOT EXISTS FOR (i:Incident) ON (i.affected_service);

// ── Sample graph bootstrap ───────────────────────────────────────────
// Uncomment to seed a demo graph:
//
// MERGE (ps:Service {name: "PaymentService", team: "payments", language: "Java"})
// MERGE (os:Service {name: "OrderService",   team: "orders",   language: "Python"})
// MERGE (is:Service {name: "InventoryService",team: "inventory",language: "Go"})
// MERGE (ke:Topic   {name: "order.created"})
//
// MERGE (ps)-[:DEPENDS_ON {since: "2021-01"}]->(os)
// MERGE (os)-[:PUBLISHES]->(ke)
// MERGE (ke)-[:CONSUMED_BY]->(is)
//
// MERGE (inc:Incident {id: "INC-001", title: "DB timeout", severity: "P1",
//                      root_cause: "Connection pool exhaustion"})
// MERGE (ps)-[:AFFECTED_BY]->(inc)
