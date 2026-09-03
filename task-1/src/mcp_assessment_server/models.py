from pydantic import BaseModel, ConfigDict, field_validator

CUSTOMER_ID_PATTERN = r"^CUST-\d{5}$"


class CustomerRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    customer_id: str

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, value: str) -> str:
        import re

        if not re.match(CUSTOMER_ID_PATTERN, value):
            raise ValueError(
                f"customer_id must match pattern CUST-XXXXX (5 digits), got: {value!r}"
            )
        return value


class RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    customer_id: str
    amount: float
    reason: str

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, value: str) -> str:
        import re

        if not re.match(CUSTOMER_ID_PATTERN, value):
            raise ValueError(
                f"customer_id must match pattern CUST-XXXXX (5 digits), got: {value!r}"
            )
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        import math

        if math.isnan(value) or math.isinf(value):
            raise ValueError("amount must be a finite number")
        if value <= 0:
            raise ValueError("amount must be a positive float")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if len(value.strip()) < 10:
            raise ValueError("reason must be at least 10 characters long")
        return value.strip()
