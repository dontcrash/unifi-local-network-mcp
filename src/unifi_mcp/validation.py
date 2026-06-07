from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    """Input validation failed before contacting UniFi."""


def _field_names(fields: list[dict[str, Any]]) -> set[str]:
    return {str(field["name"]) for field in fields if field.get("name")}


def _expected_kind(type_name: str | None) -> str:
    lower = (type_name or "any").lower()
    if lower.startswith("array of "):
        return "array"
    if lower.startswith("object"):
        return "object"
    if lower in {"string", "integer", "number", "boolean", "any"}:
        return lower
    return "string"


def _matches_kind(value: Any, kind: str) -> bool:
    if kind == "any":
        return True
    if kind == "array":
        return isinstance(value, list)
    if kind == "object":
        return isinstance(value, dict)
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    return True


def _validate_field(value: Any, field: dict[str, Any], path: str) -> None:
    kind = _expected_kind(field.get("type"))
    if value is None:
        return
    if not _matches_kind(value, kind):
        raise ValidationError(f"{path} must be {kind}, got {type(value).__name__}")

    discriminator = field.get("discriminator") or []
    allowed = [entry.get("value") for entry in discriminator if entry.get("value") is not None]
    if allowed and isinstance(value, str) and value not in allowed:
        raise ValidationError(f"{path} must be one of: {', '.join(map(str, allowed))}")

    children = field.get("children") or []
    if kind == "object" and children and isinstance(value, dict):
        validate_object(value, children, path, strict_unknown=False)
    if kind == "array" and children and isinstance(value, list):
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise ValidationError(f"{path}[{index}] must be object")
            validate_object(item, children, f"{path}[{index}]", strict_unknown=False)


def validate_object(
    values: dict[str, Any],
    fields: list[dict[str, Any]],
    label: str,
    *,
    strict_unknown: bool = True,
) -> None:
    known = _field_names(fields)
    unknown = sorted(set(values) - known)
    if strict_unknown and unknown:
        raise ValidationError(f"{label} contains unsupported fields: {', '.join(unknown)}")

    for field in fields:
        name = field.get("name")
        if not name:
            continue
        child_label = f"{label}.{name}"
        if field.get("required") and name not in values:
            raise ValidationError(f"{child_label} is required")
        if name in values:
            _validate_field(values[name], field, child_label)


def validate_arguments(
    *,
    path_params: dict[str, Any],
    query_params: dict[str, Any],
    body: dict[str, Any] | None,
    path_fields: list[dict[str, Any]],
    query_fields: list[dict[str, Any]],
    body_fields: list[dict[str, Any]],
) -> None:
    validate_object(path_params, path_fields, "pathParams")
    validate_object(query_params, query_fields, "queryParams")

    if body_fields:
        if body is None:
            if any(field.get("required") for field in body_fields):
                raise ValidationError("body is required")
            return
        if not isinstance(body, dict):
            raise ValidationError("body must be object")
        validate_object(body, body_fields, "body")
    elif body is not None:
        raise ValidationError("body is not supported for this operation")
