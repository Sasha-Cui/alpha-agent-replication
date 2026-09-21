#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export TIKTOKEN_CACHE_DIR=/nfs/roberts/project/pi_btk22/zc362/environments/caches/alpha-economic-fidelity/tiktoken
root=/nfs/roberts/project/pi_btk22/zc362/alpha_evolve
python_path=/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-fidelity-finmem-py310-20260907-v1/bin/python
exec "$root/scripts/run_finagent_paper_python.sh" -c 'import os,sys; os.environ["PYTHONPATH"]="/nfs/roberts/project/pi_btk22/zc362/alpha_evolve/src"; os.execv(sys.argv[1],sys.argv[1:])' "$python_path" "$@"
