#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export TIKTOKEN_CACHE_DIR=/nfs/roberts/project/pi_btk22/zc362/environments/caches/alpha-economic-fidelity/tiktoken
root=/nfs/roberts/project/pi_btk22/zc362/alpha_evolve
runtime=/nfs/roberts/project/pi_btk22/zc362/environments/venvs/quantaalpha-fidelity-py310-20260916-v1/bin/python
exec "$root/scripts/run_alphaagent_paper_host_python.sh" -c 'import os,sys;os.execv(sys.argv[1],sys.argv[1:])' "$runtime" "$@"
