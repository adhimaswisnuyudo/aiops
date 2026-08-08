#!/bin/bash
# AIOps Agent Docker Entrypoint
# Auto-copy template config jika config.yaml belum ada (first run / fresh clone)

set -e

CONFIG_FILE="/app/config.yaml"
CONFIG_TEMPLATE="/app/config.example.yaml"

if [ ! -f "$CONFIG_FILE" ] && [ -f "$CONFIG_TEMPLATE" ]; then
    echo "[entrypoint] config.yaml not found, copying from config.example.yaml..."
    cp "$CONFIG_TEMPLATE" "$CONFIG_FILE"
    echo "[entrypoint] Done. Edit config.yaml to add your servers."
fi

exec "$@"