import pytest

from llm_gateway.redactor import StreamRedactor


class TestStreamRedactor:
    def test_single_chunk_with_email(self):
        r = StreamRedactor()
        r.feed("Contact alice@example.com for help.")
        result = r.flush()
        assert "alice@example.com" not in result
        assert "[REDACTED]" in result

    def test_single_chunk_with_ssn(self):
        r = StreamRedactor()
        r.feed("SSN: 123-45-6789 done")
        result = r.flush()
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result

    def test_single_chunk_with_credit_card(self):
        r = StreamRedactor()
        r.feed("Card: 4111 1111 1111 1111 ok")
        result = r.flush()
        assert "4111" not in result
        assert "[REDACTED]" in result

    def test_clean_text_passes_through(self):
        r = StreamRedactor()
        result = r.feed("Hello world, no sensitive data here. ")
        result += r.flush()
        assert result == "Hello world, no sensitive data here. "

    def test_cross_chunk_email(self):
        r = StreamRedactor()
        out1 = r.feed("Email: alice@ex")
        out2 = r.feed("ample.com!")
        out3 = r.flush()
        full = out1 + out2 + out3
        assert "alice@example.com" not in full
        assert "[REDACTED]" in full

    def test_cross_chunk_ssn(self):
        r = StreamRedactor()
        out1 = r.feed("SSN is 123-45-")
        out2 = r.feed("6789 end")
        out3 = r.flush()
        full = out1 + out2 + out3
        assert "123-45-6789" not in full
        assert "[REDACTED]" in full

    def test_cross_chunk_credit_card(self):
        r = StreamRedactor()
        out1 = r.feed("Card: 4111 1111 ")
        out2 = r.feed("1111 1111 ")
        out3 = r.flush()
        full = out1 + out2 + out3
        assert "4111" not in full
        assert "[REDACTED]" in full

    def test_memory_efficient_small_buffer(self):
        r = StreamRedactor()
        long_text = "This is a long sentence with no PII. " * 100
        output = r.feed(long_text)
        assert len(r._buffer) <= 40

    def test_no_full_response_accumulation(self):
        r = StreamRedactor()
        outputs = []
        for chunk in ["chunk one ", "chunk two ", "chunk three ", "chunk four "]:
            out = r.feed(chunk)
            if out:
                outputs.append(out)
        outputs.append(r.flush())
        full = "".join(outputs)
        assert full == "chunk one chunk two chunk three chunk four "

    def test_flush_with_empty_pending(self):
        r = StreamRedactor()
        assert r.flush() == ""
        assert r.flush() == ""

    def test_multiple_pii_in_one_chunk(self):
        r = StreamRedactor()
        r.feed("Email bob@test.com and SSN 987-65-4321 and card 5555 4444 3333 2222")
        result = r.flush()
        assert "bob@test.com" not in result
        assert "987-65-4321" not in result
        assert "5555" not in result
        assert result.count("[REDACTED]") >= 2

    def test_partial_digits_at_boundary_not_leaked(self):
        r = StreamRedactor()
        out1 = r.feed("The value is 42")
        out2 = r.feed("0 dollars")
        out3 = r.flush()
        full = out1 + out2 + out3
        assert full == "The value is 420 dollars"

    def test_email_dot_at_chunk_boundary(self):
        r = StreamRedactor()
        out1 = r.feed("Contact user@example.")
        out2 = r.feed("com for info")
        out3 = r.flush()
        full = out1 + out2 + out3
        assert "user@example.com" not in full
        assert "[REDACTED]" in full
