from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def parse_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    parsed = float(value)
    if parsed <= 0:
        raise ValueError("Timeout values must be greater than zero")
    return parsed


def parse_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    parsed = int(value)
    if parsed <= 0 or parsed > 65535:
        raise ValueError("Port values must be between 1 and 65535")
    return parsed


def parse_csv(value: str | None) -> list[str]:
    if value is None or value.strip() == "":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def read_secret(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    file_value = env.get(f"{name}_FILE")
    has_value = value is not None and value.strip() != ""
    has_file = file_value is not None and file_value.strip() != ""

    if has_value and has_file:
        raise ValueError(f"Set either {name} or {name}_FILE, not both")
    if not has_file:
        return value.strip() if has_value and value is not None else None

    path = Path(str(file_value)).expanduser()
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"{name}_FILE could not be read: {path}") from exc


@dataclass(frozen=True)
class Settings:
    unifi_base_url: str
    unifi_api_key: str
    read_only: bool = True
    verify_tls: bool = True
    ca_cert: Path | None = None
    insecure_skip_verify: bool = False
    request_timeout: float = 30.0
    allow_connector_proxy: bool = False
    skills_dir: Path = Path("skills/network")
    mcp_transport: str = "streamable-http"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    mcp_path: str = "/mcp"
    mcp_auth_token: str | None = None
    mcp_cors_allow_origins: list[str] | None = None
    mcp_compact_tools: bool = True
    mcp_tool_mode: str = "dispatcher"
    allow_unauthenticated_remote: bool = False

    @property
    def httpx_verify(self) -> bool | str:
        if self.insecure_skip_verify:
            return False
        if self.ca_cert is not None:
            return str(self.ca_cert)
        return self.verify_tls

    def validate(self) -> None:
        if not self.unifi_base_url:
            raise ValueError("UNIFI_BASE_URL is required")
        split_base_url = urlsplit(self.unifi_base_url)
        if split_base_url.scheme not in {"http", "https"} or not split_base_url.netloc:
            raise ValueError("UNIFI_BASE_URL must be an absolute http(s) URL")
        if split_base_url.query or split_base_url.fragment:
            raise ValueError("UNIFI_BASE_URL must not include a query string or fragment")
        if not self.unifi_api_key:
            raise ValueError("UNIFI_API_KEY is required")
        if self.mcp_transport not in {"stdio", "sse", "streamable-http"}:
            raise ValueError("MCP_TRANSPORT must be one of: stdio, sse, streamable-http")
        if self.mcp_tool_mode not in {"dispatcher", "individual"}:
            raise ValueError("MCP_TOOL_MODE must be one of: dispatcher, individual")
        if not self.mcp_path.startswith("/"):
            raise ValueError("MCP_PATH must start with /")
        if self.mcp_auth_token and self.mcp_transport != "streamable-http":
            raise ValueError("MCP_AUTH_TOKEN is only supported with MCP_TRANSPORT=streamable-http")
        if self.ca_cert is not None and not self.ca_cert.exists():
            raise ValueError(f"UNIFI_CA_CERT does not exist: {self.ca_cert}")
        if (
            self.mcp_transport != "stdio"
            and self.mcp_host not in LOCAL_HOSTS
            and not self.mcp_auth_token
            and not self.allow_unauthenticated_remote
        ):
            raise ValueError(
                "Refusing to bind an unauthenticated MCP HTTP server to a non-local host. "
                "Set MCP_AUTH_TOKEN or MCP_ALLOW_UNAUTHENTICATED_REMOTE=true."
            )


def load_settings(env: Mapping[str, str]) -> Settings:
    ca_cert = env.get("UNIFI_CA_CERT")
    unifi_api_key = read_secret(env, "UNIFI_API_KEY") or ""
    mcp_auth_token = read_secret(env, "MCP_AUTH_TOKEN")
    settings = Settings(
        unifi_base_url=env.get("UNIFI_BASE_URL", "").strip(),
        unifi_api_key=unifi_api_key,
        read_only=parse_bool(env.get("READ_ONLY"), True),
        verify_tls=parse_bool(env.get("UNIFI_VERIFY_TLS"), True),
        ca_cert=Path(ca_cert).expanduser() if ca_cert else None,
        insecure_skip_verify=parse_bool(env.get("UNIFI_INSECURE_SKIP_VERIFY"), False),
        request_timeout=parse_float(env.get("UNIFI_REQUEST_TIMEOUT"), 30.0),
        allow_connector_proxy=parse_bool(env.get("ALLOW_CONNECTOR_PROXY"), False),
        skills_dir=Path(env.get("SKILLS_DIR", "skills/network")),
        mcp_transport=env.get("MCP_TRANSPORT", "streamable-http").strip(),
        mcp_host=env.get("MCP_HOST", "127.0.0.1").strip(),
        mcp_port=parse_int(env.get("MCP_PORT"), 8000),
        mcp_path=env.get("MCP_PATH", "/mcp").strip() or "/",
        mcp_auth_token=mcp_auth_token or None,
        mcp_cors_allow_origins=parse_csv(env.get("MCP_CORS_ALLOW_ORIGINS")),
        mcp_compact_tools=parse_bool(env.get("MCP_COMPACT_TOOLS"), True),
        mcp_tool_mode=env.get("MCP_TOOL_MODE", "dispatcher").strip(),
        allow_unauthenticated_remote=parse_bool(
            env.get("MCP_ALLOW_UNAUTHENTICATED_REMOTE"), False
        ),
    )
    settings.validate()
    return settings
