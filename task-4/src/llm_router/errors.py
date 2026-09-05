

def gateway_error(code: int, message: str) -> dict:
    return {"error": {"code": code, "message": message, "type": "gateway_error"}}
