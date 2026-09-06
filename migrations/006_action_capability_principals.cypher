MATCH (w:Workspace)-[:HAS_ACTION]->(a:Action)
SET a.workspace_id = coalesce(a.workspace_id, w.id),
    a.review_principals = coalesce(a.review_principals, [a.requested_by]),
    a.execution_principals = coalesce(a.execution_principals, []);
