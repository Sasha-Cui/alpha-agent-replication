#!/usr/bin/env bash
set -eo pipefail

# Isolate the v0.1.0 audit environment from whichever Bouchet module stack
# invoked the paper audit. The EasyBuild Python executable needs its libpython,
# and Chroma needs the Python module's SQLite >= 3.35 rather than system SQLite.
export PATH="/apps/software/2022b/software/Python/3.10.8-GCCcore-12.2.0/bin:/usr/bin:/bin"
export LD_LIBRARY_PATH="/apps/software/2022b/software/SQLite/3.39.4-GCCcore-12.2.0/lib:/apps/software/2022b/software/Python/3.10.8-GCCcore-12.2.0/lib"
unset PYTHONPATH

exec /nfs/roberts/project/pi_btk22/zc362/environments/current/tradingagents-v010/bin/python "$@"
