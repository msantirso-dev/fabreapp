#!/bin/sh
# Coolify inyecta PORT (suele ser 3000). El healthcheck DEBE usar el mismo.
PORT="${PORT:-8000}"
exec curl -fsS "http://127.0.0.1:${PORT}/accounts/login/"
