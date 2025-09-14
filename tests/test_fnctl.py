import json
import os
import tempfile
from pathlib import Path

import fnctl.cli as cli
from fnctl.runtime import load_spec, invoke_function, write_log
from fnctl.utils import fn_dir, log_path


def run_cli(args, env=None):
    env = env or {}
    old_env = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update({k: str(v) for k, v in env.items()})
        return cli.main(args)
    finally:
        for k, v in old_env.items():
            if v is None and k in os.environ:
                del os.environ[k]
            elif v is not None:
                os.environ[k] = v


def test_create_list_invoke_python_function():
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        env = {"FNCTL_HOME": str(home)}

        # list (empty)
        rc = run_cli(["list"], env)
        assert rc == 0

        # create python function
        rc = run_cli(["create", "hello", "--lang", "python"], env)
        assert rc == 0

        # list should show it
        rc = run_cli(["list"], env)
        assert rc == 0

        # invoke via runtime API
        spec = load_spec("hello")
        base = home / "functions" / "hello"
        status, headers, body = invoke_function(
            spec,
            base,
            {"method": "GET", "path": "/fn/hello", "query": {"name": "dev"}, "headers": {}, "body": ""},
            {"function": "hello"},
        )
        assert status == 200
        assert headers.get("Content-Type") == "application/json"
        data = json.loads(body.decode())
        assert data.get("hello") == "dev"
        assert data.get("from") == "hello"


def test_destroy_removes_function_and_optional_logs():
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        env = {"FNCTL_HOME": str(home)}

        # create function
        rc = run_cli(["create", "hello", "--lang", "python"], env)
        assert rc == 0
        base = fn_dir("hello")
        assert base.exists()

        # write a log entry to simulate prior traffic
        write_log("hello", {"msg": "test"})
        lp = log_path("hello")
        assert lp.exists()

        # destroy without purging logs (logs should remain)
        rc = run_cli(["destroy", "hello"], env)
        assert rc == 0
        assert not base.exists()
        assert lp.exists()

        # recreate and destroy with --purge-logs (logs should be removed)
        rc = run_cli(["create", "hello", "--lang", "python"], env)
        assert rc == 0
        write_log("hello", {"msg": "again"})
        assert log_path("hello").exists()
        rc = run_cli(["destroy", "hello", "--purge-logs"], env)
        assert rc == 0
        assert not fn_dir("hello").exists()
        assert not log_path("hello").exists()
