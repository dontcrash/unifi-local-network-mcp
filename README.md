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
- `UNIFI_API_KEY_FILE`: optional alternative to `UNIFI_API_KEY`; read the API key
  from a mounted secret file such as `/run/secrets/unifi_api_key`.

Common optional settings:

- `READ_ONLY=true`: default. Exposes only `GET` tools and blocks write execution.
- `READ_ONLY=false`: exposes POST, PUT, PATCH, and DELETE tools.
- `UNIFI_CA_CERT=/path/to/ca.pem`: trust a self-signed UniFi certificate.
- `UNIFI_INSECURE_SKIP_VERIFY=false`: dev-only equivalent of `curl -k`.
- `MCP_TRANSPORT=streamable-http`: also supports `stdio`.

Advanced optional settings:

- `UNIFI_REQUEST_TIMEOUT=30`: UniFi request timeout in seconds.
- `MCP_HOST=127.0.0.1`, `MCP_PORT=8000`, `MCP_PATH=/mcp`.
- `MCP_AUTH_TOKEN`: optional Bearer token for Streamable HTTP. For shared or
  internet-facing deployments, prefer a real MCP-aware auth gateway or proxy.
- `MCP_AUTH_TOKEN_FILE`: optional alternative to `MCP_AUTH_TOKEN`; read the
  bearer token from a mounted secret file.
- `MCP_CORS_ALLOW_ORIGINS`: comma-separated allowed browser origins for
  Streamable HTTP.

Do not set both a direct secret env var and its `_FILE` variant. The server
rejects ambiguous secret configuration at startup.

## Docker Compose

```bash
./build.sh
```

`build.sh` is a local convenience wrapper around Docker Compose. For production,
prefer your deployment system or CI/CD pipeline to build, scan, tag, and publish
the image, then inject runtime configuration through environment variables or
secret files.

The compose file binds the MCP endpoint to localhost:

```text
http://127.0.0.1:8000/mcp
```

The Docker image sets the server's container-internal bind address to
`0.0.0.0` because Docker forwards the published host port to the container
network address, not to the container's own `127.0.0.1` loopback listener.
Compose still publishes the host side only to the host loopback address.
Using plain `8000:8000` would expose the MCP server on every host network
interface. Keep `127.0.0.1:8000:8000` for local development unless you also add
real authentication and intend remote access.

For production Docker deployments, prefer mounted secrets:

```yaml
environment:
  UNIFI_API_KEY_FILE: /run/secrets/unifi_api_key
  MCP_AUTH_TOKEN_FILE: /run/secrets/mcp_auth_token
secrets:
  - unifi_api_key
  - mcp_auth_token
```

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

The default dispatcher mode keeps MCP context small:

- `unifi_network_list_skills`: list every available skill with a brief
  description; `detail=summary` also includes path and parameter names.
- `unifi_network_get_skill_schema`: fetch full input details for one selected
  endpoint; response docs and samples are opt-in.
- `unifi_network_call_skill`: execute the selected endpoint.

The importer intentionally ignores guide files without endpoint methods, including
`_index.json`, `gettingstarted.json`, `filtering.json`, `error-handling.json`, and
`quick_start.ansible.json`.

Connector wildcard proxy endpoints are generated from the upstream docs but are
not exposed at runtime. Add curated endpoint manifests instead of enabling broad
proxy access.
