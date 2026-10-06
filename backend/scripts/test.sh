#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

# A separate Compose project keeps this run independent of development services.
# Recreating the tmpfs database gives every run a fresh migration/test database.
exec docker compose -p huntly-tests --profile test up \
    --build --force-recreate --always-recreate-deps \
    --exit-code-from backend_test --no-attach db_test backend_test db_test
