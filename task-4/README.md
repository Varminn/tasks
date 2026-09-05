# Task 4: Rate-Limiting & Model Fallback Router

A resilient model routing module for LLM Gateways with token-aware sliding window rate limiting (SQLite-backed), automatic failover on 429/timeout, and standardized error sanitization.

## Architecture

```
Client ──POST /v1/completions──▶ LLM Router
                                  │
                                  ├─ RateLimiter (SQLite sliding window, 50k tokens/min)
                                  │   ├─ Allowed → proceed
                                  │   └─ Denied → 429 gateway error
                                  ├─ Primary provider (3s timeout)
                                  │   ├─ 200 → return response
                                  │   ├─ 429 / 408 / 503 → failover
                                  │   └─ Other error → failover
                                  └─ Fallback provider
                                      ├─ 200 → return response
                                      └─ Any error → 502 sanitized gateway error
```

## Rate Limiter

Token-aware sliding window per tenant API key, backed by on-disk SQLite. Each request records `tokens` with a timestamp. `check_and_record()` sums tokens within the trailing 60-second window and rejects if the sum exceeds the per-key limit. `evict_expired()` purges entries older than the window.

## Failover

The router tries the primary provider with a 3000ms timeout. On HTTP 429 (rate limited), 408 (timeout), or 503 (unavailable), it immediately retries on the fallback provider. If both fail, it returns a standardized 502 error with no internal details.

## Error Sanitization

All error responses use a standardized shape: `{"error": {"code": N, "message": "...", "type": "gateway_error"}}`. Raw upstream responses, stack traces, and internal URLs are never exposed.

## Setup

```bash
cd task-4
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running

```bash
python -m llm_router.main
```

The router listens on `http://localhost:3003/v1/completions`.

## Testing

```bash
pytest tests/ -v
```
