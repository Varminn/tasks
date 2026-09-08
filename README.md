# AI Gateway Systems Assessment

Four independently runnable Python services that build progressively from a
validated MCP server to secure gateway, streaming PII guardrail, and resilient
LLM router.

| Task | Focus | Key production concern demonstrated |
| --- | --- | --- |
| [Task 1](task-1/README.md) | MCP server | Strict schemas, JSON-RPC errors, and stdio isolation |
| [Task 2](task-2/README.md) | MCP security gateway | Signed role claims and tool-level authorization |
| [Task 3](task-3/README.md) | Streaming LLM gateway | Bounded, chunk-safe PII redaction |
| [Task 4](task-4/README.md) | LLM router | Atomic SQLite rate limits, timeouts, fallback, and error sanitization |

## Validate Locally

Each task owns its dependencies and test suite. Run its setup and tests from
that task directory:

```bash
cd task-1  # or task-2, task-3, task-4
python -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev]"
python -m pytest tests -v
```

GitHub Actions runs the same isolated test flow for every task on pushes and
pull requests.

## Repository Hygiene

Runtime credentials are supplied through environment variables; no provider
keys are committed. Local assessment notes in `.agents/` and local supporting
documents in `docs/` are intentionally excluded from version control.
