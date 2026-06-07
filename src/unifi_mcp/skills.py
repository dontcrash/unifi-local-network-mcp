from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

READ_METHODS = {"GET"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
ENDPOINT_METHODS = READ_METHODS | WRITE_METHODS


class SkillLoadError(ValueError):
    """Raised when a runtime skill manifest is invalid."""


@dataclass(frozen=True)
class SkillSource:
    file: str
    url: str | None = None


@dataclass(frozen=True)
class SkillDefinition:
    schema_version: int
    name: str
    title: str
    namespace: str
    method: str
    path: str
    description: str
    path_parameters: list[dict[str, Any]]
    query_parameters: list[dict[str, Any]]
    request_body: list[dict[str, Any]]
    responses: list[dict[str, Any]]
    response_sample: str | None
    source: SkillSource

    @property
    def is_read(self) -> bool:
        return self.method in READ_METHODS

    @property
    def is_write(self) -> bool:
        return self.method in WRITE_METHODS

    @property
    def is_connector_proxy(self) -> bool:
        return "/connector/" in self.path or self.name.startswith("unifi_network_connector_")


def load_skill(path: Path) -> SkillDefinition:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillLoadError(f"{path}: invalid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise SkillLoadError(f"{path}: manifest must be a JSON object")

    method = raw.get("method")
    if method not in ENDPOINT_METHODS:
        raise SkillLoadError(f"{path}: unsupported method {method!r}")

    parameters = raw.get("parameters")
    source = raw.get("source")
    required = ["schemaVersion", "name", "title", "namespace", "method", "path", "description"]
    for key in required:
        if key not in raw:
            raise SkillLoadError(f"{path}: missing required key {key!r}")
    if not isinstance(parameters, dict):
        raise SkillLoadError(f"{path}: parameters must be an object")
    if not isinstance(source, dict) or "file" not in source:
        raise SkillLoadError(f"{path}: source.file is required")

    return SkillDefinition(
        schema_version=int(raw["schemaVersion"]),
        name=str(raw["name"]),
        title=str(raw["title"]),
        namespace=str(raw["namespace"]),
        method=str(method),
        path=str(raw["path"]),
        description=str(raw["description"]),
        path_parameters=list(parameters.get("path", [])),
        query_parameters=list(parameters.get("query", [])),
        request_body=list(parameters.get("body", [])),
        responses=list(raw.get("responses", [])),
        response_sample=raw.get("responseSample"),
        source=SkillSource(file=str(source["file"]), url=source.get("url")),
    )


def should_expose_skill(
    skill: SkillDefinition,
    *,
    read_only: bool,
    allow_connector_proxy: bool,
) -> bool:
    if read_only and not skill.is_read:
        return False
    return not (skill.is_connector_proxy and not allow_connector_proxy)


def load_skills(
    skills_dir: Path,
    *,
    read_only: bool = True,
    allow_connector_proxy: bool = False,
) -> list[SkillDefinition]:
    if not skills_dir.exists():
        raise SkillLoadError(f"Skills directory does not exist: {skills_dir}")

    skills = [load_skill(path) for path in sorted(skills_dir.glob("*.json"))]
    return [
        skill
        for skill in skills
        if should_expose_skill(
            skill,
            read_only=read_only,
            allow_connector_proxy=allow_connector_proxy,
        )
    ]


def count_methods(skills: Iterable[SkillDefinition]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for skill in skills:
        counts[skill.method] = counts.get(skill.method, 0) + 1
    return counts
