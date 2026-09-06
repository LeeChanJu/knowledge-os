CREATE CONSTRAINT action_execution_id_unique IF NOT EXISTS
FOR (n:ActionExecution) REQUIRE n.id IS UNIQUE;
