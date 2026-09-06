CREATE CONSTRAINT source_id_unique IF NOT EXISTS FOR (n:Source) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT document_version_id_unique IF NOT EXISTS FOR (n:DocumentVersion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (n:Chunk) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT assertion_id_unique IF NOT EXISTS FOR (n:Assertion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT proposal_id_unique IF NOT EXISTS FOR (n:Proposal) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT approval_id_unique IF NOT EXISTS FOR (n:Approval) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (n:Event) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT decision_id_unique IF NOT EXISTS FOR (n:Decision) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT action_id_unique IF NOT EXISTS FOR (n:Action) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT workspace_id_unique IF NOT EXISTS FOR (n:Workspace) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (n:User) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT schema_migration_name_unique IF NOT EXISTS FOR (n:SchemaMigration) REQUIRE n.name IS UNIQUE;

CREATE FULLTEXT INDEX chunk_text_fulltext IF NOT EXISTS FOR (n:Chunk) ON EACH [n.text, n.section];
CREATE FULLTEXT INDEX entity_name_fulltext IF NOT EXISTS FOR (n:Entity) ON EACH [n.name, n.description];
