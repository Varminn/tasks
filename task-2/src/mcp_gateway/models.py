from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, field_validator

JsonRpcId = StrictInt | StrictStr | None


class JsonRpcErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    code: int
    message: str


class JsonRpcRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    jsonrpc: Literal["2.0"]
    method: StrictStr
    params: dict | list | None = None
    id: JsonRpcId = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        if not value:
            raise ValueError("method must not be empty")
        return value

    def get_tool_name(self) -> str | None:
        if isinstance(self.params, dict):
            name = self.params.get("name")
            if isinstance(name, str):
                return name
        return None


class JsonRpcResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    jsonrpc: str = "2.0"
    id: JsonRpcId = None
    result: object = None
    error: JsonRpcErrorDetail | None = None


def jsonrpc_error(request_id: JsonRpcId, code: int, message: str) -> dict:
    return JsonRpcResponse(
        id=request_id,
        error=JsonRpcErrorDetail(code=code, message=message),
    ).model_dump(exclude={"result"})
