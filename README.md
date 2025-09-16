# fnctl

A tiny, self-hosted functions (Lambda-like) runtime and CLI. Create small functions, run a local HTTP gateway to invoke them via `GET`, `POST`, etc., and manage per-function logs.

## Installation

### PyPI Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install fnctl.

```bash
pip install fnctl
```

### pipx (isolated CLI install)

pipx installs CLI tools into dedicated virtual environments and exposes their entry points on your PATH.

```bash
pipx upgrade fnctl
```

## Usage

### Create a function
```bash
# Check version
fnctl --version

# For more details use -h 
fnctl -h # Shows list of commands
fnctl serve -h # Show arguments for serve function

# Start the server (foreground, Ctrl+C to stop)
fnctl serve --host 127.0.0.1 --port 8080

# Or start in background (returns to shell)
fnctl serve --host 127.0.0.1 --port 8080 &

# Create a Python function
fnctl create hello --lang python

# Confirm that new function has been created
fnctl list

# Test that it can be called
curl -s http://127.0.0.1:8080/fn/hello
curl -s "http://127.0.0.1:8080/fn/hello?name=dev"

# To destroy a function
fnctl destroy hello

# Add --purge-logs to remove its logs
fnctl destroy hello --purge-logs
```

### Start/Restart without server logs

Silence all HTTP server output while keeping per‑function logs untouched.

- Start (no logs):

```bash
# With PID file
fnctl serve --quiet --host 127.0.0.1 --port 8080 >/dev/null 2>&1 & echo $! >/tmp/fnctl.pid

# Without PID file
fnctl serve --quiet --host 127.0.0.1 --port 8080 >/dev/null 2>&1 &
```

- Restart (no logs):

```bash
# With PID file
([ -f /tmp/fnctl.pid ] && kill "$(cat /tmp/fnctl.pid)" || true; \
 fnctl serve --quiet --host 127.0.0.1 --port 8080 >/dev/null 2>&1 & echo $! >/tmp/fnctl.pid)

# Without PID file
(pkill -f 'fnctl serve' || true) && fnctl serve --quiet --host 127.0.0.1 --port 8080 >/dev/null 2>&1 &
```

- Stop:

```bash
# With PID file
kill "$(cat /tmp/fnctl.pid)" || true; rm -f /tmp/fnctl.pid

# Without PID file
pkill -f 'fnctl serve' || true
```

Notes:
- `--quiet` suppresses HTTP access logs; redirection to `/dev/null` hides the startup line and any stderr.
- Function logs are separate and can be toggled per function:
  - `fnctl disable-logs <name>` / `fnctl enable-logs <name>`

### Start/Restart with server logs

If you want to see HTTP access logs in your terminal, do not use `--quiet` and do not redirect output to `/dev/null`.

- Start (with logs):

```bash
# Foreground (prints logs; Ctrl+C to stop)
fnctl serve --host 127.0.0.1 --port 8080

# Background (prints logs in current terminal session)
fnctl serve --host 127.0.0.1 --port 8080 & echo $! >/tmp/fnctl.pid

# Foreground, save logs to file (and print)
fnctl serve --host 127.0.0.1 --port 8080 2>&1 | tee -a ~/fnctl.http.log

# Background, append logs to file and save PID
fnctl serve --host 127.0.0.1 --port 8080 >>~/fnctl.http.log 2>&1 & echo $! >/tmp/fnctl.pid
```

- Restart (with logs):

```bash
# With PID file
([ -f /tmp/fnctl.pid ] && kill "$(cat /tmp/fnctl.pid)" || true; \
 fnctl serve --host 127.0.0.1 --port 8080 >>~/fnctl.http.log 2>&1 & echo $! >/tmp/fnctl.pid)

# Without PID file
(pkill -f 'fnctl serve' || true) && fnctl serve --host 127.0.0.1 --port 8080 >>~/fnctl.http.log 2>&1 &

# Follow the log
tail -f ~/fnctl.http.log
```

### Function location
```
~/.fnctl/
  functions/
    hello/
      fnctl.json         # function config
      main.py            # template with handler(event, context)
  logs/
      hello.log          # logs for hello function
```

### Edit your function

- Python handler: edit `~/.fnctl/functions/<name>/main.py` (default entrypoint is `main:handler`).
- Config: edit `~/.fnctl/functions/<name>/fnctl.json` to change `entrypoint`, enable/disable `logging`, or set `command` for exec functions.
- Reload: the server reloads the Python module automatically when the file changes; just save and curl again.

### Logging

Enable/disable per function via config or CLI: 
- `fnctl enable-logs <name>`
- `fnctl disable-logs <name>`

Inspect logs: 
- `fnctl logs <name>` or follow with `-f`

### Data directory (FNCTL_HOME)

- By default, fnctl stores data under `~/.fnctl`.
- Override per shell or process:

```bash
export FNCTL_HOME=/path/to/custom/dir
fnctl create demo
fnctl serve --quiet --host 127.0.0.1 --port 8080 &
```


## Contributing

### Local Installation

```bash
# Clone repository to local machine
git clone https://github.com/vedantm8/fnctl.git
cd fnctl

# Necessary libraries on Debian-based environment
apt-get install -y python3 python3-venv python3-pip ca-certificates curl

# Create a virtual environment
python3 -m venv /opt/fnctl-venv
. /opt/fnctl-venv/bin/activate

# Install fnctl
python -m pip install --upgrade pip
python -m pip install -e .
```

### Testing

- Run all tests with pytest:

```bash
pip3 install pytest
pytest -q
```

- Tests use a temporary `FNCTL_HOME` so they do not touch your real `~/.fnctl`.
- The suite covers creating, listing, invoking, and destroying functions (with and without purging logs).

- Show `print()` output during tests (optional):

```bash
pytest -s -q            # disable capture to see prints live
# or
pytest -q --capture=tee-sys  # show prints while also capturing
```


Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
