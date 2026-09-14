def test_worker_loop_cleans_storage_and_waits_when_queue_is_idle():
    from scripts.razao_worker import run_worker_loop

    calls = []

    class Worker:
        def run_once(self):
            calls.append("run")
            return False

    class Storage:
        def cleanup(self):
            calls.append("cleanup")

    class StopAfterWait:
        def __init__(self):
            self.stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, seconds):
            calls.append(("wait", seconds))
            self.stopped = True
            return True

    run_worker_loop(Worker(), Storage(), poll_seconds=3, stop_event=StopAfterWait())

    assert calls == ["run", "cleanup", ("wait", 3)]
