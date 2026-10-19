#!/usr/bin/env bash
# 结束占用端口的进程。用法：
#   bash stop.sh              # 默认 8181
#   bash stop.sh 8181 5730    # 一次多个端口

set -euo pipefail

ports=("$@")
if [[ ${#ports[@]} -eq 0 ]]; then
  ports=(8181)
fi

pids_for_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
    return
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "${port}/tcp" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' || true
    return
  fi
  # Windows Git Bash / MSYS
  netstat -ano 2>/dev/null | grep -E "[:.]${port}[[:space:]]" | grep -i LISTEN | awk '{print $NF}' | grep -E '^[0-9]+$' | grep -v '^0$' | sort -u || true
}

kill_pids() {
  local pid
  for pid in "$@"; do
    [[ -z "$pid" || "$pid" == "0" ]] && continue
    if command -v taskkill >/dev/null 2>&1; then
      cmd.exe /c "taskkill /PID ${pid} /F" >/dev/null 2>&1 && echo "killed PID $pid" || true
    else
      kill -9 "$pid" 2>/dev/null && echo "killed PID $pid" || true
    fi
  done
}

for port in "${ports[@]}"; do
  mapfile -t pids < <(pids_for_port "$port" | sort -u)
  if [[ ${#pids[@]} -eq 0 || -z "${pids[0]:-}" ]]; then
    echo "idle :$port"
    continue
  fi
  echo "port :$port -> ${pids[*]}"
  kill_pids "${pids[@]}"
done
