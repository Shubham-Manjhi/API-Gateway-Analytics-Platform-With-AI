#!/usr/bin/env bash
# Run once after cloning to generate the Gradle wrapper
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v gradle &>/dev/null; then
    echo "Generating Gradle wrapper..."
    gradle wrapper --gradle-version 8.7
    echo "Done. You can now use ./gradlew"
else
    echo "ERROR: 'gradle' not found. Install Gradle 8.x first."
    echo "  macOS: brew install gradle"
    exit 1
fi
