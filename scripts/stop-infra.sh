#!/usr/bin/env bash
# Stop all infrastructure services
set -euo pipefail

cd "$(dirname "$0")/../docker"
docker compose down

echo "Infrastructure stopped."
