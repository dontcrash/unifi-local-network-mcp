from __future__ import annotations

from typing import Any

import httpx

from tests.helpers import expected_url, find_skill, sample_values
from unifi_mcp.client import UniFiClient
from unifi_mcp.config import Settings
from unifi_mcp.executor import SkillExecutor


class FailingClient:
    async def request(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("client should not be called")


async def test_executor_calls_unifi_with_rendered_path_and_query() -> None:
    skill = find_skill(
        lambda candidate: candidate.method == "GET"
        and bool(candidate.path_parameters)
        and bool(candidate.query_parameters)
        and not candidate.is_connector_proxy
    )
    path_params = sample_values(skill.path_parameters)
    query_params = sample_values(skill.query_parameters)
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers["X-API-Key"]
        return httpx.Response(200, json={"data": [{"id": "net-1"}]})

    client = UniFiClient(
        base_url="https://unifi.local/proxy/network/integration",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
    )
    executor = SkillExecutor(settings=settings, client=client)

    result = await executor.execute(
        skill,
        pathParams=path_params,
        queryParams=query_params,
    )

    assert result["ok"] is True
    assert captured["url"] == expected_url(
        "https://unifi.local/proxy/network/integration",
        skill.path,
        path_params,
        query_params,
    )
    assert captured["api_key"] == "secret"


async def test_executor_blocks_write_when_read_only() -> None:
    skill = find_skill(
        lambda candidate: candidate.method != "GET" and not candidate.is_connector_proxy
    )
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
        read_only=True,
    )
    executor = SkillExecutor(settings=settings, client=FailingClient())  # type: ignore[arg-type]

    result = await executor.execute(skill, pathParams=sample_values(skill.path_parameters))

    assert result["ok"] is False
    assert result["error"]["code"] == "read_only_violation"


async def test_executor_validates_unknown_query_params_before_http() -> None:
    skill = find_skill(
        lambda candidate: candidate.method == "GET"
        and bool(candidate.path_parameters)
        and bool(candidate.query_parameters)
        and not candidate.is_connector_proxy
    )
    settings = Settings(
        unifi_base_url="https://unifi.local/proxy/network/integration",
        unifi_api_key="secret",
    )
    executor = SkillExecutor(settings=settings, client=FailingClient())  # type: ignore[arg-type]

    result = await executor.execute(
        skill,
        pathParams=sample_values(skill.path_parameters),
        queryParams={"unknown": "value"},
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "validation_error"
    assert "unsupported fields" in result["error"]["message"]
