import sys

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from mcp_assessment_server.models import CustomerRecordRequest, RefundRequest
from mcp_assessment_server.store import get_customer_record, trigger_refund

mcp = FastMCP("mcp-assessment-server")


@mcp.tool()
def get_customer_record(customer_id: str) -> dict:
    """Retrieve a customer record by ID.

    Args:
        customer_id: Must match format CUST-XXXXX (e.g. CUST-00001).
    """
    try:
        req = CustomerRecordRequest(customer_id=customer_id)
    except ValidationError as exc:
        raise ValueError(_format_validation_error(exc)) from exc

    record = get_customer_record(req.customer_id)
    if record is None:
        raise LookupError(f"Customer record not found for {req.customer_id}")
    return record


@mcp.tool()
def trigger_refund(customer_id: str, amount: float, reason: str) -> dict:
    """Trigger a refund for a customer.

    Args:
        customer_id: Must match format CUST-XXXXX.
        amount: Must be a positive float.
        reason: Must be at least 10 characters.
    """
    try:
        req = RefundRequest(customer_id=customer_id, amount=amount, reason=reason)
    except ValidationError as exc:
        raise ValueError(_format_validation_error(exc)) from exc

    return trigger_refund(req.customer_id, req.amount, req.reason)


def _format_validation_error(exc: ValidationError) -> str:
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append(f"{field}: {error['msg']}")
    return "; ".join(errors)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
