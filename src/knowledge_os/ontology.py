from dataclasses import dataclass
from pathlib import Path

import yaml

from knowledge_os.models import AssertionChange


@dataclass(frozen=True)
class Ontology:
    version: str
    entity_types: frozenset[str]
    relation_types: dict[str, dict[str, list[str]]]

    @classmethod
    def load(cls, path: Path) -> "Ontology":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(
            version=str(data["version"]),
            entity_types=frozenset(data["entity_types"]),
            relation_types=data["relation_types"],
        )

    def validate(self, change: AssertionChange) -> None:
        if change.subject.entity_type not in self.entity_types:
            raise ValueError(f"unknown subject entity type: {change.subject.entity_type}")
        if change.object is None:
            return
        if change.object.entity_type not in self.entity_types:
            raise ValueError(f"unknown object entity type: {change.object.entity_type}")
        rule = self.relation_types.get(change.predicate)
        if not rule:
            raise ValueError(f"unknown relation: {change.predicate}")
        if change.subject.entity_type not in rule["subjects"]:
            raise ValueError(
                f"{change.predicate} does not allow {change.subject.entity_type} subjects"
            )
        if change.object.entity_type not in rule["objects"]:
            raise ValueError(
                f"{change.predicate} does not allow {change.object.entity_type} objects"
            )

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "entity_types": sorted(self.entity_types),
            "relation_types": {
                name: {
                    "subjects": sorted(rule["subjects"]),
                    "objects": sorted(rule["objects"]),
                }
                for name, rule in sorted(self.relation_types.items())
            },
        }
