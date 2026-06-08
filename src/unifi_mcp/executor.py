from __future__ import annotations

from typing import Any

from unifi_mcp.client import UniFiClient, error_response
from unifi_mcp.config import Settings
from unifi_mcp.skills import SkillDefinition
from unifi_mcp.validation import ValidationError, validate_arguments


class SkillExecutor:
    def __init__(self, *, settings: Settings, client: UniFiClient) -> None:
        self.settings = settings
        self.client = client

    async def execute(
        self,
        skill: SkillDefinition,
        *,
        pathParams: dict[str, Any] | None = None,
        queryParams: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.settings.read_only and skill.method != "GET":
            return error_response(
                "read_only_violation",
                f"{skill.name} is a {skill.method} operation and READ_ONLY=true.",
            )
        if skill.is_connector_proxy:
            return error_response(
                "connector_proxy_disabled",
                "Connector proxy tools are not exposed by this server.",
            )

        path_params = pathParams or {}
        query_params = queryParams or {}

        try:
            validate_arguments(
                path_params=path_params,
                query_params=query_params,
                body=body,
                path_fields=skill.path_parameters,
                query_fields=skill.query_parameters,
                body_fields=skill.request_body,
            )
        except ValidationError as exc:
            return error_response("validation_error", str(exc))

        try:
            return await self.client.request(
                skill,
                path_params=path_params,
                query_params=query_params,
                body=body,
            )
        except ValueError as exc:
            return error_response("validation_error", str(exc))
