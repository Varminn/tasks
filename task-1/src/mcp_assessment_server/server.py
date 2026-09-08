from typing import Any, TypeVar

from mcp.server import MCPServer
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.shared.exceptions import MCPError
from mcp_types import INVALID_PARAMS
from pydantic import ValidationError

from mcp_assessment_server.models import (
    CustomerId,
    CustomerRecordRequest,
    RefundAmount,
    RefundReason,
    RefundRequest,
)
from mcp_assessment_server.store import (
    get_customer_record as lookup_customer_record,
    trigger_refund as initiate_refund,
)

RequestModel = TypeVar("RequestModel", bound=CustomerRecordRequest | RefundRequest)


def _validation_error(exc: ValidationError) -> MCPError:
    fields = [".".join(str(part) for part in error["loc"]) for error in exc.errors()]
    return MCPError(
        code=INVALID_PARAMS,
        message="Invalid tool arguments",
        data={"fields": fields},
    )


def _validate_request(model: type[RequestModel], arguments: object) -> RequestModel:
    try:
        return model.model_validate(arguments)
    except ValidationError as exc:
        raise _validation_error(exc) from exc


_TOOL_REQUEST_MODELS: dict[str, type[CustomerRecordRequest] | type[RefundRequest]] = {
    "get_customer_record": CustomerRecordRequest,
    "trigger_refund": RefundRequest,
}


async def validate_tool_arguments(
    ctx: ServerRequestContext[Any, Any],
    call_next: CallNext,
) -> HandlerResult:
    """Reject malformed arguments before the tool handler can run."""
    if ctx.method == "tools/call" and ctx.params is not None:
        tool_name = ctx.params.get("name")
        if isinstance(tool_name, str) and (model := _TOOL_REQUEST_MODELS.get(tool_name)) is not None:
            _validate_request(model, ctx.params.get("arguments"))
    return await call_next(ctx)


mcp = MCPServer("mcp-assessment-server", middleware=[validate_tool_arguments])


@mcp.tool()
def get_customer_record(customer_id: CustomerId) -> dict:
    """Retrieve a customer record by ID.

    Args:
        customer_id: Must match format CUST-XXXXX (e.g. CUST-00001).
    """
    req = _validate_request(CustomerRecordRequest, {"customer_id": customer_id})

    record = lookup_customer_record(req.customer_id)
    if record is None:
        raise LookupError(f"Customer record not found for {req.customer_id}")
    return record


@mcp.tool()
def trigger_refund(
    customer_id: CustomerId,
    amount: RefundAmount,
    reason: RefundReason,
) -> dict:
    """Trigger a refund for a customer.

    Args:
        customer_id: Must match format CUST-XXXXX.
        amount: Must be a positive float.
        reason: Must be at least 10 characters.
    """
    req = _validate_request(
        RefundRequest,
        {"customer_id": customer_id, "amount": amount, "reason": reason},
    )

    return initiate_refund(req.customer_id, req.amount, req.reason)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
