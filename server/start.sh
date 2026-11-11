#!/bin/bash
cd /www/wwwroot/fast-admin || exit 1
export PATH="/root/.local/bin:/usr/local/bin:$PATH"
# 把下面路径改成 which uv 的结果
exec /root/.local/bin/uv run main.py run --env=dev