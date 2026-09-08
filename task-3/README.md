# Task 3: LLM Gateway Streaming PII Redaction

A streaming LLM gateway proxy in Python that intercepts response chunks in real time and redacts PII (emails, SSNs, credit card numbers) before they reach the client.

## How It Works

```
LLM Provider ──stream──▶ StreamRedactor ──safe chunks──▶ Client
                          │
                          ├─ Applies regex patterns to a small lookahead buffer
                          ├─ Holds SSN/card tails for 40 characters
                          ├─ Tracks email-like tails until they are safe or redacted
                          └─ Redacts overlong email candidates before any prefix is emitted
```

The `StreamRedactor` keeps a 40-character lookahead for fixed-length SSNs and credit cards. Emails are handled by a bounded state machine: a possible local part is held for up to 64 characters, and an email candidate for up to 254 characters. A completed or overlong candidate is replaced with `[REDACTED]` before it can be emitted. This prevents a long email split across chunks from leaking an early prefix.

**Memory:** O(lookahead + bounded email candidate) plus the current upstream chunk — never accumulates the full response.
**Streaming:** Safe text is emitted as each upstream chunk is processed; only a small lookahead and a possible trailing email candidate are delayed.

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
pip install ".[dev]"
```

## Running

```bash
python -m llm_gateway.main
```

The gateway listens on `http://localhost:3002/v1/completions` and accepts `POST` requests with `{"prompt": "...", "mock_chunks": [...]}`.

### Real OpenAI-Compatible Provider

Without `mock_chunks`, configure an OpenAI-compatible streaming endpoint through environment variables before starting the gateway:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
export OPENAI_MODEL="gpt-4o-mini"                   # optional
python -m llm_gateway.main
```

Then send a normal completion request:

```bash
curl -N http://localhost:3002/v1/completions \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Summarize this text", "model":"gpt-4o-mini"}'
```

`mock_chunks` explicitly selects the deterministic in-process provider, so tests and local demonstrations do not require credentials or network access. If neither `mock_chunks` nor `OPENAI_API_KEY` is supplied, the gateway returns a sanitized `503` configuration error.

## Testing

```bash
pytest tests/ -v
```
