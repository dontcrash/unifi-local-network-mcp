# UniFi Network MCP Server

Model Context Protocol server for the UniFi Network Integration API.

It turns curated UniFi Network endpoints into MCP-callable skills, loaded from
JSON manifests at runtime. The server is read-only by default: `READ_ONLY=true`
exposes only `GET` skills and the executor blocks writes as a second guard.

## Highlights

- Manifest-driven endpoint catalog in `skills/network`
- Read-only default with runtime write protection
- Compact dispatcher tool surface to keep MCP context small
- Docker Compose and stdio support
- Self-signed UniFi certificate support
- Connector wildcard proxy endpoints hidden and blocked

## Quick Start

### Docker Compose

Edit `docker-compose.yml` with your UniFi console URL and API key, then run:

```bash
./build.sh
```

The MCP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

The Compose file publishes only to host loopback:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

Do not change this to `8000:8000` unless you intend to expose the server on all
host interfaces and have added real authentication. The Docker image binds to
`0.0.0.0` inside the container so Docker can forward the published port to the
Python process.

### Local Python

Requires Python 3.12 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

UNIFI_BASE_URL='https://172.16.1.1/proxy/network/integration' \
UNIFI_API_KEY='<api-key>' \
python -m unifi_mcp
```

For stdio clients:

```bash
MCP_TRANSPORT=stdio \
UNIFI_BASE_URL='https://172.16.1.1/proxy/network/integration' \
UNIFI_API_KEY='<api-key>' \
python -m unifi_mcp
```

## MCP Tools

The server intentionally exposes three MCP tools instead of one tool per UniFi
endpoint:

| Tool | Purpose |
| --- | --- |
| `unifi_network_list_skills` | List available UniFi skills with brief descriptions. Omit arguments for the default brief catalog; use `detail=summary` only when path/query names help choose a skill. |
| `unifi_network_get_skill_schema` | Fetch the exact input schema for one selected skill. Response docs and samples are opt-in. |
| `unifi_network_call_skill` | Execute the selected skill with `pathParams`, `queryParams`, and optional `body`. |

This keeps the MCP tool list small while still giving the model exact schemas
before it calls an endpoint.

Skill calls use this shape:

```json
{
  "pathParams": { "siteId": "..." },
  "queryParams": { "limit": 25, "offset": 0 },
  "body": {}
}
```

`body` is accepted only when the selected skill schema includes a request body.
With the default `READ_ONLY=true`, exposed skills are GET-only and do not need a
body.

## Configuration

Only `UNIFI_BASE_URL` and `UNIFI_API_KEY` are required. `READ_ONLY=true` is the
secure default and is shown in Compose as an explicit safety setting.

| Variable | Default | Notes |
| --- | --- | --- |
| `UNIFI_BASE_URL` | required | UniFi Network Integration API base URL, normally `https://<console>/proxy/network/integration`. If it already ends in `/v1`, the client avoids adding another `/v1`. |
| `UNIFI_API_KEY` | required | UniFi API key. Do not commit real keys. |
| `READ_ONLY` | `true` | When true, exposes only `GET` skills and blocks writes. Set `false` to expose curated write endpoints; connector proxy endpoints remain hidden and blocked. |
| `UNIFI_API_KEY_FILE` | unset | Read the API key from a mounted secret file instead of `UNIFI_API_KEY`. |
| `UNIFI_CA_CERT` | unset | Trust a self-signed UniFi certificate. Prefer this over disabling TLS verification. |
| `UNIFI_INSECURE_SKIP_VERIFY` | `false` | TLS verification stays enabled by default. Set `true` only for dev or self-signed testing; `true` is equivalent to `curl -k`. |
| `UNIFI_REQUEST_TIMEOUT` | `30` | UniFi request timeout in seconds. |
| `MCP_TRANSPORT` | `streamable-http` | Use `stdio` for stdio MCP clients. |
| `MCP_HOST` | `127.0.0.1` | HTTP bind host. The Docker image overrides this to `0.0.0.0` inside the container. |
| `MCP_PORT` | `8000` | HTTP bind port. |
| `MCP_PATH` | `/mcp` | Streamable HTTP endpoint path. |
| `MCP_AUTH_TOKEN` | unset | Optional bearer token for Streamable HTTP. For shared or internet-facing deployments, prefer a proper authenticated HTTPS proxy or gateway. |
| `MCP_AUTH_TOKEN_FILE` | unset | Read the bearer token from a mounted secret file instead of `MCP_AUTH_TOKEN`. |
| `MCP_CORS_ALLOW_ORIGINS` | unset | Comma-separated exact browser origins allowed to call the Streamable HTTP endpoint. The local compose file currently allows `https://chat.vlan.au`. |

Do not set both a direct secret env var and its `_FILE` variant. Startup fails on
ambiguous secret configuration.

## Skills

Runtime manifests live in `skills/network` and are generated from `docs/network`:

```bash
python3 scripts/import_unifi_docs.py --source docs/network --output skills/network
```

The importer writes endpoint manifests only. Guide documents such as
`_index.json`, `gettingstarted.json`, `filtering.json`, `error-handling.json`,
and `quick_start.ansible.json` are ignored.

Generated manifests preserve endpoint paths, parameters, request bodies,
responses, descriptions, required flags, types, and discriminators.

Connector wildcard proxy endpoints are generated from upstream docs but are not
exposed at runtime. Add curated endpoint manifests instead of enabling broad
proxy access.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
```
