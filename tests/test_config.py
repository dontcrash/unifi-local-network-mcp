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


def test_load_settings_reads_api_key_from_file(tmp_path) -> None:
    secret_file = tmp_path / "unifi_api_key"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    env = {
        "UNIFI_BASE_URL": "https://unifi.local/proxy/network/integration",
        "UNIFI_API_KEY_FILE": str(secret_file),
    }

    settings = load_settings(env)

    assert settings.unifi_api_key == "file-secret"


def test_load_settings_rejects_duplicate_api_key_sources(tmp_path) -> None:
    secret_file = tmp_path / "unifi_api_key"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    env = base_env()
    env["UNIFI_API_KEY_FILE"] = str(secret_file)

    with pytest.raises(ValueError, match="UNIFI_API_KEY"):
        load_settings(env)


def test_load_settings_rejects_invalid_base_url() -> None:
    env = base_env()
    env["UNIFI_BASE_URL"] = "unifi.local/proxy/network/integration"

    with pytest.raises(ValueError, match="absolute http"):
        load_settings(env)


def test_load_settings_rejects_out_of_range_port() -> None:
    env = base_env()
    env["MCP_PORT"] = "70000"

    with pytest.raises(ValueError, match="between 1 and 65535"):
        load_settings(env)
