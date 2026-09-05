import pytest

from mcp_gateway.authz import is_tool_authorized


class TestToolAuthorization:
    def test_admin_tool_with_admin_role(self):
        assert is_tool_authorized("admin_reset_key", "admin") is True

    def test_admin_tool_with_viewer_role(self):
        assert is_tool_authorized("admin_reset_key", "viewer") is False

    def test_admin_tool_with_unknown_role(self):
        assert is_tool_authorized("admin_reset_key", "operator") is False

    def test_regular_tool_with_viewer_role(self):
        assert is_tool_authorized("get_customer_record", "viewer") is True

    def test_regular_tool_with_admin_role(self):
        assert is_tool_authorized("get_customer_record", "admin") is True

    def test_exact_prefix_match(self):
        assert is_tool_authorized("admin_", "viewer") is False
