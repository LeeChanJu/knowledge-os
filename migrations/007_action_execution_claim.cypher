CREATE CONSTRAINT action_execution_claim_id_unique IF NOT EXISTS
FOR (n:ActionExecutionClaim) REQUIRE n.id IS UNIQUE;

CREATE INDEX action_execution_claim_status IF NOT EXISTS
FOR (n:ActionExecutionClaim) ON (n.status);
