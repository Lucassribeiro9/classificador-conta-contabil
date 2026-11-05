"""Worker entrypoints activate and close private process scrapes."""

import importlib

import pytest


@pytest.mark.parametrize("module_name", ["scripts.ml_worker", "scripts.razao_worker"])
def test_worker_main_serves_process_metrics_on_private_interface(module_name, monkeypatch, tmp_path):
    module = importlib.import_module(module_name)
    calls = []

    class FakeServer:
        def shutdown(self):
            calls.append("shutdown")

        def server_close(self):
            calls.append("close")

    class FakeThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            calls.append("start")

        def join(self, timeout=None):
            calls.append("join")

    monkeypatch.setattr(module.settings, "METRICS_NETWORK_PEER", "127.0.0.1")
    monkeypatch.setattr(module.settings, "METRICS_PORT", 9000)
    monkeypatch.setattr(module.settings, "TECHNICAL_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(module, "Thread", FakeThread)
    monkeypatch.setattr(module, "signal", lambda *_args: None)
    monkeypatch.setattr(
        module, "start_private_process_metrics_server",
        lambda peer, port: (calls.append((peer, port)) or FakeServer(), FakeThread()),
    )
    if module_name == "scripts.ml_worker":
        monkeypatch.setattr(module, "MLWorker", lambda *args, **kwargs: object())
    else:
        monkeypatch.setattr(
            module.RazaoStorage, "from_settings", lambda *args, **kwargs: object()
        )
        monkeypatch.setattr(module, "build_workers", lambda *args, **kwargs: [object()])

    module.main()

    assert calls[0] == ("127.0.0.1", 9000)
    assert calls[-3:] == ["shutdown", "close", "join"]
