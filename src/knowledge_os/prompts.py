import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PromptArtifact:
    name: str
    version: str
    path: Path
    sha256: str
    output_contract: str

    def read_verified(self) -> str:
        content = self.path.read_text(encoding="utf-8")
        actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if actual != self.sha256:
            raise ValueError(f"prompt {self.name} checksum mismatch; register a new prompt version")
        return content

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "sha256": self.sha256,
            "output_contract": self.output_contract,
        }

    def as_dict(self) -> dict:
        return {**self.metadata(), "content": self.read_verified()}


@dataclass(frozen=True)
class PromptRegistry:
    version: str
    prompts: dict[str, PromptArtifact]

    @classmethod
    def load(cls, path: Path) -> "PromptRegistry":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        prompts: dict[str, PromptArtifact] = {}
        for name, definition in data["prompts"].items():
            artifact = PromptArtifact(
                name=name,
                version=str(definition["version"]),
                path=(path.parent / definition["path"]).resolve(),
                sha256=str(definition["sha256"]),
                output_contract=str(definition["output_contract"]),
            )
            artifact.read_verified()
            prompts[name] = artifact
        return cls(version=str(data["version"]), prompts=prompts)

    def metadata(self) -> dict:
        return {
            "version": self.version,
            "prompts": {name: artifact.metadata() for name, artifact in self.prompts.items()},
        }

    def prompt(self, name: str) -> dict:
        artifact = self.prompts.get(name)
        if artifact is None:
            raise KeyError(name)
        return artifact.as_dict()
