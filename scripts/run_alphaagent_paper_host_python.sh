#!/usr/bin/env bash
set -eo pipefail

# Isolate the paper-era RD-Agent host from whichever Bouchet module stack
# invoked the audit. The EasyBuild interpreter needs its matching libpython and
# SQLite libraries; the central alias points at the immutable versioned env.
export PATH="/apps/software/2022b/software/Python/3.10.8-GCCcore-12.2.0/bin:/usr/bin:/bin"
export LD_LIBRARY_PATH="/apps/software/2022b/software/Python/3.10.8-GCCcore-12.2.0/lib:/apps/software/system/software/OpenSSL/1.1/lib64:/apps/software/2022b/software/libffi/3.4.4-GCCcore-12.2.0/lib64:/apps/software/2022b/software/GMP/6.2.1-GCCcore-12.2.0/lib:/apps/software/2022b/software/XZ/5.2.7-GCCcore-12.2.0/lib:/apps/software/2022b/software/SQLite/3.39.4-GCCcore-12.2.0/lib:/apps/software/2022b/software/Tcl/8.6.12-GCCcore-12.2.0/lib:/apps/software/2022b/software/libreadline/8.2-GCCcore-12.2.0/lib:/apps/software/2022b/software/ncurses/6.3-GCCcore-12.2.0/lib:/apps/software/2022b/software/bzip2/1.0.8-GCCcore-12.2.0/lib:/apps/software/2022b/software/binutils/2.39-GCCcore-12.2.0/lib:/apps/software/2022b/software/zlib/1.2.12-GCCcore-12.2.0/lib:/apps/software/system/software/GCCcore/12.2.0/lib64"
unset PYTHONPATH

exec /nfs/roberts/project/pi_btk22/zc362/environments/current/alphaagent-paper-era-host/bin/python "$@"
