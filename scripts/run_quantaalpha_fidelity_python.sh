#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export LD_LIBRARY_PATH=/apps/software/2024a/software/SQLite/3.45.3-GCCcore-13.3.0/lib:/apps/software/2024a/software/Python/3.12.3-GCCcore-13.3.0/lib:/apps/software/system/software/GCCcore/13.3.0/lib64
exec /nfs/roberts/project/pi_btk22/zc362/environments/venvs/quantaalpha-replication-py312-20260814-v1/bin/python "$@"
