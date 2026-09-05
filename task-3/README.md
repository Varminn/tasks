# Task 3: LLM Gateway Streaming PII Redaction

A streaming LLM gateway proxy in Python that intercepts response chunks in real time and redacts PII (emails, SSNs, credit card numbers) before they reach the client.

## How It Works

```
LLM Provider ──stream──▶ StreamRedactor ──safe chunks──▶ Client
                          │
                          ├─ Applies regex patterns to buffered text
                          ├─ Holds back last N chars (lookahead buffer)
                          ├─ N > longest possible PII match length
                          └─ Buffer stays bounded: N + chunk_size
```

The `StreamRedactor` maintains a small lookahead buffer (max 40 chars). On each `feed()` call, PII regexes are applied to the entire buffer, then the first `len(buffer) - 40` characters are emitted as safe. The remaining 40 chars stay pending to handle PII that spans chunk boundaries.

**Memory:** O(lookahead) — never accumulates the full response.
**TTFT:** First safe chunk is emitted as soon as it arrives, with only 40 chars of held-back text.

## Patterns Detected

| Pattern | Regex |
|---------|-------|
| Email | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` |
| SSN | `\b\d{3}-\d{2}-\d{4}\b` |
| Credit Card | `\b(?:\d{4}[ -]?){3}\d{4}\b` |

## Setup

```bash
cd task-3
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running

```bash
python -m llm_gateway.main
```

The gateway listens on `http://localhost:3002/v1/completions` and accepts `POST` requests with `{"prompt": "...", "mock_chunks": [...]}`.

## Testing

```bash
pytest tests/ -v
```
