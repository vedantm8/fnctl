import json
import os
import tempfile
from pathlib import Path
from contextlib import contextmanager

import fnctl.cli as cli
from fnctl.runtime import load_spec, invoke_function, write_log
from fnctl.utils import fn_dir, log_path


def run_cli(args):
    print(f"[fnctl CLI] $ fnctl {' '.join(args)}")
    rc = cli.main(args)
    print(f"[fnctl CLI] exit code: {rc}\n")
    return rc


@contextmanager
def set_env(env: dict):
    old = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update({k: str(v) for k, v in env.items()})
        for k, v in env.items():
            print(f"[env] {k}={v}")
        yield
    finally:
        for k, v in old.items():
            if v is None and k in os.environ:
                del os.environ[k]
            elif v is not None:
                os.environ[k] = v


def test_create_list_invoke_python_function():
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        with set_env({"FNCTL_HOME": str(home)}):
            print(f"[setup] temp FNCTL_HOME: {home}")

            # list (empty)
            rc = run_cli(["list"])
            assert rc == 0

            # create python function
            rc = run_cli(["create", "hello", "--lang", "python"])
            assert rc == 0
            print(f"[create] created function at {home / 'functions' / 'hello'}")

            # list should show it
            rc = run_cli(["list"])
            assert rc == 0

            # invoke via runtime API
            spec = load_spec("hello")
            base = home / "functions" / "hello"
            print(f"[invoke] base_dir={base}, entrypoint={spec.entrypoint}")
            status, headers, body = invoke_function(
                spec,
                base,
                {"method": "GET", "path": "/fn/hello", "query": {"name": "dev"}, "headers": {}, "body": ""},
                {"function": "hello"},
            )
            print(f"[invoke] status={status}, headers={headers}")
            print(f"[invoke] body={body.decode(errors='ignore')}")
            assert status == 200
            assert headers.get("Content-Type") == "application/json"
            data = json.loads(body.decode())
            assert data.get("hello") == "dev"
            assert data.get("from") == "hello"


def test_destroy_removes_function_and_optional_logs():
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        with set_env({"FNCTL_HOME": str(home)}):
            print(f"[setup] temp FNCTL_HOME: {home}")
            # create function
            rc = run_cli(["create", "hello", "--lang", "python"])
            assert rc == 0
            base = fn_dir("hello")
            print(f"[create] created: {base}")
            assert base.exists()

            # write a log entry to simulate prior traffic
            write_log("hello", {"msg": "test"})
            lp = log_path("hello")
            print(f"[logs] wrote log: {lp}")
            assert lp.exists()

            # destroy without purging logs (logs should remain)
            rc = run_cli(["destroy", "hello"])
            assert rc == 0
            assert not base.exists()
            print(f"[destroy] function removed, logs kept: exists={lp.exists()}")
            assert lp.exists()

            # recreate and destroy with --purge-logs (logs should be removed)
            rc = run_cli(["create", "hello", "--lang", "python"])
            assert rc == 0
            write_log("hello", {"msg": "again"})
            assert log_path("hello").exists()
            rc = run_cli(["destroy", "hello", "--purge-logs"])
            assert rc == 0
            assert not fn_dir("hello").exists()
            print(f"[destroy --purge-logs] logs removed: exists={log_path('hello').exists()}")
            assert not log_path("hello").exists()
