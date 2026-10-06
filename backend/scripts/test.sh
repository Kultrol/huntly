#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

# Use a separate project and a fresh test database to protect development data.
exec docker compose -p huntly-tests --profile test up \
    --build --force-recreate --always-recreate-deps \
    --exit-code-from backend_test --no-attach db_test backend_test db_test
