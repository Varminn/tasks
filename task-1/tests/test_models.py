import pytest
from pydantic import ValidationError

from mcp_assessment_server.models import CustomerRecordRequest, RefundRequest


class TestCustomerRecordRequest:
    def test_valid_customer_id(self):
        req = CustomerRecordRequest(customer_id="CUST-00001")
        assert req.customer_id == "CUST-00001"

    def test_missing_prefix(self):
        with pytest.raises(ValidationError, match="CUST"):
            CustomerRecordRequest(customer_id="00001")

    def test_wrong_digit_count(self):
        with pytest.raises(ValidationError, match="CUST"):
            CustomerRecordRequest(customer_id="CUST-123")

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError, match="extra"):
            CustomerRecordRequest(customer_id="CUST-00001", extra_field="nope")

    def test_non_string_type(self):
        with pytest.raises(ValidationError):
            CustomerRecordRequest(customer_id=12345)

    def test_lowercase_rejected(self):
        with pytest.raises(ValidationError, match="CUST"):
            CustomerRecordRequest(customer_id="cust-00001")


class TestRefundRequest:
    def test_valid_request(self):
        req = RefundRequest(customer_id="CUST-00001", amount=50.0, reason="Product returned unused")
        assert req.amount == 50.0

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError, match="positive"):
            RefundRequest(customer_id="CUST-00001", amount=0.0, reason="Product returned unused")

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError, match="positive"):
            RefundRequest(customer_id="CUST-00001", amount=-10.0, reason="Product returned unused")

    def test_nan_amount_rejected(self):
        with pytest.raises(ValidationError, match="finite"):
            RefundRequest(customer_id="CUST-00001", amount=float("nan"), reason="Product returned unused")

    def test_inf_amount_rejected(self):
        with pytest.raises(ValidationError, match="finite"):
            RefundRequest(customer_id="CUST-00001", amount=float("inf"), reason="Product returned unused")

    def test_reason_too_short(self):
        with pytest.raises(ValidationError, match="10 characters"):
            RefundRequest(customer_id="CUST-00001", amount=50.0, reason="short")

    def test_reason_whitespace_only(self):
        with pytest.raises(ValidationError, match="10 characters"):
            RefundRequest(customer_id="CUST-00001", amount=50.0, reason="          ")

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError, match="extra"):
            RefundRequest(customer_id="CUST-00001", amount=50.0, reason="Product returned unused", extra=1)
