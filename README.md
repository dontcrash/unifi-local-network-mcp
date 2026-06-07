# UniFi Network MCP Server

This project exposes the UniFi Network Integration API as Model Context Protocol
tools. Runtime tools are loaded from JSON manifests in `skills/network`, so adding
or updating endpoints does not require hardcoding every command in Python.

By default the server is read-only: only `GET` endpoints are exposed, and a second
executor guard rejects write methods while `READ_ONLY=true`.

## Quick Start

Generate or refresh runtime skills from the bundled docs:

```bash
python3 scripts/import_unifi_docs.py --source docs/network --output skills/network
```

Run locally:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
UNIFI_BASE_URL='https://172.16.1.1/proxy/network/integration' \
UNIFI_API_KEY='<api-key>' \
python -m unifi_mcp
```

The default Streamable HTTP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

For stdio MCP clients:

```bash
MCP_TRANSPORT=stdio UNIFI_BASE_URL='https://172.16.1.1/proxy/network/integration' \
UNIFI_API_KEY='<api-key>' python -m unifi_mcp
```

## Configuration

Required:

- `UNIFI_BASE_URL`: UniFi Network Integration API base URL, normally
  `https://<console>/proxy/network/integration`. If the value already ends in
  `/v1`, the server avoids adding a second `/v1`.
- `UNIFI_API_KEY`: UniFi API key. Do not commit this value.

Security and runtime:

- `READ_ONLY=true`: default. Exposes only `GET` tools and blocks write execution.
- `READ_ONLY=false`: exposes POST, PUT, PATCH, and DELETE tools.
- `ALLOW_CONNECTOR_PROXY=false`: default. Connector wildcard proxy endpoints are
  disabled because they are less constrained than curated endpoint manifests.
- `UNIFI_VERIFY_TLS=true`: default TLS verification.
- `UNIFI_CA_CERT=/path/to/ca.pem`: trust a self-signed UniFi certificate.
- `UNIFI_INSECURE_SKIP_VERIFY=false`: dev-only equivalent of `curl -k`.
- `MCP_TRANSPORT=streamable-http`: also supports `stdio` and `sse`.
- `MCP_HOST=127.0.0.1`, `MCP_PORT=8000`.
- `MCP_PATH=/mcp`: Streamable HTTP endpoint path. The bundled dev
  `docker-compose.yml` sets this to `/` so browser clients can use
  `http://127.0.0.1:8000` directly.
- `MCP_AUTH_TOKEN`: optional Bearer token for Streamable HTTP.
- `MCP_CORS_ALLOW_ORIGINS`: comma-separated allowed browser origins for
  Streamable HTTP, for example `http://localhost:8080,http://127.0.0.1:8080`.
  The bundled dev `docker-compose.yml` uses `*` for browser clients such as
  llama.cpp.
- `MCP_COMPACT_TOOLS=true`: default. Advertises compact tool descriptions and
  schemas to reduce MCP context size while keeping full skill manifests on disk.
- `MCP_TOOL_MODE=dispatcher`: default. Exposes a small dispatcher tool surface:
  list skills, then call one by name. Set `individual` to advertise every
  endpoint as its own MCP tool.
- `MCP_ALLOW_UNAUTHENTICATED_REMOTE=false`: required to bind HTTP to a non-local
  host without `MCP_AUTH_TOKEN`.

## Docker Compose

```bash
./build.sh
```

`docker-compose.yml` includes the test UniFi controller IP/API key from
`PLAN.md`, keeps `READ_ONLY=true`, and accepts the self-signed UniFi certificate
by default for local development.

The compose file binds the MCP endpoint to localhost:

```text
http://127.0.0.1:8000
```

Inside the container the server binds to `0.0.0.0` so Docker can publish the
port, but compose publishes it only to the host loopback address.

## Tool Inputs

Each MCP tool uses this shape:

```json
{
  "pathParams": { "siteId": "..." },
  "queryParams": { "limit": 25, "offset": 0 },
  "body": {}
}
```

`body` is only accepted for write operations. Tool schemas are generated from the
source docs and preserve path parameters, query parameters, request body fields,
response fields, descriptions, required flags, types, and discriminators.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
```

The importer intentionally ignores guide files without endpoint methods, including
`_index.json`, `gettingstarted.json`, `filtering.json`, `error-handling.json`, and
`quick_start.ansible.json`.
