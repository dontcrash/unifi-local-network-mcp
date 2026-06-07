from __future__ import annotations

from typing import Any

from tests.helpers import find_skill
from unifi_mcp.schemas import build_input_schema


def schema_nodes(schema: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [schema]
    for value in schema.get("properties", {}).values():
        nodes.extend(schema_nodes(value))
    items = schema.get("items")
    if isinstance(items, dict):
        nodes.extend(schema_nodes(items))
    return nodes


def test_input_schema_contains_path_and_query_parameters() -> None:
    skill = find_skill(
        lambda candidate: bool(candidate.path_parameters)
        and bool(candidate.query_parameters)
        and not candidate.request_body
    )

    schema = build_input_schema(skill)
    path_schema = schema["properties"]["pathParams"]
    query_schema = schema["properties"]["queryParams"]

    assert schema["required"] == ["pathParams"]
    assert path_schema["required"] == [
        field["name"] for field in skill.path_parameters if field["required"]
    ]
    assert set(path_schema["properties"]) == {field["name"] for field in skill.path_parameters}
    assert set(query_schema["properties"]) == {field["name"] for field in skill.query_parameters}
    assert "body" not in schema["properties"]


def test_input_schema_preserves_discriminator_details() -> None:
    skill = find_skill(
        lambda candidate: any(
            child.get("discriminator")
            for field in candidate.request_body
            for child in field.get("children", [])
        )
    )

    schema = build_input_schema(skill)
    discriminator_nodes = [
        node for node in schema_nodes(schema) if "x-unifi-discriminator" in node
    ]

    assert discriminator_nodes
    assert all(node["x-unifi-discriminator"] for node in discriminator_nodes)
