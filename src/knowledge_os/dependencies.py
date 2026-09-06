from functools import lru_cache

from knowledge_os.config import get_settings
from knowledge_os.contracts import ContractRegistry
from knowledge_os.graph import GraphStore
from knowledge_os.ontology import Ontology
from knowledge_os.ops import OpsStore
from knowledge_os.prompts import PromptRegistry


@lru_cache
def get_ops() -> OpsStore:
    return OpsStore(get_settings().ops_db_path)


@lru_cache
def get_graph() -> GraphStore:
    settings = get_settings()
    return GraphStore(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password,
        settings.neo4j_database,
        get_ops(),
        settings.embedding_dimensions,
        get_contracts().contracts,
    )


@lru_cache
def get_ontology() -> Ontology:
    return Ontology.load(get_settings().ontology_path)


@lru_cache
def get_contracts() -> ContractRegistry:
    return ContractRegistry.load(get_settings().contracts_path)


@lru_cache
def get_prompts() -> PromptRegistry:
    return PromptRegistry.load(get_settings().prompts_path)
