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
                                  │   ├─ 429 / timeout / 5xx → failover
                                  │   └─ 4xx → sanitized gateway error
                                  └─ Fallback provider
                                      ├─ 200 → return response
                                      └─ Any error → 502 sanitized gateway error
```

## Rate Limiter

Token-aware sliding window per tenant API key, backed by on-disk SQLite. Each request records a positive integer token estimate with a timestamp. `check_and_record()` uses a SQLite `BEGIN IMMEDIATE` transaction to evict expired rows, sum usage, and record an allowed request atomically, so concurrent requests cannot overspend a tenant's quota.

## Failover

The router tries the primary provider with a 3000ms timeout. On HTTP 429 (rate limited), 408 (timeout), or any 5xx response, it immediately retries on the fallback provider. If both fail, it returns a standardized 502 error with no internal details.

## Error Sanitization

All error responses use a standardized shape: `{"error": {"code": N, "message": "...", "type": "gateway_error"}}`. Raw upstream responses, stack traces, and internal URLs are never exposed.

## Setup

```bash
cd task-4
python -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
```

## Running

```bash
export LLM_ROUTER_PRIMARY_BASE_URL='https://your-primary-openai-compatible-endpoint/v1'
export LLM_ROUTER_PRIMARY_API_KEY='your-primary-api-key'
export LLM_ROUTER_FALLBACK_BASE_URL='https://your-fallback-openai-compatible-endpoint/v1'
export LLM_ROUTER_FALLBACK_API_KEY='your-fallback-api-key'
python -m llm_router.main
```

The router listens on `http://localhost:3003/v1/completions`. Provider credentials and endpoints are required environment configuration; they are never hard-coded in the repository.

## Testing

```bash
pytest tests/ -v
```
