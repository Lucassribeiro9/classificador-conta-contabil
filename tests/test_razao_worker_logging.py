from scripts import razao_worker


def test_worker_main_configures_its_separate_technical_log(monkeypatch, tmp_path):
    configured = {}

    def configure(*, service, log_dir):
        configured.update(service=service, log_dir=log_dir)

    monkeypatch.setattr(razao_worker, "configure_technical_logging", configure)
    monkeypatch.setattr(razao_worker, "signal", lambda *_args: None)
    monkeypatch.setattr(
        razao_worker.RazaoStorage,
        "from_settings",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(razao_worker, "build_workers", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(razao_worker.settings, "TECHNICAL_LOG_DIR", str(tmp_path))

    razao_worker.main()

    assert configured == {"service": "razao-worker", "log_dir": str(tmp_path)}
