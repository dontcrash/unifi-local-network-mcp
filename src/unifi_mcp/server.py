from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from unifi_mcp.client import UniFiClient
from unifi_mcp.config import Settings, load_settings
from unifi_mcp.executor import SkillExecutor
from unifi_mcp.schemas import build_input_schema, build_tool_description, compact_description
from unifi_mcp.skills import SkillDefinition, load_skills

LOGGER = logging.getLogger(__name__)


class BearerAuthMiddleware:
    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("latin1")
        if auth_header != f"Bearer {self.token}":
            response = JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def make_tool_function(
    executor: SkillExecutor,
    skill: SkillDefinition,
    *,
    compact: bool,
) -> Callable[..., Awaitable[dict[str, Any]]]:
    async def call_unifi_skill(
        pathParams: dict[str, Any] | None = None,
        queryParams: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await executor.execute(
            skill,
            pathParams=pathParams,
            queryParams=queryParams,
            body=body,
        )

    call_unifi_skill.__name__ = skill.name
    call_unifi_skill.__doc__ = build_tool_description(skill, compact=compact)
    return call_unifi_skill


def build_tools(
    executor: SkillExecutor,
    skills: list[SkillDefinition],
    *,
    compact: bool = True,
) -> list[Tool]:
    tools: list[Tool] = []
    for skill in skills:
        fn = make_tool_function(executor, skill, compact=compact)
        tool = Tool.from_function(
            fn,
            name=skill.name,
            title=skill.title,
            description=build_tool_description(skill, compact=compact),
            structured_output=True,
            meta=None,
        )
        tool.parameters = build_input_schema(skill, compact=compact)
        tools.append(tool)
    return tools


def summarize_field(field: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": field.get("name"),
        "required": bool(field.get("required")),
        "type": field.get("type"),
    }


def summarize_skill(skill: SkillDefinition) -> dict[str, Any]:
    return {
        "name": skill.name,
        "title": skill.title,
        "method": skill.method,
        "description": compact_description(skill.description),
        "pathParams": [summarize_field(field) for field in skill.path_parameters],
        "queryParams": [summarize_field(field) for field in skill.query_parameters],
        "hasBody": bool(skill.request_body),
    }


def skill_schema(skill: SkillDefinition) -> dict[str, Any]:
    return {
        "name": skill.name,
        "title": skill.title,
        "method": skill.method,
        "path": skill.path,
        "description": skill.description,
        "inputSchema": build_input_schema(skill, compact=False),
        "parameters": {
            "path": skill.path_parameters,
            "query": skill.query_parameters,
            "body": skill.request_body,
        },
        "responses": skill.responses,
        "responseSample": skill.response_sample,
        "source": {
            "file": skill.source.file,
            "url": skill.source.url,
        },
    }


def build_server_instructions(skills: list[SkillDefinition]) -> str:
    return (
        "Use these tools to call the configured UniFi Network Integration API. "
        "Read-only mode exposes only GET tools unless READ_ONLY=false. "
        "Dispatcher rules: call unifi_network_list_skills once per session to see "
        "available skills. Before every unifi_network_call_skill, ALWAYS call "
        "unifi_network_get_skill_schema for that skill unless you already have that exact "
        "schema in context. "
        "Most detail calls need IDs; use list/overview skills first, commonly sites before "
        "site-scoped resources. For firewall questions, inspect firewall policies/zones and "
        "related networks/devices/clients as needed to map IDs, networks, and zone membership. "
    )


def build_dispatcher_tools(
    executor: SkillExecutor,
    skills: list[SkillDefinition],
) -> list[Tool]:
    skills_by_name = {skill.name: skill for skill in skills}

    async def list_unifi_network_skills() -> dict[str, Any]:
        """List available UniFi Network skills loaded by this server."""
        items = [summarize_skill(skill) for skill in skills]
        return {"count": len(items), "skills": items}

    async def get_unifi_network_skill_schema(skillName: str) -> dict[str, Any]:
        """Get the exact input schema and parameter details for one UniFi Network skill."""
        skill = skills_by_name.get(skillName)
        if skill is None:
            return {
                "ok": False,
                "error": {
                    "code": "unknown_skill",
                    "message": f"Unknown skill: {skillName}",
                },
            }
        return {"ok": True, "skill": skill_schema(skill)}

    async def call_unifi_network_skill(
        skillName: str,
        pathParams: dict[str, Any] | None = None,
        queryParams: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call one UniFi Network skill by name."""
        skill = skills_by_name.get(skillName)
        if skill is None:
            return {
                "ok": False,
                "status_code": None,
                "data": None,
                "error": {
                    "code": "unknown_skill",
                    "message": f"Unknown skill: {skillName}",
                },
            }
        return await executor.execute(
            skill,
            pathParams=pathParams,
            queryParams=queryParams,
            body=body,
        )

    return [
        Tool.from_function(
            list_unifi_network_skills,
            name="unifi_network_list_skills",
            description=(
                "List every available UniFi Network skill with brief descriptions. "
                "Call this once per session, then use unifi_network_get_skill_schema for "
                "the selected skill before execution."
            ),
            structured_output=True,
            meta=None,
        ),
        Tool.from_function(
            get_unifi_network_skill_schema,
            name="unifi_network_get_skill_schema",
            description=(
                "Get required pathParams, queryParams, body fields, types, enums, and "
                "responses for one UniFi Network skill. ALWAYS call this before "
                "unifi_network_call_skill unless that exact skill schema is already in context."
            ),
            structured_output=True,
            meta=None,
        ),
        Tool.from_function(
            call_unifi_network_skill,
            name="unifi_network_call_skill",
            description=(
                "Call a UniFi Network skill by name with pathParams, queryParams, and body. "
                "Before calling this, ALWAYS call unifi_network_get_skill_schema for the same "
                "skill unless that exact schema is already in context."
            ),
            structured_output=True,
            meta=None,
        ),
    ]


def build_mcp_server(
    settings: Settings,
    *,
    client: UniFiClient | None = None,
) -> FastMCP:
    skills = load_skills(
        settings.skills_dir,
        read_only=settings.read_only,
        allow_connector_proxy=settings.allow_connector_proxy,
    )
    unifi_client = client or UniFiClient(
        base_url=settings.unifi_base_url,
        api_key=settings.unifi_api_key,
        verify=settings.httpx_verify,
        timeout=settings.request_timeout,
    )
    executor = SkillExecutor(settings=settings, client=unifi_client)
    if settings.mcp_tool_mode == "dispatcher":
        tools = build_dispatcher_tools(executor, skills)
    else:
        tools = build_tools(executor, skills, compact=settings.mcp_compact_tools)

    LOGGER.info("Loaded %s UniFi MCP tools", len(tools))
    return FastMCP(
        "UniFi Network",
        instructions=build_server_instructions(skills),
        tools=tools,
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path=settings.mcp_path,
        json_response=True,
        stateless_http=True,
    )


def add_cors_middleware(app: ASGIApp, settings: Settings) -> ASGIApp:
    origins = settings.mcp_cors_allow_origins or []
    if not origins:
        return app
    return CORSMiddleware(
        app,
        allow_origins=origins,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "Last-Event-ID",
            "MCP-Protocol-Version",
            "Mcp-Session-Id",
        ],
        expose_headers=[
            "MCP-Protocol-Version",
            "Mcp-Session-Id",
        ],
    )


def run_streamable_http(mcp: FastMCP, settings: Settings) -> None:
    import anyio
    import uvicorn

    async def serve() -> None:
        app = mcp.streamable_http_app()
        if settings.mcp_auth_token:
            app = BearerAuthMiddleware(app, settings.mcp_auth_token)
        app = add_cors_middleware(app, settings)
        config = uvicorn.Config(
            app,
            host=settings.mcp_host,
            port=settings.mcp_port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()

    anyio.run(serve)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings(os.environ)
    mcp = build_mcp_server(settings)

    if settings.mcp_transport == "streamable-http":
        run_streamable_http(mcp, settings)
        return

    mcp.run(transport=settings.mcp_transport)
