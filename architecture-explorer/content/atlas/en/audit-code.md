OpsStore writes operations records to SQLite. It is not one transaction with the Neo4j commit, so code must distinguish and reconcile outcomes.
