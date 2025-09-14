# fnctl

A tiny, self-hosted functions (Lambda-like) runtime and CLI. Create small functions, run a local HTTP gateway to invoke them via `GET`, `POST`, etc., and manage per-function logs.

No heavy dependencies; built on Python standard library. Designed to support Python first and be easily extended to other languages via an `exec` interface.

## Features

- Create, destroy, and list functions: `fnctl create|destroy|list`
- Run HTTP server: `fnctl serve` (routes at `/fn/<name>`)
- Optional per-function logging with `fnctl logs <name> [-f]`
- Toggle logs per function: `fnctl enable-logs <name>` / `fnctl disable-logs <name>`
- Python runtime (module file + handler), plus generic `exec` runtime (JSON over stdin/stdout)
- Minimal and extensible design; no external deps

## Quickstart

- Start the server:

```bash
fnctl serve --host 127.0.0.1 --port 8080
```

- Create a Python function:

```bash
fnctl create hello --lang python
```

This scaffolds:

```
~/.fnctl/
  functions/
    hello/
      fnctl.json         # function config
      main.py            # template with handler(event, context)
  logs/
```

- Invoke it:

```bash
curl -s http://127.0.0.1:8080/fn/hello
curl -s "http://127.0.0.1:8080/fn/hello?name=dev"
```

- List functions:

```bash
fnctl list
```

- Destroy a function:

```bash
fnctl destroy hello
# Add --purge-logs to remove its logs
```

## Request/Response Contract

- Request event passed to handler:
  - `method`: HTTP method
  - `path`: URL path
  - `query`: dict of query params
  - `headers`: dict of request headers
  - `body`: request body (string)
- Handler return options:
  - Lambda-style `{"statusCode": int, "headers": {..}, "body": any}`
  - Any JSON-serializable object (returned as JSON)
  - String (returned as `text/plain`)

## Runtimes

- Python: set `entrypoint` like `"main:handler"`. The file sits next to the config file.
- Exec: set `command` to a shell command. The command receives a single JSON object on stdin: `{ "event": ..., "context": ... }` and should print JSON to stdout in the same Lambda-style shape.

Example `exec` template (created by `fnctl create <name> --lang exec`): `handler.sh`.

## Logging

- Enable/disable per function via config or CLI:
  - `fnctl enable-logs <name>`
  - `fnctl disable-logs <name>`
- Inspect logs:
  - `fnctl logs <name>` or follow with `-f`
- Logs are JSON lines at `~/.fnctl/logs/<name>.log` (or `/var/lib/fnctl/logs` when using the system service).

## System Service (optional)

A systemd unit is included. After installing the Debian package:

```bash
sudo systemctl enable --now fnctl.service
# default: listens on 0.0.0.0:8080 and stores data in /var/lib/fnctl
```

The service runs under a dedicated `fnctl` user (created by the package).
The installed package sets a system default at `/etc/fnctl/config.json` and
adds `/etc/profile.d/fnctl.sh`, so `fnctl` commands default to `/var/lib/fnctl`.

Tip: When running locally without installing, you can override the data dir with `FNCTL_HOME`:

```bash
FNCTL_HOME=$(pwd)/.fnctl-local fnctl serve
```

## Packaging (Debian/Ubuntu)

This repo includes Debian packaging under `debian/`. Build the `.deb` locally:

```bash
# Install build tools once:
sudo apt update && sudo apt install -y build-essential debhelper dh-python python3 python3-setuptools python3-pytest

# Build the package (runs tests via pytest)
dpkg-buildpackage -us -uc -b

# Install the resulting .deb from the parent directory
sudo apt install ./fnctl_0.1.0_all.deb
```

- To skip tests during build, set `DEB_BUILD_OPTIONS=nocheck`.

## Testing

- Run all tests with pytest:

```bash
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

- During Debian package build, you can surface prints in the build log by overriding the test args:

```bash
PYBUILD_TEST_ARGS="pytest -s -q" dpkg-buildpackage -us -uc -b
```

### Hosting an APT repository (so users can `apt install fnctl`)

To allow `apt install fnctl` directly, host a signed APT repo and publish releases.
One simple approach is GitHub Pages + `reprepro` or `aptly` in CI.

High-level steps:

1. Create a GPG key for signing packages and export the public key.
2. Use `reprepro` to create a repo structure and include your built `.deb`.
3. Upload the repo to GitHub Pages (or any static host supporting HTTPS).
4. Document adding your repo:

```bash
curl -fsSL https://YOUR_DOMAIN/apt/pubkey.gpg | sudo gpg --dearmor -o /usr/share/keyrings/fnctl.gpg
echo "deb [signed-by=/usr/share/keyrings/fnctl.gpg] https://YOUR_DOMAIN/apt stable main" | sudo tee /etc/apt/sources.list.d/fnctl.list
sudo apt update
sudo apt install fnctl
```

You can automate building and publishing from GitHub Actions by:
- Building the `.deb`
- Running `reprepro` to add it into the repo
- Pushing to a dedicated `gh-pages` branch

> Note: `apt install fnctl` works once your repo is added to the system’s APT sources. Without adding your custom repo, it won’t be in the default Ubuntu/Debian archives.

## GitHub Package Page: What to Document

Include the following in the GitHub package/release page:

- What it is: self-hosted function runtime and CLI.
- Installation:
  - Add APT repository + GPG key instructions
  - `apt install fnctl`
  - Optional: how to run as systemd service
- Quickstart usage: `fnctl create`, `fnctl list`, `fnctl destroy`, `fnctl serve`, `fnctl logs`
- HTTP contract: structure of `event`, accepted handler returns
- Logging: how to enable/disable, where logs are stored
- Extending languages: describe `exec` runtime contract (stdin JSON, stdout JSON)
- Security notes: functions run locally; review exec commands; network exposure
- Versioning: semantic version; changelog highlights

## Directory Layout

- Python package: `fnctl/` containing CLI, server, runtime, templates
- Debian packaging: `debian/`
- Systemd unit: `debian/fnctl.service`

## Roadmap / Extensibility

- Add websockets/events
- Pluggable auth/middleware for the gateway
- Concurrency and scaling options
- Language shims (Node.js, Go) via `exec` wrapper

## LXC Quick Test

On a clean Ubuntu container (22.04):

```bash
lxc launch ubuntu:22.04 fnctl-test
tar czf /tmp/fnctl-src.tgz .
lxc file push /tmp/fnctl-src.tgz fnctl-test/root/
lxc exec fnctl-test -- bash -lc 'cd /root && tar xzf fnctl-src.tgz && cd fnctl'
lxc exec fnctl-test -- bash -lc 'apt-get update && apt-get install -y build-essential debhelper dh-python python3 python3-setuptools python3-pytest'
lxc exec fnctl-test -- bash -lc 'cd /root/fnctl && dpkg-buildpackage -us -uc -b'
lxc exec fnctl-test -- bash -lc 'apt-get install -y /root/fnctl_0.1.0_all.deb'
lxc exec fnctl-test -- bash -lc 'sudo -u fnctl FNCTL_HOME=/var/lib/fnctl fnctl create hello'
lxc exec fnctl-test -- systemctl enable --now fnctl.service
lxc exec fnctl-test -- curl -s http://127.0.0.1:8080/fn/hello
```

## License

MIT — see `LICENSE`.
