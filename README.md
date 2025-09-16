# fnctl

A tiny, self-hosted functions (Lambda-like) runtime and CLI. Create small functions, run a local HTTP gateway to invoke them via `GET`, `POST`, etc., and manage per-function logs.

## Installation

### PyPI Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install fnctl.

```bash
pip install fnctl
```

### Local Installation

```bash
# Clone repository to local machine
git clone https://github.com/vedantm8/fnctl.git

# Necessary libraries on Debian-based environment
apt-get install -y python3 python3-venv python3-pip ca-certificates curl

# Create a virtual environment
python3 -m venv /opt/fnctl-venv
. /opt/fnctl-venv/bin/activate

# Install fnctl
python -m pip install --upgrade pip
python -m pip install -e .
```

## Usage

### Create a function
```bash
# Check version
fnctl --version

# For more details use -h 
fnctl -h # Shows list of commands
fnctl serve -h # Show arguments for serve function

# Start the server
fnctl serve --quiet --host 127.0.0.1 --port 8080 &

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

### Function location
```
~/.fnctl/
  functions/
    hello/
      fnctl.json         # function config
      main.py            # template with handler(event, context)
  logs/
```

### Logging

Enable/disable per function via config or CLI: 
- `fnctl enable-logs <name>`
- `fnctl disable-logs <name>`

Inspect logs: 
- `fnctl logs <name>` or follow with `-f`


## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)