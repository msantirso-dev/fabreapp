#!/bin/sh
PORT="${APP_PORT:-${PORT:-8002}}"
exec curl -fsS "http://127.0.0.1:${PORT}/accounts/login/"
