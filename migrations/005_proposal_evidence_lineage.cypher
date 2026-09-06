MATCH (p:Proposal)-[:PROMOTED]->(knowledge)
MATCH (c:Chunk)-[:EVIDENCE_FOR]->(knowledge)
MERGE (p)-[:SUPPORTED_BY]->(c)
SET p.evidence_linkage_version = '1';
