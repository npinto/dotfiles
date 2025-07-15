#!/usr/bin/env bash
# benchmark_shell.sh — precise start‑up profiler + optional syscall stats

# Disable inherited xtrace unless BASH_DEBUG is set
[[ -n "${BASH_DEBUG:-}" ]] || { set +o xtrace 2>/dev/null || true; }

set -euo pipefail

SHELL_BIN="${1:-${SHELL:-/bin/bash}}"
SH_NAME=$(basename "$SHELL_BIN")

# -------- timer (ms resolution, safe argv list) ------------------------------
timer_ms() { python3 - "$@" <<'PY'
import sys, subprocess, time
t0 = time.perf_counter_ns()
subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print((time.perf_counter_ns() - t0)//1_000_000)
PY
}

pretty() { (( $1 < 1000 )) && printf "%d.%03d ms\n" $1 0 \
                           || printf "%d.%03d s\n"  $(($1/1000)) $(($1%1000)); }

run() { printf "%-35s" "$1"; shift; pretty "$(timer_ms "$@")"; }

echo "Benchmarking: $SHELL_BIN"; echo

case "$SH_NAME" in
  bash) run "bash --noprofile --norc" "$SHELL_BIN" --noprofile --norc -c exit
        run "bash -lic exit"          "$SHELL_BIN" -lic exit
        INT_CMD=("$SHELL_BIN" -lic exit) ;;
  zsh)  run "zsh -f -c exit"          "$SHELL_BIN" -f -c exit
        run "zsh -i -c exit"          "$SHELL_BIN" -i -c exit
        INT_CMD=("$SHELL_BIN" -i -c exit) ;;
  *)    run "$SH_NAME non‑login"      "$SHELL_BIN" -c exit
        run "$SH_NAME interactive"    "$SHELL_BIN" -i -c exit
        INT_CMD=("$SHELL_BIN" -i -c exit) ;;
esac

# -------- Bash slow‑line trace ----------------------------------------------
if [[ "$SH_NAME" == "bash" ]]; then
  TRACE=$(mktemp /tmp/bash_trace.XXXX)
  PS4='+${EPOCHREALTIME}\t'
  "$SHELL_BIN" -lic 'set -x; exit' 2>"$TRACE"
  echo; echo "Top 20 slowest Bash lines (Δt ms):"
  awk -F'\t' '/^[+0-9]/{ts=substr($1,2);if(NR>1){dt=(ts-p)*1000;if(dt)printf "%.3f ms\t%s\n",dt,$2}p=ts}' "$TRACE" |
    sort -nr | head -20
  echo "Full trace → $TRACE"
fi

# -------- Syscall summary (Linux: strace, macOS: sudo dtruss) ---------------
case "$(uname)" in
  Linux) command -v strace >/dev/null && { echo; strace -qq -c -f "${INT_CMD[@]}"; } ;;
  Darwin) if [[ -x /usr/bin/dtruss ]]; then
            echo; echo "Syscall time (sudo, Ctrl‑C to stop)…"
            sudo /usr/bin/dtruss -q "${INT_CMD[@]}" 2>&1 | awk '
              /^[a-z]/ {sum[$NF]+=$1} END{for(k in sum) printf "%-20s %.3f s\n",k,sum[k]/1e6}' |
              sort -k2 -nr | head -15
          fi ;;
esac

