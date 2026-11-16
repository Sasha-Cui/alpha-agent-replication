"""NFS-safe read-only accounting for resumed source-fidelity experiments."""

from __future__ import annotations
import errno
import fcntl
import time
from pathlib import Path
from alpha_evolve.publication_llm import CohortOpenRouter
from alpha_evolve.publication_replay import LiveCachedMeter


def retry_stale_read(operation, attempts=5):
    """Retry only reads; never replay a potentially charged network operation."""
    for attempt in range(attempts):
        try:
            return operation()
        except OSError as exc:
            if exc.errno != errno.ESTALE or attempt == attempts - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


class LockedLiveMeter(LiveCachedMeter):
    def __init__(self, root, *args, **kwargs):
        def initialize():
            with (Path(root) / "project_spend.lock").open("a+") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                super(LockedLiveMeter, self).__init__(root, *args, **kwargs)

        retry_stale_read(initialize)

    def snapshot(self):
        return retry_stale_read(lambda: CohortOpenRouter.snapshot(self))

    def request_status(self, request_hash):
        def read():
            with self.ledger() as state:
                return dict(state["calls"].get(request_hash, {}))

        return retry_stale_read(read)
