#!/usr/bin/env bash
set -euo pipefail

# Build and upload to PyPI or TestPyPI using Twine.
# Credentials are read by Twine from one of:
# - Environment: TWINE_USERNAME=__token__, TWINE_PASSWORD=pypi-...
# - ~/.pypirc (see .pypirc.example in this repo)
# - System keyring (if configured)
#
# Usage:
#   scripts/publish.sh            # upload to PyPI (prod)
#   scripts/publish.sh prod       # upload to PyPI (prod)
#   scripts/publish.sh test       # upload to TestPyPI

repo_arg="pypi"
if [[ "${1:-}" =~ ^(test|testpypi)$ ]]; then
  repo_arg="testpypi"
elif [[ "${1:-}" =~ ^(prod|pypi|)$ ]]; then
  repo_arg="pypi"
else
  echo "Usage: $0 [test|prod]" >&2
  exit 2
fi

echo "Publishing to: ${repo_arg}" >&2

rm -rf dist build *.egg-info
python3 -m pip install --upgrade build twine
python3 -m build
python3 -m twine check dist/*

python3 -m twine upload --repository "${repo_arg}" dist/*

echo "Done. Verify the release page:" >&2
if [[ "$repo_arg" == "testpypi" ]]; then
  echo "  https://test.pypi.org/project/fnctl/" >&2
else
  echo "  https://pypi.org/project/fnctl/" >&2
fi

