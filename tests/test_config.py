from __future__ import annotations

import pytest

from unifi_mcp.config import load_settings


def base_env() -> dict[str, str]:
    return {
        "UNIFI_BASE_URL": "https://unifi.local/proxy/network/integration",
        "UNIFI_API_KEY": "secret",
    }


def test_load_settings_supports_root_mcp_path() -> None:
    env = base_env()
    env["MCP_PATH"] = "/"

    settings = load_settings(env)

    assert settings.mcp_path == "/"


def test_load_settings_defaults_to_compact_tools() -> None:
    settings = load_settings(base_env())

    assert settings.mcp_compact_tools is True
    assert settings.mcp_tool_mode == "dispatcher"


def test_load_settings_rejects_unknown_tool_mode() -> None:
    env = base_env()
    env["MCP_TOOL_MODE"] = "unknown"

    with pytest.raises(ValueError, match="MCP_TOOL_MODE"):
        load_settings(env)


def test_load_settings_rejects_relative_mcp_path() -> None:
    env = base_env()
    env["MCP_PATH"] = "mcp"

    with pytest.raises(ValueError, match="MCP_PATH"):
        load_settings(env)
