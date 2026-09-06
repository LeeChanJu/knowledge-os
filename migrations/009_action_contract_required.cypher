CREATE CONSTRAINT action_contract_version_required IF NOT EXISTS
FOR (n:Action) REQUIRE n.contract_version IS NOT NULL;

CREATE CONSTRAINT action_execution_contract_version_required IF NOT EXISTS
FOR (n:ActionExecution) REQUIRE n.contract_version IS NOT NULL;

CREATE CONSTRAINT action_execution_claim_contract_version_required IF NOT EXISTS
FOR (n:ActionExecutionClaim) REQUIRE n.contract_version IS NOT NULL;
