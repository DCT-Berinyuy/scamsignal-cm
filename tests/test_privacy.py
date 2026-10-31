"""Privacy canary test (PRD §11): submitted text never appears in logs or error responses."""

import logging
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main_module

CANARY = f"CANARY-{uuid.uuid4().hex}"


@pytest.fixture()
def capture_all_logs(caplog):
    caplog.set_level(logging.DEBUG)  # root + every library logger (uvicorn, httpx, fastapi)
    return caplog


def _requests_with_canary(client):
    yield client.post("/check", json={"text": f"send your PIN {CANARY}", "lang": "en", "sender_type": "number"})
    yield client.post("/check", json={"text": CANARY * 100, "lang": "en", "sender_type": "named"})
    yield client.post("/check", json={"text": "hello", "lang": CANARY, "sender_type": "named"})
    yield client.post("/check", json={"text": "hello", "lang": "en", "sender_type": CANARY})
    yield client.post("/check", json={"text": "hello", "lang": "en", "sender_type": "named", CANARY: 1})
    yield client.post(
        "/check", content=f'{{"text": "{CANARY}"'.encode(), headers={"Content-Type": "application/json"}
    )


def test_canary_not_in_logs_or_responses(client, capture_all_logs, capsys) -> None:
    responses = list(_requests_with_canary(client))

    assert [r.status_code for r in responses] == [200, 422, 422, 422, 422, 422]
    for res in responses:
        assert CANARY not in res.text
    out, err = capsys.readouterr()
    assert CANARY not in capture_all_logs.text
    assert CANARY not in out + err


def test_internal_error_does_not_leak_input(capture_all_logs, capsys, monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError(f"failed on {CANARY}")

    monkeypatch.setattr(main_module, "analyze", boom)
    # raise_server_exceptions=True: if the error escaped the app, uvicorn would log its traceback.
    with TestClient(main_module.app, raise_server_exceptions=True) as client:
        res = client.post("/check", json={"text": CANARY, "lang": "en", "sender_type": "named"})

    assert res.status_code == 500
    assert res.json() == {"error": "internal error"}
    out, err = capsys.readouterr()
    assert CANARY not in capture_all_logs.text + out + err


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_canary_not_in_real_server_logs() -> None:
    """End to end with a real uvicorn process, so its access and error logs are covered too."""
    port = _free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "debug"],
        cwd=Path(__file__).resolve().parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                httpx.get(f"{base}/health", timeout=0.5)
                break
            except httpx.TransportError:
                time.sleep(0.1)
        with httpx.Client(base_url=base, timeout=5) as client:
            responses = list(_requests_with_canary(client))
    finally:
        server.terminate()
        logs, _ = server.communicate(timeout=10)

    assert [r.status_code for r in responses] == [200, 422, 422, 422, 422, 422]
    assert "POST /check" in logs  # the server did log requests...
    assert CANARY not in logs  # ...but never their content
    assert all(CANARY not in r.text for r in responses)
