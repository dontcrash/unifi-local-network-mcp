from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from unifi_mcp.skills import SkillDefinition


class UniFiClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        verify: bool | str = True,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.verify = verify
        self.timeout = timeout
        self.transport = transport

    def build_url(self, skill: SkillDefinition, path_params: dict[str, Any]) -> str:
        rendered_path = render_path(skill.path, path_params)
        path = rendered_path
        base = self.base_url
        if urlsplit(base).path.rstrip("/").endswith("/v1") and rendered_path.startswith("/v1/"):
            path = rendered_path[len("/v1") :]
        return join_url(base, path)

    async def request(
        self,
        skill: SkillDefinition,
        *,
        path_params: dict[str, Any],
        query_params: dict[str, Any],
        body: dict[str, Any] | None,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "X-API-Key": self.api_key,
        }
        url = self.build_url(skill, path_params)
        request_kwargs: dict[str, Any] = {
            "method": skill.method,
            "url": url,
            "headers": headers,
            "params": clean_query(query_params),
        }
        if body is not None:
            request_kwargs["json"] = body

        try:
            async with httpx.AsyncClient(
                verify=self.verify,
                timeout=self.timeout,
                transport=self.transport,
                follow_redirects=True,
            ) as client:
                response = await client.request(**request_kwargs)
        except httpx.TimeoutException as exc:
            return error_response("timeout", str(exc))
        except httpx.TransportError as exc:
            return error_response("transport_error", str(exc))

        payload = decode_response(response)
        if response.is_success:
            return {"ok": True, "status_code": response.status_code, "data": payload, "error": None}
        return {
            "ok": False,
            "status_code": response.status_code,
            "data": None,
            "error": payload,
        }


def error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status_code": None,
        "data": None,
        "error": {"code": code, "message": message},
    }


def join_url(base_url: str, path: str) -> str:
    split = urlsplit(base_url)
    base_path = split.path.rstrip("/")
    suffix = "/" + path.lstrip("/")
    joined_path = f"{base_path}{suffix}"
    return urlunsplit((split.scheme, split.netloc, joined_path, split.query, split.fragment))


def render_path(path_template: str, path_params: dict[str, Any]) -> str:
    path = path_template
    for name, value in path_params.items():
        replacement = quote(str(value), safe="/" if f"*{name}" in path_template else "")
        path = path.replace("{" + name + "}", replacement)
        path = path.replace("*" + name, replacement)

    if "{" in path or "}" in path or "*" in path:
        missing = path_template
        raise ValueError(f"Missing path parameters for {missing}")
    return path


def clean_query(query_params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in query_params.items() if value is not None}


def decode_response(response: httpx.Response) -> Any:
    if not response.content:
        return None

    content_type = response.headers.get("content-type", "")
    try:
        return response.json()
    except json.JSONDecodeError:
        if "json" in content_type.lower():
            return {"raw": response.text}
        return response.text
