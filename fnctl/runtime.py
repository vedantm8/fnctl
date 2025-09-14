import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from .utils import fn_config_path, read_json, log_path


@dataclass
class FunctionSpec:
    name: str
    language: str  # "python" or "exec"
    entrypoint: Optional[str] = None  # e.g., "main:handler" for python
    command: Optional[str] = None     # e.g., "/usr/local/bin/myfn"
    logging: bool = True


_PY_CACHE_LOCK = threading.Lock()
_PY_MODULE_CACHE: Dict[str, Tuple[float, Callable]] = {}


def load_spec(name: str) -> FunctionSpec:
    cfg = read_json(fn_config_path(name))
    return FunctionSpec(
        name=cfg["name"],
        language=cfg.get("language", "python"),
        entrypoint=cfg.get("entrypoint"),
        command=cfg.get("command"),
        logging=bool(cfg.get("logging", True)),
    )


def _import_python_handler(base: Path, entrypoint: str) -> Callable:
    module_file, _, func_name = entrypoint.partition(":")
    if not func_name:
        raise RuntimeError("Invalid entrypoint; expected 'module.py:handler'")
    file_path = base / module_file
    mtime = file_path.stat().st_mtime
    cache_key = str(file_path)
    with _PY_CACHE_LOCK:
        cached = _PY_MODULE_CACHE.get(cache_key)
        if cached and cached[0] == mtime:
            return cached[1]
        # load fresh
        spec = importlib.util.spec_from_file_location(f"fnctl_{hash(cache_key)}", str(file_path))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load module from {file_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)  # type: ignore
        handler = getattr(mod, func_name)
        _PY_MODULE_CACHE[cache_key] = (mtime, handler)
        return handler


def invoke_function(spec: FunctionSpec, base_dir: Path, event: Dict[str, Any], context: Dict[str, Any]) -> Tuple[int, Dict[str, str], bytes]:
    if spec.language == "python":
        if not spec.entrypoint:
            raise RuntimeError("Python function missing entrypoint")
        handler = _import_python_handler(base_dir, spec.entrypoint)
        result = handler(event, context)
        return normalize_result(result)
    elif spec.language == "exec":
        if not spec.command:
            raise RuntimeError("Exec function missing command")
        proc = subprocess.Popen(
            spec.command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(base_dir),
            text=True,
        )
        input_str = json.dumps({"event": event, "context": context})
        stdout, stderr = proc.communicate(input=input_str, timeout=120)
        if proc.returncode != 0:
            return 500, {"Content-Type": "text/plain"}, f"Error: {stderr}".encode()
        try:
            parsed = json.loads(stdout)
        except Exception:
            # treat stdout as the body
            parsed = {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": stdout}
        return normalize_result(parsed)
    else:
        raise RuntimeError(f"Unsupported language: {spec.language}")


def normalize_result(result: Any) -> Tuple[int, Dict[str, str], bytes]:
    # Accept Lambda-like dict {statusCode, headers, body}, or plain dict, or string/bytes
    if isinstance(result, tuple) and len(result) == 3:
        status, headers, body = result
        if isinstance(body, str):
            body = body.encode()
        return int(status), dict(headers or {}), body
    if isinstance(result, dict):
        if "statusCode" in result:
            status = int(result.get("statusCode", 200))
            headers = result.get("headers", {}) or {}
            body = result.get("body", b"")
            if isinstance(body, (dict, list)):
                headers = {**{"Content-Type": "application/json"}, **headers}
                body = json.dumps(body)
            if isinstance(body, str):
                body = body.encode()
            return status, dict(headers), body
        else:
            body = json.dumps(result).encode()
            return 200, {"Content-Type": "application/json"}, body
    if isinstance(result, (bytes, bytearray)):
        return 200, {"Content-Type": "application/octet-stream"}, bytes(result)
    if isinstance(result, str):
        return 200, {"Content-Type": "text/plain"}, result.encode()
    return 200, {"Content-Type": "text/plain"}, str(result).encode()


def write_log(name: str, record: Dict[str, Any]) -> None:
    path = log_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True))
        f.write("\n")

