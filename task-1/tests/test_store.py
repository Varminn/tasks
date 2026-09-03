import pytest

from mcp_assessment_server.store import get_customer_record, trigger_refund


def test_get_existing_customer():
    record = get_customer_record("CUST-00001")
    assert record is not None
    assert record["name"] == "Alice Chen"


def test_get_nonexistent_customer():
    assert get_customer_record("CUST-99999") is None


def test_trigger_refund_success():
    result = trigger_refund("CUST-00001", 25.0, "Defective product returned")
    assert result["status"] == "refund_initiated"


def test_trigger_refund_nonexistent_customer():
    with pytest.raises(LookupError, match="not found"):
        trigger_refund("CUST-99999", 25.0, "Defective product returned")
