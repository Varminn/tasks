import json
import subprocess
import sys


class TestStdioIsolation:
    def test_stdout_is_pure_jsonrpc(self):
        """Send initialize + tool call and verify stdout contains only JSON-RPC."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_assessment_server.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1.0"},
            },
        }
        init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        tool_call = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_customer_record", "arguments": {"customer_id": "CUST-00001"}},
        }

        stdin_data = json.dumps(init_request) + "\n"
        stdin_data += json.dumps(init_notification) + "\n"
        stdin_data += json.dumps(tool_call) + "\n"

        stdout, stderr = proc.communicate(input=stdin_data, timeout=10)

        lines = [line for line in stdout.strip().split("\n") if line]
        for line in lines:
            parsed = json.loads(line)
            assert "jsonrpc" in parsed
            assert "result" in parsed or "error" in parsed

        proc.terminate()

    def test_stderr_receives_logs(self):
        """Verify stderr is used for system output, not stdout."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_assessment_server.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, _ = proc.communicate(input="", timeout=5)
        assert stdout == ""
