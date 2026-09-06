MATCH (action:Action)
WHERE action.contract_version IS NULL
SET action.contract_version = 'action-v2';

MATCH (execution:ActionExecution)
WHERE execution.contract_version IS NULL
SET execution.contract_version = 'action-v2';
