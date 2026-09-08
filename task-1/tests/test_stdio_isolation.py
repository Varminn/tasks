import json
import os
import select
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_server(*messages: dict) -> tuple[list[dict], str]:
    environment = os.environ.copy()
    source_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{source_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else source_path
    )

    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_assessment_server.server"],
        cwd=PROJECT_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    responses: list[dict] = []
    try:
        for message in messages:
            assert proc.stdin is not None
            proc.stdin.write(f"{json.dumps(message)}\n")
            proc.stdin.flush()

            if "id" not in message:
                continue

            assert proc.stdout is not None
            ready, _, _ = select.select([proc.stdout], [], [], 10)
            assert ready, "server did not emit a JSON-RPC response"
            line = proc.stdout.readline()
            assert line, "server closed stdout before responding"
            responses.append(json.loads(line))

        proc.stdin.close()
        assert proc.wait(timeout=10) == 0
        assert proc.stdout is not None
        for line in proc.stdout:
            if line:
                responses.append(json.loads(line))
        assert proc.stderr is not None
        stderr = proc.stderr.read()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

    assert "Traceback" not in stderr
    assert responses, "server did not emit any JSON-RPC response"
    for response in responses:
        assert response["jsonrpc"] == "2.0"
        assert "result" in response or "error" in response
    return responses, stderr


class TestStdioIsolation:
    def test_stdout_is_pure_jsonrpc(self):
        """Send initialize + tool call and verify stdout contains only JSON-RPC."""
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

        responses, _ = _run_server(init_request, init_notification, tool_call)
        responses_by_id = {response.get("id"): response for response in responses}

        assert responses_by_id[1]["result"]["serverInfo"]["name"] == "mcp-assessment-server"
        tool_result = responses_by_id[2]["result"]
        assert tool_result["isError"] is False
        assert "Alice Chen" in tool_result["content"][0]["text"]

    def test_invalid_tool_arguments_return_standard_jsonrpc_error(self):
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
        invalid_tool_call = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "trigger_refund",
                "arguments": {
                    "customer_id": "CUST-00001",
                    "amount": "25.0",
                    "reason": "Defective product returned",
                },
            },
        }

        responses, _ = _run_server(init_request, init_notification, invalid_tool_call)
        responses_by_id = {response.get("id"): response for response in responses}

        assert responses_by_id[2]["error"]["code"] == -32602
        assert responses_by_id[2]["error"]["message"] == "Invalid tool arguments"
        assert responses_by_id[2]["error"]["data"]["fields"] == ["amount"]

    def test_empty_input_does_not_write_stdout(self):
        environment = os.environ.copy()
        source_path = str(PROJECT_ROOT / "src")
        existing_pythonpath = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            f"{source_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else source_path
        )
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_assessment_server.server"],
            cwd=PROJECT_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        stdout, stderr = proc.communicate(input="", timeout=5)
        assert proc.returncode == 0, stderr
        assert "Traceback" not in stderr
        assert stdout == ""
