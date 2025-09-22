import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

from . import __version__
from .server import serve as run_server
from .utils import ensure_dirs, functions_dir, fn_dir, fn_config_path, read_json, write_json, logs_dir, log_path


PY_TEMPLATE_REL = Path("templates/python/main.py")


def cmd_create(args: argparse.Namespace) -> int:
    ensure_dirs()
    name: str = args.name
    lang: str = args.lang
    base = fn_dir(name)
    if base.exists():
        print(f"Function '{name}' already exists at {base}", file=sys.stderr)
        return 2
    base.mkdir(parents=True, exist_ok=False)

    cfg = {
        "name": name,
        "language": lang,
        "logging": (not args.no_logs),
    }
    if lang == "python":
        cfg["entrypoint"] = "main:handler"
        # copy template
        tpl_path = Path(__file__).parent / PY_TEMPLATE_REL
        shutil.copy2(tpl_path, base / "main.py")
    elif lang == "exec":
        cfg["command"] = args.command or "./handler.sh"
        # create a simple shell template
        sh = base / "handler.sh"
        sh.write_text("""#!/usr/bin/env bash
set -euo pipefail
# Read JSON from stdin and echo a JSON response
read INPUT
echo '{"statusCode":200, "headers":{"Content-Type":"text/plain"}, "body":"hello from exec"}'
""", encoding="utf-8")
        sh.chmod(0o755)
    else:
        print(f"Unsupported language: {lang}", file=sys.stderr)
        return 2

    write_json(fn_config_path(name), cfg)
    print(f"Created function '{name}' in {base}")
    print("Try it: start the server and curl it:")
    print("  fnctl serve &")
    print(f"  curl -s http://127.0.0.1:8080/fn/{name} | jq . || curl -s http://127.0.0.1:8080/fn/{name}")
    return 0


def cmd_destroy(args: argparse.Namespace) -> int:
    name: str = args.name
    base = fn_dir(name)
    if not base.exists():
        print(f"Function '{name}' does not exist", file=sys.stderr)
        return 2
    shutil.rmtree(base)
    # keep logs unless --purge-logs
    if args.purge_logs:
        lp = log_path(name)
        if lp.exists():
            lp.unlink()
    print(f"Destroyed function '{name}'")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    ensure_dirs()
    base = functions_dir()
    rows = []
    for p in sorted(base.glob("*")):
        if not p.is_dir():
            continue
        cfg_path = p / "fnctl.json"
        if not cfg_path.exists():
            continue
        cfg = read_json(cfg_path)
        rows.append((cfg.get("name", p.name), cfg.get("language", "?"), bool(cfg.get("logging", True))))
    if not rows:
        print("No functions found. Create one with: fnctl create <name>")
        return 0
    rows = [(name, lang, "true" if logging else "false") for name, lang, logging in rows]
    headers = ("NAME", "LANG", "LOGGING")
    widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(len(headers))]
    def fmt_row(row) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print(fmt_row(headers))
    for row in rows:
        print(fmt_row(row))
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    name: str = args.name
    lp = log_path(name)
    if not lp.exists():
        print(f"No logs for '{name}' yet at {lp}")
        return 0
    if not args.follow:
        print(lp.read_text(encoding="utf-8"))
        return 0
    # tail -f
    with lp.open("r", encoding="utf-8") as f:
        # go to end
        f.seek(0, os.SEEK_END)
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                print(line, end="")
        except KeyboardInterrupt:
            return 0


def cmd_enable_logs(args: argparse.Namespace) -> int:
    name: str = args.name
    cfgp = fn_config_path(name)
    if not cfgp.exists():
        print(f"Function '{name}' does not exist", file=sys.stderr)
        return 2
    cfg = read_json(cfgp)
    cfg["logging"] = True
    write_json(cfgp, cfg)
    print(f"Enabled logging for '{name}'")
    return 0


def cmd_disable_logs(args: argparse.Namespace) -> int:
    name: str = args.name
    cfgp = fn_config_path(name)
    if not cfgp.exists():
        print(f"Function '{name}' does not exist", file=sys.stderr)
        return 2
    cfg = read_json(cfgp)
    cfg["logging"] = False
    write_json(cfgp, cfg)
    print(f"Disabled logging for '{name}'")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    host = args.host
    port = args.port
    run_server(host=host, port=port, quiet=getattr(args, "quiet", False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fnctl", description="Self-hosted function runtime and CLI")
    p.add_argument("--version", action="version", version=f"fnctl {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="Create a new function")
    c.add_argument("name")
    c.add_argument("--lang", choices=["python", "exec"], default="python")
    c.add_argument("--command", help="For exec: command to run", default=None)
    c.add_argument("--no-logs", action="store_true", help="Disable logging for this function")
    c.set_defaults(func=cmd_create)

    d = sub.add_parser("destroy", help="Destroy a function")
    d.add_argument("name")
    d.add_argument("--purge-logs", action="store_true", help="Also remove logs for this function")
    d.set_defaults(func=cmd_destroy)

    l = sub.add_parser("list", help="List functions")
    l.set_defaults(func=cmd_list)

    s = sub.add_parser("serve", help="Run the HTTP server")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--quiet", action="store_true", help="Suppress HTTP access logs")
    s.set_defaults(func=cmd_serve)

    g = sub.add_parser("logs", help="Show or follow function logs")
    g.add_argument("name")
    g.add_argument("-f", "--follow", action="store_true")
    g.set_defaults(func=cmd_logs)

    el = sub.add_parser("enable-logs", help="Enable logging for a function")
    el.add_argument("name")
    el.set_defaults(func=cmd_enable_logs)

    dl = sub.add_parser("disable-logs", help="Disable logging for a function")
    dl.add_argument("name")
    dl.set_defaults(func=cmd_disable_logs)

    return p


def main(argv: Optional[list] = None) -> int:
    ensure_dirs()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
