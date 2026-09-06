from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "replace-with-desktop-instance-password"
    neo4j_database: str = "neo4j"
    ops_db_path: Path = Path("data/ops.db")
    ontology_path: Path = Path("config/ontology.yaml")
    contracts_path: Path = Path("config/contracts.yaml")
    prompts_path: Path = Path("config/prompts.yaml")
    migrations_path: Path = Path("migrations")
    embedding_dimensions: int = 1536
    # Omit this for the durable local-first default: the stdio MCP process owns
    # the Knowledge Service ASGI lifespan. Set it only for an explicitly
    # supervised external deployment.
    mcp_base_url: str | None = None
    mcp_workspace_id: str = "personal"
    mcp_principals: str = "local-user"
    mcp_actor: str | None = None
    mcp_action_review_principals: str = ""
    mcp_action_execution_principals: str = ""
    mcp_action_policy_version: str = "action-policy-v1"
    mcp_action_policy_versions: str = ""
    mcp_timeout_seconds: float = 30.0
    review_base_url: str | None = None
    review_workspace_id: str = "personal"
    review_principals: str = "local-user"
    review_actor: str | None = None
    review_timeout_seconds: float = 30.0
    action_executor_base_url: str | None = None
    action_executor_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
