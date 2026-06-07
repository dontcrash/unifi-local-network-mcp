from __future__ import annotations

from typing import Any

from unifi_mcp.skills import SkillDefinition


def _schema_type(type_name: str | None) -> dict[str, Any]:
    normalized = (type_name or "any").strip()
    lower = normalized.lower()

    if lower.startswith("array of "):
        item_type = normalized[len("Array of ") :]
        if item_type.lower().startswith("object"):
            return {"type": "array", "items": {"type": "object"}}
        return {"type": "array", "items": _schema_type(item_type)}
    if lower.startswith("object"):
        return {"type": "object"}
    if lower == "integer":
        return {"type": "integer"}
    if lower == "number":
        return {"type": "number"}
    if lower == "boolean":
        return {"type": "boolean"}
    if lower == "string":
        return {"type": "string"}
    if lower == "any":
        return {}
    return {"type": "string"}


def field_to_json_schema(field: dict[str, Any], *, compact: bool = False) -> dict[str, Any]:
    schema = _schema_type(field.get("type"))
    description = field.get("description")
    children = field.get("children") or []
    discriminator = field.get("discriminator")

    if description and not compact:
        schema["description"] = description
    if field.get("type") and not compact:
        schema["x-unifi-type"] = field["type"]

    if discriminator:
        values = [entry.get("value") for entry in discriminator if entry.get("value") is not None]
        if values and schema.get("type") == "string":
            schema["enum"] = values
        if not compact:
            schema["x-unifi-discriminator"] = discriminator

    if schema.get("type") == "object" and children:
        child_properties: dict[str, Any] = {}
        child_required: list[str] = []
        for child in children:
            name = child.get("name")
            if not name:
                continue
            child_properties[str(name)] = field_to_json_schema(child, compact=compact)
            if child.get("required"):
                child_required.append(str(name))
        schema["properties"] = child_properties
        schema["additionalProperties"] = True
        if child_required:
            schema["required"] = child_required

    if schema.get("type") == "array" and children:
        item_properties: dict[str, Any] = {}
        item_required: list[str] = []
        for child in children:
            name = child.get("name")
            if not name:
                continue
            item_properties[str(name)] = field_to_json_schema(child, compact=compact)
            if child.get("required"):
                item_required.append(str(name))
        schema["items"] = {
            "type": "object",
            "properties": item_properties,
            "additionalProperties": True,
        }
        if item_required:
            schema["items"]["required"] = item_required

    return schema


def fields_to_object_schema(
    fields: list[dict[str, Any]],
    *,
    compact: bool = False,
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in fields:
        name = field.get("name")
        if not name:
            continue
        properties[str(name)] = field_to_json_schema(field, compact=compact)
        if field.get("required"):
            required.append(str(name))

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def build_input_schema(skill: SkillDefinition, *, compact: bool = False) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    if skill.path_parameters:
        properties["pathParams"] = fields_to_object_schema(
            skill.path_parameters,
            compact=compact,
        )
        if any(field.get("required") for field in skill.path_parameters):
            required.append("pathParams")

    if skill.query_parameters:
        properties["queryParams"] = fields_to_object_schema(
            skill.query_parameters,
            compact=compact,
        )

    if skill.request_body:
        properties["body"] = fields_to_object_schema(skill.request_body, compact=compact)
        if any(field.get("required") for field in skill.request_body):
            required.append("body")

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def compact_description(description: str, *, max_length: int = 180) -> str:
    compacted = " ".join(description.split())
    if not compacted:
        return ""
    first_sentence = compacted.split(". ", 1)[0].strip()
    if first_sentence and len(first_sentence) <= max_length:
        return first_sentence.rstrip(".") + "."
    if len(compacted) <= max_length:
        return compacted
    return compacted[: max_length - 1].rstrip() + "."


def build_tool_description(skill: SkillDefinition, *, compact: bool = False) -> str:
    if compact:
        return compact_description(skill.description) or skill.title

    parts = [
        skill.description.strip(),
        "",
        f"Method: {skill.method}",
        f"Path: {skill.path}",
    ]
    if skill.source.url:
        parts.append(f"Source: {skill.source.url}")
    if skill.is_write:
        parts.append("Write operation: hidden and blocked while READ_ONLY=true.")
    return "\n".join(part for part in parts if part is not None)
