import re


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")

PII_PATTERNS: list[re.Pattern[str]] = [
    EMAIL_PATTERN,
    SSN_PATTERN,
    CREDIT_CARD_PATTERN,
]

MAX_PATTERN_LENGTH = 40


class StreamRedactor:
    """Redacts PII from a stream of text chunks in real time.

    Applies PII regexes to the full buffer, then emits all but the last
    ``lookahead`` characters. The held-back tail ensures no partial PII
    match leaks across chunk boundaries. Buffer size stays bounded at
    ``lookahead + chunk_size``, keeping memory flat and TTFT low.
    """

    def __init__(self, redaction_token: str = "[REDACTED]", lookahead: int = MAX_PATTERN_LENGTH) -> None:
        self._token = redaction_token
        self._lookahead = max(lookahead, MAX_PATTERN_LENGTH)
        self._buffer = ""

    def feed(self, chunk: str) -> str:
        """Feed a new chunk and return safe-to-emit text."""
        self._buffer += chunk
        for pattern in PII_PATTERNS:
            self._buffer = pattern.sub(self._token, self._buffer)

        if len(self._buffer) <= self._lookahead:
            return ""

        emit = self._buffer[: -self._lookahead]
        self._buffer = self._buffer[-self._lookahead :]
        return emit

    def flush(self) -> str:
        """Force-emit any remaining buffered text (end of stream)."""
        result = self._buffer
        self._buffer = ""
        return result
