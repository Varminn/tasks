# Task 2: MCP Security Gateway Proxy (Tool Filtering & Auth)

A lightweight HTTP/JSON-RPC reverse proxy in Python that sits between an AI agent client and a downstream MCP server, enforcing role-based tool authorization.

## Architecture

```
AI Agent Client ──HTTP POST /rpc──▶ MCP Gateway ──▶ Downstream MCP Server
                                      │
                                      ├─ Parses Bearer token → extracts role
                                      ├─ tools/list → forward transparently
                                      ├─ tools/call (non-admin tool) → forward
                                      └─ tools/call (admin_* tool + non-admin) → return -32001
```

## Auth Model

Tokens are parsed from the `Authorization: Bearer <token>` header. Supports both JWT (three base64url segments with a `role` claim in the payload) and simple base64-encoded JSON tokens (e.g., `{"role": "admin"}`).

| Role | Regular tools | `admin_*` tools |
|------|--------------|-----------------|
| `admin` | ✅ | ✅ |
| `viewer` | ✅ | ❌ (-32001) |

## Setup

```bash
cd task-2
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running

```bash
python -m mcp_gateway.main http://localhost:3001/rpc
```

The gateway listens on `http://localhost:3000/rpc` and forwards to the downstream URL provided as the first argument.

## Testing

```bash
pytest tests/ -v
```

## Stacking with Task 1

The downstream MCP server from Task 1 can be adapted to expose an HTTP endpoint (using `mcp.run(transport="sse")` or a custom JSON-RPC handler), then pointed to as the gateway's downstream target. The gateway's `McpProxy._forward()` method sends standard JSON-RPC over HTTP POST to the downstream URL.
