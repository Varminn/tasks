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
MAX_EMAIL_LOCAL_PART_LENGTH = 64
MAX_EMAIL_LENGTH = 254
EMAIL_CANDIDATE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._%+-@")
EMAIL_DOMAIN_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")


class StreamRedactor:
    """Redacts PII from text chunks without accumulating a full response.

    SSNs and card numbers use a fixed lookahead buffer. Emails use a bounded
    candidate state: potential local parts stay pending until they can be
    classified, while complete or overlong candidates are redacted before any
    of their contents are emitted.
    """

    def __init__(self, redaction_token: str = "[REDACTED]", lookahead: int = MAX_PATTERN_LENGTH) -> None:
        self._token = redaction_token
        self._lookahead = max(lookahead, MAX_PATTERN_LENGTH)
        self._buffer = ""
        self._email_candidate = ""
        self._discarding: str | None = None

    def feed(self, chunk: str) -> str:
        """Feed a new chunk and return text that is safe to emit."""
        safe_parts: list[str] = []

        for char in chunk:
            if self._discarding is not None:
                allowed_chars = (
                    EMAIL_DOMAIN_CHARS if self._discarding == "email" else EMAIL_CANDIDATE_CHARS
                )
                if char in allowed_chars:
                    continue
                self._discarding = None

            if char in EMAIL_CANDIDATE_CHARS:
                self._email_candidate += char
                self._redact_candidate_if_needed(safe_parts)
                continue

            if self._email_candidate:
                safe_parts.append(self._email_candidate)
                self._email_candidate = ""
            safe_parts.append(char)

        return self._buffer_safe_text("".join(safe_parts))

    def flush(self) -> str:
        """Force-emit the remaining safe text at the end of a stream."""
        emitted = ""
        if self._email_candidate:
            emitted = self._buffer_safe_text(self._email_candidate)
            self._email_candidate = ""

        self._discarding = None
        result = emitted + self._buffer
        self._buffer = ""
        return result

    def _redact_candidate_if_needed(self, safe_parts: list[str]) -> None:
        candidate = self._email_candidate
        has_at_sign = "@" in candidate

        if not has_at_sign and len(candidate) > MAX_EMAIL_LOCAL_PART_LENGTH:
            safe_parts.append(self._token)
            self._email_candidate = ""
            self._discarding = "candidate"
        elif has_at_sign and len(candidate) > MAX_EMAIL_LENGTH:
            safe_parts.append(self._token)
            self._email_candidate = ""
            self._discarding = "candidate"
        elif EMAIL_PATTERN.fullmatch(candidate):
            safe_parts.append(self._token)
            self._email_candidate = ""
            self._discarding = "email"

    def _buffer_safe_text(self, text: str) -> str:
        if text:
            self._buffer += text
            for pattern in PII_PATTERNS:
                self._buffer = pattern.sub(self._token, self._buffer)

        if len(self._buffer) <= self._lookahead:
            return ""

        emitted = self._buffer[: -self._lookahead]
        self._buffer = self._buffer[-self._lookahead :]
        return emitted
