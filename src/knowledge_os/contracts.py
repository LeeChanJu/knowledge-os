from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ContractRegistry:
    version: str
    contracts: dict[str, str]
    change_control: dict[str, object]

    @classmethod
    def load(cls, path: Path) -> "ContractRegistry":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        required = {"source", "evidence", "knowledge", "governance", "retrieval", "action"}
        missing = required - set(data["contracts"])
        if missing:
            raise ValueError(f"missing stable contracts: {', '.join(sorted(missing))}")
        return cls(
            version=str(data["version"]),
            contracts=dict(data["contracts"]),
            change_control=dict(data["change_control"]),
        )

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "contracts": self.contracts,
            "change_control": self.change_control,
        }
