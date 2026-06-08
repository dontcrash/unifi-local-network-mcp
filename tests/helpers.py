from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from unifi_mcp.skills import SkillDefinition, load_skills

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/network"
SKILLS = ROOT / "skills/network"


def all_runtime_skills() -> list[SkillDefinition]:
    return load_skills(SKILLS, read_only=False)


def find_skill(predicate: Callable[[SkillDefinition], bool]) -> SkillDefinition:
    for skill in all_runtime_skills():
        if predicate(skill):
            return skill
    raise AssertionError("No runtime skill matched the requested shape")


def sample_value(field: dict[str, Any]) -> Any:
    type_name = str(field.get("type") or "string").lower()
    if type_name.startswith("array"):
        return []
    if type_name.startswith("object"):
        return {}
    if type_name == "integer":
        return 25
    if type_name == "number":
        return 1.5
    if type_name == "boolean":
        return True
    return f"{field['name']}-value"


def sample_values(fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {str(field["name"]): sample_value(field) for field in fields if field.get("name")}


def expected_url(
    base_url: str,
    path: str,
    path_params: dict[str, Any],
    query: dict[str, Any],
) -> str:
    rendered_path = path
    for name, value in path_params.items():
        rendered_path = rendered_path.replace("{" + name + "}", quote(str(value), safe=""))
        rendered_path = rendered_path.replace("*" + name, quote(str(value), safe="/"))
    url = base_url.rstrip("/") + rendered_path
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())
