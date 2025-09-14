import json
import os
from pathlib import Path


FNCTL_HOME_ENV = "FNCTL_HOME"
SYSTEM_CONFIG_PATH = Path("/etc/fnctl/config.json")


def get_home() -> Path:
    # 1) explicit environment wins
    home = os.environ.get(FNCTL_HOME_ENV)
    if home:
        return Path(home).expanduser()
    # 2) system-wide config (installed package path)
    try:
        if SYSTEM_CONFIG_PATH.exists():
            cfg = read_json(SYSTEM_CONFIG_PATH)
            sys_home = cfg.get("home")
            if sys_home:
                return Path(str(sys_home)).expanduser()
    except Exception:
        # fall through to per-user default if config unreadable
        pass
    # 3) per-user default
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
