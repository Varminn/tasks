ADMIN_TOOL_PREFIX = "admin_"
UNAUTHORIZED_ERROR_CODE = -32001
UNAUTHORIZED_ERROR_MESSAGE = "Unauthorized Tool Call"


def is_tool_authorized(tool_name: str, role: str) -> bool:
    if not tool_name.startswith(ADMIN_TOOL_PREFIX):
        return True
    return role == "admin"
