import json
import os
from pathlib import Path


FNCTL_HOME_ENV = "FNCTL_HOME"


def get_home() -> Path:
    home = os.environ.get(FNCTL_HOME_ENV)
    if home:
        return Path(home).expanduser()
    return Path.home() / ".fnctl"


def functions_dir() -> Path:
    return get_home() / "functions"


def logs_dir() -> Path:
    return get_home() / "logs"


def ensure_dirs() -> None:
    functions_dir().mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)


def fn_dir(name: str) -> Path:
    return functions_dir() / name


def fn_config_path(name: str) -> Path:
    return fn_dir(name) / "fnctl.json"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def log_path(name: str) -> Path:
    return logs_dir() / f"{name}.log"

