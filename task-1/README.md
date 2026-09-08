# Task 1: Custom MCP Server with Strict Validation & Transport Handling

A Python MCP server using the official `mcp` SDK v2 (`MCPServer`) with Pydantic v2 validation, stdio transport, and strict stdout isolation.

## Tools

| Tool | Input | Validation |
|------|-------|-----------|
| `get_customer_record` | `customer_id: string` | Pattern: `CUST-XXXXX` (5 digits) |
| `trigger_refund` | `customer_id`, `amount`, `reason` | customer_id pattern, amount > 0 (finite), reason ≥ 10 chars |

## Setup

```bash
cd task-1
python -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
```

## Running

```bash
python -m mcp_assessment_server.server
```

The server communicates over stdio. stdout carries JSON-RPC only; all system output goes to stderr.

## Testing

```bash
pytest tests/ -v
```

## Architecture

This server is designed as the downstream target for Task 2's MCP Gateway. It exposes two tools with strict Pydantic validation (`extra="forbid"`, strict field schemas, and custom validators). MCP v2 middleware validates `tools/call` arguments before dispatch and returns invalid arguments as the standard JSON-RPC `-32602` error; stdout remains reserved for JSON-RPC messages.
