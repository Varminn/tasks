from pydantic import BaseModel, ConfigDict, field_validator


class JsonRpcErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: int
    message: str


class JsonRpcRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    jsonrpc: str
    method: str
    params: dict | list | None = None
    id: int | str | None = None

    @field_validator("jsonrpc")
    @classmethod
    def validate_jsonrpc_version(cls, value: str) -> str:
        if value != "2.0":
            raise ValueError(f"jsonrpc must be '2.0', got {value!r}")
        return value

    def get_tool_name(self) -> str | None:
        if isinstance(self.params, dict):
            name = self.params.get("name")
            if isinstance(name, str):
                return name
        return None


class JsonRpcResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: object = None
    error: JsonRpcErrorDetail | None = None
