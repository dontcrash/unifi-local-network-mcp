from __future__ import annotations

from typing import Any

import httpx

from tests.helpers import SKILLS
from unifi_mcp.config import Settings
from unifi_mcp.server import add_cors_middleware, build_mcp_server
from unifi_mcp.skills import load_skills


class FailingClient:
    async def request(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("client should not be called")


async def test_mcp_server_list_catalog_includes_only_default_read_tools() -> None:
    expected = load_skills(SKILLS, read_only=True)
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    _, result = await mcp.call_tool("unifi_network_list_skills", {})
    tool_names = {item["name"] for item in result["skills"]}

    assert tool_names == {skill.name for skill in expected}
    assert all(skill.method == "GET" for skill in expected)


async def test_mcp_server_list_catalog_includes_write_tools_when_enabled() -> None:
    expected = load_skills(SKILLS, read_only=False)
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
        read_only=False,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    _, result = await mcp.call_tool("unifi_network_list_skills", {})
    tool_names = {item["name"] for item in result["skills"]}

    assert tool_names == {skill.name for skill in expected}
    assert any(skill.method != "GET" for skill in expected)
    assert all(not skill.is_connector_proxy for skill in expected)


async def test_mcp_server_uses_configured_streamable_http_path() -> None:
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
        mcp_path="/",
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    assert mcp.settings.streamable_http_path == "/"


async def test_mcp_server_defaults_to_dispatcher_tools() -> None:
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    tool_names = {tool.name for tool in await mcp.list_tools()}

    assert tool_names == {
        "unifi_network_list_skills",
        "unifi_network_get_skill_schema",
        "unifi_network_call_skill",
    }


async def test_server_instructions_use_progressive_discovery_without_skill_catalog() -> None:
    expected = load_skills(SKILLS, read_only=True)
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    assert f"exposes {len(expected)} curated read-only GET operations" in mcp.instructions
    assert "unifi_network_list_skills" in mcp.instructions
    assert "brief catalog" in mcp.instructions
    assert "call unifi_network_get_skill_schema" in mcp.instructions
    assert "unless that exact schema is already in context" in mcp.instructions
    assert "Do not invent UniFi IDs" in mcp.instructions
    assert not any(skill.name in mcp.instructions for skill in expected)


async def test_dispatcher_list_tool_returns_brief_catalog_by_default() -> None:
    expected = load_skills(SKILLS, read_only=True)
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    tools = await mcp.list_tools()
    list_tool = next(tool for tool in tools if tool.name == "unifi_network_list_skills")
    _, result = await mcp.call_tool("unifi_network_list_skills", {})

    assert "detail" in list_tool.inputSchema.get("properties", {})
    assert result["ok"] is True
    assert result["count"] == len(expected)
    assert {item["name"] for item in result["skills"]} == {skill.name for skill in expected}
    assert all("description" in item for item in result["skills"])
    assert all("pathParams" not in item for item in result["skills"])


async def test_dispatcher_list_tool_can_include_parameter_names() -> None:
    expected = load_skills(SKILLS, read_only=True)
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    _, result = await mcp.call_tool(
        "unifi_network_list_skills",
        {"detail": "summary"},
    )

    assert result["ok"] is True
    assert result["count"] == len(expected)
    assert all("path" in item for item in result["skills"])
    assert all("pathParams" in item for item in result["skills"])
    assert all("queryParams" in item for item in result["skills"])


async def test_dispatcher_list_tool_falls_back_to_brief_for_unknown_detail() -> None:
    expected = load_skills(SKILLS, read_only=True)
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    _, result = await mcp.call_tool(
        "unifi_network_list_skills",
        {"detail": "short"},
    )

    assert result["ok"] is True
    assert result["detail"] == "brief"
    assert result["warning"]
    assert result["count"] == len(expected)
    assert all("pathParams" not in item for item in result["skills"])


async def test_dispatcher_schema_tool_returns_full_skill_schema() -> None:
    expected = load_skills(SKILLS, read_only=True)[0]
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    _, result = await mcp.call_tool(
        "unifi_network_get_skill_schema",
        {"skillName": expected.name},
    )

    assert result["ok"] is True
    assert result["skill"]["name"] == expected.name
    assert result["skill"]["inputSchema"]
    assert result["skill"]["parameters"]["path"] == expected.path_parameters
    assert "responses" not in result["skill"]
    assert "responseSample" not in result["skill"]


async def test_dispatcher_schema_tool_can_include_responses_and_sample() -> None:
    expected = load_skills(SKILLS, read_only=True)[0]
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    _, result = await mcp.call_tool(
        "unifi_network_get_skill_schema",
        {
            "skillName": expected.name,
            "includeResponses": True,
            "includeSample": True,
        },
    )

    assert result["ok"] is True
    assert result["skill"]["responses"] == expected.responses
    assert result["skill"]["responseSample"] == expected.response_sample


async def test_dispatcher_tools_have_risk_annotations() -> None:
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        skills_dir=SKILLS,
    )
    mcp = build_mcp_server(settings, client=FailingClient())  # type: ignore[arg-type]

    tools = {tool.name: tool for tool in await mcp.list_tools()}

    assert tools["unifi_network_list_skills"].annotations.readOnlyHint is True
    assert tools["unifi_network_get_skill_schema"].annotations.readOnlyHint is True
    assert tools["unifi_network_call_skill"].annotations.readOnlyHint is True
    assert tools["unifi_network_call_skill"].annotations.destructiveHint is False


async def test_streamable_http_cors_preflight_allows_browser_clients() -> None:
    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        raise AssertionError("CORS preflight should be handled before the MCP app")

    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        mcp_cors_allow_origins=["*"],
    )
    wrapped = add_cors_middleware(app, settings)

    transport = httpx.ASGITransport(app=wrapped)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/mcp",
            headers={
                "Origin": "http://127.0.0.1:8080",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "MCP-Protocol-Version, Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "MCP-Protocol-Version" in response.headers["access-control-allow-headers"]
