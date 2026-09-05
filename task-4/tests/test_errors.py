import pytest

from llm_router.errors import gateway_error


class TestGatewayError:
    def test_standardized_shape(self):
        result = gateway_error(429, "Rate limit exceeded")
        assert result == {"error": {"code": 429, "message": "Rate limit exceeded", "type": "gateway_error"}}

    def test_no_stack_trace_leak(self):
        result = gateway_error(502, "All providers unavailable")
        assert "traceback" not in str(result).lower()
        assert "exception" not in str(result).lower()

    def test_no_internal_details(self):
        result = gateway_error(502, "error")
        assert result["error"]["type"] == "gateway_error"
