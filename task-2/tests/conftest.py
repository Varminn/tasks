import base64
import json
import threading

import pytest
from http.server import HTTPServer, BaseHTTPRequestHandler


class MockDownstreamHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(content_length))

        if body.get("method") == "tools/list":
            result = {"tools": [{"name": "get_customer_record"}, {"name": "admin_reset_key"}]}
        elif body.get("method") == "tools/call":
            tool_name = body.get("params", {}).get("name", "")
            if tool_name == "admin_reset_key":
                result = {"status": "key_reset"}
            elif tool_name == "get_customer_record":
                result = {"customer_id": "CUST-00001", "name": "Alice Chen"}
            else:
                result = {"error": "unknown tool"}
        else:
            result = {"error": "unknown method"}

        response = {"jsonrpc": "2.0", "id": body.get("id"), "result": result}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def downstream_server():
    server = HTTPServer(("127.0.0.1", 0), MockDownstreamHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/rpc"
    server.shutdown()
